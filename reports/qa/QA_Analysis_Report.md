# QA Testing Analysis Report - Week 12, 2025

## Summary Statistics

### Overall Performance
- **ATS (Against The Spread) Accuracy: 48.0%** (12/25 correct)
- **Over/Under Accuracy: 48.0%** (12/25 correct)
- **Combined Overall Accuracy: 48.0%** (24/50 correct)

**Note**: 48% is below the break-even point for betting (typically need 52.4% to break even at -110 odds). This suggests the model needs improvement.

---

## Key Findings

### 1. Overconfidence Problem
The model shows **significant overconfidence** on high-confidence picks:

- **Confidence 10/10 (Over/Under)**: Only 20% accuracy (1/5 correct) ⚠️
  - This is a major red flag - the model's highest confidence picks are performing worse than random
  - All 4 incorrect 10/10 O/U picks were "Over" predictions that went "Under"

- **Confidence 1/10 (ATS)**: Only 16.7% accuracy (1/6 correct) ⚠️
  - Low confidence picks are also underperforming

### 2. Best Performing Confidence Levels
- **Confidence 5/10 (ATS)**: 100% accuracy (2/2) - but small sample size
- **Confidence 8/10 (Over/Under)**: 100% accuracy (3/3) - but small sample size
- **Confidence 7/10 (ATS)**: 66.7% accuracy (2/3)

### 3. Patterns in Incorrect Picks

#### ATS Issues:
1. **Close games (1-2 point margins)**: Model struggled with games decided by 1-2 points
   - Clemson @ Louisville: Model picked Louisville, Clemson won by 1
   - Michigan @ Northwestern: Model picked Michigan, Michigan won by 1 (didn't cover -10)
   - West Virginia @ Arizona State: Model picked Arizona State, won by 2 (didn't cover -10)

2. **Large underdog picks**: Model picked several large underdogs that didn't cover
   - Minnesota (+26.5) @ Oregon: Lost by 29 (didn't cover)
   - UCLA (+33) @ Ohio State: Lost by 38 (didn't cover)
   - UCF (+24.5) @ Texas Tech: Lost by 39 (didn't cover)

3. **Blowout games**: Model underestimated favorites in blowouts
   - NC State (+16.5) @ Miami: Miami won by 34 (covered easily)
   - Texas (+3.5) @ Georgia: Georgia won by 25 (covered easily)

#### Over/Under Issues:
1. **High confidence "Over" picks going "Under"**: 
   - 4 out of 5 confidence 10/10 picks were "Over" that went "Under"
   - Wisconsin @ Indiana: Line 43.5, predicted Over (10/10), actual 38
   - Kansas State @ Oklahoma State: Line 50, predicted Over (10/10), actual 20
   - Oklahoma @ Alabama: Line 45.5, predicted Over (10/10), actual 44

2. **Model overestimating totals**:
   - Multiple games where model predicted high totals but actual scores were much lower
   - Kansas State @ Oklahoma State: Predicted Over 50, actual total was only 20

3. **Model underestimating totals in some cases**:
   - Utah @ Baylor: Line 60.5, predicted Under (4/10), actual 83

---

## Detailed Breakdown by Confidence Level

### ATS Performance by Confidence:
| Confidence | Correct | Total | Accuracy |
|------------|---------|-------|----------|
| 1/10 | 1 | 6 | 16.7% |
| 2/10 | 1 | 2 | 50.0% |
| 4/10 | 5 | 10 | 50.0% |
| 5/10 | 2 | 2 | 100.0% |
| 7/10 | 2 | 3 | 66.7% |
| 8/10 | 1 | 2 | 50.0% |

### Over/Under Performance by Confidence:
| Confidence | Correct | Total | Accuracy |
|------------|---------|-------|----------|
| 1/10 | 2 | 4 | 50.0% |
| 2/10 | 0 | 1 | 0.0% |
| 4/10 | 3 | 6 | 50.0% |
| 5/10 | 1 | 3 | 33.3% |
| 7/10 | 2 | 3 | 66.7% |
| 8/10 | 3 | 3 | 100.0% |
| 10/10 | 1 | 5 | **20.0%** ⚠️ |

---

## Recommendations

### 1. Fix Overconfidence Calibration
- **Critical**: The confidence scoring system is broken for high-confidence picks
- Confidence 10/10 picks should be the most reliable, but they're performing worse than random
- Need to recalibrate confidence calculation to be more conservative

### 2. Improve Total Prediction Model
- Model is systematically overestimating totals (especially on high-confidence picks)
- Consider:
  - Adding weather factors more prominently
  - Better handling of defensive matchups
  - Adjusting for pace of play

### 3. Improve ATS Model for Close Games
- Model struggles with games decided by 1-2 points
- Consider:
  - Better handling of home field advantage in close games
  - More weight on recent form in tight matchups
  - Better understanding of "clutch" performance

### 4. Re-evaluate Large Spread Picks
- Model is picking large underdogs too often
- Large underdogs (+20 or more) rarely cover
- Consider:
  - Adding a threshold to avoid picking underdogs beyond a certain spread
  - Better understanding of when blowouts are likely

### 5. Confidence Score Recalibration
- Current confidence scores don't correlate well with actual accuracy
- Need to:
  - Recalibrate confidence calculation to match actual win rates
  - Consider using historical accuracy by confidence level to adjust scores
  - Implement a more conservative confidence scale

---

## Incorrect Picks Summary

### ATS Incorrect (13 games):
1. Clemson @ Louisville - Close game (1 pt margin)
2. Minnesota @ Oregon - Large underdog didn't cover
3. Michigan @ Northwestern - Didn't cover spread (won by 1, needed 10)
4. Kansas State @ Oklahoma State - Close game
5. West Virginia @ Arizona State - Didn't cover spread (won by 2, needed 10)
6. NC State @ Miami - Blowout (Miami won by 34)
7. Iowa @ USC - Close game (won by 5, needed 6.5)
8. UCF @ Texas Tech - Large underdog didn't cover
9. Maryland @ Illinois - Underdog didn't cover
10. Utah @ Baylor - Underdog didn't cover
11. Florida @ Ole Miss - Didn't cover spread (won by 10, needed 10.5)
12. Texas @ Georgia - Blowout (Georgia won by 25)
13. UCLA @ Ohio State - Large underdog didn't cover

### Over/Under Incorrect (13 games):
1. Clemson @ Louisville - Over predicted, Under actual (39 vs 50.5)
2. South Carolina @ Texas A&M - Under predicted, Over actual (61 vs 49.5)
3. Wisconsin @ Indiana - Over 10/10, Under actual (38 vs 43.5)
4. Kansas State @ Oklahoma State - Over 10/10, Under actual (20 vs 50)
5. Arkansas @ LSU - Over predicted, Under actual (45 vs 58.5)
6. Oklahoma @ Alabama - Over 10/10, Under actual (44 vs 45.5)
7. Iowa @ USC - Over 10/10, Under actual (47 vs 48.5)
8. Penn State @ Michigan State - Over predicted, Under actual (38 vs 49)
9. UCF @ Texas Tech - Under predicted, Over actual (57 vs 48.5)
10. Maryland @ Illinois - Over predicted, Under actual (30 vs 51)
11. Utah @ Baylor - Under predicted, Over actual (83 vs 60.5)
12. Texas @ Georgia - Over predicted, Under actual (45 vs 46.5)
13. Virginia Tech @ Florida State - Over predicted, Under actual (48 vs 55)

---

## Next Steps

1. **Immediate**: Recalibrate confidence scoring system
2. **Short-term**: Improve total prediction model (especially for high-confidence picks)
3. **Medium-term**: Better handling of close games and large spreads
4. **Long-term**: Implement confidence calibration based on historical accuracy

