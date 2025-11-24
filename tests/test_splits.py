"""Tests for walk-forward splits."""

import pandas as pd
import pytest

from src.modeling.splits import get_walk_forward_splits, validate_no_leakage


def test_walk_forward_splits():
    """Test walk-forward split generation."""
    # Create test data
    data = {
        "season": [2020, 2020, 2020, 2021, 2021],
        "week": [1, 2, 3, 1, 2],
        "feature": [1, 2, 3, 4, 5],
    }
    df = pd.DataFrame(data)

    splits = get_walk_forward_splits(df)

    # Should have splits for each unique week
    assert len(splits) > 0

    # Check first split
    train_df, test_df = splits[0]
    assert not train_df.empty
    assert not test_df.empty

    # Validate no leakage
    assert validate_no_leakage(train_df, test_df)


def test_validate_no_leakage():
    """Test leakage validation."""
    train_df = pd.DataFrame({"season": [2020, 2020], "week": [1, 2]})
    test_df = pd.DataFrame({"season": [2020], "week": [3]})

    assert validate_no_leakage(train_df, test_df)

    # Test with leakage
    train_df = pd.DataFrame({"season": [2020, 2020], "week": [1, 3]})
    test_df = pd.DataFrame({"season": [2020], "week": [2]})

    assert not validate_no_leakage(train_df, test_df)


def test_splits_no_cross_season_leakage():
    """Test that splits don't leak across seasons."""
    data = {
        "season": [2020, 2020, 2021, 2021],
        "week": [15, 16, 1, 2],
        "feature": [1, 2, 3, 4],
    }
    df = pd.DataFrame(data)

    splits = get_walk_forward_splits(df)

    # Check that 2021 week 1 doesn't include 2020 week 16 in train
    for train_df, test_df in splits:
        if test_df["season"].iloc[0] == 2021 and test_df["week"].iloc[0] == 1:
            assert 2020 not in train_df["season"].values or train_df[train_df["season"] == 2020]["week"].max() < 16


