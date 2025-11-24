"""The Odds API client for live odds."""

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class OddsQuote:
    """Normalized odds quote."""

    season: int
    week: int
    home_team: str
    away_team: str
    bookmaker: str
    market: str  # 'h2h', 'spreads', 'totals'
    line: Optional[float] = None  # Home spread for spreads market
    price_home: Optional[int] = None  # American odds
    price_away: Optional[int] = None  # American odds
    total_points: Optional[float] = None  # For totals market
    price_over: Optional[int] = None  # American odds
    price_under: Optional[int] = None  # American odds
    fetched_at: int = 0  # Unix timestamp


class OddsAPIClient:
    """Client for The Odds API (free tier)."""

    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(
        self,
        api_key: Optional[str] = None,
        region: str = "us",
        markets: str = "h2h,spreads,totals",
        odds_format: str = "american",
    ):
        """Initialize Odds API client.

        Args:
            api_key: API key (reads from ODDS_API_KEY env if None)
            region: Region (default: us)
            markets: Comma-separated markets (default: h2h,spreads,totals)
            odds_format: Odds format (default: american)
        """
        self.api_key = api_key or os.getenv("ODDS_API_KEY")
        if not self.api_key:
            raise ValueError("ODDS_API_KEY must be provided or set in environment")
        self.region = region
        self.markets = markets.split(",")
        self.odds_format = odds_format

    def _get(self, endpoint: str, params: dict) -> requests.Response:
        """Make GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response object
        """
        params["apiKey"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        # Print quota info
        remaining = response.headers.get("x-requests-remaining", "unknown")
        used = response.headers.get("x-requests-used", "unknown")
        print(f"Odds API quota: {used} used, {remaining} remaining")

        return response

    def get_current_odds(
        self, sport: str = "americanfootball_ncaaf", team_name_mapper: Optional[Callable] = None
    ) -> List[OddsQuote]:
        """Get current odds for all games.

        Args:
            sport: Sport key (default: americanfootball_ncaaf)
            team_name_mapper: Function to map team names to canonical form

        Returns:
            List of OddsQuote objects
        """
        params = {
            "regions": self.region,
            "markets": ",".join(self.markets),
            "oddsFormat": self.odds_format,
        }

        try:
            response = self._get(f"/sports/{sport}/odds", params=params)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning("No odds available from The Odds API (404). This may mean:")
                logger.warning("  - CFB season is over")
                logger.warning("  - No games scheduled for this week")
                logger.warning("  - API endpoint issue")
                return []
            raise
        data = response.json()

        quotes = []
        fetched_at = int(time.time())

        for event in data:
            home_team_raw = event.get("home_team", "")
            away_team_raw = event.get("away_team", "")

            # Keep both raw (for matching outcomes) and canonical (for storage)
            home_team = team_name_mapper(home_team_raw) if team_name_mapper else home_team_raw
            away_team = team_name_mapper(away_team_raw) if team_name_mapper else away_team_raw

            # Extract season/week from commence_time
            commence_time_str = event.get("commence_time", "")
            season = None
            week = None
            
            if commence_time_str:
                try:
                    # Parse ISO format datetime
                    commence_dt = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))
                    
                    # Season is the calendar year (CFB season spans two calendar years)
                    # For CFB, season typically starts in August/September
                    # If game is in Aug-Dec, season = that year
                    # If game is in Jan-Jul, season = previous year
                    if commence_dt.month >= 8:
                        season = commence_dt.year
                    else:
                        season = commence_dt.year - 1
                    
                    # Week calculation: approximate based on date
                    # CFB season typically starts around late August/early September
                    # Week 1 is usually around Labor Day weekend
                    if season:
                        # Rough approximation: count weeks from September 1st
                        # Make season_start timezone-aware to match commence_dt
                        from datetime import timezone
                        season_start = datetime(season, 9, 1, tzinfo=timezone.utc)
                        if commence_dt.month < 8:
                            # Game is in next calendar year (bowl season)
                            season_start = datetime(season, 9, 1, tzinfo=timezone.utc)
                            # For bowl games, use a high week number
                            week = 15  # Approximate bowl week
                        else:
                            days_diff = (commence_dt - season_start).days
                            week = max(1, min(15, (days_diff // 7) + 1))
                    
                except (ValueError, AttributeError):
                    # Fallback: use current date
                    now = datetime.now()
                    if now.month >= 8:
                        season = now.year
                    else:
                        season = now.year - 1
                    week = 1
            
            # If still not set, use defaults
            if season is None:
                now = datetime.now()
                season = now.year if now.month >= 8 else now.year - 1
            if week is None:
                week = 1

            for bookmaker in event.get("bookmakers", []):
                book_name = bookmaker.get("key", "unknown")

                for market_data in bookmaker.get("markets", []):
                    market_key = market_data.get("key", "")

                    if market_key == "h2h":
                        outcomes = market_data.get("outcomes", [])
                        # Match using raw team names (with mascots), but store canonical names
                        home_outcome = next((o for o in outcomes if o.get("name") == home_team_raw), None)
                        away_outcome = next((o for o in outcomes if o.get("name") == away_team_raw), None)

                        if home_outcome and away_outcome:
                            quotes.append(
                                OddsQuote(
                                    season=season,
                                    week=week,
                                    home_team=home_team,  # canonical name
                                    away_team=away_team,  # canonical name
                                    bookmaker=book_name,
                                    market="h2h",
                                    price_home=home_outcome.get("price"),
                                    price_away=away_outcome.get("price"),
                                    fetched_at=fetched_at,
                                )
                            )

                    elif market_key == "spreads":
                        outcomes = market_data.get("outcomes", [])
                        # Match using raw team names (with mascots), but store canonical names
                        home_outcome = next((o for o in outcomes if o.get("name") == home_team_raw), None)
                        away_outcome = next((o for o in outcomes if o.get("name") == away_team_raw), None)

                        if home_outcome:
                            quotes.append(
                                OddsQuote(
                                    season=season,
                                    week=week,
                                    home_team=home_team,  # canonical name
                                    away_team=away_team,  # canonical name
                                    bookmaker=book_name,
                                    market="spreads",
                                    line=home_outcome.get("point"),
                                    price_home=home_outcome.get("price"),
                                    price_away=away_outcome.get("price") if away_outcome else None,
                                    fetched_at=fetched_at,
                                )
                            )

                    elif market_key == "totals":
                        outcomes = market_data.get("outcomes", [])
                        over_outcome = next((o for o in outcomes if "over" in o.get("name", "").lower()), None)
                        under_outcome = next((o for o in outcomes if "under" in o.get("name", "").lower()), None)

                        if over_outcome:
                            quotes.append(
                                OddsQuote(
                                    season=season,
                                    week=week,
                                    home_team=home_team,  # canonical name
                                    away_team=away_team,  # canonical name
                                    bookmaker=book_name,
                                    market="totals",
                                    total_points=over_outcome.get("point"),
                                    price_over=over_outcome.get("price"),
                                    price_under=under_outcome.get("price") if under_outcome else None,
                                    fetched_at=fetched_at,
                                )
                            )

        return quotes


