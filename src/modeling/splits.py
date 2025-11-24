"""Walk-forward split utilities."""

import pandas as pd


def get_walk_forward_splits(
    df: pd.DataFrame, season_col: str = "season", week_col: str = "week"
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Generate walk-forward splits by season/week.

    For each test week, train on all data up to (but not including) that week.
    Ensures no leakage across seasons.

    Args:
        df: Full feature DataFrame
        season_col: Name of season column
        week_col: Name of week column

    Returns:
        List of (train_df, test_df) tuples
    """
    splits = []

    # Get unique season-week combinations, sorted
    df_sorted = df.sort_values([season_col, week_col])
    unique_weeks = df_sorted[[season_col, week_col]].drop_duplicates().values

    for season, week in unique_weeks:
        # Train: all data before this week (strictly < week in same season, or < season)
        train_mask = (df[season_col] < season) | (
            (df[season_col] == season) & (df[week_col] < week)
        )
        train_df = df[train_mask].copy()

        # Test: this week
        test_mask = (df[season_col] == season) & (df[week_col] == week)
        test_df = df[test_mask].copy()

        if not train_df.empty and not test_df.empty:
            splits.append((train_df, test_df))

    return splits


def validate_no_leakage(train_df: pd.DataFrame, test_df: pd.DataFrame, season_col: str = "season", week_col: str = "week") -> bool:
    """Validate that there's no data leakage between train and test.

    Args:
        train_df: Training DataFrame
        test_df: Test DataFrame
        season_col: Name of season column
        week_col: Name of week column

    Returns:
        True if no leakage detected
    """
    if train_df.empty or test_df.empty:
        return True

    max_train_season = train_df[season_col].max()
    max_train_week = train_df[train_df[season_col] == max_train_season][week_col].max()

    min_test_season = test_df[season_col].min()
    min_test_week = test_df[test_df[season_col] == min_test_season][week_col].min()

    # Check: all test data should be after all train data
    if min_test_season < max_train_season:
        return False
    if min_test_season == max_train_season and min_test_week <= max_train_week:
        return False

    return True


