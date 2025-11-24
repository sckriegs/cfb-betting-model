"""Pydantic schemas for feature data."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FairTargets(BaseModel):
    """Fair prediction targets."""

    home_margin: float
    total_points: float


class GameFeatures(BaseModel):
    """Per-game feature row schema."""

    home_team: str
    away_team: str
    season: int
    week: int
    kickoff_dt: datetime
    fair_targets: FairTargets

    # Rolling stats (last 3/5/10 games)
    home_success_rate_3: Optional[float] = None
    home_success_rate_5: Optional[float] = None
    home_success_rate_10: Optional[float] = None
    away_success_rate_3: Optional[float] = None
    away_success_rate_5: Optional[float] = None
    away_success_rate_10: Optional[float] = None

    # Priors
    home_sp_plus: Optional[float] = None
    home_srs: Optional[float] = None
    away_sp_plus: Optional[float] = None
    away_srs: Optional[float] = None

    # Rest and travel
    home_rest_days: Optional[int] = None
    away_rest_days: Optional[int] = None
    home_short_week: Optional[bool] = None
    away_short_week: Optional[bool] = None
    home_bye_week: Optional[bool] = None
    away_bye_week: Optional[bool] = None
    travel_distance_miles: Optional[float] = None
    timezone_delta: Optional[int] = None

    # Weather
    temp_C: Optional[float] = None
    wind_kph: Optional[float] = None
    precip_flag: Optional[float] = None

    # Availability
    home_qb_out: Optional[int] = 0
    away_qb_out: Optional[int] = 0
    home_starters_out_off: Optional[int] = 0
    away_starters_out_off: Optional[int] = 0
    home_starters_out_def: Optional[int] = 0
    away_starters_out_def: Optional[int] = 0

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


