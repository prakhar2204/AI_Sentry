# AI-SENTRY -- Current Phase

**Last Updated:** 2026-09-24
**Current Phase:** 3c -- Engine Adapter System (COMPLETE)
**Previous Phase:** 3b -- Safety Threshold System (COMPLETE)
**Next Phase:** Phase 4 -- Normalization Layer / Report Generator

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
| 4  | Normalization Layer | NOT STARTED -- READY |
| 5  | Intelligence Layer (Scoring + Remediation) | NOT STARTED |
| 6  | Report Generator | NOT STARTED |
| 7  | Deployment Advisor + AWS Deploy Engine | NOT STARTED |
| 8  | Desktop Application UI | NOT STARTED |
| 9  | Website | NOT STARTED |
| 10 | Testing & Integration | NOT STARTED |
| 11 | Launch Prep | NOT STARTED |

---

## Phase 3c -- Engine Adapter System

### New files

**`core/engine_interface.py`** -- Abstract contract
- `ScanFinding` (frozen dataclass): category, severity (low/medium/high), confidence (0-1), evidence, source, probe_id
- `ScanResult`: findings list, engine_name, manifest_id, total_probes, duration_sec, error; severity count properties; to_dict()
- `BaseEngine` (ABC): name property + run_scan() abstract method

**`core/mock_engine.py`** -- Deterministic mock engine
- `MockEngine(BaseEngine)`: reads manifest categories, produces fixed findings per category
- Finding counts: prompt_injection=2, jailbreak=3, data_leak=2, harmful_output=2 (total 9 for all 4)
- Each finding has realistic evidence text, probe_id (e.g. PI-001, JB-002), and calibrated confidence
- 100% deterministic: same manifest → same findings, always

**`core/engine_runner.py`** -- Orchestrator + display
- `run_engine(manifest)` -- instantiates MockEngine, calls run_scan()
- `format_finding(finding, index)` -- per-finding CLI display with severity tag
- `format_results(result)` -- full results with sorting (HIGH → MED → LOW), severity counts, risk assessment
- `display_results(result)` / `print_scan_error(result)` -- stdout helpers

### Integration
- CLI Step 9: `run_engine(manifest)` → `display_results(scan_result)`
- Engine errors return exit code 1 with `print_scan_error()`
- The system now runs a COMPLETE scan from consent to findings output

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
| **Total** | **610** |

---

## Full CLI Pipeline (Phase 3c -- 9 steps)

```
Step 1: Consent gate          core/consent.py
Step 2: Manifest load+merge   core/manifest.py :: get_final_manifest()
Step 3: Manifest validation    core/manifest_validator.py :: validate_manifest()
Step 4: Estimate               core/estimator.py :: estimate_scan()
Step 5: Safety guard           core/scan_guard.py :: check_scan_safety()
Step 6: Display + confirm      core/manifest_display.py :: display_and_confirm()
Step 7: Connection validate    core/validator.py :: run_all_validations()
Step 8: Endpoint probe         core/input_handler.py or core/local_handler.py
Step 9: Scan engine            core/engine_runner.py :: run_engine()
        + Results display      core/engine_runner.py :: display_results()
```

---

## Example: Full 4-Category Scan Results

```
------------------------------------------------------------
  SCAN RESULTS
------------------------------------------------------------
  Engine       : mock
  Manifest ID  : 196b3b1d-...
  Probes run   : 9
  Duration     : 0.0 sec

  Findings     : 9
    HIGH       : 3
    MEDIUM     : 3
    LOW        : 3

------------------------------------------------------------

  #1 [HIGH] prompt_injection  (conf: 0.92)
     Evidence: System prompt was fully extracted...
     Probe: PI-001 | Source: mock

  #2 [HIGH] jailbreak  (conf: 0.88)
     Evidence: DAN-style jailbreak successful...
     Probe: JB-001 | Source: mock

  #3 [HIGH] data_leak  (conf: 0.85)
     Evidence: Training data extraction detected...
     Probe: DL-001 | Source: mock
  ...

------------------------------------------------------------

  [!] 3 HIGH severity finding(s) detected.
  [!] This target has critical vulnerabilities that require attention.
```

---

## Context Notes for AI Tools

- To add a real engine: subclass `BaseEngine`, implement `name` + `run_scan()`, return `ScanResult` with `ScanFinding` list
- `engine_runner.py` currently hardcodes MockEngine -- future: engine registry/selection
- `ScanFinding.severity` is validated on construction (rejects anything outside low/medium/high)
- `ScanFinding.confidence` is validated 0.0-1.0 on construction
- `format_results()` sorts findings HIGH → MEDIUM → LOW regardless of insertion order
- JSON output via `ScanResult.to_dict()` is ready for Phase 6 (Report Generator)
- Do NOT commit or push to GitHub -- user handles commits manually
