import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(".").resolve()))

from src.data.persist import read_parquet

def inspect_features():
    # Load 2025 features
    df = read_parquet("data/features/2025.parquet")
    
    # Filter to Week 13
    week_13 = df[df["week"] == 13]
    
    # Select interesting columns
    cols = [
        "home_team", "away_team", "market_spread_home", 
        "home_talent", "away_talent", "talent_diff",
        "home_coach_tenure", "away_coach_tenure",
        "home_sp_plus", "away_sp_plus"
    ]
    
    # Check specific games
    games_to_check = ["Ohio State", "Maryland", "Georgia"]
    
    print(f"--- Inspecting Week 13 Features ({len(week_13)} games) ---")
    
    for team in games_to_check:
        game = week_13[week_13["home_team"] == team]
        if not game.empty:
            print(f"\nGame: {game.iloc[0]['away_team']} @ {team}")
            for col in cols:
                print(f"  {col}: {game.iloc[0].get(col)}")
        else:
            print(f"\nCould not find home game for {team}")

    # Check for zero values in new features
    print("\n--- Data Quality Check ---")
    zeros_talent = len(week_13[week_13["home_talent"] == 0])
    zeros_coach = len(week_13[week_13["home_coach_tenure"] == 0])
    print(f"Games with Home Talent = 0: {zeros_talent}")
    print(f"Games with Home Coach Tenure = 0: {zeros_coach}")

if __name__ == "__main__":
    inspect_features()

