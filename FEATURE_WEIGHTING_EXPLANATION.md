# Feature Weighting Explanation

## How Feature Weights Are Determined

**Important**: Feature weights are **NOT manually set**. They are **automatically learned by XGBoost** during model training based on what's most predictive of game outcomes.

XGBoost uses a tree-based algorithm that:
1. Splits on features that best separate wins from losses
2. Features used more often in splits get higher importance
3. Features that improve prediction accuracy get higher weights

---

## Current Model Weights (Before New Features)

**Model**: 2024 ATS Model (trained on old feature set)

| Feature Category | Total Weight | Status |
|-----------------|--------------|--------|
| **Rest Days** | **62.8%** | ⚠️ Over-weighted |
| - `away_rest_days` | 38.6% | |
| - `home_rest_days` | 24.2% | |
| **SP+ Ratings** | **37.2%** | ✅ Good |
| - `away_sp_plus` | 19.4% | |
| - `home_sp_plus` | 17.8% | |
| **All Other Features** | **0.0%** | ❌ Not being used |
| - Rolling stats (basic) | 0.0% | |
| - Advanced rolling stats | 0.0% | (didn't exist) |
| - SRS ratings | 0.0% | (not included) |
| - Interaction features | 0.0% | (didn't exist) |
| - Weather | 0.0% | (not properly merged) |
| - Boolean flags | 0.0% | (not used by model) |

**Total Active Features**: Only 4 out of 41 (9.8%)

---

## New Features Added (Available After Retraining)

### 1. Advanced Rolling Statistics (80 new features)
- **72 individual features**: 6 offensive + 6 defensive metrics × 3 windows × 2 teams
- **8 matchup differentials**: Offense vs defense efficiency comparisons

**Expected Weight**: **30-40%** (should be #1 priority)
- These are the most predictive features (recent form, efficiency metrics)
- Many features = more opportunities for the model to use them
- Game-level data is more granular than season aggregates

### 2. SRS Ratings (4 new features)
- `home_srs`, `away_srs`, `srs_diff`, `srs_sum`

**Expected Weight**: **5-10%** (complementary to SP+)

### 3. Interaction Features (10 new features)
- `rest_advantage`, `sp_plus_diff`, `sp_plus_sum`, `srs_diff`, `srs_sum`
- `rest_advantage_weighted`, `home_field_advantage`, `rest_product`
- Matchup differentials (4 features)

**Expected Weight**: **10-15%** (captures non-linear relationships)

### 4. Weather Features (Fixed + 2 new)
- `temp_C`, `wind_kph`, `precip_flag` (fixed merging)
- `cold_game`, `windy_game` (new interaction features)

**Expected Weight**: **3-5%** (especially for totals)

### 5. Boolean Flags (Converted to Numeric)
- `home_short_week`, `away_short_week`, `home_bye_week`, `away_bye_week`
- Now numeric (0/1) instead of boolean

**Expected Weight**: **2-3%** (should now be used)

---

## Expected Weights After Retraining

**Target Distribution** (what we want to achieve):

| Feature Category | Target Weight | Priority |
|-----------------|---------------|----------|
| **1. Advanced Rolling Stats** | **30-40%** | ⭐ #1 |
| - Success rate, PPA, explosiveness, havoc, etc. | | |
| - Last 3, 5, 10 games | | |
| **2. SP+ / SRS Ratings** | **20-25%** | ⭐ #2 |
| - SP+ ratings | | |
| - SRS ratings | | |
| - Rating differentials | | |
| **3. Rest Days** | **15-20%** | ⭐ #3 |
| - Rest days (home/away) | | |
| - Rest advantage | | |
| - Rest interactions | | |
| **4. Interaction Features** | **10-15%** | |
| - Rest × Rating interactions | | |
| - Matchup differentials | | |
| - Home field advantage | | |
| **5. Basic Rolling Stats** | **5-10%** | |
| - Win %, points for/against | | |
| - Point differential | | |
| **6. Weather** | **3-5%** | |
| - Temperature, wind, precipitation | | |
| - Weather interactions | | |
| **7. Other** | **5-10%** | |
| - Boolean flags (numeric) | | |
| - Availability (when implemented) | | |

---

## Why We Can't Directly Set Weights

XGBoost learns feature importance automatically. We **cannot** manually set weights like:
```python
# This doesn't exist in XGBoost
model.set_feature_weight("home_off_ppa_3", 0.15)
```

**What we CAN do**:
1. ✅ **Add more features** in categories we want prioritized
   - Added 80 advanced rolling stat features (should naturally get high weight)
2. ✅ **Ensure features are well-calculated** and have signal
   - Advanced metrics are more predictive than basic stats
3. ✅ **Create interaction features** that capture relationships
   - Rest × Rating interactions, matchup differentials
4. ✅ **Fix data issues** that prevent features from being used
   - Weather data merging, boolean to numeric conversion

---

## How to Achieve Target Weights

The model will naturally weight features based on predictive power. To achieve our target:

1. **Advanced rolling stats get high weight** because:
   - They're the most predictive (recent form, efficiency)
   - We added 80 features in this category
   - More features = more opportunities for the model to use them

2. **SP+/SRS ratings stay important** because:
   - They're proven team strength metrics
   - We added SRS to complement SP+
   - Rating differentials capture matchup strength

3. **Rest days get lower weight** because:
   - We added many more features that are more predictive
   - Rest days are still important, but now compete with better features
   - The model will naturally weight them lower if other features are better

---

## Next Steps

1. **Rebuild features** with new advanced stats (already done)
2. **Retrain models** to learn new feature weights
3. **Check feature importance** after retraining
4. **Verify weights match targets** (rolling stats #1, SP+ #2, rest days #3)

---

## Summary

- **Current**: Rest days 62.8%, SP+ 37.2%, everything else 0%
- **After Retraining (Expected)**: 
  - Advanced rolling stats: 30-40% (#1)
  - SP+/SRS ratings: 20-25% (#2)
  - Rest days: 15-20% (#3)
  - Interactions: 10-15%
  - Other: 10-15%

The model will automatically learn these weights during training. We've added the features needed to achieve this distribution.

