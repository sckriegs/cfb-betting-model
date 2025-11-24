"""Base interface for availability providers."""

from abc import ABC, abstractmethod

import pandas as pd


class AvailabilityProvider(ABC):
    """Base class for availability data providers."""

    @abstractmethod
    def fetch(self, season: int, week: int) -> pd.DataFrame:
        """Fetch availability data for a season/week.

        Args:
            season: Season year
            week: Week number

        Returns:
            DataFrame with columns: team, unit_off_out, unit_def_out, qb_out,
            starters_out_off, starters_out_def, notes
        """
        pass


