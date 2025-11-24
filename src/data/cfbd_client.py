"""CFBD API client with retry logic."""

import os
from typing import Optional

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from dotenv import load_dotenv

load_dotenv()


class CFBDClient:
    """Client for College Football Data API."""

    BASE_URL = "https://api.collegefootballdata.com"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize CFBD client.

        Args:
            api_key: CFBD API key. If None, reads from CFBD_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("CFBD_API_KEY")
        if not self.api_key:
            raise ValueError("CFBD_API_KEY must be provided or set in environment")
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _get(self, endpoint: str, params: Optional[dict] = None) -> requests.Response:
        """Make GET request with retry logic.

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters

        Returns:
            Response object
        """
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        return response

    def get_games(
        self, season: int, week: Optional[int] = None, team: Optional[str] = None
    ) -> pd.DataFrame:
        """Get games for a season/week.

        Args:
            season: Season year
            week: Week number (optional)
            team: Team name filter (optional)

        Returns:
            DataFrame with game data
        """
        params = {"year": season}
        if week is not None:
            params["week"] = week
        if team:
            params["team"] = team

        response = self._get("/games", params=params)
        data = response.json()
        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_lines(
        self, season: int, week: Optional[int] = None, team: Optional[str] = None
    ) -> pd.DataFrame:
        """Get betting lines for a season/week.

        Args:
            season: Season year
            week: Week number (optional)
            team: Team name filter (optional)

        Returns:
            DataFrame with line data
        """
        params = {"year": season}
        if week is not None:
            params["week"] = week
        if team:
            params["team"] = team

        response = self._get("/lines", params=params)
        data = response.json()
        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_teams(self, conference: Optional[str] = None) -> pd.DataFrame:
        """Get team information.

        Args:
            conference: Conference filter (optional)

        Returns:
            DataFrame with team data
        """
        params = {}
        if conference:
            params["conference"] = conference

        response = self._get("/teams", params=params)
        data = response.json()
        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_venues(self) -> pd.DataFrame:
        """Get venue information.

        Returns:
            DataFrame with venue data
        """
        response = self._get("/venues")
        data = response.json()
        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_stats_game(self, season: int, week: Optional[int] = None) -> pd.DataFrame:
        """Get game-level statistics.

        Args:
            season: Season year
            week: Week number (optional)

        Returns:
            DataFrame with game stats
        """
        params = {"year": season}
        if week is not None:
            params["week"] = week

        response = self._get("/stats/game/advanced", params=params)
        data = response.json()
        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_stats_season(self, season: int, team: Optional[str] = None) -> pd.DataFrame:
        """Get season-level statistics.

        Args:
            season: Season year
            team: Team name filter (optional)

        Returns:
            DataFrame with season stats
        """
        params = {"year": season}
        if team:
            params["team"] = team

        response = self._get("/stats/season/advanced", params=params)
        data = response.json()
        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_ratings_sp(self, season: int) -> pd.DataFrame:
        """Get SP+ ratings for a season.

        Args:
            season: Season year

        Returns:
            DataFrame with SP+ ratings
        """
        params = {"year": season}
        response = self._get("/ratings/sp", params=params)
        data = response.json()
        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_ratings_srs(self, season: int) -> pd.DataFrame:
        """Get SRS ratings for a season.

        Args:
            season: Season year

        Returns:
            DataFrame with SRS ratings
        """
        params = {"year": season}
        response = self._get("/ratings/srs", params=params)
        data = response.json()
        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_rankings(self, season: int, week: Optional[int] = None, poll: str = "ap") -> pd.DataFrame:
        """Get AP poll rankings for a season/week.

        Args:
            season: Season year
            week: Week number (optional, uses latest if not provided)
            poll: Poll type - "ap" (AP Poll) or "cfp" (CFP Rankings)

        Returns:
            DataFrame with rankings data
        """
        params = {"year": season, "seasonType": "regular"}
        if week is not None:
            params["week"] = week
        if poll:
            params["poll"] = poll

        response = self._get("/rankings", params=params)
        data = response.json()
        return pd.DataFrame(data) if data else pd.DataFrame()


