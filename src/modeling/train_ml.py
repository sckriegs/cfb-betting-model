"""Train moneyline model."""

import logging
import pickle
from pathlib import Path

import pandas as pd

from src.data.persist import get_data_dir
from src.modeling.models import MoneylineModel

logger = logging.getLogger(__name__)


def prepare_ml_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare data for moneyline training.

    Args:
        df: Feature DataFrame

    Returns:
        Tuple of (X, y) where y is binary (1 if home wins)
    """
    # Create target: home_win = (home_margin > 0)
    y = (df["home_margin"] > 0).astype(int)

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
    feature_cols = [c for c in df.columns if c not in exclude_cols]

    X = df[feature_cols].copy()

    # Fill missing values
    X = X.fillna(0)

    return X, y


def train_ml_model(season: int, features_df: pd.DataFrame) -> MoneylineModel:
    """Train moneyline model for a season.

    Args:
        season: Season year
        features_df: Full features DataFrame

    Returns:
        Trained MoneylineModel
    """
    logger.info(f"Training moneyline model for season {season}...")

    # Get splits up to this season
    train_df = features_df[features_df["season"] < season].copy()

    if train_df.empty:
        logger.warning(f"No training data available for season {season}")
        return None

    # Prepare data
    X, y = prepare_ml_data(train_df)

    if X.empty or y.empty:
        logger.warning(f"No valid training data for season {season}")
        return None

    # Train model
    model = MoneylineModel(use_calibration=True, random_state=42)
    model.fit(X, y)

    # Save model
    data_dir = get_data_dir()
    models_dir = data_dir / "models" / "ml"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"{season}.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    logger.info(f"Saved moneyline model to {model_path}")

    return model


