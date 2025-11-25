import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(".").resolve()))

from src.data.persist import read_parquet

def inspect_raw_data():
    print("--- Inspecting Raw Talent 2025 ---")
    talent = read_parquet("data/raw/talent/2025.parquet")
    print(f"Total rows: {len(talent)}")
    print("First 5 teams:", talent["team"].head(5).tolist())
    print("Sample 'Charlotte'?", "Charlotte" in talent["team"].values)
    print("Sample 'Boise State'?", "Boise State" in talent["team"].values)
    
    print("\n--- Inspecting Raw Coaches 2025 ---")
    coaches = read_parquet("data/raw/coaches/2025.parquet")
    print(f"Total rows: {len(coaches)}")
    
    # Find Kirby Smart
    kirby = coaches[(coaches["firstName"] == "Kirby") & (coaches["lastName"] == "Smart")]
    if not kirby.empty:
        print("Kirby Smart seasons:")
        seasons = kirby.iloc[0]["seasons"]
        # Print first 2 and last 2 seasons
        if len(seasons) > 4:
            print(seasons[:2], "...", seasons[-2:])
        else:
            print(seasons)
    else:
        print("Kirby Smart not found")

if __name__ == "__main__":
    inspect_raw_data()

