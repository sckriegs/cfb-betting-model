"""Big Ten availability parser (stub)."""

import pandas as pd

from src.data.availability.base import AvailabilityProvider


class BigTenAvailabilityProvider(AvailabilityProvider):
    """Big Ten conference availability provider (stub implementation)."""

    def fetch(self, season: int, week: int) -> pd.DataFrame:
        """Fetch Big Ten availability data.

        TODO: Implement Big Ten availability parsing from official sources.

        Args:
            season: Season year
            week: Week number

        Returns:
            Empty DataFrame with correct schema
        """
        # TODO: Implement Big Ten availability parsing
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


