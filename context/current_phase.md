# AI-SENTRY -- Current Phase

**Last Updated:** 2026-09-24
**Current Phase:** 3b -- Safety Threshold System (COMPLETE)
**Previous Phase:** 3a -- Pre-Scan Estimation Engine (COMPLETE)
**Next Phase:** Phase 3c -- Engine Adapters (Garak, PyRIT, DeepTeam)

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
| 3c | Engine Adapters (Garak, PyRIT, DeepTeam) | NOT STARTED -- READY |
| 4  | Normalization Layer | NOT STARTED |
| 5  | Intelligence Layer (Scoring + Remediation) | NOT STARTED |
| 6  | Report Generator | NOT STARTED |
| 7  | Deployment Advisor + AWS Deploy Engine | NOT STARTED |
| 8  | Desktop Application UI | NOT STARTED |
| 9  | Website | NOT STARTED |
| 10 | Testing & Integration | NOT STARTED |
| 11 | Launch Prep | NOT STARTED |

---

## Phase 3b -- Safety Threshold System

### New file: `core/scan_guard.py`

**Thresholds:**
- `MAX_SAFE_PROBES = 300`
- `MAX_SAFE_TIME_SEC = 300` (5 minutes)

**Functions:**
- `is_heavy_scan(estimate)` -- returns `GuardResult` (frozen dataclass)
  - `is_heavy`: True if EITHER threshold exceeded
  - `probes_exceeded` / `time_exceeded`: which specific threshold tripped
  - Boundary: exactly at threshold is NOT heavy (uses `>`, not `>=`)
- `display_warning(guard)` -- shows which thresholds exceeded with exact values
- `confirm_heavy_scan()` -- "Proceed with heavy scan? [yes/no]", 3-attempt limit, Ctrl-C safe
- `check_scan_safety(estimate)` -- orchestrator:
  - Light scan: returns True immediately, no prompt shown
  - Heavy scan: display_warning() + confirm_heavy_scan()

### Integration
- CLI pipeline now has 9 steps (was 7)
- Safety guard (Step 5) runs AFTER estimate (Step 4), BEFORE config display (Step 6)
- Heavy scan declined = exit code 0 (not an error)

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
| **Total** | **535** |

---

## Full CLI Pipeline (Phase 3b -- 9 steps)

```
Step 1: Consent gate          core/consent.py
Step 2: Manifest load+merge   core/manifest.py :: get_final_manifest()
Step 3: Manifest validation    core/manifest_validator.py :: validate_manifest()
Step 4: Estimate               core/estimator.py :: estimate_scan()
Step 5: Safety guard           core/scan_guard.py :: check_scan_safety()
        - light (<=300 probes AND <=5min): passes silently
        - heavy (>300 probes OR >5min): warning + extra "Proceed with heavy scan?"
Step 6: Display + confirm      core/manifest_display.py :: display_and_confirm()
        Shows full config, estimate, then "Proceed with scan? [yes/no]"
Step 7: Connection validate    core/validator.py :: run_all_validations()
Step 8: Endpoint probe         core/input_handler.py or core/local_handler.py
Step 9: Scan engine            [Phase 3c -- NOT YET IMPLEMENTED]
```

---

## Example: Light Scan (no warning)

```
quick depth, 1 category, 25 probes
→ Step 5 returns True silently (no extra prompt)
→ Step 6 shows config + "Proceed with scan?"
```

## Example: Heavy Scan (warning + extra confirm)

```
deep depth, 4 categories, 390 probes

------------------------------------------------------------
  [!] HEAVY SCAN DETECTED
------------------------------------------------------------

  Total probes   : 390  (threshold: 300)
  Est. time      : ~9.8 min  (threshold: 5 min)

  This scan exceeds recommended safety limits.
  It may take significantly longer than a standard scan
  and will send a large number of adversarial probes.

  Both probe count and time thresholds exceeded.

------------------------------------------------------------

  Proceed with heavy scan? [yes / no]: yes

  Heavy scan confirmed. Proceeding...

→ Then Step 6 shows full config + "Proceed with scan?"
```

---

## Context Notes for AI Tools

- `check_scan_safety()` is the single CLI entry point for the guard
- Light scans never show a warning or prompt -- returns True immediately
- Heavy scan declined = exit code 0 (user choice, not error)
- Boundary semantics: exactly at threshold is NOT heavy (strict `>`)
- Do NOT commit or push to GitHub -- user handles commits manually
