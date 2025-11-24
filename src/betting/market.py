"""Market odds conversions and fair line calculations."""

import numpy as np


def american_to_prob(american_odds: int) -> float:
    """Convert American odds to probability.

    Args:
        american_odds: American odds (e.g., -110, +150)

    Returns:
        Implied probability (0-1)
    """
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


def prob_to_american(prob: float) -> int:
    """Convert probability to American odds.

    Args:
        prob: Probability (0-1)

    Returns:
        American odds
    """
    if prob >= 0.5:
        return int(-100 * prob / (1 - prob))
    else:
        return int(100 * (1 - prob) / prob)


def fair_spread_from_margin_distribution(
    margin_samples: np.ndarray, percentiles: list[float] = [0.5]
) -> float:
    """Calculate fair spread from margin distribution.

    Args:
        margin_samples: Array of predicted home margin samples
        percentiles: Percentiles to use (default: median)

    Returns:
        Fair spread (home team favored by this many points)
    """
    return float(np.percentile(margin_samples, [p * 100 for p in percentiles])[0])


def fair_total_from_prediction(total_pred: float) -> float:
    """Calculate fair total from prediction.

    Args:
        total_pred: Predicted total points

    Returns:
        Fair total
    """
    return float(total_pred)


