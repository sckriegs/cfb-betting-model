"""Odds snapshot caching."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from src.data.odds.odds_api import OddsQuote
from src.data.persist import get_data_dir, read_parquet, write_parquet

logger = logging.getLogger(__name__)


def save_odds_snapshot(quotes: List[OddsQuote], season: int, week: int) -> None:
    """Save odds snapshot to parquet.

    Args:
        quotes: List of OddsQuote objects
        season: Season year
        week: Week number
    """
    data_dir = get_data_dir()
    odds_dir = data_dir / "odds"
    odds_dir.mkdir(parents=True, exist_ok=True)

    # Convert to DataFrame
    records = []
    for quote in quotes:
        records.append(
            {
                "season": quote.season,
                "week": quote.week,
                "home_team": quote.home_team,
                "away_team": quote.away_team,
                "bookmaker": quote.bookmaker,
                "market": quote.market,
                "line": quote.line,
                "price_home": quote.price_home,
                "price_away": quote.price_away,
                "total_points": quote.total_points,
                "price_over": quote.price_over,
                "price_under": quote.price_under,
                "fetched_at": quote.fetched_at,
            }
        )

    df = pd.DataFrame(records)

    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{season}_w{week}_{timestamp}.parquet"
    filepath = odds_dir / filename

    write_parquet(df, str(filepath), overwrite=True)
    logger.info(f"Saved odds snapshot to {filepath}")


def load_latest_odds_snapshot(season: int, week: int) -> Optional[pd.DataFrame]:
    """Load latest odds snapshot for a season/week.

    Args:
        season: Season year
        week: Week number

    Returns:
        DataFrame with odds data or None
    """
    data_dir = get_data_dir()
    odds_dir = data_dir / "odds"

    if not odds_dir.exists():
        return None

    # Find matching files
    pattern = f"{season}_w{week}_*.parquet"
    matching_files = list(odds_dir.glob(pattern))

    if not matching_files:
        return None

    # Get most recent
    latest_file = max(matching_files, key=lambda p: p.stat().st_mtime)
    return read_parquet(str(latest_file))


