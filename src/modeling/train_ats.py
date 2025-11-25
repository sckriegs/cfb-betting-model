"""Train ATS model."""

import logging
import pickle
from pathlib import Path

import pandas as pd

from src.data.persist import get_data_dir
from src.modeling.models import ATSModel
from src.modeling.splits import get_walk_forward_splits

logger = logging.getLogger(__name__)


def prepare_ats_data(df: pd.DataFrame, market_spread_col: str = "market_spread_home") -> tuple[pd.DataFrame, pd.Series]:
    """Prepare data for ATS training.

    Args:
        df: Feature DataFrame
        market_spread_col: Column name for market spread

    Returns:
        Tuple of (X, y) where y is binary (1 if home covers)
    """
    # CRITICAL FIX: Only train on games with actual market spreads
    # Games without market spreads default to 0, which makes the target = home wins (wrong!)
    # Filter to only games with valid market spreads
    if market_spread_col not in df.columns:
        logger.warning(f"Market spread column {market_spread_col} not found, using 0")
        df[market_spread_col] = 0.0
    
    # Filter to only games with valid market spreads (not null, not 0) and valid home_margin
    # This ensures we're training on the correct target: home covers, not home wins
    # And ensures we have the outcome
    valid_spreads = df[
        df[market_spread_col].notna() & 
        (df[market_spread_col] != 0.0) & 
        df["home_margin"].notna()
    ].copy()
    
    if len(valid_spreads) == 0:
        logger.warning("No games with valid market spreads found for ATS training")
        # Fallback: use all data but this is not ideal
        valid_spreads = df.copy()
    
    logger.info(f"Training ATS model on {len(valid_spreads)}/{len(df)} games with valid market spreads ({len(valid_spreads)/len(df)*100:.1f}%)")
    
    # Create target: home_covers = (home_margin - market_spread_home > 0)
    y = (valid_spreads["home_margin"] - valid_spreads[market_spread_col] > 0).astype(int)

    # Select feature columns (exclude targets and identifiers)
    # We keep market_spread_col in the features so the model knows the hurdle
    exclude_cols = [
        "home_team",
        "away_team",
        "season",
        "week",
        "kickoff_dt",
        "home_margin",
        "total_points",
        # market_spread_col, # KEEP THIS!
    ]
    feature_cols = [c for c in valid_spreads.columns if c not in exclude_cols]

    X = valid_spreads[feature_cols].copy()

    # Fill missing values
    X = X.fillna(0)

    return X, y


def train_ats_model(season: int, features_df: pd.DataFrame) -> ATSModel:
    """Train ATS model for a season using walk-forward splits.

    Args:
        season: Season year
        features_df: Full features DataFrame

    Returns:
        Trained ATSModel
    """
    logger.info(f"Training ATS model for season {season}...")

    # Get splits up to this season
    train_df = features_df[features_df["season"] < season].copy()

    if train_df.empty:
        logger.warning(f"No training data available for season {season}")
        return None

    # Prepare data
    X, y = prepare_ats_data(train_df)

    if X.empty or y.empty:
        logger.warning(f"No valid training data for season {season}")
        return None

    # Train model
    model = ATSModel(use_calibration=True, random_state=42)
    model.fit(X, y)

    # Save model
    data_dir = get_data_dir()
    models_dir = data_dir / "models" / "ats"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"{season}.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    logger.info(f"Saved ATS model to {model_path}")

    return model
