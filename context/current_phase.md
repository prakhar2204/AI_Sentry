# AI-SENTRY -- Current Phase

**Last Updated:** 2026-09-21
**Current Phase:** 2c -- Strict Manifest Validation (COMPLETE)
**Previous Phase:** 2b -- Manifest Loader System (COMPLETE)
**Next Phase:** Phase 3 -- Engine Adapters (Garak, PyRIT, DeepTeam)

---

## Phase Status

| Phase | Name | Status |
|---|---|---|
| 0a | Idea Design | COMPLETE |
| 0b | Documentation Foundation | COMPLETE |
| 0c | System Execution Design | COMPLETE |
| 0d | Website Design | COMPLETE |
| 0e | Gap Analysis & Final Consolidation | COMPLETE |
| 1a | Consent Gate (CLI) | COMPLETE |
| 1b | API Endpoint Input & HTTP Probe | COMPLETE |
| 1c | Local Model Support (llama.cpp) | COMPLETE |
| 1d | Central Validation & Rejection System | COMPLETE |
| 2a | Manifest System (schema + enums + lifecycle) | COMPLETE |
| 2b | Manifest Loader System (file + CLI + merge) | COMPLETE |
| 2c | Strict Manifest Validation (post-merge semantic check) | COMPLETE |
| 3  | Engine Adapters (Garak, PyRIT, DeepTeam) | NOT STARTED -- READY |
| 4  | Normalization Layer | NOT STARTED |
| 5  | Intelligence Layer (Scoring + Remediation) | NOT STARTED |
| 6  | Report Generator | NOT STARTED |
| 7  | Deployment Advisor + AWS Deploy Engine | NOT STARTED |
| 8  | Desktop Application UI | NOT STARTED |
| 9  | Website | NOT STARTED |
| 10 | Testing & Integration | NOT STARTED |
| 11 | Launch Prep | NOT STARTED |

---

## Implemented Phases (Code Complete)

### Phase 1a -- Consent Gate
- `core/consent.py`: responsible use notice, yes/no gate, 3-strike exit
- `tests/test_consent.py`: 13 tests

### Phase 1b -- API Endpoint Input & HTTP Probe
- `core/input_handler.py`: URL validation, OpenAI-compatible HTTP probe, error classification
- `tests/test_input_handler.py`: 25 tests

### Phase 1c -- Local Model Support (llama.cpp)
- `core/local_handler.py`: localhost-only validation, /v1/chat/completions probe
- `tests/test_local_handler.py`: 31 tests

### Phase 1d -- Central Validation & Rejection System
- `core/validator.py`: validate_mode(), validate_target(), validate_input_combination(), run_all_validations()
- `tests/test_validator.py`: 66 tests

### Phase 2a -- Manifest System
- `core/manifest.py` (core sections): ScanManifest dataclass, enums, create_manifest(), load_manifest_from_file(), merge_cli_and_manifest(), lifecycle state machine, display helper
- `example_manifest.json`: copyable template
- `tests/test_manifest.py`: 73 tests

### Phase 2b -- Manifest Loader System
- `core/manifest.py` (loader sections): ManifestLoadResult, validate_manifest_structure(), load_manifest_file(), get_final_manifest(), print_manifest_load_error()
- `cli/main.py`: --target made optional; handle_scan() uses get_final_manifest()
- `tests/test_manifest_loader.py`: 76 tests

### Phase 2c -- Strict Manifest Validation
- `core/manifest_validator.py`:
  - ManifestValidationIssue dataclass (field, value, message, hint)
  - validate_target(): non-empty string, max 2048 chars
  - validate_mode(): "api" or "local" (accepts ScanMode enum or string)
  - validate_scan_depth(): "quick", "standard", or "deep" (rejects "basic", "full", etc.)
  - validate_categories(): non-empty list, all items must be known ProbeCategory values
  - validate_output_dir(): optional, string, max 512 chars
  - validate_manifest(): fail-fast orchestrator -- returns first issue found
  - format_manifest_validation_error(): specific, readable CLI output
- `cli/main.py`: Step 3 in pipeline now calls validate_manifest()
- `tests/test_manifest_validator.py`: 96 tests

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
| **Total** | **380** |

---

## Full CLI Pipeline (Phase 2c)

```
python __main__.py scan [--target <url>] [--manifest <file.json>]
                        [--mode api|local] [--depth quick|standard|deep]
                        [--categories <cat1> <cat2>...]
                        [--api-key <key>] [--output <dir>]

Step 1: Consent gate               (core/consent.py)
Step 2: Manifest loading + merge   (core/manifest.py :: get_final_manifest)
  - loads file if --manifest given
  - applies CLI flag overrides
  - priority: CLI > file > default
Step 3: Manifest validation        (core/manifest_validator.py :: validate_manifest)
  - validates target, mode, scan_depth, categories, output_dir
  - fail-fast: first issue returned immediately
  - strict: no silent auto-correction
Step 4: Connection validation      (core/validator.py :: run_all_validations)
  - validates URL format and mode/target combination
Step 5: Mode dispatch              (core/input_handler.py or core/local_handler.py)
  - probes the actual endpoint
Step 6: Scan orchestration         [Phase 3 -- NOT YET IMPLEMENTED]
```

---

## Validation Layer Architecture

| Layer | File | Input | What it checks |
|---|---|---|---|
| Phase 1d | `core/validator.py` | Raw CLI strings | URL format, mode string, mode+target combination |
| Phase 2b | `core/manifest.py` | JSON file content | Shape, types, required keys |
| Phase 2c | `core/manifest_validator.py` | ScanManifest object | Semantic correctness of final resolved values |

These layers are intentionally separate:
- Phase 1d: validates BEFORE manifest is built
- Phase 2b: validates DURING file loading (structural)
- Phase 2c: validates AFTER merge (semantic -- last line of defense before scan engine)

---

## Scan Depth Values (IMPORTANT)

Valid values per TRD Section 2.1 / F-03:
  - quick    (5-15 min, core probes, rapid iteration)
  - standard (30-90 min, balanced coverage -- DEFAULT)
  - deep     (2-6 hrs, full enterprise audit)

"basic" and "full" are NOT valid values and will be rejected by Phase 2c.

---

## Context Notes for AI Tools

- Primary technical reference: `docs/TRD.md`
- Primary product reference: `docs/PRD.md`
- Design decisions: `context/decisions.md`
- `ScanManifest` is the pipeline contract -- all future phases receive it
- `validate_manifest()` is the LAST semantic gate before Phase 3 receives control
- Do NOT add silent value auto-correction to manifest_validator.py (D-025)
- Do NOT commit or push to GitHub -- user handles commits manually
