"""Kelly criterion sizing."""

from typing import Optional

import numpy as np

from src.betting.market import american_to_prob


def kelly_fraction(
    prob: float,
    odds: int,
    edge: Optional[float] = None,
    market: str = "ml",
    max_f: float = 0.01,
    kelly_fraction_param: float = 1.0,
) -> float:
    """Calculate fractional Kelly bet size.

    Args:
        prob: Model probability of outcome
        odds: American odds
        edge: Explicit edge (optional, calculated if None)
        market: Market type ('ml', 'spreads', 'totals')
        max_f: Maximum fraction of bankroll per bet
        kelly_fraction_param: Fraction of full Kelly to use (default: 1.0 = full Kelly)

    Returns:
        Kelly fraction (0-1)
    """
    if prob <= 0 or prob >= 1:
        return 0.0

    if market == "ml":
        # Standard Kelly: f = (bp - q) / b
        # where b = odds (as decimal), p = win prob, q = loss prob
        if odds > 0:
            b = odds / 100
        else:
            b = 100 / abs(odds)

        q = 1 - prob
        f = (b * prob - q) / b

    elif market in ["spreads", "totals"]:
        # Heuristic: 0.5% per point of edge, capped
        if edge is None:
            # Calculate edge from prob and odds
            implied_prob = american_to_prob(odds)
            edge = prob - implied_prob

        # Convert edge to points (simplified)
        f = min(abs(edge) * 0.005, max_f)
        if edge < 0:
            f = 0.0  # No bet if negative edge

    else:
        return 0.0

    # Apply fractional Kelly and cap
    f = f * kelly_fraction_param
    f = max(0.0, min(f, max_f))

    return f

