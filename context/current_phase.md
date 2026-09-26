# AI-SENTRY -- Current Phase

**Last Updated:** 2026-09-26
**Current Phase:** 5b -- Recommendation Engine (COMPLETE)
**Previous Phase:** 5a -- Scoring Engine (COMPLETE)
**Next Phase:** Phase 6 -- Report Generator

---

## Phase Status

| Phase | Name | Status |
|---|---|---|
| 0a-0e | Design & Documentation Foundation | COMPLETE |
| 1a | Consent Gate (CLI) | COMPLETE |
| 1b | API Endpoint Input & HTTP Probe | COMPLETE |
| 1c | Local Model Support (llama.cpp) | COMPLETE |
| 1d | Central Validation & Rejection System | COMPLETE |
| 2a | Manifest System (schema + enums + lifecycle) | COMPLETE |
| 2b | Manifest Loader System (file + CLI + merge) | COMPLETE |
| 2c | Strict Manifest Validation (post-merge semantic check) | COMPLETE |
| 2d | Manifest Display & Pre-Scan Confirmation | COMPLETE |
| 3a | Pre-Scan Estimation Engine | COMPLETE |
| 3b | Safety Threshold System (heavy scan guard) | COMPLETE |
| 3c | Engine Adapter System (mock engine) | COMPLETE |
| 5a | Scoring Engine (risk assessment) | COMPLETE |
| 5b | Recommendation Engine (remediation actions) | COMPLETE |
| 6  | Report Generator | NOT STARTED -- READY |
| 7  | Deployment Advisor + AWS Deploy Engine | NOT STARTED |
| 8  | Desktop Application UI | NOT STARTED |
| 9  | Website | NOT STARTED |
| 10 | Testing & Integration | NOT STARTED |
| 11 | Launch Prep | NOT STARTED |

---

## Phase 5b -- Recommendation Engine

### New file: `core/recommender.py`

**Architecture:**
- `_ACTION_DATABASE`: severity-tiered remediation actions for all 4 categories
  - Each category has `high`, `medium`, `low` action tiers
  - Higher tiers have more actions (high >= 5, medium >= 3, low >= 2)
- `get_actions_for_category(category, severity)` -- lookup + dedup
- `prioritize_recommendations(recs)` -- sort HIGH → MEDIUM → LOW, then alphabetically
- `generate_recommendations(risk_report)` -- orchestrator, returns frozen RecommendationReport
- `format_recommendations(report)` -- CLI display with severity tags and numbered actions

**Data types:**
- `Recommendation` (frozen): category, severity, actions (as tuple)
- `RecommendationReport` (frozen): recommendations, risk_level, risk_score, total_actions

### Integration
- CLI Step 11: `generate_recommendations(risk_report)` → `display_recommendations(rec_report)`
- Follows immediately after risk scoring (Step 10)

---

## Current Test Counts

| Suite | Tests |
|---|---|
| test_consent.py | 13 |
| test_input_handler.py | 25 |
| test_local_handler.py | 31 |
| test_validator.py | 66 |
| test_manifest.py | 73 |
| test_manifest_loader.py | 76 |
| test_manifest_validator.py | 96 |
| test_manifest_display.py | 47 |
| test_estimator.py | 57 |
| test_scan_guard.py | 51 |
| test_engine.py | 75 |
| test_scorer.py | 72 |
| test_recommender.py | 48 |
| **Total** | **730** |

---

## Full CLI Pipeline (Phase 5b -- 11 steps)

```
Step 1:  Consent gate          core/consent.py
Step 2:  Manifest load+merge   core/manifest.py
Step 3:  Manifest validation   core/manifest_validator.py
Step 4:  Estimate              core/estimator.py
Step 5:  Safety guard          core/scan_guard.py
Step 6:  Display + confirm     core/manifest_display.py
Step 7:  Connection validate   core/validator.py
Step 8:  Endpoint probe        core/input_handler.py or core/local_handler.py
Step 9:  Scan engine           core/engine_runner.py
Step 10: Risk scoring          core/scorer.py
Step 11: Recommendations       core/recommender.py
```

---

## Example: Full 4-Category Recommendations

```
------------------------------------------------------------
  RECOMMENDATIONS
------------------------------------------------------------

  [HIGH] data_leak
    1. Implement output filtering to detect and redact PII...
    2. Add a data loss prevention (DLP) layer...
    3. Restrict verbatim text reproduction...
    4. Audit training data for sensitive content...
    5. Deploy differential privacy techniques...

  [HIGH] jailbreak
    1. Implement multi-layer content filter...
    2. Deploy jailbreak detection classifier...
    3. Add response validation layer...
    4. Disable roleplay/persona-switching...
    5. Conduct regular adversarial testing...

  [HIGH] prompt_injection
    1. Implement strict input sanitization...
    2. Deploy prompt injection detection layer...
    3. Use parameterized prompt templates...
    4. Add system prompt integrity check...
    5. Conduct red-team exercise...

  [MED ] harmful_output
    1. Deploy toxicity classifier...
    2. Implement bias detection...
    3. Add factual grounding checks...

  Total actions: 18

------------------------------------------------------------
```

---

## Context Notes for AI Tools

- Recommender is PURE: no I/O, no network, no randomness
- Recommendations are ONLY for categories present in findings (no generic padding)
- Sorted HIGH → MEDIUM → LOW, then alphabetically within same severity
- Each category's action tier is determined by its max_severity from the scorer
- Unknown categories get a single generic "Review findings" action
- JSON output via `RecommendationReport.to_dict()` ready for Phase 6
- Do NOT commit or push to GitHub -- user handles commits manually
