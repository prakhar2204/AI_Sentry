# AI-SENTRY — Current Phase

**Last Updated:** 2026-09-20
**Current Phase:** 2a — Manifest System (COMPLETE)
**Previous Phase:** 1d — Central Validation System (COMPLETE)
**Next Phase:** 2b — Model Adapter Layer

---

## Phase Status

| Phase | Name | Status |
|---|---|---|
| 0a | Idea Design | ✅ COMPLETE |
| 0b | Documentation Foundation | ✅ COMPLETE |
| 0c | System Execution Design | ✅ COMPLETE |
| 0d | Website Design | ✅ COMPLETE |
| 0e | Gap Analysis & Final Consolidation | ✅ COMPLETE |
| 1a | Consent Gate (CLI) | ✅ COMPLETE |
| 1b | API Endpoint Input & HTTP Probe | ✅ COMPLETE |
| 1c | Local Model Support (llama.cpp) | ✅ COMPLETE |
| 1d | Central Validation & Rejection System | ✅ COMPLETE |
| 2a | Manifest System | ✅ COMPLETE |
| 2b | Model Adapter Layer | 🔲 NOT STARTED — READY TO BEGIN |
| 3  | Engine Adapters (Garak, PyRIT, DeepTeam) | 🔲 NOT STARTED |
| 4  | Normalization Layer | 🔲 NOT STARTED |
| 5  | Intelligence Layer (Scoring + Remediation) | 🔲 NOT STARTED |
| 6  | Report Generator | 🔲 NOT STARTED |
| 7  | Deployment Advisor + AWS Deploy Engine | 🔲 NOT STARTED |
| 8  | Desktop Application UI | 🔲 NOT STARTED |
| 9  | Website | 🔲 NOT STARTED |
| 10 | Testing & Integration | 🔲 NOT STARTED |
| 11 | Launch Prep | 🔲 NOT STARTED |

---

## Implemented Phases (Code Complete)

### Phase 1a — Consent Gate
- `core/consent.py` — responsible use notice, yes/no gate, 3-strike exit
- `tests/test_consent.py` — 13 tests

### Phase 1b — API Endpoint Input & HTTP Probe
- `core/input_handler.py` — URL validation, OpenAI-compatible HTTP probe, full error classification
- `tests/test_input_handler.py` — 25 tests

### Phase 1c — Local Model Support (llama.cpp)
- `core/local_handler.py` — localhost validation, `/v1/chat/completions` probe, connection-refused guidance
- `tests/test_local_handler.py` — 31 tests

### Phase 1d — Central Validation & Rejection System
- `core/validator.py` — `validate_mode()`, `validate_target()` (api + local), `validate_input_combination()`, `run_all_validations()` orchestrator
- `tests/test_validator.py` — 66 tests

### Phase 2a — Manifest System
- `core/manifest.py` — `ScanManifest` dataclass, `ProbeCategory` / `ScanDepth` / `ScanMode` / `ManifestStatus` enums, `create_manifest()`, `load_manifest_from_file()`, `merge_cli_and_manifest()`, lifecycle state machine, serialization, display helper
- `example_manifest.json` — copyable template
- `tests/test_manifest.py` — 73 tests
- `cli/main.py` updated — `--manifest`, `--categories` flags; manifest built and displayed before scan dispatch

---

## Current Test Counts

| Suite | Tests |
|---|---|
| test_consent.py | 13 |
| test_input_handler.py | 25 |
| test_local_handler.py | 31 |
| test_validator.py | 66 |
| test_manifest.py | 73 |
| **Total** | **208** |

---

## CLI Pipeline (as of Phase 2a)

```
python __main__.py scan --target <url> [--mode api|local] [--depth quick|standard|deep]
                        [--categories <cat1> <cat2>] [--manifest <file.json>]
                        [--api-key <key>] [--output <dir>]

Flow:
  1. Consent gate (yes/no)
  2. Strict validation (mode + target + combination)
  3. Manifest creation (or file load + merge)
  4. Manifest summary displayed
  5. Endpoint probe (api or local)
  6. [Phase 3: scan engine dispatch — NOT YET IMPLEMENTED]
```

---

## Blockers

None. Phase 2b (Model Adapter Layer) is ready to begin.

---

## Context Notes for AI Tools

- All decisions documented in `context/decisions.md`
- Primary technical reference: `docs/TRD.md`
- Primary product reference: `docs/PRD.md`
- `ScanManifest` is the central contract between Input Layer and Orchestration Layer — treat its schema as stable
- `ProbeCategory` maps to TRD `VulnClass` taxonomy — Phase 3 engine adapters must respect this mapping
- PyRIT requires a secondary attacker LLM — documented in TRD §2.1, must be resolved in Phase 3
- Do NOT commit or push to GitHub — user handles commits manually
