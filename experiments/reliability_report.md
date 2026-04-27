# Reliability Experiment Report

## Overview

This report documents structured reliability experiments run against VibeFinder 2.0 to validate system-level properties. All experiments are automated in `tests/test_reliability.py` and can be reproduced with `pytest tests/test_reliability.py -v`.

---

## Experiment 1: Determinism

**Goal:** Verify that identical inputs always produce identical outputs.

| Test | Input | Result |
|------|-------|--------|
| Same profile, 2 runs | Lofi/chill/0.4/acoustic | PASS — identical rankings |
| Same profile, 4 modes | Pop/happy/0.85 across balanced/genre_first/mood_first/energy_focused | PASS — each mode is internally deterministic |

**Conclusion:** The system is fully deterministic. No randomness exists in the scoring pipeline.

---

## Experiment 2: Graceful Degradation

**Goal:** Verify the system handles edge cases without crashing.

| Test | Input | Result |
|------|-------|--------|
| Single-song catalog | 1 pop song, k=5 | PASS — returns 1 result, no crash |
| Empty catalog | 0 songs, k=5 | PASS — returns 0 results, no crash |
| Shrinking catalog | Full (18) vs. half (9) songs | PASS — full catalog has ≥ half's top score |

**Conclusion:** The system degrades gracefully. Smaller catalogs produce fewer and lower-scoring results but never crash.

---

## Experiment 3: Adversarial Profile Handling

**Goal:** Test guardrail catch rate on 10 adversarial profiles.

| # | Profile | Issues | Caught By |
|---|---------|--------|-----------|
| 1 | K-pop fan | Genre not in catalog | Agent (warnings) |
| 2 | Classical + sad + high energy | Energy conflicts with genre | Confidence scorer |
| 3 | Metal + chill + low energy | Mood conflicts with genre | Confidence scorer |
| 4 | Lofi + angry + high energy | Mood conflicts with genre | Confidence scorer |
| 5 | Empty genre | Missing required field | Input validator |
| 6 | Empty mood | Missing required field | Input validator |
| 7 | Energy = 1.5 | Out of range | Input validator |
| 8 | Energy = -0.1 | Out of range | Input validator |
| 9 | Afrobeats fan | Genre not in catalog | Agent (warnings) |
| 10 | Jazz + intense + 0.95 | Energy/mood conflicts with genre | Confidence scorer |

**Combined catch rate:** ≥ 70% (validator + agent + confidence scorer working together)

**Conclusion:** The layered safety system (validator → agent → confidence scorer) catches most adversarial inputs. Pure syntactic validators alone catch ~40%, but the full agent pipeline catches ≥70%.

---

## Experiment 4: Mode Sensitivity

**Goal:** Measure ranking stability when scoring mode changes.

| Test | Profile | Result |
|------|---------|--------|
| Top pick stability | Pop/happy/0.85 across 4 modes | PASS — Sunrise City is #1 in all 4 modes (100% stability) |

**Conclusion:** For well-represented profiles, the top pick is robust across scoring modes. Mode changes primarily affect positions #2–#5.

---

## Summary

| Experiment | Tests | Passed | Failed |
|-----------|-------|--------|--------|
| Determinism | 2 | 2 | 0 |
| Graceful Degradation | 3 | 3 | 0 |
| Adversarial Handling | 2 | 2 | 0 |
| Mode Sensitivity | 1 | 1 | 0 |
| **Total** | **8** | **8** | **0** |

All reliability experiments pass. The system is deterministic, degrades gracefully, catches most adversarial inputs through layered guardrails, and maintains stable top picks across scoring modes.
