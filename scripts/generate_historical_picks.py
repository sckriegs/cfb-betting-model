import pandas as pd
import logging
import sys
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.persist import read_parquet, get_data_dir
from src.modeling.splits import get_walk_forward_splits
from src.modeling.eval import load_model
from src.modeling.train_ats import prepare_ats_data
from src.modeling.train_ml import prepare_ml_data
from src.modeling.train_total import prepare_total_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_history():
    data_dir = get_data_dir()
    
    # Load all features
    dfs = []
    for year in range(2015, 2026):
        p = data_dir / "features" / f"{year}.parquet"
        if p.exists():
            dfs.append(read_parquet(str(p)))
            
    if not dfs:
        logger.error("No features found.")
        return
        
    features_df = pd.concat(dfs, ignore_index=True)
    
    # Filter out games with 0 total points (unplayed games that were filled with 0s)
    # This prevents fake results for future games
    features_df = features_df[features_df["total_points"] > 0].copy()
    
    # Walk forward
    splits = get_walk_forward_splits(features_df)
    
    all_picks = []
    
    for train_df, test_df in splits:
        season = test_df["season"].iloc[0]
        week = test_df["week"].iloc[0]
        
        logger.info(f"Processing {season} Week {week}...")
        
        # Load models
        ats_model = load_model("ats", season)
        ml_model = load_model("ml", season)
        total_model = load_model("total", season)
        
        # We want to capture: Team, Opponent, Spread, Pick, Result, Score?
        # We need raw columns from test_df + predictions
        
        # 1. ATS Predictions
        if ats_model:
            X_ats, y_ats = prepare_ats_data(test_df) # y_ats is (Home Cover)
            # Align
            if not X_ats.empty:
                # Filter features
                if hasattr(ats_model, "feature_names"):
                    for f in ats_model.feature_names:
                        if f not in X_ats.columns: X_ats[f] = 0.0
                    X_ats = X_ats[ats_model.feature_names]
                
                probs = ats_model.predict_proba(X_ats)[:, 1]
                
                # We need to map these back to the original test_df rows
                # X_ats index should match test_df index
                
                # Create a df for this batch
                batch = test_df.loc[X_ats.index].copy()
                batch["ats_prob"] = probs
                batch["ats_pick_home"] = (probs > 0.5)
                
                # Determine outcome
                # y_ats is 1 if Home Covered.
                # If ats_pick_home == 1 and y_ats == 1 -> Correct
                # If ats_pick_home == 0 and y_ats == 0 -> Correct (Away picked, Away covered)
                # But wait, y_ats is binary.
                # Correctness: (Pick == y_ats)
                batch["ats_correct"] = (batch["ats_pick_home"].astype(int) == y_ats)
                
                # Add Spread info
                
                # 2. ML Predictions
                if ml_model:
                    X_ml, y_ml = prepare_ml_data(test_df)
                    if not X_ml.empty:
                        if hasattr(ml_model, "feature_names"):
                            for f in ml_model.feature_names:
                                if f not in X_ml.columns: X_ml[f] = 0.0
                            X_ml = X_ml[ml_model.feature_names]
                        
                        probs_ml = ml_model.predict_proba(X_ml)[:, 1]
                        ml_series = pd.Series(probs_ml, index=X_ml.index, name="ml_prob")
                        # Join to batch (batch is indexed by test_df original index)
                        batch = batch.join(ml_series, how="left")

                # 3. Total Predictions
                if total_model:
                    X_tot, y_tot = prepare_total_data(test_df)
                    if not X_tot.empty:
                        if hasattr(total_model, "feature_names"):
                            for f in total_model.feature_names:
                                if f not in X_tot.columns: X_tot[f] = 0.0
                            X_tot = X_tot[total_model.feature_names]
                        
                        preds_tot = total_model.predict(X_tot)
                        tot_series = pd.Series(preds_tot, index=X_tot.index, name="pred_total")
                        batch = batch.join(tot_series, how="left")

                all_picks.append(batch)
    
    if not all_picks:
        logger.error("No picks generated.")
        return

    full_df = pd.concat(all_picks, ignore_index=True)
    
    final_cols = [
        "season", "week", "kickoff_dt", "home_team", "away_team", 
        "home_margin", "total_points", 
        "market_spread_home", "market_total", 
        "ats_prob", "ats_correct", "ml_prob", "pred_total"
    ]
    
    # Filter cols that exist
    cols = [c for c in final_cols if c in full_df.columns]
    save_df = full_df[cols].copy()
    
    # Reconstruct Scores
    if "home_margin" in save_df.columns and "total_points" in save_df.columns:
        save_df["home_points"] = (save_df["total_points"] + save_df["home_margin"]) / 2
        save_df["away_points"] = (save_df["total_points"] - save_df["home_margin"]) / 2
    
    # Determine Pick Name
    # If ats_prob > 0.5 -> Home. Else Away.
    save_df["ATS Pick Team"] = np.where(save_df["ats_prob"] > 0.5, save_df["home_team"], save_df["away_team"])
    
    # Determine Result Color
    save_df["Result"] = np.where(save_df["ats_correct"], "Win", "Loss")
    
    # ML Pick Team
    if "ml_prob" in save_df.columns:
        save_df["ML Pick Team"] = np.where(save_df["ml_prob"] > 0.5, save_df["home_team"], save_df["away_team"])
        # ML Correct?
        # Win if (Pick Home & Home Win) OR (Pick Away & Away Win)
        # Home Win = (home_points > away_points)
        home_won = (save_df["home_points"] > save_df["away_points"])
        picked_home_ml = (save_df["ml_prob"] > 0.5)
        save_df["ml_correct"] = (picked_home_ml == home_won)
        save_df["ML Result"] = np.where(save_df["ml_correct"], "Win", "Loss")

    # Total Pick
    if "pred_total" in save_df.columns and "market_total" in save_df.columns:
        save_df["O/U Pick Side"] = np.where(save_df["pred_total"] > save_df["market_total"], "OVER", "UNDER")
        # Correct?
        actual_total = save_df["home_points"] + save_df["away_points"]
        over_hit = actual_total > save_df["market_total"]
        under_hit = actual_total < save_df["market_total"]
        
        save_df["total_correct"] = np.where(
            save_df["O/U Pick Side"] == "OVER", over_hit, under_hit
        )
        # Handle pushes (Actual == Market) -> treat as... Loss? Or Push?
        # If actual == market, neither hit.
        # Let's leave as False (Loss) or maybe "Push"?
        save_df["Total Result"] = np.where(save_df["total_correct"], "Win", "Loss")
        # Push logic
        is_push = (actual_total == save_df["market_total"])
        save_df.loc[is_push, "Total Result"] = "Push"

    # Save
    out_path = data_dir / "processed" / "historical_picks.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_df.to_parquet(out_path)
    logger.info(f"Saved {len(save_df)} historical picks to {out_path}")

if __name__ == "__main__":
    generate_history()

