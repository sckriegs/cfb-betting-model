# Week 13 Performance Analysis (2025)

**Date:** November 25, 2025
**Data Source:** `reports/2025_w13_picks_export_v8.xlsx`
**Total Games Graded:** 54

## 📊 Executive Summary

Following significant updates to the model's feature engineering (market data integration) and logic fixes (sign errors, confidence thresholds), Week 13 performance shows a strong rebound, particularly in **Totals (Over/Under)** and **Moneyline** accuracy. **ATS performance** has returned to profitable territory (>52.4%).

| Model Type | Accuracy | Record | High Confidence (5+) Accuracy | Record (High Conf) |
| :--- | :--- | :--- | :--- | :--- |
| **ATS (Spread)** | **53.7%** | 29-25 | 52.9% | 9-8 |
| **Moneyline** | **77.8%** | 42-12 | **83.0%** | 39-8 |
| **Total (O/U)** | **63.0%** | 34-20 | **66.7%** | 12-6 |

---

## 🔍 Detailed Breakdown

### 1. Against The Spread (ATS)
- **Overall:** 29 Wins, 25 Losses (53.7%)
- **Performance:** This is a "winning week" for spread betting, clearing the standard vig break-even point of 52.38%.
- **Observation:** High confidence picks (52.9%) performed virtually identically to the overall set. This suggests the model's "edge" calculation for spreads is correctly identifying value but isn't yet successfully filtering for *higher* probability wins at the top end. The sign error fixes implemented mid-week likely saved this from being a losing week.

### 2. Moneyline (Straight Up)
- **Overall:** 42 Wins, 12 Losses (77.8%)
- **Performance:** Strong ability to pick the winner.
- **High Confidence:** The model was exceptional when confident, hitting **83%** on picks with confidence >= 5/10. This confirms the probability calibration is working well for win/loss prediction.

### 3. Totals (Over/Under)
- **Overall:** 34 Wins, 20 Losses (63.0%)
- **Performance:** **Exceptional.** This is the standout performer of the week. 
- **High Confidence:** Hitting **66.7% (12-6)** on high-confidence totals indicates the recalibrated XGBoost regression model is finding genuine edges in the market totals.

---

## 📝 Key Takeaways & Next Steps

1. **Totals Model Validation:** The recalibration of the Totals model (adjusting hyperparameters for depth and learning rate) has been highly effective. We should continue with these settings for Week 14.
2. **ATS Stability:** The ATS model is stable but not dominant. The fix to ensuring market spreads are correctly signed (negative for favorites) was critical. We should monitor if the accuracy holds or improves in Week 14 now that the data pipeline is fully corrected.
3. **Confidence Metric:** The "Confidence Score" (0-10) is proving highly predictive for Moneyline and Totals, but less so for ATS. Future work could involve tuning the ATS confidence formula to better reward "true" edges and punish uncertain ones.

## 📈 Recommendations for Week 14

- **Trust the Totals:** The O/U model is currently the "hot hand."
- **Monitor ATS High Confidence:** Watch to see if the ATS high-confidence tier separates itself from the pack in Week 14.
- **Maintain Pipeline:** Ensure all Week 14 games have valid market lines (DraftKings/FanDuel) before running the final predictions, as missing lines force the model to guess blindly.

