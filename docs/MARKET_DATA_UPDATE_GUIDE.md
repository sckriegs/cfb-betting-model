# Market Data Update Frequency Guide

## Overview

The system uses **two sources** for market spreads and totals:

1. **CFBD API (Closing Lines)** - Historical/static data
2. **The Odds API (Live Odds)** - Real-time/current data

---

## 1. CFBD API - Closing Lines

### Update Frequency
- **Manual**: Only updated when you run the `ingest` command
- **Type**: Historical closing lines (static after games are played)
- **When Available**: 
  - Closing lines are typically available **after games are played**
  - For future weeks, lines may be **incomplete or missing**

### How to Update
```bash
# Re-ingest data for a season
poetry run python -m src.cli.main ingest --start 2025 --end 2025
```

### Current Status
- **Last ingested**: Checked when you last ran `ingest`
- **Coverage**: Varies by week
  - Past weeks: Usually 50-60% coverage (closing lines available)
  - Current/future weeks: May be 20-40% coverage (lines not yet available)

### Limitations
- **Not real-time**: Data is static once ingested
- **Incomplete for future weeks**: Closing lines aren't available until after games
- **May need re-ingestion**: If lines become available later, you need to re-run `ingest`

---

## 2. The Odds API - Live Odds

### Update Frequency
- **Real-time**: Fetched every time you use `--use-live-odds` flag
- **Type**: Current lines from sportsbooks
- **When Available**: 
  - Available for **upcoming games** (before they're played)
  - Updated frequently by sportsbooks

### How to Use
```bash
# Use live odds for current week
poetry run python -m src.cli.main pick-week 2025 13 --use-live-odds
```

### Advantages
- **Current lines**: Always up-to-date
- **Complete coverage**: Should have lines for all upcoming games
- **No manual updates needed**: Fetched automatically when flag is used

### Limitations
- **Requires API key**: Need `ODDS_API_KEY` in `.env`
- **API quota**: Free tier has limited requests per month
- **Only for upcoming games**: Not available for past games

---

## Recommendation for Week 13

Since Week 13 is an **upcoming week** (games haven't been played yet):

### Option 1: Use Live Odds (Recommended)
```bash
poetry run python -m src.cli.main pick-week 2025 13 --use-live-odds
```
- Gets current lines from sportsbooks
- Should have lines for all games
- Most up-to-date

### Option 2: Re-ingest CFBD Data
```bash
# Re-ingest 2025 data to refresh lines
poetry run python -m src.cli.main ingest --start 2025 --end 2025
```
- May get more lines if CFBD has updated their data
- But may still be incomplete for future weeks

---

## Why Week 13 Has Limited Lines

**Current Issue**: Only 15/64 games (23.4%) have spreads, 4/64 (6.2%) have totals

**Possible Reasons**:
1. **Data was ingested 3+ days ago** - Lines may not have been available then
2. **CFBD closing lines aren't available for future weeks** - They're "closing" lines, meaning final lines after games
3. **Some games may not have lines yet** - Lower-profile games may not have lines posted

**Solution**: Use `--use-live-odds` flag to get current lines from The Odds API

---

## Best Practices

### For Current/Upcoming Weeks
- **Use `--use-live-odds` flag** to get real-time lines
- Lines are updated frequently by sportsbooks
- Should have complete coverage

### For Historical Analysis
- **Use CFBD closing lines** (ingested data)
- Closing lines are the final lines before games
- Good for backtesting and training

### For Training Models
- **Use CFBD closing lines** (already in features)
- Historical data is needed for training
- 44.5% of training data has market spreads (this is normal for historical data)

---

## Summary

| Data Source | Update Frequency | Best For | Coverage |
|-------------|------------------|----------|----------|
| **CFBD Closing Lines** | Manual (when you run `ingest`) | Historical analysis, training | 50-60% for past weeks |
| **The Odds API Live** | Real-time (when you use flag) | Current/upcoming weeks | ~100% for upcoming games |

**For Week 13**: Use `--use-live-odds` flag to get current lines!


