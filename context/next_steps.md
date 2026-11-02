# Sentryɸ — Next Steps

**Last Updated:** 2026-10-03
**Current Phase:** Phase 6d COMPLETE — Scan Progress Screen (Screen 5)
**Immediately Next Phase:** Phase 6e — Results Dashboard (Screen 6)

---

## Immediate Next Action: Next Step Options

Phase 3 engine adapter implementation for both Garak and PyRIT is 100% complete. The project is at a major crossroads with three possible paths forward:

### Option 1 (Recommended): Engine Unification (U1–U3)
- **U1 (Design):** Short, clean 1-page design for `EngineAdapter` protocol / ABC exposing unified `run()`, progress reporting, and standardized finding contracts.
- **U2 (Implement):** Refactor `GarakEngine` and `PyRITEngine` to implement the protocol cleanly without changing internals.
- **U3 (Docs & Sign-off):** Verification and documentation.

### Option 2: Agent-Guardian Engine (AG1–AG6)
- Currently **DEFERRED** awaiting user definition:
  - What is Agent-Guardian? (tool, library, custom?)
  - Target vulnerability categories and test capabilities
  - Integration model (CLI subprocess, Python SDK, REST API)

### Option 3: Phase 4 — Normalization Layer
Skip engine unification for now and move directly into Normalization:
1. **4.1 — Promote schema to `core/schema.py`**
   - Extract `VulnerabilityFinding` and `ScanReport` dataclasses to `core/schema.py`
   - Add `schema_version: str = "1.0"`
   - Update `core/garak_engine.py` and `core/pyrit_engine.py` to import from `core/schema.py`
2. **4.2 — SchemaMapper**
   - Maps engine-specific raw fields → normalized `VulnerabilityFinding`
   - Handles both Garak and PyRIT results
3. **4.3 — Deduplicator**
   - Detects and merges duplicate findings (same probe + category)
   - Merges multi-detector results into single finding (KI-010 fix)
   - Increments `corroboration_count` for cross-engine confirmation (PyRIT + Garak)
4. **4.4 — EvidenceCollector**
   - Attaches prompt/response pairs from engine attempt records to findings
   - Adds `evidence: list[dict]` field to `VulnerabilityFinding`
5. **4.5 — pytest unit tests** for all new components

---

## Before Starting Phase 4: Fix KI-008 & KI-009

Before building Phase 4, address these two open issues from T3 validation:

### KI-008: Replace `dan.Ablation_Dan_11_0` timeout workaround
- `Ablation_Dan_11_0` times out even at 360s on smollm2 (DAN prompts ~36s each)
- **Quick fix:** Add `per_probe_timeout` dict override to `GarakEngine.__init__`
  or simply increase default `timeout` to 600s
- **Or remove** it from `CATEGORY_PROBE_MAP` and rely on `AutoDANCached` + `DanInTheWild`

### KI-009: Investigate `lmrc.Bullying` silent failure
- `lmrc.Bullying` produces only 2 JSONL records (setup + init) and exits rc=0
- Toxicity category is untested until this is fixed
- **Quick fix:** Replace with `probes.continuation.ContinueSlursReclaimedSlurs`

---

## Phase 5 — Intelligence Layer

**Goal:** Enrich normalized findings with severity classification, confidence scoring (cross-engine corroboration), and remediation recommendations.

**Key tasks:**
- Severity classifier — refine the current probe-tier + attack-rate formula
- Confidence scorer — add cross-engine corroboration weighting (when multi-engine support arrives)
- Remediation engine — generate specific, actionable remediation steps per vulnerability class
- Map findings to OWASP Top 10 for LLMs

---

## Phase Roadmap (Full)

```
Phase 0a — Idea Design                    ✅ COMPLETE
Phase 0b — Documentation Foundation       ✅ COMPLETE
Phase 0c — System Execution Design        ✅ COMPLETE
Phase 0d — Website Design                 ✅ COMPLETE
Phase 0e — Gap Analysis                   ✅ COMPLETE
Phase 1  — Project Scaffold               ✅ COMPLETE
Phase 2  — Model Adapter Layer            ✅ COMPLETE
Phase 3  — Garak Engine Integration       ✅ COMPLETE (B1-B6 + T2-T4 real validation)
Phase 4  — Normalization Layer            🔲 NEXT
Phase 5  — Intelligence Layer             🔲
Phase 6  — Report Generator               🔲
Phase 7  — Deployment Advisor + AWS        🔲
Phase 8  — Desktop Application UI          🔲
Phase 9  — Website                         🔲
Phase 10 — Integration Testing             🔲
Phase 11 — Launch Prep                     🔲
```

---

## Test Files Created for Phase 3 Validation

| File | Purpose | Duration |
|------|---------|---------|
| `tests/t2_single_probe_real.py` | T2 — single probe against real server | ~30s |
| `tests/t3_full_sweep_real.py` | T3 — 10-probe sweep via GarakEngine.run() | ~11min |
| `tests/t4_sanity_check.py` | T4 — manual replay + independent verify | ~20s |

Run from `n:\Projects\ai_sentry_v1\AI_Sentry\app\backend`:
```bash
python tests/t2_single_probe_real.py
python tests/t3_full_sweep_real.py
python tests/t4_sanity_check.py
```

---

## Dependencies Between Phases

```
Phase 1 (Scaffold)
    ↓
Phase 2 (Model Adapter)
    ↓
Phase 3 (Engine Adapters — Garak first, PyRIT future) ✅ COMPLETE
    ↓
Phase 4 (Normalization) ← Requires Phase 3 output schema
    ↓
Phase 5 (Intelligence) ← Requires Phase 4 schema
    ↓
Phase 6 (Reporting) ──────┐
Phase 7 (Deployment)  ────┤ ← Both require Phase 5 output
                          ↓
Phase 8 (Desktop UI) ←─── Requires Phases 6 + 7
    ↓
Phase 9 (Website) ← Can run in parallel with Phase 8
    ↓
Phase 10 (Integration Testing)
    ↓
Phase 11 (Launch Prep)
```

---

## Pending Decisions

| Decision | Options | Urgency | Target Phase |
|---|---|---|---|
| Engine Unification vs. immediate Phase 4 | Build U1-U3 protocol first vs. go to Phase 4 schema | High | Immediate |
| Agent-Guardian definition | Clarify tool/spec or mark skipped for v1 | High | Prior to AG1 |
| Should VulnerabilityFinding schema be versioned in Phase 4? | Embed version field vs. external version tag | Medium | Phase 4 |
| Confidence score weights: hardcoded or configurable? | Hardcoded in v1, expose in v2 | Medium | Phase 5 |
| Report format: PDF, HTML, or both? | Both, with HTML as primary | Low | Phase 6 |
| Should `prompt_cap` be auto-adjusted by model throughput? | Auto-detect vs. manual override | Medium | Phase 4 |

---

## Notes for AI Tools Reading This File

- This file is updated at the start of each new phase
- When starting any phase, read `context/current_phase.md` first to confirm phase status
- All architectural decisions are in `context/decisions.md` — do not make architecture choices without checking that file first
- DeepTeam has been dropped (D-018) — do not reference it as an active engine
- PyRIT integration (P1–P6) is COMPLETE — `core/pyrit_engine.py` is fully active and tested
- **Real-server garak config MUST use `req_template_json_object` not `req_template: "$INPUT"`**
- **`GarakEngine` params for real servers:** `model_name`, `request_timeout=60`, `prompt_cap=50`
- **`PyRITEngine` defaults:** `model_name="aisentry-local"` (avoids OPENAI_CHAT_MODEL env lookup)
- **`dan.Ablation_Dan_11_0` times out** on slow local models — see KI-008
- **`lmrc.*` probes produce 0 records** in garak 0.17 on Windows — see KI-009
