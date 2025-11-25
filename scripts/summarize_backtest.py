import pandas as pd

# Load backtest results
df = pd.read_csv('reports/backtest_2014_2025.csv')

# Aggregate by season
summary = df.groupby('season').agg({
    'n_games': 'sum',
    'ats_hit_rate': 'mean',
    'ml_hit_rate': 'mean',
    'total_mae': 'mean'
}).round(3)

print(summary)

# Calculate overall weighted average (weighted by n_games? No, simple mean of weeks is what was logged)
# But weighted by games is better for true hit rate.

# Let's calculate weighted hit rates
weighted_summary = []
for season, group in df.groupby('season'):
    total_games = group['n_games'].sum()
    # hit_rate is accuracy per week. To get season accuracy:
    # We need (hit_rate * n_games) summed / total_games
    # Note: n_games in backtest CSV is total games in the week?
    # Wait, n_games is len(test_df).
    # But ats_hit_rate is based on VALID games.
    # We don't have n_valid_ats in the CSV.
    # We'll use the weekly average as a proxy, or just report the raw mean.
    # Raw mean of weekly hit rates is decent.
    
    season_stats = {
        'Season': season,
        'ATS Hit Rate': f"{group['ats_hit_rate'].mean():.1%}",
        'ML Hit Rate': f"{group['ml_hit_rate'].mean():.1%}",
        'Total MAE': f"{group['total_mae'].mean():.2f}"
    }
    weighted_summary.append(season_stats)

# Convert to DataFrame for display
summary_df = pd.DataFrame(weighted_summary)
print("\nYear-by-Year Summary:")
print(summary_df.to_markdown(index=False))

