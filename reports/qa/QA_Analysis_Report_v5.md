# QA Analysis Report - Week 12, 2025 (V5 Model)

**Date**: November 17, 2025  
**Model Version**: V5 (Fixed ATS Model - Market Spreads in Training)  
**Week**: 12, 2025  
**Total Games**: 57

---

## Executive Summary

### Overall Performance

| Market Type | Total QA'd | Correct | Incorrect | Accuracy | Status |
|-------------|------------|---------|-----------|----------|--------|
| **ATS** | 57 | 30 | 27 | **52.6%** | ⚠️ **Below break-even (52.4%)** |
| **ML** | 57 | 50 | 7 | **87.7%** | ✅ Excellent |
| **O/U** | 57 | 24 | 33 | **42.1%** | ⚠️ **Below break-even (52.4%)** |
| **Combined** | 171 | 104 | 67 | **60.8%** | ⚠️ Below target |

**Key Findings**:
- **ML performance is excellent** (87.7%) - significantly above break-even
- **ATS performance is WORSE than V4** (52.6% vs 59.6%) - **CONCERNING**
- **O/U performance is below break-even** (42.1%) - needs improvement
- **Combined accuracy is below target** (60.8%)

---

## Version Comparison

| Version | ATS | ML | O/U | Combined | Notes |
|---------|-----|----|-----|----------|-------|
| **V3** | **67.2%** | N/A | 51.7% | 59.5% | Original model |
| **V4** | 59.6% | 85.7% | 50.9% | 65.3% | Direct ATS prob + Dynamic std dev |
| **V5** | **52.6%** | **87.7%** | **42.1%** | **60.8%** | **Fixed ATS training target** |

**Critical Issue**: ATS accuracy **decreased** from V4 (59.6%) to V5 (52.6%) after fixing the training target bug.

---

## ATS Performance Analysis

### Overall: 52.6% (30/57) ⚠️

**Status**: **Below break-even (52.4%)** and **worse than V4**

### Performance by Confidence

| Confidence | Accuracy | Count | Status |
|------------|----------|-------|--------|
| **1/10** | **50.0%** (7/14) | 14 | ⚠️ At break-even |
| **2/10** | **53.3%** (8/15) | 15 | ⚠️ Slightly above break-even |
| **3/10** | **50.0%** (10/20) | 20 | ⚠️ At break-even |
| **4/10** | **66.7%** (4/6) | 6 | ✅ Good |
| **6/10** | **50.0%** (1/2) | 2 | ⚠️ Small sample |

**Key Insights**:
- **Low confidence picks (1-3/10) account for 49 of 57 picks** (86%)
- **Low confidence picks are performing at or near break-even** (50-53%)
- **Only 4/10 confidence shows improvement** (66.7%), but small sample (6 games)
- **No high confidence picks** (7-10/10) - all confidence is low

### Patterns in Incorrect ATS Picks

**Large Spread Misses** (7 games):
- Minnesota @ Oregon: +26.5, picked underdog, lost by 29
- App State @ James Madison: +21.0, picked underdog, lost by 48
- Purdue @ Washington: +14.5, picked underdog, lost by 36
- Texas @ Georgia: +3.5, picked underdog, lost by 25
- Mississippi State @ Missouri: +7.0, picked underdog, lost by 22
- Louisiana Tech @ Washington State: +10.0, picked underdog, lost by 25
- UTSA @ Charlotte: -17.0, picked underdog, lost by 21

**Close Game Misses** (8 games):
- Ohio @ Western Michigan: +1.5, lost by 4
- Clemson @ Louisville: -1.5, lost by 1
- South Carolina @ Texas A&M: -16.5, won by 1 (didn't cover)
- Iowa @ USC: -6.5, won by 5 (didn't cover)
- Georgia Tech @ Boston College: -16.5, won by 2 (didn't cover)
- Florida Atlantic @ Tulane: -16.5, won by 11 (didn't cover)
- New Mexico @ Colorado State: -15.5, won by 3 (didn't cover)
- Tennessee @ New Mexico State: -41.5, won by 33 (didn't cover)

**Underdog Value Misses** (12 games):
- Multiple games where model picked underdog but favorite won comfortably

---

## ML Performance Analysis

### Overall: 87.7% (50/57) ✅

**Status**: **Excellent** - significantly above break-even

### Performance by Confidence

| Confidence | Accuracy | Count | Status |
|------------|----------|-------|--------|
| **1/10** | 50.0% (1/2) | 2 | ⚠️ Small sample |
| **2/10** | 100.0% (2/2) | 2 | ✅ Perfect (small sample) |
| **3/10** | 100.0% (2/2) | 2 | ✅ Perfect (small sample) |
| **4/10** | 50.0% (1/2) | 2 | ⚠️ Small sample |
| **5/10** | 66.7% (4/6) | 6 | ✅ Good |
| **6/10** | 50.0% (1/2) | 2 | ⚠️ Small sample |
| **7/10** | 100.0% (3/3) | 3 | ✅ Perfect |
| **8/10** | 100.0% (3/3) | 3 | ✅ Perfect |
| **9/10** | 100.0% (4/4) | 4 | ✅ Perfect |
| **10/10** | **93.5%** (29/31) | 31 | ✅ Excellent |

**Key Insights**:
- **High confidence picks (7-10/10) are performing excellently** (93-100%)
- **10/10 confidence picks account for 31 of 57 picks** (54%)
- **10/10 confidence accuracy is 93.5%** - very strong
- **Only 7 incorrect picks total** - excellent overall performance

### Incorrect ML Picks (7 games)

1. **Clemson @ Louisville**: Picked Louisville (4/10), Clemson won
2. **Virginia @ Duke**: Picked Duke (1/10), Virginia won
3. **San José State @ Nevada**: Picked San José State (10/10), Nevada won
4. **Texas State @ Southern Miss**: Picked Southern Miss (5/10), Texas State won
5. **Memphis @ East Carolina**: Picked East Carolina (5/10), Memphis won
6. **Delaware @ Sam Houston**: Picked Delaware (10/10), Sam Houston won
7. **Kennesaw State @ Jacksonville State**: Picked Kennesaw State (6/10), Jacksonville State won

**Pattern**: 2 of 7 incorrect picks were 10/10 confidence - rare but significant misses.

---

## O/U Performance Analysis

### Overall: 42.1% (24/57) ⚠️

**Status**: **Below break-even (52.4%)** - needs significant improvement

### Performance by Confidence

| Confidence | Accuracy | Count | Status |
|------------|----------|-------|--------|
| **1/10** | **33.3%** (2/6) | 6 | ⚠️ Poor |
| **2/10** | **41.2%** (7/17) | 17 | ⚠️ Poor |
| **3/10** | **33.3%** (7/21) | 21 | ⚠️ Poor |
| **4/10** | **66.7%** (6/9) | 9 | ✅ Good |
| **6/10** | 50.0% (2/4) | 4 | ⚠️ At break-even |

**Key Insights**:
- **Low confidence picks (1-3/10) account for 44 of 57 picks** (77%)
- **Low confidence picks are performing poorly** (33-41%)
- **Only 4/10 confidence shows improvement** (66.7%)
- **Overall accuracy is below break-even** - model is not profitable

### Patterns in Incorrect O/U Picks

**OVER Misses** (17 games):
- Model predicted OVER but actual was UNDER
- Examples: Air Force @ UConn (predicted 60+, actual 42), Louisiana Tech @ Washington State (predicted 49+, actual 31)

**UNDER Misses** (16 games):
- Model predicted UNDER but actual was OVER
- Examples: Minnesota @ Oregon (predicted <55, actual 55), South Florida @ Navy (predicted <79, actual 79)

**Large Errors**:
- Louisiana Tech @ Washington State: Predicted OVER (49+), Actual 31 (18+ point error)
- Boise State @ San Diego State: Predicted OVER (24+), Actual 24 (close but wrong side)

---

## Critical Issues

### 1. ATS Accuracy Decreased After Fix ⚠️ **HIGH PRIORITY**

**Problem**: ATS accuracy dropped from 59.6% (V4) to 52.6% (V5) after fixing the training target bug.

**Possible Causes**:
1. **ATS model may not be well-calibrated** - training on correct target but predictions are off
2. **Market spread data quality** - only 36.9% of games have market spreads in training data
3. **Model needs more training data** - ATS model may need more examples with market spreads
4. **Feature importance may have shifted** - with correct target, different features may be important

**Recommendation**: 
- Investigate why ATS accuracy decreased despite fixing the bug
- Check if market spread coverage in training data is sufficient
- Consider retraining with more historical data or different hyperparameters

### 2. Low Confidence ATS Picks Dominating ⚠️

**Problem**: 86% of ATS picks are low confidence (1-3/10), and they're performing at break-even.

**Impact**: Model is not providing strong edges for ATS picks.

**Recommendation**:
- Review ATS probability conversion logic
- Check if fair spread calculation is accurate
- Consider if dynamic margin std dev needs adjustment

### 3. O/U Model Underperforming ⚠️

**Problem**: O/U accuracy is 42.1% - significantly below break-even.

**Impact**: O/U picks are losing money.

**Recommendation**:
- Review O/U model hyperparameters
- Check if total prediction model needs recalibration
- Consider additional features for total prediction

---

## Recommendations

### Immediate Actions

1. **Investigate ATS Accuracy Drop** ⚠️ **CRITICAL**
   - Compare V4 vs V5 ATS predictions
   - Check if market spread coverage is sufficient
   - Review ATS probability conversion logic

2. **Improve O/U Model**
   - Review hyperparameters
   - Check feature importance
   - Consider recalibration

3. **Monitor ML Performance**
   - Continue tracking - performing excellently
   - Investigate the 2 high-confidence misses (10/10)

### Long-term Improvements

1. **Increase Market Spread Coverage**
   - Only 36.9% of games have market spreads in training
   - Need more historical market data for better ATS training

2. **Recalibrate Confidence Thresholds**
   - Low confidence picks are dominating
   - May need to adjust thresholds to filter out weak edges

3. **Feature Engineering**
   - Review which features are most important for ATS
   - Consider adding game-specific features

---

## Conclusion

**V5 Model Performance**:
- ✅ **ML**: Excellent (87.7%)
- ⚠️ **ATS**: Below break-even (52.6%) - **WORSE than V4**
- ⚠️ **O/U**: Below break-even (42.1%)
- ⚠️ **Combined**: Below target (60.8%)

**Key Finding**: While the ATS model fix was correct (ATS and ML probabilities are now different), **ATS accuracy actually decreased**. This suggests the ATS model itself may need further investigation or recalibration.

**Next Steps**: 
1. Investigate why ATS accuracy decreased
2. Review market spread data coverage
3. Consider model recalibration or hyperparameter tuning

---

**Generated**: November 17, 2025  
**Model Version**: V5  
**Week**: 12, 2025


