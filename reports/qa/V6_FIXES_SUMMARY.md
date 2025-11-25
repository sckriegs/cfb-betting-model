# V6 Fixes Summary - ATS and O/U Improvements

**Date**: November 17, 2025  
**Status**: ✅ **FIXES IMPLEMENTED**

---

## Critical Issues Identified

### 1. ATS Model Training on Wrong Data ⚠️ **CRITICAL**

**Problem**: 
- Only 44.5% of training data has market spreads
- Games without market spreads default to `market_spread_home = 0`
- This makes the target = `home_margin > 0` (home wins), not `home_margin > market_spread_home` (home covers)
- **Result**: Model was still training on wrong target for 55.5% of data!

**Fix**: 
- **Filter training data to only games with valid market spreads** (not null, not 0)
- This ensures ATS model trains on correct target: home covers
- **File**: `src/modeling/train_ats.py`

**Impact**:
- 2025 model now trains on 11,047 / 24,222 games (45.6%) with valid market spreads
- All training data now uses correct target (home covers, not home wins)

### 2. O/U Model Underperforming ⚠️

**Problem**:
- V5 O/U accuracy: 42.1% (24/57) - significantly below break-even (52.4%)
- Low confidence picks (1-3/10) performing at 33-41%

**Fix**:
- **Improved hyperparameters** for better generalization
- Increased regularization to prevent overfitting
- **File**: `src/modeling/models.py` - `TotalsModel`

**Changes**:
- `n_estimators`: 200 → 300 (more trees)
- `max_depth`: 6 → 5 (reduced to prevent overfitting)
- `learning_rate`: 0.05 → 0.03 (lower for more stable predictions)
- `min_child_weight`: 3 → 5 (more conservative, require more samples per leaf)
- `reg_alpha`: 0.1 → 0.2 (increased L1 regularization)

---

## Expected Improvements

### ATS Accuracy
- **V5**: 52.6% (30/57) - below break-even
- **V6 Expected**: Should improve significantly now that model trains on correct target
- **Target**: Return to V3 level (67.2%) or better

### O/U Accuracy
- **V5**: 42.1% (24/57) - significantly below break-even
- **V6 Expected**: Should improve with better hyperparameters
- **Target**: Above break-even (52.4%+)

---

## Key Changes

### 1. ATS Training Data Filtering

**Before (V5)**:
```python
# All games used, but market_spread_home = 0 for 55.5% of data
y = (df["home_margin"] - df[market_spread_col] > 0).astype(int)
# For games without spreads: y = (home_margin > 0) = home wins (WRONG!)
```

**After (V6)**:
```python
# Only games with valid market spreads
valid_spreads = df[df[market_spread_col].notna() & (df[market_spread_col] != 0.0)]
y = (valid_spreads["home_margin"] - valid_spreads[market_spread_col] > 0).astype(int)
# All training data uses correct target: home covers
```

### 2. O/U Model Hyperparameters

**Before (V5)**:
- `n_estimators=200`, `max_depth=6`, `learning_rate=0.05`, `min_child_weight=3`, `reg_alpha=0.1`

**After (V6)**:
- `n_estimators=300`, `max_depth=5`, `learning_rate=0.03`, `min_child_weight=5`, `reg_alpha=0.2`

---

## Next Steps

1. **QA Week 12 V6 picks** to verify improvements
2. **Compare to V5** (52.6% ATS, 42.1% O/U)
3. **Target**: ATS > 60%, O/U > 52.4%

---

## Files Modified

1. **`src/modeling/train_ats.py`**
   - Added filtering to only train on games with valid market spreads
   - Ensures correct target (home covers) for all training data

2. **`src/modeling/models.py`**
   - Improved `TotalsModel` hyperparameters
   - Better regularization to prevent overfitting

---

**Status**: ✅ **FIXES IMPLEMENTED AND MODELS RETRAINED**  
**Next**: QA Week 12 V6 picks to verify improvements


