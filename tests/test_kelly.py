"""Tests for Kelly sizing."""

import pytest

from src.betting.kelly import kelly_fraction


def test_kelly_fraction_ml_positive_edge():
    """Test Kelly fraction for moneyline with positive edge."""
    # Model says 60% chance, odds imply 50% (even money)
    prob = 0.6
    odds = 100  # +100 = even money

    f = kelly_fraction(prob, odds, market="ml")

    assert f > 0
    assert f <= 0.01  # Should be capped at max_f


def test_kelly_fraction_ml_negative_edge():
    """Test Kelly fraction for moneyline with negative edge."""
    # Model says 40% chance, odds imply 50%
    prob = 0.4
    odds = 100

    f = kelly_fraction(prob, odds, market="ml")

    assert f == 0.0  # No bet on negative edge


def test_kelly_fraction_spreads():
    """Test Kelly fraction for spreads."""
    prob = 0.55
    odds = -110
    edge = 0.05  # 5 point edge

    f = kelly_fraction(prob, odds, edge=edge, market="spreads")

    assert f >= 0
    assert f <= 0.01


def test_kelly_fraction_caps():
    """Test that Kelly fraction respects caps."""
    prob = 0.9  # Very high probability
    odds = -200  # Heavy favorite

    f = kelly_fraction(prob, odds, market="ml", max_f=0.01)

    assert f <= 0.01


def test_kelly_fraction_fractional():
    """Test fractional Kelly."""
    prob = 0.6
    odds = 100

    f_full = kelly_fraction(prob, odds, market="ml", kelly_fraction_param=1.0)
    f_half = kelly_fraction(prob, odds, market="ml", kelly_fraction_param=0.5)

    assert f_half <= f_full


