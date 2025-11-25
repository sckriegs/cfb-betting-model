import streamlit as st
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
import sys
import os
import xgboost as xgb
from datetime import datetime
import requests

# Add project root to path so we can import from src
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.data.persist import get_data_dir
from src.betting.market import american_to_prob
from src.data.cfbd_client import CFBDClient
from src.viz.reports import get_ats_pick, get_ml_pick, get_total_pick

from src.data.team_mapping import to_canonical

# --- CONFIG ---
st.set_page_config(
    page_title="CFB Model Dashboard",
    page_icon="🏈",
    layout="wide"
)

def get_api_key():
    """Get API key from streamlit secrets or environment."""
    try:
        return st.secrets["CFBD_API_KEY"]
    except (FileNotFoundError, KeyError):
        return os.getenv("CFBD_API_KEY")

# --- HELPER FUNCTIONS ---
@st.cache_data
def load_team_info():
    """Load team info (logos, colors) from CFBD."""
    data_dir = get_data_dir()
    cache_path = data_dir / "raw" / "teams.parquet"
    
    # If exists, verify it has the required columns (e.g. 'conference')
    # If not, force refresh.
    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        if "conference" in df.columns:
            return df
        # else fall through to re-fetch
    
    try:
        client = CFBDClient(api_key=get_api_key())
        teams_df = client.get_teams()
        if not teams_df.empty:
            # Save relevant columns
            cols = ["id", "school", "mascot", "abbreviation", "conference", "color", "alt_color", "logos"]
            # specific handling for logos (list of strings)
            teams_df["logo"] = teams_df["logos"].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
            
            # Keep only what we need
            final_df = teams_df[["id", "school", "mascot", "conference", "color", "logo"]]
            
            # Ensure directory exists
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            final_df.to_parquet(cache_path)
            return final_df
    except Exception as e:
        st.error(f"Error loading team info: {e}")
        return None

@st.cache_data
def load_rankings(season, week):
    """Load AP Top 25 rankings for a given week. Returns list and dict."""
    try:
        client = CFBDClient(api_key=get_api_key())
        # Fetch rankings
        # Note: get_rankings returns a DataFrame where 'polls' column contains the list of polls
        rankings_df = client.get_rankings(season=season, week=week)
        
        if rankings_df.empty:
            return [], {}
            
        # Get the polls list from the first row (should be only one row for specific week)
        polls_list = rankings_df.iloc[0]['polls']
            
        # Find AP Poll
        ap_poll = next((p for p in polls_list if p['poll'] == 'AP Top 25'), None)
        
        if ap_poll:
            # Return list of schools in Top 25
            top_25_list = [r['school'] for r in ap_poll.get('ranks', [])]
            # Return dict map {School: Rank}
            top_25_map = {r['school']: r['rank'] for r in ap_poll.get('ranks', [])}
            return top_25_list, top_25_map
            
        return [], {}
    except Exception as e:
        # Fail silently on rankings, not critical
        # st.error(f"Debug: Ranking Error: {e}") # Uncomment for debug if needed
        return [], {}

@st.cache_data
def load_features(season):
    data_dir = get_data_dir()
    path = data_dir / "features" / f"{season}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None

@st.cache_resource
def load_models(season):
    data_dir = get_data_dir()
    models_dir = data_dir / "models"
    
    # Try to find models for this season or closest previous
    for year in range(season, 2014, -1):
        ats_path = models_dir / "ats" / f"{year}.pkl"
        if ats_path.exists():
            with open(ats_path, "rb") as f:
                ats_model = pickle.load(f)
            with open(models_dir / "ml" / f"{year}.pkl", "rb") as f:
                ml_model = pickle.load(f)
            with open(models_dir / "total" / f"{year}.pkl", "rb") as f:
                total_model = pickle.load(f)
            return ats_model, ml_model, total_model, year
    return None, None, None, None

def get_latest_team_stats(features_df, team_name):
    """Extract the most recent stats for a team to use in hypothetical matchups."""
    # Find games involving this team
    team_games = features_df[
        (features_df["home_team"] == team_name) | 
        (features_df["away_team"] == team_name)
    ].sort_values("week", ascending=False)
    
    if team_games.empty:
        return None
        
    last_game = team_games.iloc[0]
    
    stats = {}
    
    # If they were home in the last game, grab home stats. If away, grab away stats.
    if last_game["home_team"] == team_name:
        prefix = "home_"
    else:
        prefix = "away_"
        
    # Extract all rolling stats and ratings
    for col in features_df.columns:
        if col.startswith(prefix):
            # Remove prefix to get "neutral" stat name
            stat_name = col[len(prefix):]
            stats[stat_name] = last_game[col]
            
    return stats

def construct_matchup_row(home_stats, away_stats, home_rest=7, away_rest=7):
    """Build a feature row for a hypothetical matchup."""
    row = {}
    
    # Add Home stats
    for k, v in home_stats.items():
        row[f"home_{k}"] = v
        
    # Add Away stats
    for k, v in away_stats.items():
        row[f"away_{k}"] = v
        
    # Recalculate diffs and situational features
    row["home_rest_days"] = home_rest
    row["away_rest_days"] = away_rest
    row["rest_advantage"] = home_rest - away_rest
    
    # Ratings diffs
    if "sp_plus" in home_stats and "sp_plus" in away_stats:
        row["sp_plus_diff"] = home_stats["sp_plus"] - away_stats["sp_plus"]
        row["sp_plus_sum"] = home_stats["sp_plus"] + away_stats["sp_plus"]
        row["rest_advantage_weighted"] = row["rest_advantage"] * abs(row["sp_plus_diff"])
        row["home_field_advantage"] = (1 if row["rest_advantage"] > 0 else 0) * row["sp_plus_diff"]
    
    if "srs" in home_stats and "srs" in away_stats:
        row["srs_diff"] = home_stats["srs"] - away_stats["srs"]
        row["srs_sum"] = home_stats["srs"] + away_stats["srs"]
        
    # Default situational flags for hypothetical
    row["home_short_week"] = 1 if home_rest < 7 else 0
    row["away_short_week"] = 1 if away_rest < 7 else 0
    row["home_bye_week"] = 1 if home_rest > 10 else 0
    row["away_bye_week"] = 1 if away_rest > 10 else 0
    
    return pd.DataFrame([row])

def enrich_picks_data(df):
    """Add calculated pick columns (ATS Pick, ML Pick, etc.) to raw data."""
    if df is None or df.empty:
        return df
        
    # Ensure columns exist
    cols = ["fair_spread_home", "market_spread_home", "dk_spread_home", "fd_spread_home", "p_home_win", "market_ml_home", "fair_total", "market_total"]
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan

    # 1. Format Spreads/Totals FIRST so they can be used in Pick strings
    df["Model Spread"] = df["fair_spread_home"].apply(lambda x: f"{x:+.1f}" if pd.notna(x) else "N/A")
    df["Total"] = df["market_total"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
    df["Model Total"] = df["fair_total"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
    
    if "dk_spread_home" in df.columns:
        df["DK Line"] = df.apply(lambda x: f"{x['dk_spread_home']:+.1f}" if pd.notna(x['dk_spread_home']) else (f"{x['market_spread_home']:+.1f}" if pd.notna(x['market_spread_home']) else "N/A"), axis=1)
    else:
        df["DK Line"] = df["market_spread_home"].apply(lambda x: f"{x:+.1f}" if pd.notna(x) else "N/A")
        
    if "fd_spread_home" in df.columns:
        df["FD Line"] = df.apply(lambda x: f"{x['fd_spread_home']:+.1f}" if pd.notna(x['fd_spread_home']) else (f"{x['market_spread_home']:+.1f}" if pd.notna(x['market_spread_home']) else "N/A"), axis=1)
    else:
        df["FD Line"] = df["market_spread_home"].apply(lambda x: f"{x:+.1f}" if pd.notna(x) else "N/A")

    # 2. Calculate Picks using the formatted columns
    df["ATS Pick Raw"] = df.apply(lambda x: get_ats_pick(x['fair_spread_home'], x['market_spread_home']), axis=1)
    df["ML Pick Raw"] = df.apply(lambda x: get_ml_pick(x['p_home_win'], x['market_ml_home']), axis=1)
    
    # Format ATS Pick: "Team Name (Spread) (Conf)"
    def format_ats_pick(row):
        side, conf = row["ATS Pick Raw"]
        
        # Determine which spread to display (DK, then FD, then Market)
        if pd.notna(row.get('dk_spread_home')) and row.get('dk_spread_home') != "N/A":
            home_spread_val = row['dk_spread_home']
        elif pd.notna(row.get('fd_spread_home')) and row.get('fd_spread_home') != "N/A":
            home_spread_val = row['fd_spread_home']
        else:
            home_spread_val = row['market_spread_home']
            
        # Parse spread value if it's a string (from formatted columns) or float
        try:
            h_spread = float(home_spread_val)
        except (ValueError, TypeError):
            h_spread = 0.0 # Fallback
            
        if side == "Home":
            return f"{row['home_team']} ({h_spread:+.1f}) ({conf}/10)"
        elif side == "Away":
            # Away spread is inverse of home spread
            # Note: The logic here is "Bet on Away Team at +X.X"
            # h_spread is home_spread (e.g. -7.5). Away spread is +7.5.
            # So we negate h_spread.
            return f"{row['away_team']} ({-h_spread:+.1f}) ({conf}/10)"
        return "N/A"

    # Format ML Pick: "Team Name (Conf)"
    def format_ml_pick(row):
        side, conf = row["ML Pick Raw"]
        if side == "Home":
            return f"{row['home_team']} ({conf}/10)"
        elif side == "Away":
            return f"{row['away_team']} ({conf}/10)"
        return "N/A"

    df["ATS Pick"] = df.apply(format_ats_pick, axis=1)
    df["ML Pick"] = df.apply(format_ml_pick, axis=1)
    df["O/U Pick"] = df.apply(lambda x: f"{get_total_pick(x['fair_total'], x['market_total'])[0]} ({get_total_pick(x['fair_total'], x['market_total'])[1]}/10)", axis=1)
    
    return df

# --- MAIN APP ---
st.title("🏈 CFB Betting Model Interface")

# Load Team Info (Logos)
team_info = load_team_info()

# Global sidebar season for Dashboard and Stats tabs
sidebar_season = st.sidebar.number_input("Current Season (Dashboard/Stats)", min_value=2014, max_value=2025, value=2025)
features_df = load_features(sidebar_season)

if features_df is None:
    st.error(f"No data found for {sidebar_season}. Run `python src/cli/main.py features` first.")
    st.stop()

# Load Models (always use latest trained models for prediction logic)
ats_model, ml_model, total_model, model_year = load_models(sidebar_season)
st.sidebar.success(f"Loaded Models (Trained on {model_year})")

tab1, tab2, tab3 = st.tabs(["📊 Weekly Dashboard", "🧪 The Lab (Hypothetical)", "📈 Team Stats"])

# --- TAB 1: WEEKLY DASHBOARD ---
with tab1:
    st.header("Weekly Predictions")
    
    # Load existing picks file if available
    data_dir = get_data_dir()
    reports_dir = data_dir.parent / "reports"
    
    # Find available pick files
    pick_files = list(reports_dir.glob(f"{sidebar_season}_w*_picks.csv"))
    
    # 1. Get list of existing weeks
    existing_weeks = []
    if pick_files:
        pick_files.sort(key=lambda x: int(x.stem.split('_w')[1].split('_')[0]), reverse=True)
        existing_weeks = [int(f.stem.split('_w')[1].split('_')[0]) for f in pick_files]
    
    # 2. Allow selecting ANY week (1-16)
    all_weeks = list(range(1, 17))
    # Default to latest existing week, or Week 1
    default_index = all_weeks.index(existing_weeks[0]) if existing_weeks else 0
    selected_week = st.selectbox("Select Week", all_weeks, index=default_index)
    
    # 3. Check if file exists
    file_path = reports_dir / f"{sidebar_season}_w{selected_week}_picks.csv"
    
    if file_path.exists():
        # Load existing
        picks_df = pd.read_csv(file_path)
        st.success(f"Loaded existing picks for Week {selected_week}")
    else:
        # Generate on demand
        st.info(f"Generating picks for Week {selected_week}...")
        
        # Import necessary prediction logic
        from src.cli.main import load_model_week_predictions
        
        # Run prediction
        with st.spinner("Running model..."):
            try:
                # Use the CLI function directly
                preds_df = load_model_week_predictions(sidebar_season, selected_week)
                
                if not preds_df.empty:
                    # Save it for next time
                    preds_df.to_csv(file_path, index=False)
                    picks_df = preds_df
                    st.success("Picks generated!")
                else:
                    st.error(f"No games found for Week {selected_week}")
                    picks_df = None
            except Exception as e:
                st.error(f"Error generating picks: {e}")
                picks_df = None

    if picks_df is not None:
        # Enrich with explicit picks
        picks_df = enrich_picks_data(picks_df)
        
        # Filters
        col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
        min_conf = col1.slider("Minimum Confidence", 0, 10, 0)
        
        # Merge logos/conference info if available
        if team_info is not None:
            # Merge Home Info
            picks_df = picks_df.merge(
                team_info[["school", "logo", "conference"]].rename(columns={"school": "home_team", "logo": "home_logo", "conference": "home_conf"}),
                on="home_team", how="left"
            )
            # Merge Away Info
            picks_df = picks_df.merge(
                team_info[["school", "logo", "conference"]].rename(columns={"school": "away_team", "logo": "away_logo", "conference": "away_conf"}),
                on="away_team", how="left"
            )
        else:
            picks_df["home_logo"] = None
            picks_df["away_logo"] = None
            picks_df["home_conf"] = None
            picks_df["away_conf"] = None

        # Load Rankings for Top 25 Filter
        top_25_teams, top_25_map = load_rankings(sidebar_season, selected_week)
        
        # Canonicalize the top 25 list for filtering
        if top_25_teams:
            top_25_teams_canon = [to_canonical(t) for t in top_25_teams]
            # Also rebuild map with canonical keys for display lookups
            # Note: This assumes the original key in top_25_map is what we want to match against? 
            # No, we want to match the 'home_team' column (which is canonical) against the map.
            # So we need map: {canonical_name: rank}
            top_25_map_canon = {to_canonical(k): v for k, v in top_25_map.items()}
        else:
            top_25_teams_canon = []
            top_25_map_canon = {}

        show_top_25 = col4.checkbox("Top 25 Only")
        
        # Enrich Team Names with Rankings (e.g. "#1 Oregon")
        if top_25_map_canon:
            def add_rank(team):
                # Team here is already canonical (from picks_df)
                if team in top_25_map_canon:
                    return f"#{top_25_map_canon[team]} {team}"
                return team
                
            # Update displayed team names
            # Note: This logic runs BEFORE filtering? No, let's run it.
            
            # Create display columns
            picks_df["home_team_display"] = picks_df["home_team"].apply(add_rank)
            picks_df["away_team_display"] = picks_df["away_team"].apply(add_rank)
        else:
            picks_df["home_team_display"] = picks_df["home_team"]
            picks_df["away_team_display"] = picks_df["away_team"]

        # Conference Filter
        all_confs = sorted(list(set(picks_df["home_conf"].dropna().unique()) | set(picks_df["away_conf"].dropna().unique())))
        selected_confs = col2.multiselect("Filter by Conference", all_confs, placeholder="All Conferences")

        # Team Filter
        all_teams = sorted(list(set(picks_df["home_team"].unique()) | set(picks_df["away_team"].unique())))
        
        # Pre-select specific team if user searched for it
        default_teams = []
        
        # Add selectbox for team filtering
        selected_teams = col3.multiselect("Filter by Team", all_teams, default=default_teams, placeholder="Select teams to filter...")
        
        # --- COLUMN EXPLANATIONS ---
        with st.expander("ℹ️  Column Definitions (Click to Expand)", expanded=False):
            st.markdown("""
            ### **Matchup Info**
            - **home_team / away_team**: The teams playing. Home team is listed first in matchups usually, but check column headers.
            - **home_rest_days / away_rest_days**: Number of days since the team's last game. (7 = normal week).
            - **home_sp_plus / away_sp_plus**: The team's SP+ efficiency rating (Higher is better).

            ### **Spread Betting (ATS)**
            - **fair_spread_home**: The model's calculated "Fair Line". 
                - Negative (e.g., -7.5) = Home is favored by 7.5 points.
                - Positive (e.g., +3.0) = Home is underdog by 3 points.
            - **market_spread_home**: The current line at DraftKings/FanDuel.
            - **dk_spread_home / fd_spread_home**: Specific lines from DraftKings and FanDuel.
            - **edge_spread_pts**: The "value" the model sees. 
                - `Fair Spread + Market Spread`
                - **Positive Edge** = Bet on **Home Team**.
                - **Negative Edge** = Bet on **Away Team**.
            - **kelly_spread**: Recommended bet size (fraction of bankroll) for the spread bet.

            ### **Moneyline (Win/Loss)**
            - **p_home_win**: The model's estimated probability (0% to 100%) that the Home Team wins the game outright.
            - **market_ml_home**: The Vegas moneyline odds (e.g., -150, +130).
            - **market_ml_home_p**: The implied probability of the Vegas odds.
            - **edge_ml_prob**: `Model Probability - Market Implied Probability`. Positive means the model thinks the team is more likely to win than Vegas does.
            - **kelly_ml**: Recommended bet size for the moneyline.

            ### **Totals (Over/Under)**
            - **fair_total**: The model's predicted total points scored by both teams combined.
            - **market_total**: The current Over/Under line in Vegas.
            - **edge_total_pts**: `Fair Total - Market Total`.
                - **Positive** = Model predicts **MORE** points (Bet Over).
                - **Negative** = Model predicts **FEWER** points (Bet Under).
            - **kelly_total**: Recommended bet size for the total.
            """)

        # Display Metrics
        filtered_df = picks_df.copy()
        
        # Apply Filters
        if min_conf > 0:
            # Filter by confidence (This is tricky as conf is embedded in string, skipping for now or needing parsing)
            pass

        if show_top_25 and top_25_teams_canon:
            # Use RAW team names for filtering logic
            # Need to ensure 'top_25_teams' contains canonical team names
            # Note: rankings API might return different names than canonical 'team_mapping'.
            # Ideally we should map them, but assuming CFBD consistency for now.
            
            # We filter on the ORIGINAL columns, not the display ones
            filtered_df = filtered_df[
                (filtered_df["home_team"].isin(top_25_teams_canon)) | 
                (filtered_df["away_team"].isin(top_25_teams_canon))
            ]
        elif show_top_25 and not top_25_teams_canon:
            st.warning("No Top 25 rankings found for this week/season yet.")

        if selected_confs:
            filtered_df = filtered_df[
                (filtered_df["home_conf"].isin(selected_confs)) | 
                (filtered_df["away_conf"].isin(selected_confs))
            ]

        if selected_teams:
            filtered_df = filtered_df[
                (filtered_df["home_team"].isin(selected_teams)) | 
                (filtered_df["away_team"].isin(selected_teams))
            ]
        
        # Merge logos if available (Already done above!)
        
        # Select Main Columns for Display
        # Use DISPLAY columns for team names
        display_cols = [
            "away_logo", "away_team_display", "home_logo", "home_team_display", 
            "DK Line", "FD Line", "ATS Pick",
            "ML Pick",
            "Total", "Model Total", "O/U Pick"
        ]
        
        # Configure column display (images, formatting)
        column_config = {
            "away_logo": st.column_config.ImageColumn("Away", width="small"),
            "home_logo": st.column_config.ImageColumn("Home", width="small"),
            "away_team_display": "Away Team",
            "home_team_display": "Home Team",
        }

        # Display DataFrame with configs
        st.dataframe(
            filtered_df[display_cols],
            column_config=column_config,
            use_container_width=True,
            height=800,
            hide_index=True
        )

# --- TAB 2: THE LAB ---
with tab2:
    st.header("Hypothetical Matchup Predictor (Historical)")
    st.markdown("Create dream matchups across any season (e.g., 2019 LSU vs 2020 Alabama).")
    
    # Team Selection Columns
    col1, col_mid, col2 = st.columns([1, 0.2, 1])
    
    with col1:
        st.subheader("🏠 Home Team")
        home_year = st.number_input("Season", 2014, 2025, 2025, key="home_year")
        
        # Load features for selected year to get teams
        home_features = load_features(home_year)
        if home_features is not None:
            home_teams = sorted(list(set(home_features["home_team"].unique()) | set(home_features["away_team"].unique())))
            home_team = st.selectbox("Team", home_teams, index=home_teams.index("Georgia") if "Georgia" in home_teams else 0, key="home_team")
            
            # Display Logo
            if team_info is not None:
                logo_row = team_info[team_info["school"] == home_team]
                if not logo_row.empty and logo_row.iloc[0]["logo"]:
                    st.image(logo_row.iloc[0]["logo"], width=100)
        else:
            st.error(f"No data for {home_year}")
    
    with col_mid:
        st.markdown("<h2 style='text-align: center; padding-top: 100px;'>VS</h2>", unsafe_allow_html=True)

    with col2:
        st.subheader("✈️ Away Team")
        away_year = st.number_input("Season", 2014, 2025, 2025, key="away_year")
        
        # Load features for selected year
        away_features = load_features(away_year)
        if away_features is not None:
            away_teams = sorted(list(set(away_features["home_team"].unique()) | set(away_features["away_team"].unique())))
            away_team = st.selectbox("Team", away_teams, index=away_teams.index("Alabama") if "Alabama" in away_teams else 0, key="away_team")
            
            # Display Logo
            if team_info is not None:
                logo_row = team_info[team_info["school"] == away_team]
                if not logo_row.empty and logo_row.iloc[0]["logo"]:
                    st.image(logo_row.iloc[0]["logo"], width=100)
        else:
            st.error(f"No data for {away_year}")

    # Analyze Button
    if st.button("Simulate Matchup", type="primary", use_container_width=True):
        if home_features is not None and away_features is not None:
            # 1. Get Stats
            home_stats = get_latest_team_stats(home_features, home_team)
            away_stats = get_latest_team_stats(away_features, away_team)
            
            if home_stats and away_stats:
                # 2. Build Row (Neutral Rest = 7 days)
                X = construct_matchup_row(home_stats, away_stats, home_rest=7, away_rest=7)
                
                # Ensure columns match model EXACTLY (add missing, drop extra, reorder)
                if hasattr(ats_model, "feature_names") and ats_model.feature_names:
                    # 1. Add missing
                    for feat in ats_model.feature_names:
                        if feat not in X.columns:
                            X[feat] = 0.0
                    # 2. Keep only expected columns in correct order
                    X_ats = X[ats_model.feature_names].copy()
                else:
                    X_ats = X.copy()
                
                # For ML model
                if hasattr(ml_model, "feature_names") and ml_model.feature_names:
                    for feat in ml_model.feature_names:
                        if feat not in X.columns:
                            X[feat] = 0.0
                    X_ml = X[ml_model.feature_names].copy()
                else:
                    X_ml = X.copy()
                
                # For Total model
                if hasattr(total_model, "feature_names") and total_model.feature_names:
                    for feat in total_model.feature_names:
                        if feat not in X.columns:
                            X[feat] = 0.0
                    X_total = X[total_model.feature_names].copy()
                else:
                    X_total = X.copy()
                
                # 3. Predict
                ats_prob = ats_model.predict_proba(X_ats)[0][1] # P(Home Covers)
                ml_prob = ml_model.predict_proba(X_ml)[0][1]   # P(Home Wins)
                pred_total = total_model.predict(X_total)[0]
                
                # 4. Display Results
                st.divider()
                
                # Winner Logic
                winner = home_team if ml_prob > 0.5 else away_team
                win_prob = max(ml_prob, 1-ml_prob)
                
                # Spread Logic
                implied_spread = (ml_prob - 0.5) * 25 * -1
                
                # Main Result Header
                st.markdown(f"<h2 style='text-align: center;'>Winner: {winner} ({win_prob:.1%})</h2>", unsafe_allow_html=True)
                
                # Metrics Columns
                m1, m2, m3 = st.columns(3)
                m1.metric("Projected Spread", f"{home_team} {implied_spread:+.1f}")
                m2.metric("Projected Total", f"{pred_total:.1f}")
                m3.metric("Win Probability", f"{ml_prob:.1%}", help=f"Probability {home_team} wins")
                
                # Explicit Picks Table for Hypothetical
                st.subheader("Full Matchup Projection")
                
                # Create a 1-row dataframe for this matchup
                matchup_df = pd.DataFrame([{
                    "home_team": home_team, "away_team": away_team,
                    "fair_spread_home": implied_spread, "market_spread_home": 0.0, # No market for hypothetical
                    "p_home_win": ml_prob, "market_ml_home": 0,
                    "fair_total": pred_total, "market_total": 0.0
                }])
                
                # Enrich it
                matchup_df = enrich_picks_data(matchup_df)
                
                # Show clean table
                st.dataframe(
                    matchup_df[["ATS Pick", "ML Pick", "O/U Pick", "Model Spread", "Model Total"]].style.format(),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Tale of the Tape
                st.subheader("Tale of the Tape")
                
                # Prepare comparison data
                tape_data = {
                    "Metric": ["Year", "SP+ Rating", "Off. Efficiency (PPA)", "Def. Efficiency (PPA)", "Avg Points For", "Avg Points Allowed"],
                    f"{home_team}": [
                        home_year,
                        f"{home_stats.get('sp_plus', 0):.1f}",
                        f"{home_stats.get('off_ppa_10', 0):.2f}",
                        f"{home_stats.get('def_ppa_10', 0):.2f}",
                        f"{home_stats.get('off_points_for_avg_10', 0):.1f}",
                        f"{home_stats.get('def_points_per_opp_10', 0):.1f}"
                    ],
                    f"{away_team}": [
                        away_year,
                        f"{away_stats.get('sp_plus', 0):.1f}",
                        f"{away_stats.get('off_ppa_10', 0):.2f}",
                        f"{away_stats.get('def_ppa_10', 0):.2f}",
                        f"{away_stats.get('off_points_for_avg_10', 0):.1f}",
                        f"{away_stats.get('def_points_per_opp_10', 0):.1f}"
                    ]
                }
                st.table(pd.DataFrame(tape_data))
                
            else:
                st.error("Could not find stats for one of the teams. They may not have played enough games in that season.")


# --- TAB 3: STATS ---
with tab3:
    st.header("Team Power Ratings (SP+)")
    
    # Extract latest SP+ for all teams
    latest_stats = []
    for team in features_df["home_team"].unique():
        stats = get_latest_team_stats(features_df, team)
        if stats and "sp_plus" in stats:
            latest_stats.append({"Team": team, "SP+": stats["sp_plus"]})
            
    sp_df = pd.DataFrame(latest_stats).sort_values("SP+", ascending=False).reset_index(drop=True)
    sp_df.index += 1
    
    st.dataframe(sp_df, height=600)
