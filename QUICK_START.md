# Quick Start Guide

Get up and running in 5 minutes.

## Setup

```bash
# 1. Install dependencies
poetry install

# 2. Install libomp (macOS only, for XGBoost)
brew install libomp

# 3. Configure API keys
cp .env.example .env
# Edit .env with your CFBD_API_KEY and ODDS_API_KEY
```

## First Run

```bash
# Ingest data (30-60 min)
poetry run python -m src.cli.main ingest --start 2014 --end 2024

# Build features (10-20 min)
poetry run python -m src.cli.main features

# Train models (30-60 min)
poetry run python -m src.cli.main train --models ats,ml,total

# Generate picks
poetry run python -m src.cli.main pick-week 2025 12
```

## Weekly Routine

```bash
# Generate picks for current week
poetry run python -m src.cli.main pick-week 2025 12

# Review: reports/2025_w12_picks.md
```

## Report Format

The picks report shows:
- **Rankings**: AP Top 25 next to team names
- **Spread**: Favorite shows negative (e.g., `Alabama (-6.5)`), underdog shows positive (e.g., `Oklahoma (+6.5)`)
- **ATS Pick**: Home/Away with confidence 1-10
- **Total O/U**: Market total
- **O/U Pick**: OVER/UNDER with confidence 1-10

Games are filtered to **top 25 teams and Power 5 matchups only**.

## Need More Help?

See `README.md` for complete documentation.
