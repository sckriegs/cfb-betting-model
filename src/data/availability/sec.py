"""SEC availability parser (stub)."""

import pandas as pd

from src.data.availability.base import AvailabilityProvider


class SECAvailabilityProvider(AvailabilityProvider):
    """SEC conference availability provider (stub implementation)."""

    def fetch(self, season: int, week: int) -> pd.DataFrame:
        """Fetch SEC availability data.

        TODO: Implement SEC availability parsing from official sources.

        Args:
            season: Season year
            week: Week number

        Returns:
            Empty DataFrame with correct schema
        """
        # TODO: Implement SEC availability parsing
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


