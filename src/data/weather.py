"""Weather data integration using Meteostat."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from meteostat import Hourly, Point

from src.data.persist import get_data_dir, read_parquet, write_parquet

logger = logging.getLogger(__name__)


def fetch_weather_for_game(
    lat: float, lon: float, kickoff_dt: datetime
) -> dict[str, Optional[float]]:
    """Fetch weather data for a game at kickoff.

    Args:
        lat: Venue latitude
        lon: Venue longitude
        kickoff_dt: Kickoff datetime

    Returns:
        Dictionary with temp_C, wind_kph, precip_flag
    """
    try:
        location = Point(lat, lon)
        start = kickoff_dt.replace(minute=0, second=0, microsecond=0)
        end = start.replace(hour=start.hour + 1)

        data = Hourly(location, start, end)
        df = data.fetch()

        if df.empty:
            logger.warning(f"No weather data for {lat}, {lon} at {kickoff_dt}")
            return {"temp_C": None, "wind_kph": None, "precip_flag": None}

        # Get the hour closest to kickoff
        row = df.iloc[0]

        temp_c = float(row.get("temp", None)) if pd.notna(row.get("temp")) else None
        wind_kph = float(row.get("wspd", None)) if pd.notna(row.get("wspd")) else None
        precip = row.get("prcp", 0)
        precip_flag = 1.0 if pd.notna(precip) and float(precip) > 0 else 0.0

        return {
            "temp_C": temp_c,
            "wind_kph": wind_kph,
            "precip_flag": precip_flag,
        }
    except Exception as e:
        logger.warning(f"Error fetching weather for {lat}, {lon} at {kickoff_dt}: {e}")
        return {"temp_C": None, "wind_kph": None, "precip_flag": None}


def fetch_weather_for_season(
    games_df: pd.DataFrame, season: int, force_refresh: bool = False
) -> pd.DataFrame:
    """Fetch weather data for all games in a season.

    Args:
        games_df: DataFrame with games (must have venue lat/lon and start_date)
        season: Season year
        force_refresh: If True, refetch even if cached

    Returns:
        DataFrame with weather data merged
    """
    data_dir = get_data_dir()
    weather_dir = data_dir / "weather"
    weather_dir.mkdir(parents=True, exist_ok=True)
    cache_path = weather_dir / f"{season}.parquet"

    if not force_refresh:
        cached = read_parquet(str(cache_path))
        if cached is not None:
            logger.info(f"Using cached weather for {season}")
            return cached

    logger.info(f"Fetching weather for {season}...")

    weather_records = []
    for _, game in games_df.iterrows():
        if pd.isna(game.get("venue_latitude")) or pd.isna(game.get("venue_longitude")):
            weather_records.append(
                {
                    "game_id": game.get("id"),
                    "temp_C": None,
                    "wind_kph": None,
                    "precip_flag": None,
                }
            )
            continue

        try:
            kickoff_str = game.get("start_date")
            if pd.isna(kickoff_str):
                weather_records.append(
                    {
                        "game_id": game.get("id"),
                        "temp_C": None,
                        "wind_kph": None,
                        "precip_flag": None,
                    }
                )
                continue

            kickoff_dt = pd.to_datetime(kickoff_str)
            weather = fetch_weather_for_game(
                float(game["venue_latitude"]),
                float(game["venue_longitude"]),
                kickoff_dt,
            )
            weather["game_id"] = game.get("id")
            weather_records.append(weather)
        except Exception as e:
            logger.warning(f"Error processing game {game.get('id')}: {e}")
            weather_records.append(
                {
                    "game_id": game.get("id"),
                    "temp_C": None,
                    "wind_kph": None,
                    "precip_flag": None,
                }
            )

    weather_df = pd.DataFrame(weather_records)
    write_parquet(weather_df, str(cache_path), overwrite=True)

    return weather_df


