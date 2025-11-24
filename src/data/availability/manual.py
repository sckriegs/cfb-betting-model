"""Manual CSV availability overrides."""

import logging
from pathlib import Path

import pandas as pd

from src.data.availability.base import AvailabilityProvider
from src.data.persist import get_data_dir

logger = logging.getLogger(__name__)


class ManualAvailabilityProvider(AvailabilityProvider):
    """Manual CSV availability provider."""

    def fetch(self, season: int, week: int) -> pd.DataFrame:
        """Fetch manual availability data from CSV if present.

        Args:
            season: Season year
            week: Week number

        Returns:
            DataFrame with availability data or empty DataFrame
        """
        data_dir = get_data_dir()
        csv_path = data_dir / "availability" / f"manual_overrides_{season}.csv"

        if not csv_path.exists():
            return pd.DataFrame(
                columns=[
                    "team",
                    "unit_off_out",
                    "unit_def_out",
                    "qb_out",
                    "starters_out_off",
                    "starters_out_def",
                    "notes",
                ]
            )

        try:
            df = pd.read_csv(csv_path)
            # Filter by week if column exists
            if "week" in df.columns:
                df = df[df["week"] == week]
            return df
        except Exception as e:
            logger.warning(f"Error reading manual availability CSV: {e}")
            return pd.DataFrame(
                columns=[
                    "team",
                    "unit_off_out",
                    "unit_def_out",
                    "qb_out",
                    "starters_out_off",
                    "starters_out_def",
                    "notes",
                ]
            )


