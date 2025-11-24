# CFB Betting Model

Production-ready machine learning system for predicting college football game outcomes (ATS, Moneyline, Totals) with Kelly sizing recommendations. Focuses on top 25 teams and Power 5 matchups.

## Features

- **Three Prediction Markets**: ATS (spreads), Moneyline (win probability), and Totals (over/under)
- **AP Poll Rankings**: Displays current top 25 rankings next to team names
- **Confidence Levels**: 1-10 scale for each pick based on model edge
- **Data Integration**: Historical games, lines, stats, ratings (2005-present), weather, and live odds
- **Feature Engineering**: Rolling stats, team priors (SP+, SRS), rest days, travel, timezone, weather
- **Machine Learning**: XGBoost models with probability calibration
- **Risk Management**: Fractional Kelly criterion with conservative caps (1% max per bet)
- **Backtesting**: Strict walk-forward validation (2014-2024) to prevent data leakage
- **Live Integration**: The Odds API for current market lines

## Quick Start

### 1. Install Dependencies

```bash
# Install Poetry (if not already installed)
pip install poetry

# Install project dependencies
cd cfb-betting-model
poetry install

# On macOS, install libomp for XGBoost
brew install libomp
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required keys:
- `CFBD_API_KEY` - Get from https://collegefootballdata.com/ (free tier available)
- `ODDS_API_KEY` - Get from https://the-odds-api.com/ (free tier: 500 requests/month)

### 3. Run Full Pipeline

```bash
# Step 1: Ingest historical data (30-60 min)
poetry run python -m src.cli.main ingest --start 2014 --end 2024

# Step 2: Build features (10-20 min)
poetry run python -m src.cli.main features

# Step 3: Train models (30-60 min)
poetry run python -m src.cli.main train --models ats,ml,total

# Step 4: Backtest (15-30 min)
poetry run python -m src.cli.main backtest --start 2014 --end 2024

# Step 5: Generate picks for a week
poetry run python -m src.cli.main pick-week 2025 12
```

**Note**: On macOS, you may need to set the library path for XGBoost:
```bash
export DYLD_LIBRARY_PATH="/usr/local/opt/libomp/lib:$DYLD_LIBRARY_PATH"
```
```

## Weekly Workflow

During the season, generate picks each week:

```bash
# Option 1: Using live odds (when available)
poetry run python -m src.cli.main pick-week 2025 12 --use-live-odds

# Option 2: Using historical closing lines
poetry run python -m src.cli.main pick-week 2025 12
```

**Output**: 
- `reports/2025_w12_picks.csv` - Full data with all metrics
- `reports/2025_w12_picks.md` - Formatted report with rankings, spreads, picks, and confidence levels

## Understanding the Picks Report

The report shows games filtered to **top 25 teams and Power 5 matchups** with:

- **Rankings**: AP Top 25 rankings next to team names (e.g., `#4 Alabama`)
- **Spread**: Displayed next to the favorite (e.g., `Alabama (-6.5)`, `Oklahoma (+6.5)`)
- **ATS Pick**: Model's pick (Home/Away) with confidence 1-10
- **Total O/U**: Over/Under line
- **O/U Pick**: Model's pick (OVER/UNDER) with confidence 1-10

**Confidence Levels**:
- 1-3 = Low confidence
- 4-6 = Medium confidence  
- 7-9 = High confidence
- 10 = Very high confidence

## CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `ingest --start X --end Y` | Download historical data | `ingest --start 2014 --end 2024` |
| `features` | Build modeling features | `features` |
| `train --models ats,ml,total` | Train models | `train --models ats,ml,total` |
| `backtest --start X --end Y` | Validate performance | `backtest --start 2014 --end 2024` |
| `pick-week SEASON WEEK` | Generate picks | `pick-week 2025 12` |
| `pick-week SEASON WEEK --use-live-odds` | Use live odds instead of historical | `pick-week 2025 12 --use-live-odds` |

## Project Structure

```
cfb-betting-model/
├── data/                    # All data (gitignored)
│   ├── raw/                 # Raw CFBD data (games, lines, stats, ratings)
│   ├── features/            # Engineered features
│   ├── models/              # Trained models (ATS, ML, Total)
│   ├── odds/                # Odds snapshots
│   └── rankings/            # AP poll rankings cache
├── reports/                 # Generated reports (gitignored)
│   ├── {season}_w{week}_picks.csv
│   └── {season}_w{week}_picks.md
├── src/
│   ├── data/                # Data ingestion (CFBD, Odds API, Weather)
│   ├── features/            # Feature engineering
│   ├── modeling/            # ML models (XGBoost)
│   ├── betting/             # Kelly sizing, market conversions
│   ├── viz/                 # Report generation
│   └── cli/                 # Command-line interface
└── tests/                   # Unit tests
```

## Data Sources

- **CFBD API**: Games, lines, stats, ratings, venues (2005-present)
- **Meteostat**: Weather data at kickoff (temperature, wind, precipitation)
- **The Odds API**: Live odds for spreads, moneylines, totals
- **AP Poll**: Current top 25 rankings

## Model Details

- **ATS Model**: Binary classification (home covers spread: yes/no)
- **Moneyline Model**: Binary classification (home wins: yes/no) with calibrated probabilities
- **Totals Model**: Regression (predicts total points scored)

All models use XGBoost with probability calibration (isotonic regression) and strict walk-forward validation to prevent data leakage.

## Report Format

The picks report includes:
1. **Team Rankings**: AP Top 25 rankings displayed next to team names
2. **Spread**: Shown next to favorite (negative) and underdog (positive)
3. **ATS Pick**: Model recommendation with confidence level (1-10)
4. **Total O/U**: Market total points line
5. **O/U Pick**: Model recommendation (OVER/UNDER) with confidence level (1-10)

Example:
```
| #11 Oklahoma (+6.5) | #4 Alabama (-6.5) | +6.5 | Away (4/10) | 45.5 | OVER (10/10) |
```

## Troubleshooting

### Common Issues

1. **"poetry: command not found"**
   ```bash
   pip install poetry
   ```

2. **"XGBoost Library could not be loaded"** (macOS)
   ```bash
   brew install libomp
   export DYLD_LIBRARY_PATH="/usr/local/opt/libomp/lib:$DYLD_LIBRARY_PATH"
   ```

3. **"No trained models found"**
   - Run `train` command first
   - Check `data/models/` directory

4. **"No odds data available"**
   - Check Odds API quota at https://the-odds-api.com/dashboard
   - Use `--no-use-live-odds` to use historical closing lines instead

5. **"No games found for season X Week Y"**
   - Ensure data is ingested: `ingest --start X --end Y`
   - Verify week number (CFB weeks typically 1-15)

## Best Practices

1. **Start Small**: Test with a single season before full backtest
2. **Monitor API Quotas**: Check Odds API usage regularly
3. **Validate Predictions**: Compare model outputs to actual results
4. **Regular Updates**: Re-train models weekly as new data arrives
5. **Backup Data**: Keep `data/` directory backed up (it's gitignored)

## Security

- **Never commit `.env`**: Contains sensitive API keys
- `data/` and `reports/` are gitignored
- API keys should be kept secure and rotated regularly

## Development

### Code Quality

```bash
poetry run ruff check src/
poetry run black src/
poetry run isort src/
```

### Testing

```bash
poetry run pytest
```

## License

[Add your license here]
