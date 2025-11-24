# Feature Improvements Analysis & Recommendations

**Analysis Date**: Based on Week 12, 2025 QA Results  
**Current Model Accuracy**: 56.0% (65/116 picks)  
**Target**: Improve to 60%+ accuracy

---

## 📊 Current Feature Importance Analysis

### What's Currently Weighted Most (from XGBoost model)

| Feature | Importance | Status |
|---------|------------|--------|
| **away_rest_days** | **38.6%** | ⭐ Most important |
| **home_rest_days** | **24.2%** | ⭐ Very important |
| **away_sp_plus** | **19.4%** | ✅ Working well |
| **home_sp_plus** | **17.8%** | ✅ Working well |
| **All other features** | **0.0%** | ❌ Not being used |

**Total Active Features**: Only 4 out of 41 features are being used (9.8%)

### Key Insight
The model is **over-relying on rest days** (62.8% combined importance). While rest is important, this suggests:
1. Other features aren't providing signal
2. Features may not be properly calculated/merged
3. Model needs more diverse features to improve accuracy

---

## 🎯 Priority Improvements (Ranked by Impact)

### Priority 1: Add Advanced Rolling Statistics ⭐⭐⭐ (HIGHEST IMPACT)

**Current State**: Basic rolling stats exist (win %, points for/against) but have **0% importance**

**Problem**: We're only using basic box score stats. Advanced efficiency metrics are available but not being used.

**Available Data**: CFBD `stats_season` contains rich nested dictionaries with:
- `successRate` - % of successful plays (offense/defense)
- `explosiveness` - Big play ability (yards per successful play)
- `ppa` - Points Per Attempt (efficiency metric)
- `lineYards` - Rushing effectiveness
- `stuffRate` - Defensive stops (tackles for loss)
- `totalPPA` - Overall offensive/defensive efficiency
- `havoc` - Defensive disruption (TFL + INT + PBU + FF)
- `pointsPerOpportunity` - Scoring efficiency

**What to Add** (rolling averages over last 3, 5, 10 games):

```python
# Offensive efficiency (rolling)
home_off_success_rate_3/5/10
home_off_ppa_3/5/10
home_off_explosiveness_3/5/10
home_off_line_yards_3/5/10
home_off_points_per_opp_3/5/10

# Defensive efficiency (rolling) - LOWER is better
home_def_success_rate_3/5/10  # Lower = better defense
home_def_ppa_3/5/10  # Lower = better defense
home_def_havoc_3/5/10  # Higher = better defense
home_def_stuff_rate_3/5/10  # Higher = better defense

# Matchup differentials (home vs away)
off_success_rate_diff_3/5/10 = home_off_success_rate - away_def_success_rate
def_success_rate_diff_3/5/10 = home_def_success_rate - away_off_success_rate
ppa_matchup_diff_3/5/10 = home_off_ppa - away_def_ppa
```

**Expected Impact**: **+3-5% accuracy** (could bring you to 59-61%)

**Why This Matters**:
- Recent form is more predictive than season-long averages
- Efficiency metrics (success rate, PPA) are better predictors than raw points
- Matchup differentials (offense vs defense) capture game-specific dynamics

**Implementation**: Extract from `stats_season` data, calculate rolling averages per team, merge into features

---

### Priority 2: Add Interaction Features ⭐⭐ (QUICK WIN)

**Current State**: Features are independent. No interactions between rest days, ratings, etc.

**What to Add**:

```python
# Rest advantage (home team benefit)
rest_advantage = home_rest_days - away_rest_days

# Team strength differential
sp_plus_diff = home_sp_plus - away_sp_plus

# Combined strength (for totals)
sp_plus_sum = home_sp_plus + away_sp_plus

# Rest matters more in close games
rest_advantage_weighted = rest_advantage * abs(sp_plus_diff)

# Home field advantage (rest + rating)
home_field_advantage = (home_rest_days > away_rest_days) * sp_plus_diff

# Rest product (both teams well-rested = higher scoring)
rest_product = home_rest_days * away_rest_days
```

**Expected Impact**: **+1-2% accuracy**

**Why This Matters**:
- Rest advantage is more meaningful when teams are evenly matched
- Home field advantage is a combination of rest + team strength
- Interaction features help the model learn non-linear relationships

**Implementation**: 15 minutes - just add calculated columns to feature building

---

### Priority 3: Add SRS Ratings ⭐⭐ (EASY WIN)

**Current State**: SRS ratings are ingested but not used (0% importance)

**What to Add**:
- `home_srs` - Simple Rating System rating
- `away_srs` - Simple Rating System rating
- `srs_diff` - Home SRS - Away SRS

**Expected Impact**: **+0.5-1% accuracy**

**Why This Matters**:
- SRS provides complementary information to SP+
- Different calculation method may capture different aspects of team strength
- Already have the data, just need to use it

**Implementation**: 5 minutes - already in ratings data, just need to extract

---

### Priority 4: Fix Weather Data ⭐⭐ (MEDIUM IMPACT)

**Current State**: Weather data exists but has 0% importance (likely not properly merged)

**What to Fix**:
- Ensure `temp_C`, `wind_kph`, `precip_flag` are properly merged
- Add weather interactions:
  - `cold_game` = temp_C < 5°C (affects passing)
  - `windy_game` = wind_kph > 30 (affects passing/totals)
  - `precip_game` = precip_flag == 1 (affects scoring)

**Expected Impact**: **+1-2% accuracy** (especially for totals)

**Why This Matters**:
- Weather can swing totals by 5-10 points
- Cold/windy games favor running, reduce scoring
- Precipitation affects passing efficiency

**Implementation**: 30 minutes - check weather data merging logic

---

### Priority 5: Convert Boolean Flags to Numeric ⭐ (SMALL WIN)

**Current State**: Boolean flags (`home_short_week`, `home_bye_week`) have 0% importance

**Problem**: XGBoost may not handle boolean flags well. Convert to numeric.

**What to Change**:
```python
# Instead of boolean
home_short_week: bool

# Use numeric
home_short_week_numeric: int  # 0 or 1
home_bye_week_numeric: int  # 0 or 1
away_short_week_numeric: int  # 0 or 1
away_bye_week_numeric: int  # 0 or 1

# Or create interaction
short_week_penalty = (home_short_week * -3) + (away_short_week * 3)  # Home disadvantage, away advantage
```

**Expected Impact**: **+0.5-1% accuracy**

**Implementation**: 10 minutes - simple conversion

---

### Priority 6: Add Market-Based Features ⭐ (IF DATA AVAILABLE)

**What to Add**:
- `line_movement` - Change in spread from opening to closing
- `closing_line_value` - Difference between model prediction and closing line
- `market_consensus` - How close model is to market

**Expected Impact**: **+1-2% accuracy** (if closing lines available)

**Why This Matters**:
- Line movement indicates sharp money
- Large discrepancies between model and market may indicate value
- Market is generally efficient, so being close to market is good

**Implementation**: 1-2 hours - need to track opening vs closing lines

---

### Priority 7: Add Temporal/Context Features ⭐ (SMALL IMPACT)

**What to Add**:
- `week_of_season` - Early season (1-3) vs late season (10+)
- `conference_game` - Conference games are more competitive
- `rivalry_game` - Known rivalries (higher variance)
- `bowl_game` - Post-season games

**Expected Impact**: **+0.5-1% accuracy**

**Why This Matters**:
- Early season has more variance (teams still gelling)
- Conference games are more competitive (rivalries)
- Rivalry games have higher variance (upsets more likely)

**Implementation**: 30 minutes - add flags based on game metadata

---

## 📈 Expected Accuracy Improvements

**Current**: 56.0% accuracy

**With Priority 1 (Advanced Rolling Stats)**: **59-61%** (+3-5%)
**With Priority 1 + 2 (Rolling Stats + Interactions)**: **60-62%** (+4-6%)
**With Priorities 1-3 (Rolling Stats + Interactions + SRS)**: **61-63%** (+5-7%)
**With Priorities 1-4 (All above + Weather)**: **62-64%** (+6-8%)
**With All Priorities**: **63-66%** (+7-10%)

---

## 🔧 Implementation Roadmap

### Phase 1: Quick Wins (1-2 hours)
1. ✅ Add SRS ratings (5 min)
2. ✅ Add interaction features (15 min)
3. ✅ Convert boolean flags to numeric (10 min)
4. ✅ Fix weather data merging (30 min)

**Expected Impact**: +2-3% accuracy

### Phase 2: High Impact (3-4 hours)
1. ✅ Implement advanced rolling statistics (2-3 hours)
   - Extract from `stats_season`
   - Calculate rolling averages (3, 5, 10 games)
   - Create matchup differentials

**Expected Impact**: +3-5% accuracy

### Phase 3: Polish (1-2 hours)
1. ✅ Add temporal/context features (30 min)
2. ✅ Add market-based features if data available (1-2 hours)

**Expected Impact**: +1-2% accuracy

---

## 🎯 Recommended Next Steps

1. **Start with Phase 1** (Quick Wins) - Easy 2-3% improvement
2. **Then Phase 2** (Advanced Rolling Stats) - Biggest impact
3. **Finally Phase 3** (Polish) - Incremental improvements

**Total Expected Improvement**: **+6-10% accuracy** (from 56% to 62-66%)

---

## 📊 Feature Importance Goals

**Target Distribution** (after improvements):
- Rest days: 30-40% (down from 62.8%)
- Advanced rolling stats: 25-35% (up from 0%)
- SP+/SRS ratings: 15-20% (maintain)
- Interaction features: 10-15% (new)
- Weather: 5-10% (up from 0%)
- Other: 5-10%

This would create a more balanced, robust model that doesn't over-rely on any single feature.

---

## 💡 Key Insights

1. **Rest days are over-weighted** (62.8%) - Need to diversify
2. **Advanced metrics exist but aren't used** - Big opportunity
3. **Rolling stats are basic** - Need efficiency metrics, not just points
4. **No interaction features** - Missing non-linear relationships
5. **Weather data exists but broken** - Quick fix with good impact

The model has strong fundamentals (rest days, SP+ ratings) but needs more diverse features to improve accuracy beyond 56%.

