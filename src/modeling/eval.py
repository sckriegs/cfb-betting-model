"""Backtest evaluation."""

import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error, roc_auc_score

from src.betting.kelly import kelly_fraction
from src.betting.market import american_to_prob
from src.data.persist import get_data_dir
from src.modeling.splits import get_walk_forward_splits
from src.modeling.train_ats import prepare_ats_data
from src.modeling.train_ml import prepare_ml_data
from src.modeling.train_total import prepare_total_data

logger = logging.getLogger(__name__)


def load_model(model_type: str, season: int):
    """Load a trained model.

    Args:
        model_type: 'ats', 'ml', or 'total'
        season: Season year

    Returns:
        Loaded model or None
    """
    data_dir = get_data_dir()
    model_path = data_dir / "models" / model_type / f"{season}.pkl"

    if not model_path.exists():
        return None

    with open(model_path, "rb") as f:
        return pickle.load(f)


def evaluate_ats(
    test_df: pd.DataFrame, model, market_spread_col: str = "market_spread_home"
) -> dict:
    """Evaluate ATS model.

    Args:
        test_df: Test DataFrame
        model: Trained ATS model
        market_spread_col: Column name for market spread

    Returns:
        Dictionary with metrics
    """
    if model is None:
        return {}

    X, y_true = prepare_ats_data(test_df, market_spread_col)

    if X.empty:
        return {}

    # Ensure feature columns match model's expected features
    if hasattr(model, 'feature_names') and model.feature_names:
        # Reorder and select only the features the model was trained on
        missing_features = set(model.feature_names) - set(X.columns)
        if missing_features:
            # Add missing features as zeros
            for feat in missing_features:
                X[feat] = 0.0
        # Select only the features the model expects, in the right order
        X = X[model.feature_names]

    y_pred_proba = model.predict_proba(X)[:, 1]
    y_pred = (y_pred_proba > 0.5).astype(int)

    # Handle edge case where y_true has only one class
    unique_labels = np.unique(y_true)
    log_loss_val = 0.0
    if len(unique_labels) > 1:
        log_loss_val = log_loss(y_true, y_pred_proba)
    else:
        # If only one class, log loss is undefined, use 0 or a default value
        log_loss_val = 0.0

    metrics = {
        "brier": brier_score_loss(y_true, y_pred_proba),
        "log_loss": log_loss_val,
        "hit_rate": (y_pred == y_true).mean(),
        "n_samples": len(y_true),
    }

    return metrics


def evaluate_ml(test_df: pd.DataFrame, model) -> dict:
    """Evaluate moneyline model.

    Args:
        test_df: Test DataFrame
        model: Trained moneyline model

    Returns:
        Dictionary with metrics
    """
    if model is None:
        return {}

    X, y_true = prepare_ml_data(test_df)

    if X.empty:
        return {}

    # Ensure feature columns match model's expected features
    if hasattr(model, 'feature_names') and model.feature_names:
        # Reorder and select only the features the model was trained on
        missing_features = set(model.feature_names) - set(X.columns)
        if missing_features:
            # Add missing features as zeros
            for feat in missing_features:
                X[feat] = 0.0
        # Select only the features the model expects, in the right order
        X = X[model.feature_names]

    y_pred_proba = model.predict_proba(X)[:, 1]
    y_pred = (y_pred_proba > 0.5).astype(int)

    # Handle edge case where y_true has only one class
    unique_labels = np.unique(y_true)
    log_loss_val = 0.0
    if len(unique_labels) > 1:
        log_loss_val = log_loss(y_true, y_pred_proba)
    else:
        log_loss_val = 0.0

    metrics = {
        "brier": brier_score_loss(y_true, y_pred_proba),
        "log_loss": log_loss_val,
        "roc_auc": roc_auc_score(y_true, y_pred_proba) if len(unique_labels) > 1 else 0.0,
        "hit_rate": (y_pred == y_true).mean(),
        "n_samples": len(y_true),
    }

    return metrics


def evaluate_total(test_df: pd.DataFrame, model, market_total_col: str = "market_total") -> dict:
    """Evaluate totals model.

    Args:
        test_df: Test DataFrame
        model: Trained totals model
        market_total_col: Column name for market total

    Returns:
        Dictionary with metrics
    """
    if model is None:
        return {}

    X, y_true = prepare_total_data(test_df)

    if X.empty:
        return {}

    # Ensure feature columns match model's expected features
    if hasattr(model, 'feature_names') and model.feature_names:
        # Reorder and select only the features the model was trained on
        missing_features = set(model.feature_names) - set(X.columns)
        if missing_features:
            # Add missing features as zeros
            for feat in missing_features:
                X[feat] = 0.0
        # Select only the features the model expects, in the right order
        X = X[model.feature_names]

    y_pred = model.predict(X)

    if market_total_col in test_df.columns:
        # Align market_total with X using the index
        # X has only valid rows (subset of test_df)
        market_total = test_df.loc[X.index, market_total_col]
        
        # Drop NaNs from market_total for comparison
        valid_mask = market_total.notna()
        if valid_mask.any():
            mae_vs_market = mean_absolute_error(market_total[valid_mask], y_pred[valid_mask])
            correlation = np.corrcoef(market_total[valid_mask], y_pred[valid_mask])[0, 1] if len(market_total[valid_mask]) > 1 else 0.0
            
            # Calculate O/U Hit Rate
            # Align y_true (actual total) with the valid mask
            # y_true corresponds to X, and market_total corresponds to X.
            y_true_valid = y_true[valid_mask]
            y_pred_valid = y_pred[valid_mask]
            market_valid = market_total[valid_mask]
            
            # Determine Picks (Model vs Market)
            pick_over = y_pred_valid > market_valid
            pick_under = y_pred_valid < market_valid
            
            # Determine Outcomes (Actual vs Market)
            actual_over = y_true_valid > market_valid
            actual_under = y_true_valid < market_valid
            
            # Calculate Hits
            # Hit if (Pick Over AND Actual Over) OR (Pick Under AND Actual Under)
            hits = (pick_over & actual_over) | (pick_under & actual_under)
            
            # Filter out pushes (Actual == Market) and "No Pick" (Model == Market) from denominator
            # Usually we care about cases where we made a pick and there was a result
            valid_bet_mask = (pick_over | pick_under) & (y_true_valid != market_valid)
            
            if valid_bet_mask.any():
                hit_rate = hits[valid_bet_mask].mean()
            else:
                hit_rate = 0.0
        else:
            mae_vs_market = None
            correlation = None
            hit_rate = None
    else:
        mae_vs_market = None
        correlation = None
        hit_rate = None

    metrics = {
        "mae": mean_absolute_error(y_true, y_pred),
        "mae_vs_market": mae_vs_market,
        "correlation": correlation,
        "hit_rate": hit_rate,
        "n_samples": len(y_true),
    }

    return metrics


def backtest(
    features_df: pd.DataFrame,
    start_season: int = 2014,
    end_season: int = 2024,
    kelly_fraction_param: float = 0.25,
    max_kelly: float = 0.01,
) -> pd.DataFrame:
    """Run backtest with walk-forward validation.

    Args:
        features_df: Full features DataFrame
        start_season: Start season (inclusive)
        end_season: End season (inclusive)
        kelly_fraction_param: Fraction of full Kelly to use
        max_kelly: Maximum Kelly fraction per bet

    Returns:
        DataFrame with backtest results
    """
    logger.info(f"Running backtest from {start_season} to {end_season}...")

    # Filter to backtest period
    backtest_df = features_df[
        (features_df["season"] >= start_season) & (features_df["season"] <= end_season)
    ].copy()

    if backtest_df.empty:
        logger.warning("No data for backtest period")
        return pd.DataFrame()

    # Get walk-forward splits
    splits = get_walk_forward_splits(backtest_df)

    results = []

    for train_df, test_df in splits:
        season = test_df["season"].iloc[0]
        week = test_df["week"].iloc[0]

        logger.info(f"Evaluating {season} Week {week}...")

        # Load models (trained on data up to this week)
        ats_model = load_model("ats", season)
        ml_model = load_model("ml", season)
        total_model = load_model("total", season)

        # Evaluate each model
        ats_metrics = evaluate_ats(test_df, ats_model)
        ml_metrics = evaluate_ml(test_df, ml_model)
        total_metrics = evaluate_total(test_df, total_model)

        # Portfolio simulation (simplified)
        # TODO: Implement full portfolio simulation with actual betting logic

        result = {
            "season": season,
            "week": week,
            "n_games": len(test_df),
            **{f"ats_{k}": v for k, v in ats_metrics.items()},
            **{f"ml_{k}": v for k, v in ml_metrics.items()},
            **{f"total_{k}": v for k, v in total_metrics.items()},
        }

        results.append(result)

    results_df = pd.DataFrame(results)

    # Save results
    data_dir = get_data_dir()
    reports_dir = data_dir.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    results_path = reports_dir / f"backtest_{start_season}_{end_season}.csv"
    results_df.to_csv(results_path, index=False)
    logger.info(f"Saved backtest results to {results_path}")

    return results_df
