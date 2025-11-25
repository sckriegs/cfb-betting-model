# ATS Improvement Recommendations: 67.2% → 70%+

**Current Performance**: 67.2% (39/58 correct)  
**Target**: 70%+ (41-42/58 correct)  
**Gap**: Need +2-3 more correct picks

---

## Performance Breakdown by Confidence

| Confidence | Accuracy | Count | Status |
|------------|----------|-------|--------|
| **1/10** | **47.1%** (8/17) | 17 | ⚠️ **Dragging down average** |
| **3/10** | **58.3%** (7/12) | 12 | ⚠️ Below average |
| **5/10** | **86.7%** (13/15) | 15 | ✅ Excellent |
| **7/10** | **80.0%** (8/10) | 10 | ✅ Excellent |
| **9/10** | **75.0%** (3/4) | 4 | ✅ Good |

**Key Insight**: Low confidence picks (1/10, 3/10) account for **14 of 19 incorrect picks**. Medium-high confidence (5/10, 7/10) is performing excellently.

---

## Issue #1: Not Using ATS Probability Directly ⚠️ **HIGH PRIORITY**

**Current Problem**:
- We train an ATS model to predict `P(home covers)`
- We calculate ATS probabilities: `ats_proba = ats_model.predict_proba(X_ats)[:, 1]`
- **BUT**: We then **ignore** the ATS probability and convert from ML probability instead!

**Current Code** (`src/cli/main.py` lines 279-302):
```python
ats_proba = ats_model.predict_proba(X_ats)[:, 1]  # P(home covers) - CALCULATED BUT NOT USED!
ml_proba = ml_model.predict_proba(X_ml)[:, 1]     # P(home wins)

# Convert ML prob to fair spread using fixed 14-point std dev
fair_spreads = []
for win_prob in ml_proba:
    z_score = norm.ppf(win_prob)
    margin_estimate = z_score * margin_std  # Fixed 14 points
    fair_spreads.append(margin_estimate)
```

**Why This Is Problematic**:
1. **We're not using our ATS model's prediction** - it's designed specifically for ATS!
2. **ML probability is for win/loss, not covering the spread** - different target
3. **Fixed 14-point std dev** is inaccurate - margin distributions vary by game type

**Solution**: Use ATS probability to directly calculate fair spread

```python
# Method 1: Direct conversion from ATS probability
# P(home covers) = P(margin > -market_spread)
# For a given P(covers) and market_spread, solve for fair_spread
# This is more accurate than converting from ML

# Method 2: Ensemble approach
# Combine ATS prob and ML conversion, weighted by confidence
```

**Expected Impact**: **+1-2% accuracy** (1-2 more correct picks)

---

## Issue #2: Fixed Margin Standard Deviation ⚠️ **MEDIUM PRIORITY**

**Current Problem**:
- Using fixed `margin_std = 14.0` for all games
- Reality: Margin distributions vary significantly by game type

**Examples**:
- **Large favorites (SP+ diff > 20)**: Smaller variance (blowouts more predictable) → std ~12 pts
- **Close games (SP+ diff < 5)**: Larger variance (upsets more common) → std ~14-16 pts
- **Blowouts (SP+ diff > 30)**: Very small variance → std ~10 pts

**Solution**: Dynamic margin std dev based on team strength difference

```python
def calculate_margin_std(home_sp_plus, away_sp_plus):
    """Calculate expected margin standard deviation based on team strength."""
    sp_diff = abs(home_sp_plus - away_sp_plus)
    
    if sp_diff > 30:  # Blowouts
        return 10.0
    elif sp_diff > 20:  # Large favorites
        return 12.0
    elif sp_diff > 10:  # Moderate favorites
        return 13.0
    elif sp_diff > 5:   # Small favorites
        return 14.0
    else:  # Close games
        return 15.0  # Higher variance for toss-ups
```

**Expected Impact**: **+0.5-1% accuracy** (better spread estimates for edge cases)

---

## Issue #3: Large Spread Picks Underperforming ⚠️ **MEDIUM PRIORITY**

**Current Performance**:
- **Large spreads (15+ pts)**: 7 incorrect picks
- **Medium spreads (7-15 pts)**: 4 incorrect
- **Small spreads (<7 pts)**: 8 incorrect

**Notable Misses**:
- Pittsburgh +12.5 vs Notre Dame (9/10 confidence) - Lost by 22
- Texas A&M -16.5 vs South Carolina (7/10 confidence) - Won by only 1
- Tulane -16.5 vs Florida Atlantic (7/10 confidence)

**Why This Happens**:
1. Large spreads are harder to predict (smaller sample sizes)
2. Model may over-rely on rest days (Pittsburgh had +7 rest days)
3. Upset potential is higher with large underdogs

**Solution**: Adjust confidence thresholds for large spreads

```python
def adjust_confidence_for_spread(confidence, spread_abs):
    """Reduce confidence for large spreads."""
    if spread_abs >= 20:
        return max(1, confidence - 2)  # Reduce by 2
    elif spread_abs >= 15:
        return max(1, confidence - 1)  # Reduce by 1
    return confidence
```

**Expected Impact**: **+0.5% accuracy** (fewer high-confidence misses on large spreads)

---

## Issue #4: Low Confidence Picks (1/10) Dragging Down Average ⚠️

**Current Performance**:
- **1/10 confidence**: 47.1% accuracy (8/17 correct)
- **9 incorrect picks at 1/10** - accounts for nearly half of all misses

**Note**: You requested to keep all picks included, so we won't filter these out.

**Potential Solutions**:
1. **Recalibrate 1/10 threshold**: Current < 0.5 pt edge → 1/10. Maybe raise to < 1.0 pt?
2. **Improve model accuracy**: Better features/training → smaller edges become more reliable
3. **Accept lower confidence**: Keep 1/10 but acknowledge it's essentially coin flips

**Expected Impact**: If we could improve 1/10 from 47.1% to even 52%, that's **+1.7% overall** (+1 correct pick)

---

## Issue #5: Feature Weighting (Rest Days Still Present)

**Current Feature Importance**:
- Rest days: **9.3%** (down from 62.8% - excellent improvement!)
- Advanced rolling stats: **38.5%** ✅
- Basic rolling stats: **31.0%** ✅
- SP+/SRS ratings: **20.4%** ✅

**Analysis**: Feature weighting is now well-balanced. However, the Pittsburgh vs Notre Dame miss suggests rest days may still be over-weighted in edge cases.

**Recommendation**: Monitor rest day impact on high-confidence misses. Current weighting is acceptable.

---

## Recommended Implementation Plan

### Phase 1: Quick Wins (Expected +1.5-2% → 68.5-69%)

1. **✅ Use ATS probability directly** (HIGH PRIORITY)
   - Modify `load_model_week_predictions()` to use `ats_proba` for fair spread
   - Implement direct conversion: `P(covers) → fair_spread`
   - **Expected**: +1-1.5% accuracy

2. **✅ Dynamic margin std dev** (MEDIUM PRIORITY)
   - Add `calculate_margin_std()` function
   - Adjust based on SP+ difference
   - **Expected**: +0.5% accuracy

### Phase 2: Advanced Improvements (Expected +0.5-1% → 69-70%)

3. **✅ Adjust confidence for large spreads**
   - Reduce confidence for spreads >= 15 pts
   - Prevent high-confidence misses on risky large spreads
   - **Expected**: +0.5% accuracy

4. **✅ Ensemble approach (optional)**
   - Combine ATS prob and ML conversion
   - Weight by model confidence
   - **Expected**: +0.5% accuracy

### Phase 3: Long-term (Future)

5. **Direct margin regression model**
   - Train model to predict game margin directly (not probability)
   - More accurate than probability conversion
   - Requires new model training

6. **Additional features**
   - Player availability/injuries
   - Coaching matchups
   - Home/away splits
   - Weather-adjusted statistics

---

## Priority Ranking

| Rank | Improvement | Impact | Effort | Expected Gain |
|------|-------------|--------|--------|---------------|
| **1** | **Use ATS probability directly** | HIGH | MEDIUM | **+1-1.5%** |
| **2** | **Dynamic margin std dev** | MEDIUM | LOW | **+0.5%** |
| **3** | **Adjust confidence for large spreads** | MEDIUM | LOW | **+0.5%** |
| **4** | **Ensemble approach** | LOW | MEDIUM | **+0.5%** |

**Total Expected**: **+2-3% accuracy** → **69-70%** ✅

---

## Implementation Example

### Option 1: Direct ATS Probability Conversion

```python
# In src/cli/main.py load_model_week_predictions()

# Get both probabilities
ats_proba = ats_model.predict_proba(X_ats)[:, 1]  # P(home covers)
ml_proba = ml_model.predict_proba(X_ml)[:, 1]     # P(home wins)

# Use ATS probability to calculate fair spread
# P(home covers) = P(margin > -market_spread)
# For given P(covers), solve for fair_spread that makes P(margin > -fair_spread) = P(covers)
# Using normal distribution with dynamic std dev

fair_spreads = []
for i, (ats_prob, market_spread) in enumerate(zip(ats_proba, week_df['market_spread_home'].values)):
    if pd.notna(market_spread):
        # Calculate dynamic std dev
        home_sp = week_df.iloc[i].get('home_sp_plus', 0)
        away_sp = week_df.iloc[i].get('away_sp_plus', 0)
        margin_std = calculate_margin_std(home_sp, away_sp)
        
        # Convert ATS probability to fair spread
        # P(covers) = 1 - norm.cdf(-fair_spread / margin_std)
        # Solving: fair_spread = -norm.ppf(1 - ats_prob) * margin_std
        z_score = norm.ppf(ats_prob)  # z-score for P(covers)
        fair_spread = z_score * margin_std
        
        # Adjust for market spread context (more accurate)
        # The ATS prob is relative to market, so adjust fair_spread accordingly
        fair_spread = market_spread + (fair_spread - market_spread) * 0.5  # Blend with market
    else:
        # Fallback to ML conversion
        z_score = norm.ppf(ml_proba[i])
        margin_std = calculate_margin_std(
            week_df.iloc[i].get('home_sp_plus', 0),
            week_df.iloc[i].get('away_sp_plus', 0)
        )
        fair_spread = z_score * margin_std
    
    fair_spreads.append(fair_spread)
```

### Option 2: Ensemble Approach

```python
# Combine ATS and ML predictions
ats_fair_spread = convert_ats_prob_to_spread(ats_proba[i], market_spread, margin_std)
ml_fair_spread = convert_ml_prob_to_spread(ml_proba[i], margin_std)

# Weight by model confidence (ATS model is more accurate)
ats_weight = 0.7  # ATS model gets 70% weight
ml_weight = 0.3   # ML conversion gets 30% weight

fair_spread = ats_weight * ats_fair_spread + ml_weight * ml_fair_spread
```

---

## Summary

**To get from 67.2% to 70%+**:

1. ✅ **Use ATS probability directly** - **BIGGEST OPPORTUNITY** (+1-1.5%)
2. ✅ **Dynamic margin std dev** - Better accuracy for edge cases (+0.5%)
3. ✅ **Adjust confidence for large spreads** - Prevent high-confidence misses (+0.5%)

**Total Expected Improvement**: **+2-3% → 69-70% accuracy** ✅

**Next Steps**:
1. Implement Option 1 (direct ATS probability conversion)
2. Add dynamic margin std dev calculation
3. Test on Week 12, 2025 data to measure improvement
4. Iterate based on results

---

## Notes

- Low confidence picks (1/10) will continue to drag down average, but keeping all picks as requested
- Large spread picks require special handling (lower confidence, dynamic std dev)
- The ATS model is performing excellently at medium-high confidence (5/10, 7/10) - we just need to use it better!

