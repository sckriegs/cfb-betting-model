"""Main CLI entry point."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import typer
from dotenv import load_dotenv

from src.betting.kelly import kelly_fraction
from src.betting.market import american_to_prob, fair_spread_from_margin_distribution, fair_total_from_prediction
from src.data.cfbd_client import CFBDClient
from src.data.ingest import ingest_range
from src.data.odds.cache import load_latest_odds_snapshot, save_odds_snapshot
from src.data.odds.odds_api import OddsAPIClient
from src.data.team_mapping import to_canonical
from src.features.build_features import build_features_for_season
from src.modeling.eval import backtest as run_backtest
from src.modeling.train_ats import train_ats_model
from src.modeling.train_ml import train_ml_model
from src.modeling.train_total import train_total_model
from src.viz.reports import generate_weekly_markdown

load_dotenv()

app = typer.Typer()
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@app.command()
def ingest(
    start: int = typer.Option(2005, help="Start season"),
    end: int = typer.Option(2025, help="End season"),
):
    """Ingest data from CFBD API for a range of seasons."""
    logger.info(f"Ingesting data from {start} to {end}...")
    ingest_range(start, end)
    logger.info("Ingestion complete")


@app.command()
def features():
    """Build and cache modeling features for all available seasons."""
    from src.data.persist import get_data_dir, read_parquet

    data_dir = get_data_dir()
    raw_dir = data_dir / "raw" / "games"

    # Find all seasons with game data
    seasons = []
    if raw_dir.exists():
        for file in raw_dir.glob("*.parquet"):
            try:
                season = int(file.stem)
                seasons.append(season)
            except ValueError:
                continue

    seasons = sorted(seasons)
    logger.info(f"Building features for {len(seasons)} seasons...")

    for season in seasons:
        try:
            build_features_for_season(season)
        except Exception as e:
            logger.error(f"Error building features for {season}: {e}")
            continue

    logger.info("Feature building complete")


@app.command()
def train(
    models: str = typer.Option("ats,ml,total", "--models"),
):
    """Train models for all available seasons."""
    from src.data.persist import get_data_dir, read_parquet

    model_types = [m.strip() for m in models.split(",")]

    data_dir = get_data_dir()
    features_dir = data_dir / "features"

    # Find all seasons with features
    seasons = []
    if features_dir.exists():
        for file in features_dir.glob("*.parquet"):
            try:
                season = int(file.stem)
                seasons.append(season)
            except ValueError:
                continue

    seasons = sorted(seasons)
    logger.info(f"Training models for {len(seasons)} seasons...")

    # Load all features
    all_features = []
    for season in seasons:
        features_df = read_parquet(str(features_dir / f"{season}.parquet"))
        if features_df is not None and not features_df.empty:
            all_features.append(features_df)

    if not all_features:
        logger.error("No features found")
        return

    features_df = pd.concat(all_features, ignore_index=True)

    # Train models for each season
    for season in seasons:
        if "ats" in model_types:
            try:
                train_ats_model(season, features_df)
            except Exception as e:
                logger.error(f"Error training ATS model for {season}: {e}")

        if "ml" in model_types:
            try:
                train_ml_model(season, features_df)
            except Exception as e:
                logger.error(f"Error training ML model for {season}: {e}")

        if "total" in model_types:
            try:
                train_total_model(season, features_df)
            except Exception as e:
                logger.error(f"Error training Total model for {season}: {e}")

    logger.info("Training complete")


@app.command()
def backtest(
    start: int = typer.Option(2014, "--start"), end: int = typer.Option(2024, "--end")
):
    """Run backtest with walk-forward validation."""
    from src.data.persist import get_data_dir, read_parquet

    data_dir = get_data_dir()
    features_dir = data_dir / "features"

    # Load all features
    all_features = []
    for season in range(start, end + 1):
        features_df = read_parquet(str(features_dir / f"{season}.parquet"))
        if features_df is not None and not features_df.empty:
            all_features.append(features_df)

    if not all_features:
        logger.error("No features found for backtest period")
        return

    features_df = pd.concat(all_features, ignore_index=True)

    results_df = run_backtest(features_df, start_season=start, end_season=end)

    # Print summary
    if not results_df.empty:
        logger.info("\nBacktest Summary:")
        logger.info(f"Total weeks: {len(results_df)}")
        logger.info(f"ATS hit rate: {results_df['ats_hit_rate'].mean():.3f}")
        logger.info(f"ML hit rate: {results_df['ml_hit_rate'].mean():.3f}")
        logger.info(f"Total MAE: {results_df['total_mae'].mean():.2f}")


@app.command()
def fetch_odds(
    season: int = typer.Option(..., help="Season year"),
    week: int = typer.Option(..., help="Week number"),
    save: bool = typer.Option(True, "--save", help="Save odds snapshot"),
):
    """Fetch current odds from The Odds API."""
    client = OddsAPIClient()
    quotes = client.get_current_odds(team_name_mapper=to_canonical)

    if save:
        save_odds_snapshot(quotes, season, week)
        logger.info(f"Saved {len(quotes)} odds quotes")

    logger.info(f"Fetched {len(quotes)} odds quotes")


def load_model_week_predictions(season: int, week: int, live_spreads_map: Optional[dict] = None) -> pd.DataFrame:
    """Load model predictions for a week.

    Args:
        season: Season year
        week: Week number
        live_spreads_map: Optional dictionary of {(home, away): feature_spread} to override feature spreads

    Returns:
        DataFrame with predictions
    """
    import pickle
    import numpy as np
    from src.data.persist import get_data_dir, read_parquet
    from src.features.build_features import build_features_for_season
    from src.modeling.train_ats import prepare_ats_data
    from src.modeling.train_ml import prepare_ml_data
    from src.modeling.train_total import prepare_total_data
    from src.betting.market import fair_spread_from_margin_distribution

    data_dir = get_data_dir()
    models_dir = data_dir / "models"

    # Load features for this week
    features_df = read_parquet(str(data_dir / "features" / f"{season}.parquet"))
    if features_df is None or features_df.empty:
        logger.warning(f"No features found for season {season}")
        return pd.DataFrame()

    # Filter to this week
    week_df = features_df[features_df["week"] == week].copy()
    if week_df.empty:
        logger.warning(f"No games found for {season} Week {week}")
        return pd.DataFrame()

    # Canonicalize team names to ensure match with live odds
    week_df["home_team"] = week_df["home_team"].apply(to_canonical)
    week_df["away_team"] = week_df["away_team"].apply(to_canonical)

    # OVERRIDE spreads with live spreads if provided
    if live_spreads_map:
        logger.info("Overriding feature spreads with live odds for prediction...")
        for idx, row in week_df.iterrows():
            key = (row["home_team"], row["away_team"])
            if key in live_spreads_map:
                # Update directly in dataframe
                week_df.at[idx, "market_spread_home"] = live_spreads_map[key]

    # Load models (use model from this season, or latest available)
    model_season = season
    ats_model_path = models_dir / "ats" / f"{model_season}.pkl"
    ml_model_path = models_dir / "ml" / f"{model_season}.pkl"
    total_model_path = models_dir / "total" / f"{model_season}.pkl"

    # If models don't exist for this season, try previous season
    if not ats_model_path.exists():
        for prev_season in range(season - 1, 2000, -1):
            if (models_dir / "ats" / f"{prev_season}.pkl").exists():
                model_season = prev_season
                ats_model_path = models_dir / "ats" / f"{model_season}.pkl"
                ml_model_path = models_dir / "ml" / f"{model_season}.pkl"
                total_model_path = models_dir / "total" / f"{model_season}.pkl"
                logger.info(f"Using models from season {model_season}")
                break

    if not ats_model_path.exists():
        logger.error(f"No trained models found for season {season} or earlier")
        return pd.DataFrame()

    # Load models
    with open(ats_model_path, "rb") as f:
        ats_model = pickle.load(f)
    with open(ml_model_path, "rb") as f:
        ml_model = pickle.load(f)
    with open(total_model_path, "rb") as f:
        total_model = pickle.load(f)

    # Prepare feature matrices (same as training)
    # NOTE: prepare_ats_data now filters to only games with market spreads
    # For prediction, we need predictions for ALL games, so we'll prepare features manually
    # to avoid filtering
    
    # For ATS: prepare features without filtering (we'll handle missing spreads in prediction)
    if "market_spread_home" not in week_df.columns:
        week_df["market_spread_home"] = 0.0
    
    # Prepare ATS features (exclude market_spread_home from features)
    ats_exclude_cols = [
        "home_team", "away_team", "season", "week", "kickoff_dt",
        "home_margin", "total_points", 
        # "market_spread_home" # Keep spread for ATS prediction!
    ]
    ats_feature_cols = [c for c in week_df.columns if c not in ats_exclude_cols]
    X_ats = week_df[ats_feature_cols].copy().fillna(0)
    
    # For ML and Total: prepare normally
    X_ml, _ = prepare_ml_data(week_df)
    X_total, _ = prepare_total_data(week_df)

    # Ensure feature columns match model's expected features
    if hasattr(ats_model, 'feature_names') and ats_model.feature_names:
        missing = set(ats_model.feature_names) - set(X_ats.columns)
        for feat in missing:
            X_ats[feat] = 0.0
        X_ats = X_ats[ats_model.feature_names]
    
    if hasattr(ml_model, 'feature_names') and ml_model.feature_names:
        missing = set(ml_model.feature_names) - set(X_ml.columns)
        for feat in missing:
            X_ml[feat] = 0.0
        X_ml = X_ml[ml_model.feature_names]
    
    if hasattr(total_model, 'feature_names') and total_model.feature_names:
        missing = set(total_model.feature_names) - set(X_total.columns)
        for feat in missing:
            X_total[feat] = 0.0
        X_total = X_total[total_model.feature_names]

    # Make predictions
    # ATS: Get probability of home covering - USE THIS DIRECTLY for fair spread
    ats_proba = ats_model.predict_proba(X_ats)[:, 1]  # P(home covers)
    
    # Moneyline: Get probability of home winning - USE THIS for moneyline picks
    ml_proba = ml_model.predict_proba(X_ml)[:, 1]  # P(home wins)
    
    # Convert ATS probability to fair spread using dynamic margin std dev
    # P(home covers) = P(margin > -market_spread)
    # For a given P(covers) and market_spread, solve for fair_spread
    import numpy as np
    from scipy.stats import norm
    
    def calculate_margin_std(home_sp_plus: float, away_sp_plus: float) -> float:
        """Calculate expected margin standard deviation based on team strength.
        
        Dynamic std dev based on SP+ difference:
        - Large favorites (SP+ diff > 20): Smaller variance (std ~11 pts)
        - Close games (SP+ diff < 5): Larger variance (std ~13 pts)
        - Blowouts (SP+ diff > 30): Very small variance (std ~10 pts)
        
        Args:
            home_sp_plus: Home team SP+ rating
            away_sp_plus: Away team SP+ rating
            
        Returns:
            Expected margin standard deviation
        """
        sp_diff = abs(home_sp_plus - away_sp_plus) if pd.notna(home_sp_plus) and pd.notna(away_sp_plus) else 0
        
        if sp_diff > 30:  # Blowouts
            return 10.0
        elif sp_diff > 20:  # Large favorites
            return 11.0
        elif sp_diff > 10:  # Moderate favorites
            return 12.0
        elif sp_diff > 5:   # Small favorites
            return 12.5
        else:  # Close games
            return 13.0  # Higher variance for toss-ups, but tightened to reduce false confidence
    
    fair_spreads = []
    market_spreads = week_df.get("market_spread_home", pd.Series([np.nan] * len(week_df)))
    
    for i in range(len(week_df)):
        ats_prob = ats_proba[i]
        market_spread = market_spreads.iloc[i] if hasattr(market_spreads, 'iloc') else market_spreads[i] if i < len(market_spreads) else np.nan
        
        # Get team SP+ ratings for dynamic std dev
        home_sp = week_df.iloc[i].get("home_sp_plus", np.nan)
        away_sp = week_df.iloc[i].get("away_sp_plus", np.nan)
        margin_std = calculate_margin_std(home_sp, away_sp)
        
        # Convert ATS probability to fair spread
        # P(home covers) = P(margin > -market_spread)
        # Fair spread is where P(margin > -fair_spread) = 0.5
        # 
        # We know: P(margin > -market_spread) = ats_prob
        # This means: -market_spread / std = norm.ppf(ats_prob)
        # 
        # For fair spread (P = 0.5): -fair_spread / std = norm.ppf(0.5) = 0
        # So: fair_spread = market_spread + (norm.ppf(ats_prob) - norm.ppf(0.5)) * std
        # Since norm.ppf(0.5) = 0: fair_spread = market_spread + norm.ppf(ats_prob) * std
        #
        # If ats_prob > 0.5, norm.ppf(ats_prob) > 0, so fair_spread > market_spread
        # This means fair_spread is less negative (closer to 0), which means less favoritism
        # But if ats_prob > 0.5, home is MORE likely to cover, so we should favor home MORE
        # 
        # Actually, the correct interpretation:
        # - market_spread = -7 means home is favored by 7
        # - ats_prob = 0.6 means P(margin > 7) = 0.6, so home is MORE likely to cover
        # - This means the fair spread should favor home MORE (more negative, e.g., -10)
        # - So: fair_spread = market_spread - adjustment (more negative)
        # - But we want edge = fair_spread - market_spread to be positive when ats_prob > 0.5
        # - So: fair_spread = market_spread + adjustment (so edge = adjustment > 0)
        
        if pd.notna(ats_prob) and 0 < ats_prob < 1:
            if pd.notna(market_spread):
                z_score = norm.ppf(ats_prob)  # z-score for P(home covers)
                # Adjustment: how much the margin differs from the implied market margin
                adjustment = z_score * margin_std
                
                # Fair Margin Calculation:
                # market_spread from features is the "Hurdle" (e.g. +7 for -7 favorite)
                # We want Fair Margin = Hurdle + Adjustment
                fair_spread = market_spread + adjustment
            else:
                # Fallback: use ML probability if no market spread
                ml_prob = ml_proba[i]
                if pd.notna(ml_prob) and 0 < ml_prob < 1:
                    ml_z_score = norm.ppf(ml_prob)
                    fair_spread = ml_z_score * margin_std
                else:
                    fair_spread = 0.0
        else:
            # Fallback to ML probability if ATS prob is invalid
            ml_prob = ml_proba[i]
            if pd.notna(ml_prob) and 0 < ml_prob < 1:
                ml_z_score = norm.ppf(ml_prob)
                fair_spread = ml_z_score * margin_std
            else:
                fair_spread = 0.0
        
        fair_spreads.append(fair_spread)

    # Totals: Direct prediction
    total_preds = total_model.predict(X_total)

    # Build results DataFrame
    results = pd.DataFrame({
        "home_team": week_df["home_team"].values,
        "away_team": week_df["away_team"].values,
        "fair_spread_home": fair_spreads,
        "p_home_win": ml_proba,
        "p_home_covers": ats_proba,  # Also include ATS prob for reference
        "fair_total": total_preds,
    })

    return results


def filter_top25_power5_picks(picks_df: pd.DataFrame, season: int, week: int) -> pd.DataFrame:
    """Filter picks to include all Division 1 FBS teams.
    
    Includes all FBS games (CFBD API already filters to FBS only).
    This ensures no teams are missed.
    
    Args:
        picks_df: DataFrame with picks
        season: Season year
        week: Week number
        
    Returns:
        Filtered DataFrame (all FBS games)
    """
    from src.data.persist import get_data_dir, read_parquet
    
    # Get games data to verify FBS classification
    data_dir = get_data_dir()
    games_df = read_parquet(str(data_dir / "raw" / "games" / f"{season}.parquet"))
    
    # Filter to only FBS teams (CFBD API should already be FBS-only, but double-check)
    if games_df is not None and not games_df.empty:
        week_games = games_df[games_df["week"] == week].copy()
        if not week_games.empty:
            # Get FBS teams from this week's games
            fbs_teams = set()
            for _, game in week_games.iterrows():
                home_team = game.get("homeTeam")
                away_team = game.get("awayTeam")
                home_class = game.get("homeClassification")
                away_class = game.get("awayClassification")
                
                # Include if classification is "fbs" (CFBD uses lowercase)
                if home_team and (pd.isna(home_class) or str(home_class).lower() == "fbs"):
                    fbs_teams.add(to_canonical(home_team))
                if away_team and (pd.isna(away_class) or str(away_class).lower() == "fbs"):
                    fbs_teams.add(to_canonical(away_team))
            
            # Filter picks to only include FBS teams
            def is_fbs_game(row):
                home_team = row.get("home_team")
                away_team = row.get("away_team")
                return home_team in fbs_teams and away_team in fbs_teams
            
            filtered = picks_df[picks_df.apply(is_fbs_game, axis=1)].copy()
            logger.info(f"Filtered to {len(filtered)} FBS games (all Division 1 FBS teams included)")
            return filtered
    
    # If we can't filter, return original (assume all are FBS)
    logger.info(f"Including all {len(picks_df)} games (all FBS teams)")
    return picks_df


def load_cfbd_closing_lines(season: int, week: int) -> pd.DataFrame:
    """Load CFBD closing lines for a week.

    Args:
        season: Season year
        week: Week number

    Returns:
        DataFrame with closing lines
    """
    from src.data.persist import get_data_dir, read_parquet
    from src.betting.market import prob_to_american

    data_dir = get_data_dir()
    lines_df = read_parquet(str(data_dir / "raw" / "lines" / f"{season}.parquet"))

    if lines_df is None or lines_df.empty:
        logger.warning(f"No lines data found for season {season}")
        return pd.DataFrame()

    # Filter to this week
    week_lines = lines_df[lines_df["week"] == week].copy()
    if week_lines.empty:
        logger.warning(f"No lines found for {season} Week {week}")
        return pd.DataFrame()

    # CFBD lines format: lines column contains array of provider lines
    # Extract closing line (median across providers, or last one)
    results = []

    for _, row in week_lines.iterrows():
        home_team = row.get("homeTeam")
        away_team = row.get("awayTeam")
        
        # Extract lines array
        lines_array = row.get("lines")
        
        market_spread = None
        market_ml = None
        market_total = None
        
        if lines_array is not None and len(lines_array) > 0:
            # Extract spreads, totals, and moneylines from all providers
            spreads = []
            totals = []
            home_mls = []
            
            for line_obj in lines_array:
                if isinstance(line_obj, dict):
                    # Spread: CFBD format shows spread from home team perspective
                    # If spread is positive, away team is favored; if negative, home is favored
                    spread_val = line_obj.get("spread")
                    if spread_val is not None:
                        # CFBD spread is from home perspective, so negate to get home spread
                        spreads.append(-float(spread_val))
                    
                    # Total
                    total_val = line_obj.get("overUnder")
                    if total_val is not None:
                        totals.append(float(total_val))
                    
                    # Moneyline (home)
                    ml_val = line_obj.get("homeMoneyline")
                    if ml_val is not None:
                        home_mls.append(float(ml_val))
            
            # Use median across providers
            if spreads:
                market_spread = pd.Series(spreads).median()
            if totals:
                market_total = pd.Series(totals).median()
            if home_mls:
                market_ml = pd.Series(home_mls).median()

        results.append({
            "home_team": home_team,
            "away_team": away_team,
            "market_spread_home": market_spread,
            "market_ml_home": market_ml,
            "market_total": market_total,
        })

    result_df = pd.DataFrame(results)
    
    return result_df


def generate_picks(season: int, week: int, use_live_odds: bool = False) -> pd.DataFrame:
    """Generate picks DataFrame for a week."""
    from src.data.persist import get_data_dir
    
    live_spreads_map = {}
    market_df = pd.DataFrame()
    
    if use_live_odds:
        logger.info("Loading live odds...")
        odds_df = load_latest_odds_snapshot(season, week)
        if odds_df is None or odds_df.empty:
            logger.warning("No live odds found, fetching...")
            client = OddsAPIClient()
            quotes = client.get_current_odds(team_name_mapper=to_canonical)
            save_odds_snapshot(quotes, season, week)
            odds_df = load_latest_odds_snapshot(season, week)

        # Aggregate odds (median across books)
        if odds_df is None or odds_df.empty:
            logger.warning("No live odds available, falling back to CFBD closing lines...")
            market_df = load_cfbd_closing_lines(season, week)
            if market_df.empty:
                logger.error("No odds data available (neither live nor historical)")
                # Continue without market data (will use 0 spread)
            else:
                logger.info(f"Using CFBD closing lines: {len(market_df)} games")
        else:
            # Filter to only DraftKings and FanDuel
            logger.info("Filtering odds to DraftKings and FanDuel only...")
            odds_df = odds_df[odds_df["bookmaker"].isin(["draftkings", "fanduel"])]
            logger.info(f"Filtered to {len(odds_df)} records from DraftKings and FanDuel")
            
            # Aggregate by game and market, keeping DK and FD separate
            market_records = []
            
            for (home, away), game_odds in odds_df.groupby(["home_team", "away_team"]):
                record = {"home_team": home, "away_team": away}
                
                # Spreads: separate columns for DraftKings and FanDuel
                spreads = game_odds[game_odds["market"] == "spreads"]
                dk_spread = spreads[spreads["bookmaker"] == "draftkings"]["line"]
                fd_spread = spreads[spreads["bookmaker"] == "fanduel"]["line"]
                
                if not dk_spread.empty:
                    record["dk_spread_home"] = dk_spread.iloc[0]
                if not fd_spread.empty:
                    record["fd_spread_home"] = fd_spread.iloc[0]
                
                # Use DraftKings spread as primary, fall back to FanDuel
                # IMPORTANT: Live Spreads are usually "Home +9.5" (Dog).
                # Feature Convention: Dog is -9.5.
                # So we must NEGATE the spread for the feature map.
                primary_spread = None
                if not dk_spread.empty:
                    primary_spread = dk_spread.iloc[0]
                elif not fd_spread.empty:
                    primary_spread = fd_spread.iloc[0]
                
                if primary_spread is not None:
                    record["market_spread_home"] = primary_spread
                    # Store in map for prediction injection (NEGATED for Feature Convention)
                    # Assuming standard US odds where + is dog. 
                    # Feature convention uses - for dog/cushion.
                    live_spreads_map[(home, away)] = -primary_spread
                
                # Moneylines: use DraftKings as primary
                mls = game_odds[game_odds["market"] == "h2h"]
                dk_ml = mls[mls["bookmaker"] == "draftkings"]["price_home"]
                fd_ml = mls[mls["bookmaker"] == "fanduel"]["price_home"]
                
                if not dk_ml.empty:
                    record["market_ml_home"] = dk_ml.iloc[0]
                elif not fd_ml.empty:
                    record["market_ml_home"] = fd_ml.iloc[0]
                
                # Totals: use DraftKings as primary
                totals = game_odds[game_odds["market"] == "totals"]
                dk_total = totals[totals["bookmaker"] == "draftkings"]["total_points"]
                fd_total = totals[totals["bookmaker"] == "fanduel"]["total_points"]
                
                if not dk_total.empty:
                    record["market_total"] = dk_total.iloc[0]
                elif not fd_total.empty:
                    record["market_total"] = fd_total.iloc[0]
                
                market_records.append(record)
            
            market_df = pd.DataFrame(market_records)
    else:
        logger.info("Loading CFBD closing lines...")
        market_df = load_cfbd_closing_lines(season, week)

    # Load predictions with INJECTED live spreads
    predictions_df = load_model_week_predictions(season, week, live_spreads_map)

    if predictions_df.empty:
        logger.warning("No predictions available - using placeholder")
        return pd.DataFrame()

    # Merge predictions with market
    picks_df = predictions_df.copy()
    
    # Merge features data to get rest days, weather, etc. for reasoning
    from src.data.persist import get_data_dir, read_parquet
    data_dir = get_data_dir()
    features_df = read_parquet(str(data_dir / "features" / f"{season}.parquet"))
    if features_df is not None and not features_df.empty:
        week_features = features_df[features_df["week"] == week].copy()
        if not week_features.empty:
            # Merge relevant feature columns for reasoning
            feature_cols_to_merge = ["home_team", "away_team", "home_rest_days", "away_rest_days", 
                                     "home_sp_plus", "away_sp_plus",  # SP+ ratings for team strength
                                     "temp_C", "wind_kph", "precip_flag"]
            available_cols = [col for col in feature_cols_to_merge if col in week_features.columns]
            if available_cols:
                picks_df = picks_df.merge(
                    week_features[available_cols],
                    on=["home_team", "away_team"],
                    how="left"
                )

    # Calculate edges and Kelly
    if not market_df.empty and "market_spread_home" in market_df.columns:
        # Include dk_spread_home and fd_spread_home if they exist
        merge_cols = ["home_team", "away_team", "market_spread_home"]
        if "dk_spread_home" in market_df.columns:
            merge_cols.append("dk_spread_home")
        if "fd_spread_home" in market_df.columns:
            merge_cols.append("fd_spread_home")
        
        picks_df = picks_df.merge(
            market_df[merge_cols],
            on=["home_team", "away_team"],
            how="left",
        )
        # Correct edge calculation: Fair (Margin) + Market (Spread)
        picks_df["edge_spread_pts"] = (
            picks_df["fair_spread_home"] + picks_df["market_spread_home"]
        )
        # Calculate Kelly for spreads
        picks_df["kelly_spread"] = picks_df.apply(
            lambda row: kelly_fraction(
                0.5 + abs(row["edge_spread_pts"]) / 14.0,  # Rough prob estimate from edge
                int(row.get("market_spread_price", -110)),
                edge=abs(row["edge_spread_pts"]),
                market="spreads",
            )
            if pd.notna(row.get("market_spread_home")) and pd.notna(row["edge_spread_pts"])
            else 0.0,
            axis=1,
        )

    if not market_df.empty and "market_ml_home" in market_df.columns:
        picks_df = picks_df.merge(
            market_df[["home_team", "away_team", "market_ml_home"]],
            on=["home_team", "away_team"],
            how="left",
        )
        picks_df["market_ml_home_p"] = picks_df["market_ml_home"].apply(
            lambda x: american_to_prob(x) if pd.notna(x) else None
        )
        picks_df["edge_ml_prob"] = picks_df["p_home_win"] - picks_df["market_ml_home_p"]
        picks_df["kelly_ml"] = picks_df.apply(
            lambda row: kelly_fraction(
                row["p_home_win"], int(row["market_ml_home"]), market="ml"
            )
            if pd.notna(row["market_ml_home"])
            else 0.0,
            axis=1,
        )

    if not market_df.empty and "market_total" in market_df.columns:
        picks_df = picks_df.merge(
            market_df[["home_team", "away_team", "market_total"]],
            on=["home_team", "away_team"],
            how="left",
        )
        picks_df["edge_total_pts"] = picks_df["fair_total"] - picks_df["market_total"]
        # Calculate Kelly for totals
        picks_df["kelly_total"] = picks_df.apply(
            lambda row: kelly_fraction(
                0.5 + abs(row["edge_total_pts"]) / 20.0,  # Rough prob estimate from edge
                int(row.get("market_total_price", -110)),
                edge=abs(row["edge_total_pts"]),
                market="totals",
            )
            if pd.notna(row.get("market_total")) and pd.notna(row["edge_total_pts"])
            else 0.0,
            axis=1,
        )

    # Filter to focus on top 25 teams and Power 5 matchups
    picks_df = filter_top25_power5_picks(picks_df, season, week)
    
    return picks_df


@app.command()
def pick_week(
    season: int = typer.Argument(..., help="Season year"),
    week: int = typer.Argument(..., help="Week number"),
    use_live_odds: bool = typer.Option(False, "--use-live-odds", help="Fetch live odds from API"),
    save: bool = typer.Option(False, "--save", help="Save picks to database"),
):
    """Generate picks for a week."""
    from src.data.persist import get_data_dir

    # Force live odds for now based on user preference
    use_live_odds = True
    logger.info(f"use_live_odds flag = {use_live_odds}")
    
    picks_df = generate_picks(season, week, use_live_odds)
    
    if picks_df.empty:
        logger.error("Failed to generate picks")
        return

    # Save CSV
    data_dir = get_data_dir()
    reports_dir = data_dir.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    csv_path = reports_dir / f"{season}_w{week}_picks.csv"
    picks_df.to_csv(csv_path, index=False)
    logger.info(f"Saved picks CSV to {csv_path}")

    # Generate and save Markdown
    md_path = reports_dir / f"{season}_w{week}_picks.md"
    markdown = generate_weekly_markdown(picks_df, season, week, str(md_path))
    logger.info(f"Saved picks Markdown to {md_path}")

    print(markdown)


if __name__ == "__main__":
    app()
