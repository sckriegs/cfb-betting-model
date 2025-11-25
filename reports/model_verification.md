# Model Training Logic Verification

## 1. Training Target
The ATS model is trained on the following condition:
`home_covers = (Home Margin - Market Spread Line) > 0`

## 2. Data Inspection (2024 Season)
I inspected the training data to verify the "Market Spread Line" sign convention.

**Example 1: Home Underdog**
- **Game**: Georgia Tech (Home) vs Florida State (Away)
- **Result**: GT won 24-21 (Margin +3)
- **Market Spread Feature**: -10.5
- **Target Calculation**: `3 - (-10.5) = 13.5 > 0` -> **Cover (TRUE)**
- **Interpretation**: GT covered the +10.5 spread.

**Example 2: Home Favorite**
- **Game**: Southeast Missouri St (Home) vs North Alabama
- **Result**: SEMO won 37-15 (Margin +22)
- **Market Spread Feature**: +7.5
- **Target Calculation**: `22 - 7.5 = 14.5 > 0` -> **Cover (TRUE)**
- **Interpretation**: SEMO covered the -7.5 spread.

## 3. Conclusion
The feature data uses a specific convention:
- **Positive Value** = Points the Home Team must win by (Hurdle).
- **Negative Value** = Cushion the Home Team has (Underdog points).

The training logic correctly subtracts this value from the actual margin.
- If Home is favored by 7.5 (Feature = 7.5), they must win by > 7.5.
- If Home is underdog by 10.5 (Feature = -10.5), they must not lose by more than 10.5 (Margin > -10.5).

**Status**: The model is fundamentally trained on **COVERING THE SPREAD**, not just winning.

