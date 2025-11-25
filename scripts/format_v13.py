import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add project root to path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from src.viz.reports import get_ats_pick, get_ml_pick, get_total_pick, generate_pick_reasoning, get_team_rankings

# Load raw picks
df = pd.read_csv('reports/2025_w13_picks.csv')

# Load Rankings for formatting
season = 2025
week = 13
rankings = get_team_rankings(season, week)

def format_team_name(team):
    rank = rankings.get(team)
    if rank:
        return f"#{rank} {team}"
    return team

# Create new list of rows
rows = []

for _, row in df.iterrows():
    # 1. Format Teams
    home_team = row['home_team']
    away_team = row['away_team']
    home_fmt = format_team_name(home_team)
    away_fmt = format_team_name(away_team)
    
    # 2. Format Spreads
    dk_spread = row.get('dk_spread_home')
    fd_spread = row.get('fd_spread_home')
    market_spread = row.get('market_spread_home')
    
    dk_str = f"{dk_spread:+.1f}" if pd.notna(dk_spread) else "N/A"
    fd_str = f"{fd_spread:+.1f}" if pd.notna(fd_spread) else "N/A"
    
    # 3. Format ATS Pick
    fair_spread = row.get('fair_spread_home')
    ats_pick, ats_conf = get_ats_pick(fair_spread, market_spread)
    
    if ats_conf >= 1:
        # Use market spread if available, otherwise fair spread (negated)
        display_spread = market_spread if pd.notna(market_spread) else (-fair_spread if pd.notna(fair_spread) else 0.0)
        
        if ats_pick == "Home":
            pick_team = home_fmt
            pick_val = display_spread
        else:
            pick_team = away_fmt
            pick_val = -display_spread
            
        ats_str = f"{pick_team} ({pick_val:+.1f}) ({ats_conf}/10)"
    else:
        ats_str = "N/A"
        
    # 4. Format ML Pick
    p_home_win = row.get('p_home_win')
    market_ml = row.get('market_ml_home')
    ml_pick, ml_conf = get_ml_pick(p_home_win, market_ml)
    
    if ml_conf >= 1:
        ml_team = home_fmt if ml_pick == "Home" else away_fmt
        ml_str = f"{ml_team} ({ml_conf}/10)"
    else:
        ml_str = "N/A"
        
    # 5. Format O/U
    market_total = row.get('market_total')
    fair_total = row.get('fair_total')
    
    if pd.notna(market_total):
        total_str = f"{market_total:.1f}"
    elif pd.notna(fair_total):
        total_str = f"{fair_total:.1f} (est.)"
    else:
        total_str = "N/A"
        
    ou_pick, ou_conf = get_total_pick(fair_total, market_total)
    ou_str = f"{ou_pick} ({ou_conf}/10)" if ou_conf >= 1 else "N/A"
    
    # 6. Generate Reasoning (just basic string for Excel)
    reasoning_list = generate_pick_reasoning(row, season, week, rankings)
    reasoning_str = "\n".join(reasoning_list[:3]) if reasoning_list else ""
    
    rows.append({
        'Away Team': away_fmt,
        'Home Team': home_fmt,
        'DK Spread': dk_str,
        'FD Spread': fd_str,
        'ATS Pick': ats_str,
        'ML Pick': ml_str,
        'Total O/U': total_str,
        'O/U Pick': ou_str,
        'Reasoning': reasoning_str,
        'ATS Correct Y/N': None,
        'Actual Result': None,
        'ML Correct Y/N': None,
        'Actual Winner': None,
        'O/U Correct Y/N': None,
        'Actual Total': None,
        'Notes': None
    })

# Create formatted DataFrame
out_df = pd.DataFrame(rows)

# Define column order (V8 Layout)
cols = ['Away Team', 'Home Team', 'DK Spread', 'FD Spread', 'ATS Pick', 'ML Pick', 
        'Total O/U', 'O/U Pick', 'Reasoning', 
        'ATS Correct Y/N', 'Actual Result', 
        'ML Correct Y/N', 'Actual Winner', 
        'O/U Correct Y/N', 'Actual Total', 'Notes']

out_df = out_df[cols]

# Save
out_path = 'reports/2025_w13_picks_export_v13.xlsx'
out_df.to_excel(out_path, index=False)
print(f"Saved formatted export to {out_path}")

