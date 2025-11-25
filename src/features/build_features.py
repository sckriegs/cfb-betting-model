"""Feature engineering pipeline."""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from geopy.distance import geodesic

from src.data.persist import get_data_dir, read_parquet, write_parquet
from src.features.schemas import GameFeatures

logger = logging.getLogger(__name__)


def calculate_advanced_rolling_stats(
    game_stats_df: pd.DataFrame, team: str, window: int, current_week: int, current_season: int
) -> dict:
    """Calculate advanced rolling statistics from game-level advanced stats.
    
    Extracts efficiency metrics (success rate, PPA, explosiveness, havoc) from game stats
    and calculates rolling averages. These metrics are more predictive than raw points.

    Args:
        game_stats_df: DataFrame with game-level advanced stats
        team: Team name
        window: Rolling window size (3, 5, or 10)
        current_week: Current week
        current_season: Current season

    Returns:
        Dictionary with advanced rolling stats for offense and defense
    """
    # Filter to games before current week for this team
    team_games = game_stats_df[
        (game_stats_df["season"] == current_season)
        & (game_stats_df["week"] < current_week)
        & (game_stats_df["team"] == team)
    ].copy()
    
    if len(team_games) < window:
        # Return neutral/default values if not enough games
        return {
            # Offensive metrics
            "off_success_rate": 0.5,
            "off_ppa": 0.0,
            "off_explosiveness": 1.0,
            "off_line_yards": 3.0,
            "off_points_per_opp": 3.0,
            "off_havoc_total": 0.0,
            # Defensive metrics (lower is better for success_rate, ppa)
            "def_success_rate": 0.5,
            "def_ppa": 0.0,
            "def_explosiveness": 1.0,
            "def_line_yards": 3.0,
            "def_points_per_opp": 3.0,
            "def_havoc_total": 0.0,
        }
    
    # Get last N games
    team_games = team_games.tail(window).sort_values(["week"])
    
    # Extract offensive and defensive metrics
    off_metrics = []
    def_metrics = []
    
    for _, game in team_games.iterrows():
        offense = game.get("offense")
        defense = game.get("defense")
        
        if isinstance(offense, dict):
            off_metrics.append({
                "success_rate": offense.get("successRate", 0.5),
                "ppa": offense.get("ppa", 0.0),
                "explosiveness": offense.get("explosiveness", 1.0),
                "line_yards": offense.get("lineYards", 3.0),
                "points_per_opp": offense.get("pointsPerOpportunity", 3.0),
                "havoc_total": offense.get("havoc", {}).get("total", 0.0) if isinstance(offense.get("havoc"), dict) else 0.0,
            })
        
        if isinstance(defense, dict):
            def_metrics.append({
                "success_rate": defense.get("successRate", 0.5),
                "ppa": defense.get("ppa", 0.0),
                "explosiveness": defense.get("explosiveness", 1.0),
                "line_yards": defense.get("lineYards", 3.0),
                "points_per_opp": defense.get("pointsPerOpportunity", 3.0),
                "havoc_total": defense.get("havoc", {}).get("total", 0.0) if isinstance(defense.get("havoc"), dict) else 0.0,
            })
    
    # Calculate averages
    if off_metrics:
        return {
            # Offensive metrics (higher is better)
            "off_success_rate": np.mean([m["success_rate"] for m in off_metrics]),
            "off_ppa": np.mean([m["ppa"] for m in off_metrics]),
            "off_explosiveness": np.mean([m["explosiveness"] for m in off_metrics]),
            "off_line_yards": np.mean([m["line_yards"] for m in off_metrics]),
            "off_points_per_opp": np.mean([m["points_per_opp"] for m in off_metrics]),
            "off_havoc_total": np.mean([m["havoc_total"] for m in off_metrics]),
            # Defensive metrics (lower is better for success_rate, ppa, points_per_opp)
            "def_success_rate": np.mean([m["success_rate"] for m in def_metrics]) if def_metrics else 0.5,
            "def_ppa": np.mean([m["ppa"] for m in def_metrics]) if def_metrics else 0.0,
            "def_explosiveness": np.mean([m["explosiveness"] for m in def_metrics]) if def_metrics else 1.0,
            "def_line_yards": np.mean([m["line_yards"] for m in def_metrics]) if def_metrics else 3.0,
            "def_points_per_opp": np.mean([m["points_per_opp"] for m in def_metrics]) if def_metrics else 3.0,
            "def_havoc_total": np.mean([m["havoc_total"] for m in def_metrics]) if def_metrics else 0.0,
        }
    else:
        # Return defaults if no metrics found
        return {
            "off_success_rate": 0.5, "off_ppa": 0.0, "off_explosiveness": 1.0,
            "off_line_yards": 3.0, "off_points_per_opp": 3.0, "off_havoc_total": 0.0,
            "def_success_rate": 0.5, "def_ppa": 0.0, "def_explosiveness": 1.0,
            "def_line_yards": 3.0, "def_points_per_opp": 3.0, "def_havoc_total": 0.0,
        }


def calculate_rolling_stats(
    games_df: pd.DataFrame, team: str, window: int, current_week: int, current_season: int
) -> dict:
    """Calculate rolling performance statistics for a team from actual game results.
    
    This gives the model on-field performance data that should outweigh rest days.

    Args:
        games_df: DataFrame with game results
        team: Team name
        window: Rolling window size (3, 5, or 10)
        current_week: Current week
        current_season: Current season

    Returns:
        Dictionary with rolling stats: win_pct, points_for_avg, points_against_avg, 
        point_differential_avg, wins, losses
    """
    # Filter games before current week
    team_games = games_df[
        ((games_df["season"] < current_season) | ((games_df["season"] == current_season) & (games_df["week"] < current_week)))
        & ((games_df["homeTeam"] == team) | (games_df["awayTeam"] == team))
    ].copy()

    if len(team_games) < window:
        # Return neutral values if not enough games
        return {
            "win_pct": 0.5,
            "points_for_avg": 0.0,
            "points_against_avg": 0.0,
            "point_differential_avg": 0.0,
            "wins": 0,
            "losses": 0,
        }

    # Get last N games
    team_games = team_games.tail(window).sort_values(["season", "week"])

    wins = 0
    total_points_for = 0.0
    total_points_against = 0.0
    games_counted = 0

    for _, game in team_games.iterrows():
        home_team = game.get("homeTeam")
        away_team = game.get("awayTeam")
        home_points = game.get("homePoints")
        away_points = game.get("awayPoints")

        # Skip games without scores
        if pd.isna(home_points) or pd.isna(away_points):
            continue

        games_counted += 1

        # Calculate points for/against and wins
        if home_team == team:
            team_points = float(home_points)
            opp_points = float(away_points)
            if team_points > opp_points:
                wins += 1
        else:  # away_team == team
            team_points = float(away_points)
            opp_points = float(home_points)
            if team_points > opp_points:
                wins += 1

        total_points_for += team_points
        total_points_against += opp_points

    if games_counted == 0:
        return {
            "win_pct": 0.5,
            "points_for_avg": 0.0,
            "points_against_avg": 0.0,
            "point_differential_avg": 0.0,
            "wins": 0,
            "losses": 0,
        }

    losses = games_counted - wins
    win_pct = wins / games_counted if games_counted > 0 else 0.5
    points_for_avg = total_points_for / games_counted
    points_against_avg = total_points_against / games_counted
    point_differential_avg = points_for_avg - points_against_avg

    return {
        "win_pct": win_pct,
        "points_for_avg": points_for_avg,
        "points_against_avg": points_against_avg,
        "point_differential_avg": point_differential_avg,
        "wins": wins,
        "losses": losses,
    }


def calculate_rest_days(
    games_df: pd.DataFrame, team: str, current_week: int, current_season: int, kickoff_dt: datetime
) -> dict:
    """Calculate rest days and flags for a team.

    Args:
        games_df: DataFrame with game results
        team: Team name
        current_week: Current week
        current_season: Current season
        kickoff_dt: Current game kickoff datetime

    Returns:
        Dictionary with rest_days, short_week, bye_week
    """
    # Find previous game
    prev_games = games_df[
        ((games_df["season"] < current_season) | ((games_df["season"] == current_season) & (games_df["week"] < current_week)))
        & ((games_df["homeTeam"] == team) | (games_df["awayTeam"] == team))
    ]

    if prev_games.empty:
        return {"rest_days": 7, "short_week": False, "bye_week": False}

    last_game = prev_games.iloc[-1]
    last_kickoff = pd.to_datetime(last_game.get("startDate", kickoff_dt))

    rest_days = (kickoff_dt - last_kickoff).days
    short_week = rest_days < 7
    bye_week = rest_days >= 10

    return {"rest_days": rest_days, "short_week": short_week, "bye_week": bye_week}


def calculate_travel_distance(
    home_venue_lat: float,
    home_venue_lon: float,
    away_venue_lat: float,
    away_venue_lon: float,
) -> float:
    """Calculate travel distance in miles.

    Args:
        home_venue_lat: Home venue latitude
        home_venue_lon: Home venue longitude
        away_venue_lat: Away venue latitude
        away_venue_lon: Away venue longitude

    Returns:
        Distance in miles
    """
    try:
        home_point = (home_venue_lat, home_venue_lon)
        away_point = (away_venue_lat, away_venue_lon)
        distance_km = geodesic(home_point, away_point).kilometers
        return distance_km * 0.621371  # Convert to miles
    except Exception:
        return 0.0


def build_features_for_season(season: int, force_refresh: bool = False) -> pd.DataFrame:
    """Build features for all games in a season.

    Args:
        season: Season year
        force_refresh: If True, rebuild even if cached

    Returns:
        DataFrame with engineered features
    """
    data_dir = get_data_dir()
    features_dir = data_dir / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    cache_path = features_dir / f"{season}.parquet"

    if not force_refresh:
        cached = read_parquet(str(cache_path))
        if cached is not None:
            logger.info(f"Using cached features for {season}")
            return cached

    logger.info(f"Building features for {season}...")

    # Load raw data
    raw_dir = data_dir / "raw"

    games = read_parquet(str(raw_dir / "games" / f"{season}.parquet"))
    if games is None or games.empty:
        logger.warning(f"No games data for {season}")
        return pd.DataFrame()

    # Load additional data
    lines = read_parquet(str(raw_dir / "lines" / f"{season}.parquet"))
    stats_season = read_parquet(str(raw_dir / "stats_season" / f"{season}.parquet"))
    game_stats = read_parquet(str(raw_dir / "stats_game" / f"{season}.parquet"))
    ratings_sp = read_parquet(str(raw_dir / "ratings_sp" / f"{season}.parquet"))
    ratings_srs = read_parquet(str(raw_dir / "ratings_srs" / f"{season}.parquet"))
    weather = read_parquet(str(data_dir / "weather" / f"{season}.parquet"))
    venues = read_parquet(str(raw_dir / "venues" / "venues.parquet"))
    
    # Load new data sources (handle missing files gracefully)
    talent = read_parquet(str(raw_dir / "talent" / f"{season}.parquet"))
    returning = read_parquet(str(raw_dir / "returning" / f"{season}.parquet"))
    coaches = read_parquet(str(raw_dir / "coaches" / f"{season}.parquet"))

    # Pre-process coaches into a lookup map: (team) -> tenure
    # Since we loaded coaches for a specific season, we just need to find the coach for each team
    coach_tenure_map = {}
    if coaches is not None and not coaches.empty:
        try:
            for _, coach_row in coaches.iterrows():
                seasons_list = coach_row.get("seasons")
                if isinstance(seasons_list, (list, np.ndarray)):
                    # Find the school/team for the current season in this list
                    current_school = None
                    tenure = 0
                    
                    # First pass: find current school for this season
                    for s_obj in seasons_list:
                        if isinstance(s_obj, dict) and s_obj.get("year") == season:
                            current_school = s_obj.get("school")
                            break
                    
                    # Second pass: calculate tenure at this school
                    if current_school:
                        # Count seasons at this school up to current season
                        tenure = sum(1 for s in seasons_list if isinstance(s, dict) and s.get("school") == current_school and s.get("year") <= season)
                        coach_tenure_map[current_school] = tenure
        except Exception as e:
            logger.warning(f"Error processing coaches data: {e}")

    # Merge venues to get lat/lon
    if venues is not None and not venues.empty:
        # CFBD uses camelCase: venueId in games, id in venues
        games = games.merge(
            venues[["id", "latitude", "longitude"]],
            left_on="venueId",
            right_on="id",
            how="left",
            suffixes=("", "_venue"),
        )
        games = games.rename(columns={"latitude": "venue_latitude", "longitude": "venue_longitude"})

    # Merge weather
    if weather is not None and not weather.empty:
        games = games.merge(weather, left_on="id", right_on="game_id", how="left")

    # Extract and merge market spreads from lines data (needed for ATS model training)
    # This ensures market_spread_home is available during training, not just prediction
    market_spreads = []
    if lines is not None and not lines.empty:
        for _, line_row in lines.iterrows():
            home_team = line_row.get("homeTeam")
            away_team = line_row.get("awayTeam")
            week = line_row.get("week")
            lines_array = line_row.get("lines")
            
            market_spread = None
            market_ml = None
            market_total = None
            
            if lines_array is not None and len(lines_array) > 0:
                spreads = []
                totals = []
                home_mls = []
                
                for line_obj in lines_array:
                    if isinstance(line_obj, dict):
                        spread_val = line_obj.get("spread")
                        if spread_val is not None:
                            # CFBD spread is from home perspective, negate to get home spread
                            spreads.append(-float(spread_val))
                        
                        total_val = line_obj.get("overUnder")
                        if total_val is not None:
                            totals.append(float(total_val))
                        
                        ml_val = line_obj.get("homeMoneyline")
                        if ml_val is not None:
                            home_mls.append(float(ml_val))
                
                if spreads:
                    market_spread = pd.Series(spreads).median()
                if totals:
                    market_total = pd.Series(totals).median()
                if home_mls:
                    market_ml = pd.Series(home_mls).median()
            
            market_spreads.append({
                "homeTeam": home_team,
                "awayTeam": away_team,
                "week": week,
                "market_spread_home": market_spread,
                "market_ml_home": market_ml,
                "market_total": market_total,
            })
    
    if market_spreads:
        market_df = pd.DataFrame(market_spreads)
        games = games.merge(
            market_df[["homeTeam", "awayTeam", "week", "market_spread_home", "market_ml_home", "market_total"]],
            on=["homeTeam", "awayTeam", "week"],
            how="left"
        )
    else:
        # Add empty columns if no lines data
        games["market_spread_home"] = None
        games["market_ml_home"] = None
        games["market_total"] = None

    # Build feature rows
    feature_rows = []

    for _, game in games.iterrows():
        try:
            # CFBD uses camelCase column names
            home_team = game.get("homeTeam")
            away_team = game.get("awayTeam")
            week = game.get("week")
            kickoff_str = game.get("startDate")

            if pd.isna(home_team) or pd.isna(away_team) or pd.isna(week):
                continue

            kickoff_dt = pd.to_datetime(kickoff_str) if pd.notna(kickoff_str) else datetime.now()

            # Calculate targets (from actual results if available)
            home_score = game.get("homePoints")
            away_score = game.get("awayPoints")
            if pd.notna(home_score) and pd.notna(away_score):
                home_margin = float(home_score) - float(away_score)
                total_points = float(home_score) + float(away_score)
            else:
                home_margin = 0.0
                total_points = 0.0

            # Calculate rolling performance stats (last 3, 5, 10 games)
            # These should outweigh rest days as they reflect actual on-field performance
            home_rolling_3 = calculate_rolling_stats(games, home_team, 3, week, season)
            home_rolling_5 = calculate_rolling_stats(games, home_team, 5, week, season)
            home_rolling_10 = calculate_rolling_stats(games, home_team, 10, week, season)
            
            away_rolling_3 = calculate_rolling_stats(games, away_team, 3, week, season)
            away_rolling_5 = calculate_rolling_stats(games, away_team, 5, week, season)
            away_rolling_10 = calculate_rolling_stats(games, away_team, 10, week, season)
            
            # Calculate advanced rolling statistics from game-level stats (efficiency metrics)
            # These are more predictive than raw points and should be weighted highest
            if game_stats is not None and not game_stats.empty:
                home_adv_3 = calculate_advanced_rolling_stats(game_stats, home_team, 3, week, season)
                home_adv_5 = calculate_advanced_rolling_stats(game_stats, home_team, 5, week, season)
                home_adv_10 = calculate_advanced_rolling_stats(game_stats, home_team, 10, week, season)
                
                away_adv_3 = calculate_advanced_rolling_stats(game_stats, away_team, 3, week, season)
                away_adv_5 = calculate_advanced_rolling_stats(game_stats, away_team, 5, week, season)
                away_adv_10 = calculate_advanced_rolling_stats(game_stats, away_team, 10, week, season)
            else:
                # Default values if game stats not available
                default_adv = {
                    "off_success_rate": 0.5, "off_ppa": 0.0, "off_explosiveness": 1.0,
                    "off_line_yards": 3.0, "off_points_per_opp": 3.0, "off_havoc_total": 0.0,
                    "def_success_rate": 0.5, "def_ppa": 0.0, "def_explosiveness": 1.0,
                    "def_line_yards": 3.0, "def_points_per_opp": 3.0, "def_havoc_total": 0.0,
                }
                home_adv_3 = home_adv_5 = home_adv_10 = default_adv
                away_adv_3 = away_adv_5 = away_adv_10 = default_adv
            
            # Rest days (still important, but should be 3rd in importance behind rolling stats and SP+)
            home_rest = calculate_rest_days(games, home_team, week, season, kickoff_dt)
            away_rest = calculate_rest_days(games, away_team, week, season, kickoff_dt)

            # Travel distance (simplified)
            travel_distance = 0.0
            if pd.notna(game.get("venue_latitude")) and pd.notna(game.get("venue_longitude")):
                # Would need away team's home venue coordinates
                pass

            # Ratings (SP+ and SRS - should be 2nd in importance)
            home_sp = None
            away_sp = None
            home_srs = None
            away_srs = None
            if ratings_sp is not None and not ratings_sp.empty:
                home_rating = ratings_sp[ratings_sp["team"] == home_team]
                away_rating = ratings_sp[ratings_sp["team"] == away_team]
                if not home_rating.empty:
                    home_sp = home_rating.iloc[0].get("rating")
                if not away_rating.empty:
                    away_sp = away_rating.iloc[0].get("rating")

            if ratings_srs is not None and not ratings_srs.empty:
                home_srs_rating = ratings_srs[ratings_srs["team"] == home_team]
                away_srs_rating = ratings_srs[ratings_srs["team"] == away_team]
                if not home_srs_rating.empty:
                    home_srs = home_srs_rating.iloc[0].get("rating")
                if not away_srs_rating.empty:
                    away_srs = away_srs_rating.iloc[0].get("rating")

            # ===== NEW FEATURES =====
            # Talent
            home_talent = 0.0
            away_talent = 0.0
            if talent is not None and not talent.empty:
                # Use "team" column for Talent (checked via cli)
                home_t = talent[talent["team"] == home_team]
                away_t = talent[talent["team"] == away_team]
                if not home_t.empty:
                    home_talent = home_t.iloc[0].get("talent", 0.0)
                if not away_t.empty:
                    away_talent = away_t.iloc[0].get("talent", 0.0)

            # Returning Production
            home_returning = 0.0
            away_returning = 0.0
            if returning is not None and not returning.empty:
                home_r = returning[returning["team"] == home_team]
                away_r = returning[returning["team"] == away_team]
                if not home_r.empty:
                    # Use total returning production (or average of off/def)
                    home_returning = home_r.iloc[0].get("totalPPA", 0.0) # Or usage/production
                    if pd.isna(home_returning): home_returning = home_r.iloc[0].get("totalPercent", 0.0)
                if not away_r.empty:
                    away_returning = away_r.iloc[0].get("totalPPA", 0.0)
                    if pd.isna(away_returning): away_returning = away_r.iloc[0].get("totalPercent", 0.0)

            # Coaches (use pre-calculated map)
            home_coach_tenure = coach_tenure_map.get(home_team, 0)
            away_coach_tenure = coach_tenure_map.get(away_team, 0)

            # Build feature row with rolling performance stats
            # Priority: 1) Advanced rolling stats, 2) SP+/SRS ratings, 3) Rest days
            row = {
                "home_team": home_team,
                "away_team": away_team,
                "season": season,
                "week": week,
                "kickoff_dt": kickoff_dt,
                "home_margin": home_margin,
                "total_points": total_points,
                
                # ===== NEW FEATURES =====
                "home_talent": home_talent,
                "away_talent": away_talent,
                "home_returning_production": home_returning,
                "away_returning_production": away_returning,
                "home_coach_tenure": home_coach_tenure,
                "away_coach_tenure": away_coach_tenure,
                "talent_diff": home_talent - away_talent,
                "returning_diff": home_returning - away_returning,
                "coach_tenure_diff": home_coach_tenure - away_coach_tenure,
                
                # ===== ADVANCED ROLLING STATS (PRIORITY 1) =====
                # Last 3 games - most recent form (most predictive)
                "home_off_success_rate_3": home_adv_3.get("off_success_rate", 0.5),
                "home_off_ppa_3": home_adv_3.get("off_ppa", 0.0),
                "home_off_explosiveness_3": home_adv_3.get("off_explosiveness", 1.0),
                "home_off_line_yards_3": home_adv_3.get("off_line_yards", 3.0),
                "home_off_points_per_opp_3": home_adv_3.get("off_points_per_opp", 3.0),
                "home_off_havoc_3": home_adv_3.get("off_havoc_total", 0.0),
                "home_def_success_rate_3": home_adv_3.get("def_success_rate", 0.5),
                "home_def_ppa_3": home_adv_3.get("def_ppa", 0.0),
                "home_def_explosiveness_3": home_adv_3.get("def_explosiveness", 1.0),
                "home_def_havoc_3": home_adv_3.get("def_havoc_total", 0.0),
                
                "away_off_success_rate_3": away_adv_3.get("off_success_rate", 0.5),
                "away_off_ppa_3": away_adv_3.get("off_ppa", 0.0),
                "away_off_explosiveness_3": away_adv_3.get("off_explosiveness", 1.0),
                "away_off_line_yards_3": away_adv_3.get("off_line_yards", 3.0),
                "away_off_points_per_opp_3": away_adv_3.get("off_points_per_opp", 3.0),
                "away_off_havoc_3": away_adv_3.get("off_havoc_total", 0.0),
                "away_def_success_rate_3": away_adv_3.get("def_success_rate", 0.5),
                "away_def_ppa_3": away_adv_3.get("def_ppa", 0.0),
                "away_def_explosiveness_3": away_adv_3.get("def_explosiveness", 1.0),
                "away_def_havoc_3": away_adv_3.get("def_havoc_total", 0.0),
                
                # Last 5 games - short-term form
                "home_off_success_rate_5": home_adv_5.get("off_success_rate", 0.5),
                "home_off_ppa_5": home_adv_5.get("off_ppa", 0.0),
                "home_off_explosiveness_5": home_adv_5.get("off_explosiveness", 1.0),
                "home_off_line_yards_5": home_adv_5.get("off_line_yards", 3.0),
                "home_off_points_per_opp_5": home_adv_5.get("off_points_per_opp", 3.0),
                "home_off_havoc_5": home_adv_5.get("off_havoc_total", 0.0),
                "home_def_success_rate_5": home_adv_5.get("def_success_rate", 0.5),
                "home_def_ppa_5": home_adv_5.get("def_ppa", 0.0),
                "home_def_havoc_5": home_adv_5.get("def_havoc_total", 0.0),
                
                "away_off_success_rate_5": away_adv_5.get("off_success_rate", 0.5),
                "away_off_ppa_5": away_adv_5.get("off_ppa", 0.0),
                "away_off_explosiveness_5": away_adv_5.get("off_explosiveness", 1.0),
                "away_off_line_yards_5": away_adv_5.get("off_line_yards", 3.0),
                "away_off_points_per_opp_5": away_adv_5.get("off_points_per_opp", 3.0),
                "away_off_havoc_5": away_adv_5.get("off_havoc_total", 0.0),
                "away_def_success_rate_5": away_adv_5.get("def_success_rate", 0.5),
                "away_def_ppa_5": away_adv_5.get("def_ppa", 0.0),
                "away_def_havoc_5": away_adv_5.get("def_havoc_total", 0.0),
                
                # Last 10 games - season trend
                "home_off_success_rate_10": home_adv_10.get("off_success_rate", 0.5),
                "home_off_ppa_10": home_adv_10.get("off_ppa", 0.0),
                "home_off_explosiveness_10": home_adv_10.get("off_explosiveness", 1.0),
                "home_off_line_yards_10": home_adv_10.get("off_line_yards", 3.0),
                "home_off_points_per_opp_10": home_adv_10.get("off_points_per_opp", 3.0),
                "home_off_havoc_10": home_adv_10.get("off_havoc_total", 0.0),
                "home_def_success_rate_10": home_adv_10.get("def_success_rate", 0.5),
                "home_def_ppa_10": home_adv_10.get("def_ppa", 0.0),
                "home_def_havoc_10": home_adv_10.get("def_havoc_total", 0.0),
                
                "away_off_success_rate_10": away_adv_10.get("off_success_rate", 0.5),
                "away_off_ppa_10": away_adv_10.get("off_ppa", 0.0),
                "away_off_explosiveness_10": away_adv_10.get("off_explosiveness", 1.0),
                "away_off_line_yards_10": away_adv_10.get("off_line_yards", 3.0),
                "away_off_points_per_opp_10": away_adv_10.get("off_points_per_opp", 3.0),
                "away_off_havoc_10": away_adv_10.get("off_havoc_total", 0.0),
                "away_def_success_rate_10": away_adv_10.get("def_success_rate", 0.5),
                "away_def_ppa_10": away_adv_10.get("def_ppa", 0.0),
                "away_def_havoc_10": away_adv_10.get("def_havoc_total", 0.0),
                
                # Basic rolling stats (win %, points) - still useful
                "home_win_pct_3": home_rolling_3.get("win_pct", 0.5),
                "home_points_for_avg_3": home_rolling_3.get("points_for_avg", 0.0),
                "home_points_against_avg_3": home_rolling_3.get("points_against_avg", 0.0),
                "home_point_diff_avg_3": home_rolling_3.get("point_differential_avg", 0.0),
                "away_win_pct_3": away_rolling_3.get("win_pct", 0.5),
                "away_points_for_avg_3": away_rolling_3.get("points_for_avg", 0.0),
                "away_points_against_avg_3": away_rolling_3.get("points_against_avg", 0.0),
                "away_point_diff_avg_3": away_rolling_3.get("point_differential_avg", 0.0),
                
                "home_win_pct_5": home_rolling_5.get("win_pct", 0.5),
                "home_points_for_avg_5": home_rolling_5.get("points_for_avg", 0.0),
                "home_points_against_avg_5": home_rolling_5.get("points_against_avg", 0.0),
                "home_point_diff_avg_5": home_rolling_5.get("point_differential_avg", 0.0),
                "away_win_pct_5": away_rolling_5.get("win_pct", 0.5),
                "away_points_for_avg_5": away_rolling_5.get("points_for_avg", 0.0),
                "away_points_against_avg_5": away_rolling_5.get("points_against_avg", 0.0),
                "away_point_diff_avg_5": away_rolling_5.get("point_differential_avg", 0.0),
                
                "home_win_pct_10": home_rolling_10.get("win_pct", 0.5),
                "home_points_for_avg_10": home_rolling_10.get("points_for_avg", 0.0),
                "home_points_against_avg_10": home_rolling_10.get("points_against_avg", 0.0),
                "home_point_diff_avg_10": home_rolling_10.get("point_differential_avg", 0.0),
                "away_win_pct_10": away_rolling_10.get("win_pct", 0.5),
                "away_points_for_avg_10": away_rolling_10.get("points_for_avg", 0.0),
                "away_points_against_avg_10": away_rolling_10.get("points_against_avg", 0.0),
                "away_point_diff_avg_10": away_rolling_10.get("point_differential_avg", 0.0),
                
                # ===== TEAM STRENGTH RATINGS (PRIORITY 2) =====
                "home_sp_plus": home_sp,
                "away_sp_plus": away_sp,
                "home_srs": home_srs,
                "away_srs": away_srs,
                
                # ===== REST DAYS (PRIORITY 3) =====
                "home_rest_days": home_rest.get("rest_days", 7),
                "away_rest_days": away_rest.get("rest_days", 7),
                # Convert boolean flags to numeric (0/1) for better model handling
                "home_short_week": 1 if home_rest.get("short_week", False) else 0,
                "away_short_week": 1 if away_rest.get("short_week", False) else 0,
                "home_bye_week": 1 if home_rest.get("bye_week", False) else 0,
                "away_bye_week": 1 if away_rest.get("bye_week", False) else 0,
                
                # Weather (ensure proper merging)
                "temp_C": game.get("temp_C") if pd.notna(game.get("temp_C")) else None,
                "wind_kph": game.get("wind_kph") if pd.notna(game.get("wind_kph")) else None,
                "precip_flag": 1 if game.get("precip_flag") == 1 else 0,
                
                # Availability (stubbed)
                "home_qb_out": 0,
                "away_qb_out": 0,
                "home_starters_out_off": 0,
                "away_starters_out_off": 0,
                "home_starters_out_def": 0,
                "away_starters_out_def": 0,
                
                # Market data (for ATS model training - needed to create correct target)
                "market_spread_home": game.get("market_spread_home") if pd.notna(game.get("market_spread_home")) else None,
                "market_ml_home": game.get("market_ml_home") if pd.notna(game.get("market_ml_home")) else None,
                "market_total": game.get("market_total") if pd.notna(game.get("market_total")) else None,
            }
            
            # ===== INTERACTION FEATURES =====
            # Rest advantage (home team benefit)
            rest_advantage = row["home_rest_days"] - row["away_rest_days"]
            row["rest_advantage"] = rest_advantage
            
            # Team strength differentials
            if pd.notna(home_sp) and pd.notna(away_sp):
                row["sp_plus_diff"] = home_sp - away_sp
                row["sp_plus_sum"] = home_sp + away_sp
            else:
                row["sp_plus_diff"] = 0.0
                row["sp_plus_sum"] = 0.0
            
            if pd.notna(home_srs) and pd.notna(away_srs):
                row["srs_diff"] = home_srs - away_srs
                row["srs_sum"] = home_srs + away_srs
            else:
                row["srs_diff"] = 0.0
                row["srs_sum"] = 0.0
            
            # Rest matters more in close games
            row["rest_advantage_weighted"] = rest_advantage * abs(row["sp_plus_diff"]) if pd.notna(row["sp_plus_diff"]) else 0.0
            
            # Home field advantage (rest + rating)
            row["home_field_advantage"] = (1 if rest_advantage > 0 else 0) * row["sp_plus_diff"] if pd.notna(row["sp_plus_diff"]) else 0.0
            
            # Rest product (both teams well-rested = higher scoring potential)
            row["rest_product"] = row["home_rest_days"] * row["away_rest_days"]
            
            # Matchup differentials (offense vs defense efficiency)
            # Home offense vs away defense
            row["off_def_success_rate_diff_3"] = home_adv_3.get("off_success_rate", 0.5) - away_adv_3.get("def_success_rate", 0.5)
            row["off_def_ppa_diff_3"] = home_adv_3.get("off_ppa", 0.0) - away_adv_3.get("def_ppa", 0.0)
            row["off_def_success_rate_diff_5"] = home_adv_5.get("off_success_rate", 0.5) - away_adv_5.get("def_success_rate", 0.5)
            row["off_def_ppa_diff_5"] = home_adv_5.get("off_ppa", 0.0) - away_adv_5.get("def_ppa", 0.0)
            
            # Away offense vs home defense
            row["away_off_home_def_success_rate_diff_3"] = away_adv_3.get("off_success_rate", 0.5) - home_adv_3.get("def_success_rate", 0.5)
            row["away_off_home_def_ppa_diff_3"] = away_adv_3.get("off_ppa", 0.0) - home_adv_3.get("def_ppa", 0.0)
            row["away_off_home_def_success_rate_diff_5"] = away_adv_5.get("off_success_rate", 0.5) - home_adv_5.get("def_success_rate", 0.5)
            row["away_off_home_def_ppa_diff_5"] = away_adv_5.get("off_ppa", 0.0) - home_adv_5.get("def_ppa", 0.0)
            
            # Weather interactions
            if pd.notna(row["temp_C"]):
                row["cold_game"] = 1 if row["temp_C"] < 5 else 0
            else:
                row["cold_game"] = 0
            
            if pd.notna(row["wind_kph"]):
                row["windy_game"] = 1 if row["wind_kph"] > 30 else 0
            else:
                row["windy_game"] = 0

            feature_rows.append(row)

        except Exception as e:
            logger.warning(f"Error processing game {game.get('id')}: {e}")
            continue

    features_df = pd.DataFrame(feature_rows)
    write_parquet(features_df, str(cache_path), overwrite=True)

    return features_df


