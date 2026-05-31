# Time-Weighted Hero Recommendation System

**Date:** 2026-06-01  
**Project:** MLBB Draft Assistant  
**Objective:** Improve hero recommendation algorithm using time-based matchup data from API

## Problem Statement

The current recommendation system uses general win rates and `increaseWinRate` counters but ignores game-length specific performance data available in the API. MLBB games have distinct phases (early/mid/late game), and hero effectiveness varies dramatically by timing. The API provides `min_win_rate10_12`, `min_win_rate14_16`, `min_win_rate18_20`, etc., but this data is unused.

**Current limitations:**
- Recommends heroes based only on general matchup win rates
- Doesn't account for draft strategy timing (aggressive early vs scaling late)
- Misses opportunities to counter time-specific threats
- Underutilizes rich API data

## Goals

1. Integrate time-window matchup data into hero scoring
2. Detect draft phase context (early/balanced/late game focus)
3. Amplify counter recommendations when they're strongest in the relevant time window
4. Maintain backward compatibility and graceful degradation
5. Preserve existing UI/UX flow

## Architecture Overview

### Components

**1. Phase Detector (`detectGamePhase`)**
- Analyzes current draft state (allies + enemies)
- Returns strategy context: `'early'`, `'balanced'`, or `'late'`
- Determines which time window to prioritize

**2. Time Window Mapper**
- Maps phase to API field names:
  - Early → `['min_win_rate10_12', 'min_win_rate12_14']`
  - Balanced → `['min_win_rate14_16', 'min_win_rate16_18']`
  - Late → `['min_win_rate18_20', 'min_win_rate20']`

**3. Enhanced Scoring (`computeScore`)**
- Integrates time-weighted matchup data
- Amplifies counters that are strong in the detected phase
- Falls back to existing logic when time data unavailable

### Data Flow

```
Draft State → detectGamePhase() → Phase ('early'/'balanced'/'late')
                                      ↓
Enemy Heroes → Extract matchup data → Apply time window filter
                                      ↓
                              Amplify strong matchups
                                      ↓
                              Enhanced counter score → Final recommendation
```

## Detailed Design

### 1. Phase Detection Logic

```javascript
function detectGamePhase(allies, enemies) {
  // Insufficient data - use balanced default
  if (enemies.length < 2) return 'balanced';
  
  let lateGameCount = 0;
  let earlyGameCount = 0;
  
  // Analyze enemy composition
  for (const enemyId of enemies) {
    const enemy = HEROES[enemyId];
    const counterInfo = enemy?.hero_counter_info;
    
    // Check if enemy scales to late game
    // (high win rate at 18-20+ minutes across matchups)
    let lateAvg = 0, lateCount = 0;
    let earlyAvg = 0, earlyCount = 0;
    
    for (const matchupData of Object.values(counterInfo?.sub_hero || {})) {
      if (matchupData.min_win_rate20) {
        lateAvg += matchupData.min_win_rate20 * 100;
        lateCount++;
      }
      if (matchupData.min_win_rate10_12) {
        earlyAvg += matchupData.min_win_rate10_12 * 100;
        earlyCount++;
      }
    }
    
    if (lateCount > 0 && lateAvg / lateCount > 52) lateGameCount++;
    if (earlyCount > 0 && earlyAvg / earlyCount > 53) earlyGameCount++;
  }
  
  // Decision logic
  if (lateGameCount >= 2) return 'early';    // Enemy scales - end fast
  if (earlyGameCount >= 2) return 'late';    // Enemy bullies - survive
  return 'balanced';                          // Mixed/default
}
```

**Rationale:**
- 2+ late-game enemies → aggressive early strategy to deny scaling
- 2+ early-game bullies → defensive late strategy to survive pressure
- Otherwise → balanced, flexible picks

### 2. Enhanced Counter Scoring

```javascript
function computeScore(heroId, allies, enemies) {
  const h = HEROES[heroId];
  if (!h) return -Infinity;
  
  // Detect draft phase
  const phase = detectGamePhase(allies, enemies);
  const timeFields = {
    'early': ['min_win_rate10_12', 'min_win_rate12_14'],
    'balanced': ['min_win_rate14_16', 'min_win_rate16_18'],
    'late': ['min_win_rate18_20', 'min_win_rate20']
  }[phase];
  
  // Base score (unchanged)
  let s = (h.winRate || 0) + (h.appearanceRate || 0) * 100 - (h.banRate || 0) * 0.10;
  
  const compat = h.hero_compatibility_info || {};
  const counter = h.hero_counter_info || {};
  
  // Compatibility score (unchanged)
  for (const a of allies) {
    if (compat.sub_hero?.[a]) {
      s += (compat.sub_hero[a].increaseWinRate ?? 0);
    }
    if (compat.sub_hero_last?.[a]) {
      s += (compat.sub_hero_last[a].increaseWinRate ?? 0);
    }
  }
  
  // ENHANCED: Counter score with time-window amplification
  for (const e of enemies) {
    const eCounter = HEROES[e]?.hero_counter_info || {};
    
    // Check if this hero counters enemy
    if (eCounter.sub_hero?.[heroId]) {
      const matchup = eCounter.sub_hero[heroId];
      let bonus = matchup.increaseWinRate ?? 0;
      
      // TIME AMPLIFICATION: Check if counter is strong at phase time window
      let timeWR = 0, timeCount = 0;
      for (const field of timeFields) {
        if (matchup[field] !== undefined) {
          timeWR += matchup[field] * 100;
          timeCount++;
        }
      }
      
      if (timeCount > 0) {
        const avgTimeWR = timeWR / timeCount;
        // Amplify if matchup is strong (>55%) at this time window
        if (avgTimeWR > 55) {
          bonus *= 1.25;  // 25% boost for time-specific strength
        }
        // Dampen if matchup is weak (<48%) at this time window
        else if (avgTimeWR < 48) {
          bonus *= 0.75;  // 25% reduction
        }
      }
      
      s += bonus;
    }
    
    // Check if enemy counters this hero (penalty)
    if (eCounter.sub_hero_last?.[heroId]) {
      const matchup = eCounter.sub_hero_last[heroId];
      let penalty = matchup.increaseWinRate ?? 0;
      
      // TIME AMPLIFICATION for bad matchups too
      let timeWR = 0, timeCount = 0;
      for (const field of timeFields) {
        if (matchup[field] !== undefined) {
          timeWR += matchup[field] * 100;
          timeCount++;
        }
      }
      
      if (timeCount > 0) {
        const avgTimeWR = timeWR / timeCount;
        // Amplify penalty if we're weak at this time window
        if (avgTimeWR < 45) {
          penalty *= 1.25;
        }
      }
      
      s -= penalty;
    }
  }
  
  // Role scoring (unchanged)
  const allyRoles = allies.map(a => HEROES[a]?.heroType).filter(Boolean);
  const role = h.heroType;
  if (role) {
    if (!allyRoles.includes(role)) {
      s += ROLE_BONUSES[role] || 0;
    } else {
      const flex = (role === "EXP" && allyRoles.includes("Jungle"))
                || (role === "Jungle" && allyRoles.includes("EXP"));
      s += flex ? (ROLE_PENALTIES[role] || 0) * 0.5 : (ROLE_PENALTIES[role] || 0);
    }
  }
  
  return s;
}
```

**Key improvements:**
- Phase detection determines which time window matters
- Matchup-specific time data amplifies or dampens counter scores
- Strong counters (55%+ WR at time window) get 25% boost
- Weak matchups (<48% WR) get 25% reduction
- Falls back gracefully when time data missing

### 3. Data Structure

**Existing API fields used:**
```json
{
  "hero_counter_info": {
    "sub_hero": {
      "88": {
        "winRate": 54.1095,
        "increaseWinRate": 3.9036,
        "min_win_rate10_12": 0.682197,
        "min_win_rate12_14": 0.651849,
        "min_win_rate14_16": 0.620172,
        "min_win_rate16_18": 0.58691,
        "min_win_rate18_20": 0.566675,
        "min_win_rate20": 0.523699
      }
    }
  }
}
```

**No schema changes required** - all data already exists in `hero_info.json`.

## Implementation Plan

### Phase 1: Core Logic
1. Add `detectGamePhase()` function
2. Modify `computeScore()` to integrate time-window amplification
3. Test with existing data

### Phase 2: UI Enhancement (Optional)
1. Add phase indicator badge: "🗡️ Early" / "⚖️ Balanced" / "🛡️ Late"
2. Show in turn bar or recommendations panel
3. Help users understand recommendation context

### Phase 3: Testing
1. First pick scenario (no enemies) → verify balanced default
2. Late-game enemy comp → verify early phase triggers, recommends early bullies
3. Early-game enemy comp → verify late phase triggers, recommends scaling heroes
4. Missing time data → verify graceful fallback

## Error Handling

**Missing time data:**
- Falls back to base `increaseWinRate` (current behavior)
- No errors or undefined values

**Malformed matchup data:**
- Check `!== undefined` before accessing time fields
- Skip amplification if data unavailable
- Graceful degradation to existing scoring

**Performance:**
- Time field lookups are O(1) nested object access
- Phase detection is O(n) where n = enemy count (max 5)
- Negligible impact on UI responsiveness

## Testing Scenarios

### Test Case 1: Late-Game Enemy Composition
**Setup:**
- Enemy picks: Fanny (late-game scaler), Lesley (late-game carry)
- Phase should detect: `'early'` (counter their scaling)

**Expected:**
- Recommendations prioritize heroes with high win rates at 10-14 minutes against Fanny/Lesley
- Early-game bullies rank higher than usual

### Test Case 2: Early-Game Enemy Pressure
**Setup:**
- Enemy picks: Gusion (early aggro), Claude (early push)
- Phase should detect: `'late'` (survive to scale)

**Expected:**
- Recommendations prioritize heroes with high win rates at 18-20 minutes
- Safe, scaling heroes rank higher

### Test Case 3: Mixed Composition
**Setup:**
- Enemy picks: 1 early, 1 late, 1 balanced
- Phase should detect: `'balanced'`

**Expected:**
- Recommendations use 14-18 minute time windows
- Balanced scoring across all factors

### Test Case 4: Missing Data
**Setup:**
- Hero with no time-specific win rates in matchup data

**Expected:**
- Falls back to base `increaseWinRate`
- No errors or warnings
- Recommendation still appears

## Success Metrics

**Qualitative:**
- Recommendations feel more contextually appropriate
- Users understand why certain heroes are suggested
- Counters align with game phase strategy

**Quantitative:**
- Phase detection triggers correctly (manual verification)
- Time-amplified scores differ from base scores by 10-25%
- No performance degradation (<10ms additional compute time)
- Zero errors in production

## Rollback Plan

If issues arise:
1. Comment out phase detection call in `computeScore()`
2. Remove time-window amplification logic
3. System reverts to original behavior
4. All existing functionality preserved

The changes are additive and non-breaking - easy to disable if needed.

## Future Enhancements

**Not in this implementation, but possible:**
- User preference for draft strategy (let user force early/balanced/late)
- Machine learning to predict optimal phase based on rank/meta
- Historical performance tracking of time-weighted recommendations
- Integration with live game duration statistics

## Summary

This design integrates rich time-based matchup data from the API into the recommendation algorithm. By detecting draft phase context and amplifying counters that are strongest in the relevant time window, recommendations become more strategically aligned with game timing. The implementation is non-breaking, gracefully degrades when data is missing, and preserves all existing functionality while adding intelligence to hero scoring.
