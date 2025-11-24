"""Parquet read/write utilities with idempotent operations."""

import os
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow.parquet as pq


def ensure_dir(path: Path) -> None:
    """Ensure directory exists.

    Args:
        path: Directory path
    """
    path.mkdir(parents=True, exist_ok=True)


def write_parquet(df: pd.DataFrame, filepath: str, overwrite: bool = False) -> None:
    """Write DataFrame to parquet file.

    Args:
        df: DataFrame to write
        filepath: Output file path
        overwrite: If False, skip if file exists
    """
    path = Path(filepath)
    ensure_dir(path.parent)

    if path.exists() and not overwrite:
        return

    df.to_parquet(path, engine="pyarrow", index=False)


def read_parquet(filepath: str) -> Optional[pd.DataFrame]:
    """Read parquet file to DataFrame.

    Args:
        filepath: Input file path

    Returns:
        DataFrame or None if file doesn't exist
    """
    path = Path(filepath)
    if not path.exists():
        return None
    return pd.read_parquet(path, engine="pyarrow")


def get_data_dir() -> Path:
    """Get base data directory.

    Returns:
        Path to data directory
    """
    # Assume we're running from project root
    base = Path(__file__).parent.parent.parent
    data_dir = base / "data"
    ensure_dir(data_dir)
    return data_dir


