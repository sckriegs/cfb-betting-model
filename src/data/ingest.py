"""Data ingestion from CFBD API."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from src.data.cfbd_client import CFBDClient
from src.data.persist import get_data_dir, read_parquet, write_parquet

logger = logging.getLogger(__name__)


def ingest_reference(client: Optional[CFBDClient] = None) -> None:
    """Ingest reference data (teams, venues, conferences).

    Args:
        client: CFBD client instance (creates new if None)
    """
    if client is None:
        client = CFBDClient()

    data_dir = get_data_dir()
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Ingesting teams...")
    teams = client.get_teams()
    write_parquet(teams, str(raw_dir / "teams" / "teams.parquet"))

    logger.info("Ingesting venues...")
    venues = client.get_venues()
    write_parquet(venues, str(raw_dir / "venues" / "venues.parquet"))

    logger.info("Reference data ingestion complete")


def ingest_season(season: int, client: Optional[CFBDClient] = None) -> None:
    """Ingest data for a single season.

    Args:
        season: Season year
        client: CFBD client instance (creates new if None)
    """
    if client is None:
        client = CFBDClient()

    data_dir = get_data_dir()
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Ingesting season {season}...")

    # Games
    logger.info(f"  Fetching games for {season}...")
    games = client.get_games(season=season)
    if not games.empty:
        write_parquet(games, str(raw_dir / "games" / f"{season}.parquet"))

    # Lines (closing lines where available)
    logger.info(f"  Fetching lines for {season}...")
    lines = client.get_lines(season=season)
    if not lines.empty:
        write_parquet(lines, str(raw_dir / "lines" / f"{season}.parquet"))

    # Season stats
    logger.info(f"  Fetching season stats for {season}...")
    season_stats = client.get_stats_season(season=season)
    if not season_stats.empty:
        write_parquet(season_stats, str(raw_dir / "stats_season" / f"{season}.parquet"))

    # Game stats
    logger.info(f"  Fetching game stats for {season}...")
    game_stats = client.get_stats_game(season=season)
    if not game_stats.empty:
        write_parquet(game_stats, str(raw_dir / "stats_game" / f"{season}.parquet"))

    # Ratings
    logger.info(f"  Fetching SP+ ratings for {season}...")
    sp_ratings = client.get_ratings_sp(season=season)
    if not sp_ratings.empty:
        write_parquet(sp_ratings, str(raw_dir / "ratings_sp" / f"{season}.parquet"))

    logger.info(f"  Fetching SRS ratings for {season}...")
    srs_ratings = client.get_ratings_srs(season=season)
    if not srs_ratings.empty:
        write_parquet(srs_ratings, str(raw_dir / "ratings_srs" / f"{season}.parquet"))

    logger.info(f"Season {season} ingestion complete")


def ingest_range(start: int, end: int, client: Optional[CFBDClient] = None) -> None:
    """Ingest data for a range of seasons.

    Args:
        start: Start season (inclusive)
        end: End season (inclusive)
        client: CFBD client instance (creates new if None)
    """
    if client is None:
        client = CFBDClient()

    logger.info(f"Ingesting seasons {start} to {end}...")

    # Ingest reference data once
    ingest_reference(client)

    # Ingest each season
    for season in range(start, end + 1):
        try:
            ingest_season(season, client)
        except Exception as e:
            logger.error(f"Error ingesting season {season}: {e}")
            continue

    logger.info("Range ingestion complete")


