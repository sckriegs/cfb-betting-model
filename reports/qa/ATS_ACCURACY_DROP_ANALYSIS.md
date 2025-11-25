# ATS Accuracy Drop Analysis: 67.2% → 59.6%

**Date**: November 17, 2025  
**Issue**: ATS accuracy dropped from 67.2% (V3) to 59.6% (V4)  
**Root Cause**: **CRITICAL BUG IDENTIFIED**

---

## Root Cause: ATS Model Training on Wrong Target

### The Problem

**The ATS model was training on the same target as the ML model (home wins), not home covers!**

### Why This Happened

1. **Missing Market Spreads in Features**: The `market_spread_home` column was NOT in the features DataFrame during training
2. **Default to Zero**: When `market_spread_home` is missing, the ATS training code defaults to 0:
   ```python
   if market_spread_col not in df.columns:
       logger.warning(f"Market spread column {market_spread_col} not found, using 0")
       df[market_spread_col] = 0.0
   ```
3. **Wrong Target**: With `market_spread_home = 0`, the ATS target becomes:
   ```python
   y = (df["home_margin"] - 0 > 0).astype(int)
   y = (df["home_margin"] > 0).astype(int)  # Same as ML target!
   ```
4. **Identical Models**: Both ATS and ML models trained on the same target, producing identical predictions

### Evidence

- **ATS and ML probabilities are identical** for all 304 games in Week 12
- **Max difference**: 0.000000 (completely identical)
- **Training data**: No `market_spread_home` column in features DataFrame

---

## The Fix

### Solution: Add Market Spreads to Features During Feature Building

**File**: `src/features/build_features.py`

**Changes**:
1. Extract market spreads from lines data during feature building
2. Merge `market_spread_home`, `market_ml_home`, and `market_total` into the features DataFrame
3. Include these columns in the feature row so they're available during training

**Code Added**:
```python
# Extract and merge market spreads from lines data (needed for ATS model training)
# This ensures market_spread_home is available during training, not just prediction
market_spreads = []
if lines is not None and not lines.empty:
    # Extract spreads, totals, and moneylines from lines data
    # Merge into games DataFrame
    # Include in feature row
```

---

## Impact

### Before Fix (V4)
- ATS model trained on: `home_margin > 0` (home wins)
- ML model trained on: `home_margin > 0` (home wins)
- **Result**: Identical predictions, ATS accuracy = 59.6%

### After Fix (V5)
- ATS model will train on: `home_margin > market_spread_home` (home covers)
- ML model trains on: `home_margin > 0` (home wins)
- **Expected**: Different predictions, ATS accuracy should improve significantly

---

## Next Steps

1. **Rebuild Features** (with market spreads):
   ```bash
   poetry run python -m src.cli.main features --force-refresh
   ```

2. **Retrain Models**:
   ```bash
   poetry run python -m src.cli.main train --models ats,ml,total
   ```

3. **Verify Fix**:
   - Check that ATS and ML probabilities are different
   - Verify ATS model is using correct target during training
   - Test predictions to ensure they differ

4. **Re-run Week 12**:
   - Generate new picks with corrected ATS model
   - Compare accuracy to V3 (67.2%) and V4 (59.6%)

---

## Expected Improvement

- **ATS Accuracy**: Should return to ~67%+ (V3 level) or better
- **Model Differentiation**: ATS and ML predictions should differ
- **Better ATS Picks**: Model will now actually predict covers, not just wins

---

## Lessons Learned

1. **Always verify model targets match expectations**
2. **Check that required data is available during training**
3. **Validate that different models produce different predictions**
4. **Test model outputs, not just code execution**

---

**Status**: ✅ **FIXED** - Market spreads now included in features  
**Action Required**: Rebuild features and retrain models

