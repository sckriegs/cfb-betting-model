"""Train totals model."""

import logging
import pickle
from pathlib import Path

import pandas as pd

from src.data.persist import get_data_dir
from src.modeling.models import TotalsModel

logger = logging.getLogger(__name__)


def prepare_total_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare data for totals training.

    Args:
        df: Feature DataFrame

    Returns:
        Tuple of (X, y) where y is total points
    """
    # Filter to valid target data
    valid_df = df.dropna(subset=["total_points"]).copy()
    
    if valid_df.empty:
        return pd.DataFrame(), pd.Series()
    
    # Target is total_points
    y = valid_df["total_points"].copy()

    # Select feature columns
    exclude_cols = [
        "home_team",
        "away_team",
        "season",
        "week",
        "kickoff_dt",
        "home_margin",
        "total_points",
    ]
    feature_cols = [c for c in valid_df.columns if c not in exclude_cols]

    X = valid_df[feature_cols].copy()

    # Fill missing values
    X = X.fillna(0)

    return X, y


def train_total_model(season: int, features_df: pd.DataFrame) -> TotalsModel:
    """Train totals model for a season.

    Args:
        season: Season year
        features_df: Full features DataFrame

    Returns:
        Trained TotalsModel
    """
    logger.info(f"Training totals model for season {season}...")

    # Get splits up to this season
    train_df = features_df[features_df["season"] < season].copy()

    if train_df.empty:
        logger.warning(f"No training data available for season {season}")
        return None

    # Prepare data
    X, y = prepare_total_data(train_df)

    if X.empty or y.empty:
        logger.warning(f"No valid training data for season {season}")
        return None

    # Train model
    model = TotalsModel(random_state=42)
    model.fit(X, y)

    # Save model
    data_dir = get_data_dir()
    models_dir = data_dir / "models" / "total"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"{season}.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    logger.info(f"Saved totals model to {model_path}")

    return model
