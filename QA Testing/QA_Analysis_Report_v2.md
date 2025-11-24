# QA Analysis Report - Week 12, 2025 (v2)

**Analysis Date**: November 17, 2025  
**Total Games Evaluated**: 58 FBS games  
**Model Version**: Retrained with rolling performance statistics

---

## Executive Summary

The model achieved **56.0% overall accuracy** (65/116 picks) across ATS and O/U markets. While this is above the 52.4% break-even threshold, there are significant calibration issues with confidence levels that need attention.

### Key Findings
- ✅ **ATS Accuracy**: 56.9% (33/58) - Above break-even
- ✅ **O/U Accuracy**: 55.2% (32/58) - Above break-even
- ⚠️ **High Confidence ATS Picks (9/10)**: 0% accuracy (0/2) - **CRITICAL ISSUE**
- ✅ **Mid-Range Confidence (5/10)**: 80% ATS accuracy - Best performing
- ⚠️ **Low Confidence (1/10)**: 37.5% O/U accuracy - Underperforming

---

## Overall Performance

### ATS (Against The Spread)
- **Total Picks**: 58
- **Correct**: 33
- **Incorrect**: 25
- **Accuracy**: **56.9%**
- **Break-even**: 52.4% (assuming -110 odds)
- **Edge**: +4.5% above break-even ✅

### Over/Under
- **Total Picks**: 58
- **Correct**: 32
- **Incorrect**: 26
- **Accuracy**: **55.2%**
- **Break-even**: 52.4% (assuming -110 odds)
- **Edge**: +2.8% above break-even ✅

### Combined Performance
- **Total Picks**: 116 (58 ATS + 58 O/U)
- **Correct**: 65
- **Incorrect**: 51
- **Overall Accuracy**: **56.0%**
- **Edge**: +3.6% above break-even ✅

---

## Performance by Confidence Level

### ATS Confidence Breakdown

| Confidence | Correct | Total | Accuracy | Status |
|------------|---------|-------|----------|--------|
| 1/10 | 9 | 14 | **64.3%** | ✅ Good |
| 3/10 | 11 | 24 | **45.8%** | ⚠️ Below break-even |
| 5/10 | 8 | 10 | **80.0%** | ✅ Excellent |
| 7/10 | 5 | 8 | **62.5%** | ✅ Good |
| 9/10 | 0 | 2 | **0.0%** | ❌ Critical failure |

**Key Observations:**
- **Confidence 5/10 is the sweet spot** - 80% accuracy (best performing)
- **Confidence 9/10 is completely broken** - 0% accuracy (0/2 correct)
- **Confidence 3/10 underperforms** - 45.8% (below break-even)
- **Confidence 1/10 performs well** - 64.3% (surprisingly good)

### O/U Confidence Breakdown

| Confidence | Correct | Total | Accuracy | Status |
|------------|---------|-------|----------|--------|
| 1/10 | 3 | 8 | **37.5%** | ❌ Poor |
| 3/10 | 7 | 12 | **58.3%** | ✅ Good |
| 5/10 | 6 | 10 | **60.0%** | ✅ Good |
| 7/10 | 8 | 15 | **53.3%** | ✅ Above break-even |
| 9/10 | 7 | 12 | **58.3%** | ✅ Good |
| 10/10 | 1 | 1 | **100.0%** | ✅ (small sample) |

**Key Observations:**
- **Confidence 1/10 is problematic** - 37.5% accuracy (well below break-even)
- **Confidence 3/10, 5/10, 9/10 all perform well** - 58-60% range
- **Confidence 7/10 is solid** - 53.3% (slightly above break-even)
- **No clear pattern** - O/U confidence levels are more evenly distributed

---

## Incorrect Picks Analysis

### ATS Incorrect Picks (25 total)

**High Confidence Failures (9/10):**
1. **Minnesota @ #7 Oregon**: Minnesota (+26.5) - Actual: Oregon 29 pt win ❌
2. **#9 Notre Dame @ #23 Pittsburgh**: Pittsburgh (+12.5) - Actual: Notre Dame 22 pt win ❌

**Moderate Confidence Failures (5/10, 7/10):**
- Toledo @ Miami (OH): Miami (+5.5) (5/10) - Actual: Toledo 21 pt win
- NC State @ #16 Miami: NC State (+16.5) (7/10) - Actual: Miami 34 pt win
- UCLA @ #1 Ohio State: UCLA (+33.0) (7/10) - Actual: Ohio State 38 pt win
- Louisiana Tech @ Washington State: Louisiana Tech (+10.0) (7/10) - Actual: Washington State 25 pt win

**Low Confidence Failures (1/10, 3/10):**
- Multiple games with 1/10 and 3/10 confidence that missed

**Patterns:**
- **Underdog picks struggled** - Many incorrect picks were on underdogs getting points
- **Large spreads were problematic** - Games with spreads >20 points had poor accuracy
- **High confidence picks were wrong** - Both 9/10 confidence picks were incorrect

### O/U Incorrect Picks (26 total)

**High Confidence Failures (9/10):**
- Toledo @ Miami (OH): OVER (9/10) - Actual: 27 points (market 44.5)
- Wisconsin @ #2 Indiana: OVER (9/10) - Actual: 38 points (market 43.5)
- Kansas State @ Oklahoma State: OVER (9/10) - Actual: 20 points (market 50.5)
- Iowa @ #17 USC: OVER (9/10) - Actual: 47 points (market 48.5)
- Louisiana Tech @ Washington State: OVER (9/10) - Actual: 31 points (market 51.5)

**Patterns:**
- **OVER picks struggled** - Many incorrect picks were OVER predictions
- **High confidence OVER picks were wrong** - Multiple 9/10 confidence OVER picks missed
- **Model overestimated scoring** - Many games scored significantly less than predicted

---

## Critical Issues Identified

### 1. **High Confidence ATS Picks Are Broken** ❌
- **Confidence 9/10**: 0% accuracy (0/2)
- Both high-confidence picks were on underdogs getting large points
- **Recommendation**: Recalibrate confidence thresholds for ATS picks, especially for large spreads

### 2. **Low Confidence O/U Picks Underperform** ⚠️
- **Confidence 1/10**: 37.5% accuracy (3/8)
- Well below break-even threshold
- **Recommendation**: Consider filtering out 1/10 confidence O/U picks or recalibrate

### 3. **Model Overestimates Scoring** ⚠️
- Many OVER picks missed because games scored less than predicted
- Pattern: Model predicts high totals, actual games score lower
- **Recommendation**: Review totals model calibration, may need to adjust for defensive matchups

### 4. **Large Spread Underdog Picks Struggle** ⚠️
- Underdogs getting 20+ points had poor accuracy
- High confidence picks on large underdogs were wrong
- **Recommendation**: Be more conservative on large spread underdog picks

---

## Positive Findings

### 1. **Mid-Range Confidence Performs Best** ✅
- **ATS Confidence 5/10**: 80% accuracy (8/10)
- This suggests the model is well-calibrated in the middle range
- Sweet spot for actionable picks

### 2. **Overall Above Break-Even** ✅
- 56.0% combined accuracy is profitable
- Both ATS and O/U are above 52.4% break-even
- Model is generating positive expected value

### 3. **Low Confidence ATS Picks Perform Well** ✅
- **ATS Confidence 1/10**: 64.3% accuracy (9/14)
- Surprisingly good performance for "low confidence" picks
- May indicate these are actually good value plays

---

## Recommendations

### Immediate Actions

1. **Recalibrate High Confidence ATS Thresholds**
   - Confidence 9/10 is broken (0% accuracy)
   - Consider capping maximum confidence at 7/10 for ATS
   - Or require larger edge thresholds for 9/10 confidence

2. **Filter Low Confidence O/U Picks**
   - Confidence 1/10 O/U picks: 37.5% accuracy
   - Consider not showing picks below 3/10 confidence for O/U
   - Or recalibrate to be more conservative

3. **Review Totals Model**
   - Model appears to overestimate scoring
   - Many OVER picks missed because games scored less
   - May need defensive matchup adjustments

4. **Be Cautious with Large Spread Underdogs**
   - Underdogs getting 20+ points had poor results
   - High confidence picks on large underdogs were wrong
   - Consider additional filters for spreads >20 points

### Model Improvements

1. **Adjust Confidence Calibration**
   - Current calibration doesn't match actual accuracy
   - High confidence (9/10) should mean >70% accuracy, not 0%
   - Low confidence (1/10) should mean ~50% accuracy, not 37.5%

2. **Review Rolling Statistics Impact**
   - Model was retrained with rolling performance stats
   - Need to verify these features are helping, not hurting
   - Check feature importance to ensure performance metrics are weighted correctly

3. **Consider Market Context**
   - Some incorrect picks may be due to market efficiency
   - Large spreads may be efficiently priced
   - Consider market-based features (line movement, sharp money indicators)

---

## Detailed Incorrect Picks

### ATS Incorrect (25 total)

**By Confidence Level:**
- 1/10: 5 incorrect (out of 14 total)
- 3/10: 13 incorrect (out of 24 total)
- 5/10: 2 incorrect (out of 10 total)
- 7/10: 3 incorrect (out of 8 total)
- 9/10: 2 incorrect (out of 2 total) ❌

**Notable Misses:**
- Minnesota @ Oregon: Model picked Minnesota +26.5 (9/10) - Oregon won by 29
- Notre Dame @ Pittsburgh: Model picked Pittsburgh +12.5 (9/10) - Notre Dame won by 22
- NC State @ Miami: Model picked NC State +16.5 (7/10) - Miami won by 34

### O/U Incorrect (26 total)

**By Confidence Level:**
- 1/10: 5 incorrect (out of 8 total)
- 3/10: 5 incorrect (out of 12 total)
- 5/10: 4 incorrect (out of 10 total)
- 7/10: 7 incorrect (out of 15 total)
- 9/10: 5 incorrect (out of 12 total)
- 10/10: 0 incorrect (out of 1 total)

**Notable Misses:**
- Toledo @ Miami (OH): OVER 9/10 (predicted 63, actual 27) - Massive miss
- Kansas State @ Oklahoma State: OVER 9/10 (predicted 69, actual 20) - Huge miss
- Wisconsin @ Indiana: OVER 9/10 (predicted 64, actual 38) - Significant miss

---

## Special Game Notes

Games with special circumstances noted:
1. **Kent State @ Akron**: Overtime win
2. **Troy @ Old Dominion**: Troy scored zero points (unusual)
3. **South Carolina @ Texas A&M**: Texas A&M 28 pt 2nd half comeback
4. **Liberty @ Florida International**: Overtime win
5. **Utah State @ UNLV**: Double Overtime win

These games had unusual circumstances that may have affected outcomes.

---

## Conclusion

The model is **profitable overall** (56.0% accuracy) but has **significant calibration issues**:

1. ✅ **Above break-even** - Model is generating positive expected value
2. ❌ **High confidence broken** - 9/10 confidence ATS picks are 0% accurate
3. ⚠️ **Low confidence problematic** - 1/10 confidence O/U picks underperform
4. ✅ **Mid-range works well** - 5/10 confidence is the sweet spot

**Priority Actions:**
1. Recalibrate confidence thresholds (especially high confidence)
2. Review totals model (appears to overestimate scoring)
3. Be more conservative on large spread underdog picks
4. Consider filtering very low confidence picks

The model shows promise but needs calibration adjustments to improve reliability of confidence levels.
