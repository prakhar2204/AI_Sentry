# AI-SENTRY -- Current Phase

**Last Updated:** 2026-09-20
**Current Phase:** 2b -- Manifest Loader System (COMPLETE)
**Previous Phase:** 2a -- Manifest System (COMPLETE)
**Next Phase:** 2c -- Health Check System  OR  Phase 3 -- Engine Adapters

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
| 2c | Health Check System | NOT STARTED |
| 3  | Engine Adapters (Garak, PyRIT, DeepTeam) | NOT STARTED |
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
- `core/consent.py` -- responsible use notice, yes/no gate, 3-strike exit
- `tests/test_consent.py` -- 13 tests

### Phase 1b -- API Endpoint Input & HTTP Probe
- `core/input_handler.py` -- URL validation, OpenAI-compatible HTTP probe, error classification
- `tests/test_input_handler.py` -- 25 tests

### Phase 1c -- Local Model Support (llama.cpp)
- `core/local_handler.py` -- localhost validation, /v1/chat/completions probe
- `tests/test_local_handler.py` -- 31 tests

### Phase 1d -- Central Validation & Rejection System
- `core/validator.py` -- validate_mode(), validate_target(), validate_input_combination(), run_all_validations()
- `tests/test_validator.py` -- 66 tests

### Phase 2a -- Manifest System
- `core/manifest.py` (sections 1-4): ScanManifest dataclass, enums, create_manifest(), load_manifest_from_file(), merge_cli_and_manifest()
- `example_manifest.json` -- copyable template
- `tests/test_manifest.py` -- 73 tests

### Phase 2b -- Manifest Loader System
- `core/manifest.py` (sections 5-8 added):
  - ManifestLoadResult dataclass (ok, manifest, error, hint, source)
  - validate_manifest_structure() -- pure structural check before enum parsing
  - load_manifest_file() -- hardened loader (empty file, null JSON, array JSON, comment keys)
  - get_final_manifest() -- single CLI entry point, all 3 scenarios
  - print_manifest_load_error() -- formatted error display
- `cli/main.py` updated:
  - --target now optional (can come from manifest file)
  - handle_scan() calls get_final_manifest() instead of inline try/except
  - [Config source: cli|file|merged] shown in output
- `tests/test_manifest_loader.py` -- 76 tests

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
| **Total** | **284** |

---

## CLI Pipeline (as of Phase 2b)

```
python __main__.py scan [--target <url>] [--manifest <file.json>]
                        [--mode api|local] [--depth quick|standard|deep]
                        [--categories <cat1> <cat2>...]
                        [--api-key <key>] [--output <dir>]

Scenario A -- CLI only:
  python __main__.py scan --target https://api.openai.com/v1

Scenario B -- File only:
  python __main__.py scan --manifest config.json

Scenario C -- Both (CLI wins on conflict):
  python __main__.py scan --manifest config.json --depth deep --categories jailbreak

Flow:
  1. Consent gate (yes/no)
  2. get_final_manifest() -> loads file (if any) + applies CLI overrides
  3. Strict validation (mode + target + combination)
  4. Manifest summary displayed + [Config source: cli|file|merged]
  5. Endpoint probe (api or local)
  6. [Phase 3: scan engine dispatch -- NOT YET IMPLEMENTED]
```

---

## get_final_manifest() Priority Table

| Field | Source Priority |
|---|---|
| target | CLI --target > JSON "target" > ERROR (required) |
| mode | CLI --mode > JSON "mode" > default: "api" |
| scan_depth | CLI --depth > JSON "scan_depth" > default: "standard" |
| categories | CLI --categories > JSON "categories" > depth defaults |
| api_key | CLI --api-key > env AI_SENTRY_API_KEY > JSON "api_key" > "" |
| output_dir | CLI --output > JSON "output_dir" > default: "./aisentry-report" |

---

## Blockers

None. Phase 2c (Health Check) or Phase 3 (Engine Adapters) ready to begin.

---

## Context Notes for AI Tools

- All design decisions in `context/decisions.md`
- Primary technical reference: `docs/TRD.md`
- Primary product reference: `docs/PRD.md`
- `get_final_manifest()` is the ONLY function the CLI calls for manifest resolution
- `ScanManifest` object is what all future phases receive as their config
- `ProbeCategory` (user-facing, 4 values) maps to TRD VulnClass (engine-facing, 17 values) in Phase 3
- PyRIT requires attacker LLM -- documented in TRD Section 2.1, must handle in Phase 3
- Do NOT commit or push to GitHub -- user handles commits manually
