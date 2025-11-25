"""Markdown report generation."""

from typing import Optional

import pandas as pd


def get_team_rankings(season: int, week: int) -> dict:
    """Get team rankings from AP poll.
    
    Args:
        season: Season year
        week: Week number
        
    Returns:
        Dictionary mapping team name to rank (1-25, or None if not ranked)
    """
    from src.data.persist import get_data_dir, read_parquet
    from src.data.cfbd_client import CFBDClient
    
    data_dir = get_data_dir()
    rankings = {}
    
    # Try to load from cached rankings file first
    rankings_file = data_dir / "raw" / "rankings" / f"{season}_week{week}.parquet"
    if rankings_file.exists():
        rankings_df = read_parquet(str(rankings_file))
        if rankings_df is not None and not rankings_df.empty:
            for _, row in rankings_df.iterrows():
                team = row.get("school") or row.get("team")
                rank = row.get("rank")
                if team and pd.notna(rank):
                    rankings[team] = int(rank)
            return rankings
    
    # Fetch from API if not cached
    try:
        client = CFBDClient()
        # Try AP poll first, fallback to CFP if needed
        rankings_df = client.get_rankings(season, week, poll="ap")
        
        if rankings_df is None or rankings_df.empty:
            # Try CFP rankings as fallback
            rankings_df = client.get_rankings(season, week, poll="cfp")
        
        if rankings_df is not None and not rankings_df.empty:
            # CFBD rankings format: DataFrame has "polls" column which is a list of dicts
            # Each poll dict has "poll" name and "ranks" array
            # Each rank entry has "school" and "rank" fields
            for _, row in rankings_df.iterrows():
                polls = row.get("polls", [])
                if isinstance(polls, list):
                    for poll in polls:
                        poll_name = poll.get("poll", "")
                        # Look for AP Top 25 or CFP rankings
                        if "AP Top 25" in poll_name or poll.get("poll") == "ap":
                            ranks = poll.get("ranks", [])
                            if isinstance(ranks, list):
                                for rank_entry in ranks:
                                    if isinstance(rank_entry, dict):
                                        team = rank_entry.get("school")
                                        rank = rank_entry.get("rank")
                                        if team and rank is not None:
                                            rankings[team] = int(rank)
                            break  # Prefer AP poll, so break after finding it
                        elif "Playoff Committee" in poll_name or poll.get("poll") == "cfp":
                            # Use CFP as fallback if AP not found
                            if not rankings:
                                ranks = poll.get("ranks", [])
                                if isinstance(ranks, list):
                                    for rank_entry in ranks:
                                        if isinstance(rank_entry, dict):
                                            team = rank_entry.get("school")
                                            rank = rank_entry.get("rank")
                                            if team and rank is not None:
                                                rankings[team] = int(rank)
            
            # Cache the rankings
            if rankings:
                rankings_dir = data_dir / "raw" / "rankings"
                rankings_dir.mkdir(parents=True, exist_ok=True)
                # Save as simple format
                cache_data = [{"team": team, "rank": rank} for team, rank in rankings.items()]
                cache_df = pd.DataFrame(cache_data)
                cache_df.to_parquet(str(rankings_file), index=False)
    except Exception as e:
        # If API fails, return empty dict (no rankings shown)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not fetch AP poll rankings: {e}")
    
    return rankings


def calculate_confidence(edge: float, market_type: str = "spread") -> int:
    """Calculate confidence level (1-10) based on edge.
    
    RECALIBRATED V3 (Week 12, 2025 QA Results):
    - ATS: 5/10 (86.7%), 7/10 (80.0%) performing excellently
    - O/U: 1/10 (60.0%), 7/10 (62.5%) performing well; 3/10 (40.0%) poor
    - O/U thresholds adjusted so higher confidence = higher expected accuracy
    
    Args:
        edge: Edge value (points for spread/total, probability for ML)
        market_type: Type of market ("spread", "total", or "ml")
        
    Returns:
        Confidence level from 1-10 (calibrated to match actual accuracy)
    """
    if pd.isna(edge) or edge == 0:
        return 0
    
    if market_type == "total":
        # O/U CONFIDENCE RECALIBRATION (based on V3 QA results)
        # V3 Results: 1/10=60%, 3/10=40%, 5/10=50%, 7/10=62.5%, 9/10=50%
        # Strategy: Make thresholds more conservative, ensure higher confidence = better accuracy
        abs_edge = abs(edge)
        
        # Recalibrated O/U thresholds:
        # User requested: every game should have a line by now
        # Very small edges (<0.5): 1/10 (60% accuracy in V3 - good!)
        # Small edges (0.5-1.5): 2/10 (group with 3/10 that had 40% - avoid)
        # Medium-small (1.5-3): 3/10 (40% accuracy - poor, but include)
        # Medium (3-5): 4-5/10 (50% accuracy - break-even range)
        # Medium-large (5-8): 6-7/10 (62.5% accuracy - good range)
        # Large (8-12): 8/10 (should be better)
        # Very large (12-18): 9/10 (should be best)
        # Huge (18+): 10/10 (rare, should be excellent)
        
        if abs_edge < 0.001:
            return 0  # Skip only truly zero edges (< 0.001)
        elif abs_edge < 0.5:
            return 1  # Very small edge - 60% accuracy in V3 - include all edges >= 0.001
        elif abs_edge < 1.5:
            return 2  # Small edge - group with problematic 3/10 range
        elif abs_edge < 3:
            return 3  # Medium-small edge - 40% accuracy in V3 (poor, but include)
        elif abs_edge < 5:
            # Medium edge - break-even range (50%)
            return 4 + int((abs_edge - 3) / 2)  # 4-5 range
        elif abs_edge < 8:
            # Medium-large edge - good range (62.5% at 7/10)
            return 6 + int((abs_edge - 5) / 3)  # 6-7 range
        elif abs_edge < 12:
            return 8  # Large edge - should perform well
        elif abs_edge < 18:
            return 9  # Very large edge - high confidence
        else:
            return 10  # Huge edge - maximum confidence
    
    elif market_type == "spread":
        # ATS CONFIDENCE (working well, minor adjustments)
        # V3 Results: 1/10=47.1%, 3/10=58.3%, 5/10=86.7%, 7/10=80.0%, 9/10=75.0%
        # 5/10 and 7/10 performing excellently - thresholds are good
        abs_edge = abs(edge)
        
        # Keep ATS thresholds similar but ensure all games get picks
        # User requested: every game should have a line by now
        if abs_edge < 0.001:
            return 0  # Skip only truly zero edges (< 0.001)
        elif abs_edge < 0.5:
            return 1  # Very low confidence (47.1% in V3) - include all edges >= 0.001
        elif abs_edge < 1.5:
            return 2  # Low confidence
        elif abs_edge < 3:
            return 3  # Low-medium confidence (58.3% in V3)
        elif abs_edge < 5:
            # Medium confidence - excellent range (86.7% at 5/10 in V3)
            return 4 + int((abs_edge - 3) / 2)  # 4-5 range
        elif abs_edge < 8:
            # Medium-high confidence - excellent range (80.0% at 7/10 in V3)
            return 6 + int((abs_edge - 5) / 3)  # 6-7 range
        elif abs_edge < 12:
            return 8  # High confidence
        elif abs_edge < 18:
            return 9  # Very high confidence (75.0% in V3)
        else:
            return 10  # Maximum confidence
            
    else:  # moneyline
        # For ML: edge in probability (0-1)
        # RECALIBRATED: Lower threshold to include all picks (user requested no filtering)
        # Similar to ATS/O/U - ensure all games get at least 1/10 confidence
        abs_edge = abs(edge)
        
        if abs_edge < 0.001:
            return 0  # Skip only truly zero edges (< 0.1% = essentially 50/50)
        elif abs_edge < 0.01:
            return 1  # Very small edge (0.1-1%) - include with 1/10 confidence
        elif abs_edge < 0.02:
            return 1  # Small edge (1-2%) - include with 1/10 confidence
        elif abs_edge < 0.04:
            return 1  # Very low confidence
        elif abs_edge < 0.06:
            return 2  # Low confidence
        elif abs_edge < 0.09:
            return 3  # Low-medium confidence
        elif abs_edge < 0.12:
            return 4  # Medium confidence
        elif abs_edge < 0.15:
            return 5  # Medium confidence
        elif abs_edge < 0.18:
            return 6  # Medium-high confidence
        elif abs_edge < 0.22:
            return 7  # High confidence
        elif abs_edge < 0.25:
            return 8  # Very high confidence
        elif abs_edge < 0.30:
            return 9  # Maximum confidence
        else:
            return 10  # Extreme confidence - only for 30%+ edges


def get_ats_pick(fair_spread: float, market_spread: float) -> tuple[str, int]:
    """Determine ATS pick and confidence.
    
    RECALIBRATED: Adjust confidence for large spreads to prevent high-confidence misses.
    Large spreads are riskier, so confidence is reduced but picks are still included.
    
    Args:
        fair_spread: Model's fair spread (home team perspective)
        market_spread: Market spread (home team perspective) - can be None if not available
    
    Returns:
        Tuple of (pick, confidence) where pick is "Home" or "Away"
    """
    if pd.isna(fair_spread):
        return ("N/A", 0)
    
    # If no market spread, use fair_spread to determine pick with low confidence
    if pd.isna(market_spread):
        # Pick based on fair_spread: if > 0, home is favored; if < 0, away is favored
        if fair_spread > 0:
            return ("Home", 1)  # Low confidence since no market comparison
        elif fair_spread < 0:
            return ("Away", 1)  # Low confidence since no market comparison
        else:
            return ("N/A", 0)
    
    # CORRECTED EDGE FORMULA: Fair Margin + Market Spread
    # Fair Margin: Positive = Home Wins by X (e.g., +10)
    # Market Spread: Negative = Home Favored by X (e.g., -7)
    # If Home projected to win by 10 (+10) and spread is -7:
    # Edge = 10 + (-7) = +3 (Home covers by 3)
    edge = fair_spread + market_spread
    
    # If edge is positive, model thinks home should cover (home is better value)
    # If edge is negative, model thinks away should cover (away is better value)
    if edge > 0:
        pick = "Home"
    else:
        pick = "Away"
    
    # Calculate base confidence from edge
    confidence = calculate_confidence(abs(edge), "spread")
    
    # Adjust confidence for large spreads (riskier, but don't filter out)
    spread_abs = abs(market_spread)
    if spread_abs >= 20:
        confidence = max(1, confidence - 2)  # Reduce by 2 for very large spreads
    elif spread_abs >= 15:
        confidence = max(1, confidence - 1)  # Reduce by 1 for large spreads
    
    return (pick, confidence)


def get_ml_pick(p_home_win: float, market_ml_home: float = None) -> tuple[str, int]:
    """Determine Moneyline pick and confidence.
    
    Uses ML probability directly to determine pick and confidence.
    
    Args:
        p_home_win: Model's probability of home team winning (0-1)
        market_ml_home: Market moneyline odds for home team (American odds, optional)
        
    Returns:
        Tuple of (pick, confidence) where pick is "Home" or "Away"
    """
    # Handle edge cases: cap probabilities at 0.001 and 0.999 to avoid exact 0 or 1
    if pd.isna(p_home_win) or p_home_win <= 0:
        return ("N/A", 0)
    
    # Cap at 0.999 to avoid exact 1.0 (which would be filtered out)
    if p_home_win >= 1.0:
        p_home_win = 0.999
    
    # If p_home_win > 0.5, pick home; otherwise pick away
    if p_home_win > 0.5:
        pick = "Home"
        edge = p_home_win - 0.5  # Edge above 50%
    else:
        pick = "Away"
        edge = 0.5 - p_home_win  # Edge below 50% (away win prob = 1 - p_home_win)
    
    # Calculate confidence based on edge from 50%
    # Edge is probability difference from even money (0.5)
    confidence = calculate_confidence(edge, "ml")
    
    # If we have market odds, can refine confidence based on implied probability
    if pd.notna(market_ml_home) and market_ml_home != 0:
        from src.betting.market import american_to_prob
        market_prob = american_to_prob(market_ml_home)
        
        if pick == "Home":
            ml_edge = p_home_win - market_prob
        else:
            ml_edge = (1 - p_home_win) - market_prob
        
        # Use the larger edge (from 50% or from market)
        if ml_edge > edge:
            confidence = calculate_confidence(ml_edge, "ml")
    
    return (pick, confidence)


def get_total_pick(fair_total: float, market_total: float) -> tuple[str, int]:
    """Determine O/U pick and confidence.
    
    Args:
        fair_total: Model's predicted total
        market_total: Market total - can be None if not available
        
    Returns:
        Tuple of (pick, confidence) where pick is "OVER" or "UNDER"
    """
    if pd.isna(fair_total):
        return ("N/A", 0)
    
    # If no market total, we can't determine OVER/UNDER without a line to compare to
    # Return N/A in this case
    if pd.isna(market_total):
        return ("N/A", 0)
    
    edge = fair_total - market_total
    
    # If edge is positive, model thinks OVER (fair total > market total)
    # If edge is negative, model thinks UNDER (fair total < market total)
    if edge > 0:
        pick = "OVER"
    else:
        pick = "UNDER"
    
    confidence = calculate_confidence(abs(edge), "total")
    return (pick, confidence)


def get_recent_form(games_df: pd.DataFrame, team: str, current_week: int, current_season: int, games_back: int = 5) -> dict:
    """Get recent form stats for a team.
    
    Args:
        games_df: DataFrame with game results
        team: Team name
        current_week: Current week
        current_season: Current season
        games_back: Number of recent games to analyze
        
    Returns:
        Dictionary with W-L record, win_pct, avg_points_for, avg_points_against, avg_margin
    """
    # Get recent games (before current week)
    recent_games = games_df[
        ((games_df["season"] < current_season) | ((games_df["season"] == current_season) & (games_df["week"] < current_week)))
        & ((games_df["homeTeam"] == team) | (games_df["awayTeam"] == team))
    ].tail(games_back)
    
    if len(recent_games) == 0:
        return None
    
    wins = 0
    total_points_for = 0
    total_points_against = 0
    games_count = 0
    
    for _, game in recent_games.iterrows():
        home_team = game.get("homeTeam")
        away_team = game.get("awayTeam")
        home_points = game.get("homePoints")
        away_points = game.get("awayPoints")
        
        if pd.isna(home_points) or pd.isna(away_points):
            continue
        
        games_count += 1
        
        # Determine if team won
        if home_team == team:
            total_points_for += home_points
            total_points_against += away_points
            if home_points > away_points:
                wins += 1
        else:  # away_team == team
            total_points_for += away_points
            total_points_against += home_points
            if away_points > home_points:
                wins += 1
    
    if games_count == 0:
        return None
    
    win_pct = wins / games_count
    avg_points_for = total_points_for / games_count
    avg_points_against = total_points_against / games_count
    avg_margin = avg_points_for - avg_points_against
    
    return {
        "record": f"{wins}-{games_count - wins}",
        "win_pct": win_pct,
        "avg_points_for": avg_points_for,
        "avg_points_against": avg_points_against,
        "avg_margin": avg_margin,
        "games_count": games_count
    }


def generate_pick_reasoning(
    row: pd.Series,
    season: int,
    week: int,
    rankings: dict,
) -> list[str]:
    """Generate reasoning bullets for why a pick was made.
    
    Uses football-specific data: SP+ ratings, win probability, recent form.
    
    Args:
        row: Row from picks DataFrame with all model outputs
        season: Season year
        week: Week number
        rankings: Dictionary mapping team name to AP rank
        
    Returns:
        List of reasoning bullet points
    """
    reasons = []
    
    # Get key values
    home_team = row.get("home_team", "")
    away_team = row.get("away_team", "")
    fair_spread = row.get("fair_spread_home")
    market_spread = row.get("market_spread_home")
    fair_total = row.get("fair_total")
    market_total = row.get("market_total")
    p_home_win = row.get("p_home_win")
    edge_spread = row.get("edge_spread_pts", 0)
    edge_total = row.get("edge_total_pts", 0)
    
    # Get SP+ ratings
    home_sp_plus = row.get("home_sp_plus")
    away_sp_plus = row.get("away_sp_plus")
    
    # Get recent form
    from src.data.persist import get_data_dir, read_parquet
    data_dir = get_data_dir()
    games_df = read_parquet(str(data_dir / "raw" / "games" / f"{season}.parquet"))
    
    home_form = None
    away_form = None
    if games_df is not None and not games_df.empty:
        home_form = get_recent_form(games_df, home_team, week, season, games_back=5)
        away_form = get_recent_form(games_df, away_team, week, season, games_back=5)
    
    # Determine which side the model likes for ATS
    if pd.notna(fair_spread) and pd.notna(market_spread) and abs(edge_spread) >= 1:
        if edge_spread > 0:
            pick_side = "home"
            pick_team = home_team
            other_team = away_team
        else:
            pick_side = "away"
            pick_team = away_team
            other_team = home_team
        
        pick_rank = rankings.get(pick_team)
        rank_str = f"#{pick_rank} " if pick_rank else ""
        
        # 1. SP+ RATING COMPARISON (Football-specific strength metric)
        if pd.notna(home_sp_plus) and pd.notna(away_sp_plus):
            sp_diff = home_sp_plus - away_sp_plus  # Always home - away
            
            if pick_side == "home":
                pick_sp = home_sp_plus
                other_sp = away_sp_plus
                pick_advantage = sp_diff  # Positive = pick is stronger
            else:
                pick_sp = away_sp_plus
                other_sp = home_sp_plus
                pick_advantage = -sp_diff  # Negative of home-away = away advantage
            
            # Show strength comparison accurately
            if abs(sp_diff) >= 10:
                if pick_advantage > 0:
                    reasons.append(f"• SP+ advantage: {rank_str}{pick_team} ({pick_sp:.1f}) is {abs(sp_diff):.1f} points stronger than {other_team} ({other_sp:.1f})")
                else:
                    reasons.append(f"• SP+ underdog: {rank_str}{pick_team} ({pick_sp:.1f}) vs {other_team} ({other_sp:.1f}) - model sees value despite strength gap")
            elif abs(sp_diff) >= 5:
                if pick_advantage > 0:
                    reasons.append(f"• Team strength: {rank_str}{pick_team} SP+ {pick_sp:.1f} vs {other_team} SP+ {other_sp:.1f} ({abs(sp_diff):.1f} pt advantage)")
                else:
                    reasons.append(f"• Strength matchup: {rank_str}{pick_team} SP+ {pick_sp:.1f} vs {other_team} SP+ {other_sp:.1f}")
            elif abs(sp_diff) >= 2:
                reasons.append(f"• Close matchup: {rank_str}{pick_team} SP+ {pick_sp:.1f} vs {other_team} SP+ {other_sp:.1f}")
        
        # 2. WIN PROBABILITY (Model's confidence)
        if pd.notna(p_home_win):
            if pick_side == "home":
                pick_win_prob = p_home_win
                other_win_prob = 1 - p_home_win
            else:
                pick_win_prob = 1 - p_home_win
                other_win_prob = p_home_win
            
            if pick_win_prob >= 0.70:
                reasons.append(f"• Strong win probability: Model gives {rank_str}{pick_team} {pick_win_prob*100:.0f}% chance to win")
            elif pick_win_prob >= 0.60:
                reasons.append(f"• Win probability: {rank_str}{pick_team} {pick_win_prob*100:.0f}% vs {other_team} {other_win_prob*100:.0f}%")
        
        # 3. RECENT FORM (Last 5 games)
        pick_form = home_form if pick_side == "home" else away_form
        other_form = away_form if pick_side == "home" else home_form
        
        if pick_form and other_form:
            # Compare recent records
            if pick_form["win_pct"] > 0.70 and other_form["win_pct"] < 0.50:
                reasons.append(f"• Recent form: {rank_str}{pick_team} {pick_form['record']} (last 5) vs {other_team} {other_form['record']}")
            elif pick_form["win_pct"] - other_form["win_pct"] >= 0.30:
                reasons.append(f"• Form advantage: {rank_str}{pick_team} {pick_form['record']} ({pick_form['win_pct']*100:.0f}%) vs {other_team} {other_form['record']}")
            
            # Scoring trends
            if pick_form["avg_margin"] > 10 and other_form["avg_margin"] < -5:
                reasons.append(f"• Scoring: {rank_str}{pick_team} +{pick_form['avg_margin']:.1f} PPG margin vs {other_team} {other_form['avg_margin']:.1f} PPG")
            elif abs(pick_form["avg_margin"] - other_form["avg_margin"]) >= 10:
                reasons.append(f"• Point differential: {rank_str}{pick_team} averaging {pick_form['avg_points_for']:.1f} PPG vs allowing {pick_form['avg_points_against']:.1f} PPG")
    
    # Over/Under Reasoning (using football-specific context)
    if pd.notna(fair_total) and pd.notna(market_total) and abs(edge_total) >= 1:
        pick = "OVER" if edge_total > 0 else "UNDER"
        edge_magnitude = abs(edge_total)
        
        # Use recent scoring form for O/U reasoning
        if home_form and away_form:
            combined_avg = home_form["avg_points_for"] + away_form["avg_points_against"] + away_form["avg_points_for"] + home_form["avg_points_against"]
            combined_avg = combined_avg / 2  # Average of both teams' scoring averages
            
            if edge_magnitude >= 10:
                if pick == "OVER":
                    reasons.append(f"• Total OVER: Model predicts {fair_total:.0f} pts (vs market {market_total:.0f}) - both teams averaging {combined_avg:.1f} PPG")
                else:
                    reasons.append(f"• Total UNDER: Model predicts {fair_total:.0f} pts (vs market {market_total:.0f}) - defensive matchup")
            elif edge_magnitude >= 5:
                reasons.append(f"• {pick} edge: Model total {fair_total:.0f} vs market {market_total:.0f} ({edge_magnitude:.1f} pt difference)")
        else:
            # Fallback to generic edge if no form data
            if edge_magnitude >= 10:
                reasons.append(f"• Strong {pick} lean: Model predicts {fair_total:.0f} vs market {market_total:.0f}")
            elif edge_magnitude >= 5:
                reasons.append(f"• {pick} edge: {edge_magnitude:.1f} pt difference (model {fair_total:.0f} vs market {market_total:.0f})")
        
        # High/low total reasoning with context
        if market_total > 60:
            reasons.append(f"• High-scoring matchup expected (total {market_total:.0f})")
        elif market_total < 45:
            reasons.append(f"• Defensive battle expected (total {market_total:.0f})")
    
    # Weather reasoning (if available - note: weather currently 0% feature importance)
    # Check if we have weather data in the features
    temp_c = row.get("temp_C")
    wind_kph = row.get("wind_kph")
    precip = row.get("precip_flag")
    
    if pd.notna(temp_c) or pd.notna(wind_kph) or pd.notna(precip):
        weather_note = []
        if pd.notna(temp_c) and temp_c < 5:
            weather_note.append(f"Cold conditions ({temp_c:.1f}°C)")
        if pd.notna(wind_kph) and wind_kph > 25:
            weather_note.append(f"High wind ({wind_kph:.1f} km/h - may reduce passing)")
        if pd.notna(precip) and precip:
            weather_note.append("Precipitation expected")
        
        if weather_note:
            reasons.append(f"• Weather factor: {', '.join(weather_note)}")
        elif pd.notna(temp_c):
            reasons.append(f"• Expected weather: {temp_c:.1f}°C")
    
    # Rest days reasoning (most important feature - 62.8% importance)
    home_rest = row.get("home_rest_days")
    away_rest = row.get("away_rest_days")
    
    if pd.notna(home_rest) and pd.notna(away_rest):
        rest_diff = home_rest - away_rest
        if abs(rest_diff) >= 3:
            if rest_diff > 0:
                reasons.append(f"• Rest advantage: {home_team} has {rest_diff} more rest days ({home_rest} vs {away_rest} days) - key factor")
            else:
                reasons.append(f"• Rest advantage: {away_team} has {abs(rest_diff)} more rest days ({away_rest} vs {home_rest} days) - key factor")
        elif home_rest < 7:
            reasons.append(f"• {home_team} on short week ({home_rest} days rest) - potential fatigue factor")
        elif away_rest < 7:
            reasons.append(f"• {away_team} on short week ({away_rest} days rest) - potential fatigue factor")
    
    # Weather reasoning (if available for future games)
    temp_c = row.get("temp_C")
    wind_kph = row.get("wind_kph")
    precip = row.get("precip_flag")
    
    if pd.notna(temp_c) or pd.notna(wind_kph) or pd.notna(precip):
        weather_note = []
        if pd.notna(temp_c) and temp_c < 5:
            weather_note.append(f"Cold ({temp_c:.0f}°C)")
        if pd.notna(wind_kph) and wind_kph > 25:
            weather_note.append(f"High wind ({wind_kph:.0f} km/h - affects passing)")
        if pd.notna(precip) and precip:
            weather_note.append("Precipitation expected")
        
        if weather_note:
            reasons.append(f"• Weather: {', '.join(weather_note)}")
    
    # Confidence level (only add if not enough football-specific reasons)
    if len(reasons) < 2:
        ats_pick, ats_conf = get_ats_pick(fair_spread, market_spread) if pd.notna(fair_spread) and pd.notna(market_spread) else ("N/A", 0)
        ou_pick, ou_conf = get_total_pick(fair_total, market_total) if pd.notna(fair_total) and pd.notna(market_total) else ("N/A", 0)
        max_conf = max(ats_conf, ou_conf)
        
        if max_conf >= 9:
            reasons.append(f"• High confidence ({max_conf}/10)")
        elif max_conf <= 3:
            reasons.append(f"• Low confidence ({max_conf}/10) - smaller edge")
    
    # Fallback if no reasons generated
    if len(reasons) == 0:
        reasons.append("• Model analysis based on team strength (SP+), win probability, and market comparison")
    
    return reasons


def format_odds(american_odds: int) -> str:
    """Format American odds for display.

    Args:
        american_odds: American odds

    Returns:
        Formatted string
    """
    if american_odds > 0:
        return f"+{american_odds}"
    return str(american_odds)


def format_percent(value: float) -> str:
    """Format percentage for display.

    Args:
        value: Value (0-1)

    Returns:
        Formatted string
    """
    return f"{value * 100:.1f}%"


def generate_weekly_markdown(
    df: pd.DataFrame, season: int, week: int, output_path: Optional[str] = None
) -> str:
    """Generate beginner-friendly weekly picks markdown report.

    Args:
        df: DataFrame with picks (must have required columns)
        season: Season year
        week: Week number
        output_path: Optional path to save markdown file

    Returns:
        Markdown string
    """
    # Get team rankings
    rankings = get_team_rankings(season, week)
    
    def format_team_name(team: str) -> str:
        """Format team name with ranking if available."""
        rank = rankings.get(team)
        if rank:
            return f"#{rank} {team}"
        return team
    
    lines = []
    lines.append(f"# CFB Betting Picks - {season} Week {week}\n")
    lines.append("## How to Read This Report\n")
    lines.append("- **Ranking**: Current team ranking (top 25 only)")
    lines.append("- **DK Spread**: DraftKings point spread (negative = home favored)")
    lines.append("- **FD Spread**: FanDuel point spread (negative = home favored)")
    lines.append("- **ATS Pick**: Against The Spread pick (team and spread) with confidence 1-10")
    lines.append("- **ML Pick**: Moneyline (straight up winner) pick with confidence 1-10")
    lines.append("- **Total O/U**: Over/Under total points line")
    lines.append("- **O/U Pick**: Over or Under pick with confidence 1-10")
    lines.append("- **Confidence**: 1-3 = Low, 4-6 = Medium, 7-9 = High, 10 = Very High")
    lines.append("- **Note**: Only DraftKings and FanDuel odds are used\n")
    lines.append("---\n")
    
    # Main picks table
    lines.append("## Game Picks\n")
    lines.append("| Away Team | Home Team | DK Spread | FD Spread | ATS Pick | ML Pick | Total O/U | O/U Pick | Reasoning |")
    lines.append("|-----------|-----------|-----------|-----------|----------|---------|-----------|----------|-----------|")
    
    # Show all games in original order (no sorting by confidence)
    for _, row in df.iterrows():
        home_team = row.get("home_team", "")
        away_team = row.get("away_team", "")
        
        # Format team names with rankings
        home_formatted = format_team_name(home_team)
        away_formatted = format_team_name(away_team)
        
        # DraftKings and FanDuel spreads - show separately
        dk_spread = row.get("dk_spread_home")
        fd_spread = row.get("fd_spread_home")
        market_spread = row.get("market_spread_home")  # Primary spread (DK or FD)
        
        # Format DraftKings spread
        if pd.notna(dk_spread):
            dk_spread_str = f"{dk_spread:+.1f}"
        else:
            dk_spread_str = "N/A"
        
        # Format FanDuel spread
        if pd.notna(fd_spread):
            fd_spread_str = f"{fd_spread:+.1f}"
        else:
            fd_spread_str = "N/A"
        
        # ATS Pick - show team name and spread instead of Home/Away
        fair_spread = row.get("fair_spread_home")
        ats_pick, ats_conf = get_ats_pick(fair_spread, market_spread)

        # DEBUG: Print info for Michigan and Ohio State
        if "Michigan" in home_team or "Michigan" in away_team or "Ohio State" in home_team or "Ohio State" in away_team:
            print(f"DEBUG: {away_team} @ {home_team} | Pick: {ats_pick} | Market: {market_spread} | Fair: {fair_spread}")
            
        # Show picks with confidence >= 1
        # If no market spread, use fair_spread as the "market" for display purposes
        if ats_conf >= 1:
            # Use market_spread if available
            # If falling back to fair_spread (Margin), NEGATE it to convert to Spread Line
            # Margin +10 (Home Wins 10) -> Line -10 (Home Favorite 10)
            display_spread = market_spread if pd.notna(market_spread) else -fair_spread if pd.notna(fair_spread) else 0.0
            
            if ats_pick == "Home":
                # Model picks home team, show home team with spread
                team_pick = home_formatted.split(" (")[0]  # Remove existing spread if present
                
                # DEBUG LOGIC
                # print(f"DEBUG ATS HOME: {team_pick} | Spread: {display_spread}")
                
                if display_spread > 0:
                    # Home is underdog (+X)
                    ats_str = f"{team_pick} (+{display_spread:.1f}) ({ats_conf}/10)"
                elif display_spread < 0:
                    # Home is favorite (-X)
                    # display_spread is negative (e.g. -32.5), so {display_spread:.1f} will include minus sign
                    ats_str = f"{team_pick} ({display_spread:.1f}) ({ats_conf}/10)"
                else:
                    ats_str = f"{team_pick} (Pick) ({ats_conf}/10)"
            else:  # Away
                # Model picks away team, show away team with spread
                team_pick = away_formatted.split(" (")[0]  # Remove existing spread if present
                # Away spread is opposite of home spread
                away_spread = -display_spread
                
                # DEBUG LOGIC
                # print(f"DEBUG ATS AWAY: {team_pick} | HomeSpread: {display_spread} | AwaySpread: {away_spread}")
                
                if away_spread > 0:
                    # Away is underdog (+X)
                    ats_str = f"{team_pick} (+{away_spread:.1f}) ({ats_conf}/10)"
                elif away_spread < 0:
                    # Away is favorite (-X)
                    ats_str = f"{team_pick} ({away_spread:.1f}) ({ats_conf}/10)"
                else:
                    ats_str = f"{team_pick} (Pick) ({ats_conf}/10)"
        else:
            ats_str = "N/A"
        
        # Moneyline Pick - show team name instead of Home/Away
        p_home_win = row.get("p_home_win")
        market_ml_home = row.get("market_ml_home")
        ml_pick, ml_conf = get_ml_pick(p_home_win, market_ml_home)
        # Only show picks with confidence >= 1
        if ml_conf >= 1:
            if ml_pick == "Home":
                # Model picks home team
                team_pick = home_formatted.split(" (")[0]  # Remove existing spread if present
                ml_str = f"{team_pick} ({ml_conf}/10)"
            elif ml_pick == "Away":
                # Model picks away team
                team_pick = away_formatted.split(" (")[0]  # Remove existing spread if present
                ml_str = f"{team_pick} ({ml_conf}/10)"
            else:
                ml_str = f"{ml_pick} ({ml_conf}/10)"
        else:
            ml_str = "N/A"
        
        # Total O/U - show market total if available, otherwise show model's fair total
        market_total = row.get("market_total")
        fair_total = row.get("fair_total")
        if pd.notna(market_total):
            total_str = f"{market_total:.1f}"
        elif pd.notna(fair_total):
            total_str = f"{fair_total:.1f} (est.)"  # Show model's estimate if no market data
        else:
            total_str = "N/A"
        
        # O/U Pick
        ou_pick, ou_conf = get_total_pick(fair_total, market_total)
        # Show picks with confidence >= 1
        # If no market total but we have fair_total, we can't determine OVER/UNDER
        ou_str = f"{ou_pick} ({ou_conf}/10)" if ou_conf >= 1 else "N/A"
        
        # Generate reasoning
        reasoning = generate_pick_reasoning(row, season, week, rankings)
        reasoning_str = "<br>".join(reasoning[:3]) if reasoning else "N/A"  # Show top 3 reasons
        
        lines.append(
            f"| {away_formatted} | {home_formatted} | {dk_spread_str} | {fd_spread_str} | {ats_str} | {ml_str} | {total_str} | {ou_str} | {reasoning_str} |"
            )

        lines.append("")
    lines.append("---\n")
    lines.append("## Important Notes\n")
    lines.append("- Always verify current lines before placing bets")
    lines.append("- Confidence levels are based on model edge vs market (recalibrated)")
    lines.append("- Rankings are based on AP Top 25 poll (top 25 only)")
    lines.append("- Higher confidence = stronger model recommendation")
    lines.append("- **Weather**: Historical weather is tracked, but forecasts for future games are not yet integrated")
    lines.append("- **Rest Days**: Most important factor (62.8% feature importance) - rest advantages shown in reasoning\n")

    markdown = "\n".join(lines)

    if output_path:
        with open(output_path, "w") as f:
            f.write(markdown)

    return markdown


