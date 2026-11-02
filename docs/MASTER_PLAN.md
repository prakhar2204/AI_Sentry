# AI-SENTRY — Engine Build Master Plan

**Last Updated:** 2026-11-02  
**Status:** ACTIVE — Phase 3 (Garak B1–B6 + T2–T4 & PyRIT P1–P6 COMPLETE; 148 tests passing)  
**Owner:** Engine Team

---

## SECTION 1: PROJECT OVERVIEW & CURRENT STATE

### 1.1 The Engine

AI-Sentry's core engine is ONE engine made of THREE independent adapters:

| # | Adapter | Technology | Status |
|---|---------|-----------|--------|
| 1 | **Garak** | [NVIDIA Garak 0.17.0](https://github.com/leondz/garak) — CLI subprocess | ✅ **COMPLETE** (B1–B6 + T2–T4 real-server validated) |
| 2 | **PyRIT** | [Microsoft PyRIT 1.1.0](https://github.com/Azure/PyRIT) — Python SDK | ✅ **COMPLETE** (P1–P6 complete, 66 tests passing, DoD passed) |
| 3 | **Agent-Guardian** | TBD (user to define) | ⏸️ **DEFERRED** — awaiting user definition |

### 1.2 What Exists Today

| Component | Location | Status |
|-----------|----------|--------|
| **Garak Engine** | `core/garak_engine.py` (654 lines) | ✅ Complete + real-server validated |
| **PyRIT Engine** | `core/pyrit_engine.py` (470 lines) | ✅ Complete (12 attack specs, 6 categories, offline scorers, in-memory SQLite) |
| **CLI** | `cli/main.py` | ✅ Garak & PyRIT wired (`--engine garak\|pyrit\|all`, live progress streaming) |
| **Input/Model Adapters** | `core/input_handler.py`, `core/local_handler.py`, `core/consent.py` | ✅ Complete |
| **Unit Tests** | `tests/test_pyrit_engine.py`, `tests/test_garak_engine.py`, `tests/test_consent.py` | ✅ 148 tests passing (0 failures) |
| **VulnerabilityFinding** | Defined in `core/garak_engine.py`, reused in `core/pyrit_engine.py` (D-023) | Lives here for now; Phase 4 moves it to `core/schema.py` |
| **Third-Party Licenses** | `app/backend/THIRD_PARTY_LICENSES.md` | ✅ Complete (real licenses recorded for all runtime & engine packages) |
| **Agent-Guardian** | Not started, not defined | ⏸️ Deferred until user defines scope and interface |

### 1.3 Test Baseline

```
tests/test_pyrit_engine.py + tests/test_garak_engine.py + tests/test_consent.py
  148 passed (0 failures) in ~9.8s
  - tests/test_pyrit_engine.py: 66 passed
  - tests/test_garak_engine.py: 69 passed
  - tests/test_consent.py: 13 passed
```

### 1.4 Garak Engine — Completed Work Summary

| Step | Name | Key Output |
|------|------|-----------|
| B1 | Environment & Real Integration | `tests/b1_garak_inspection.py`, JSONL structure documented |
| B2 | Probe Mapping | 21 probes × 6 categories verified, `CATEGORY_PROBE_MAP` built |
| B3 | Production Adapter | `core/garak_engine.py` — 654-line adapter with depth profiles |
| B4 | CLI Wiring | `_run_garak_scan()` in `cli/main.py`, live per-probe streaming |
| B5 | pytest Unit Tests | `tests/test_garak_engine.py` — 561 lines, fully mocked |
| B6 | Definition of Done | All 6 checklist items passed |
| T2 | Single Probe (real server) | `HijackHateHumans` — 50% attack rate, severity 4/5 |
| T3 | Full Sweep (real server) | 9/10 probes passed, 657.5s, jailbreak severity 5/5 |
| T4 | Manual Sanity Check | `DanInTheWild` confirmed vulnerable — engine is accurate |

**Bug Fixes Applied During Real-Server Validation:**

| Fix | What Changed | Before → After |
|-----|-------------|---------------|
| B-FIX-001a | Request body format | `req_template: "$INPUT"` → `req_template_json_object` (OpenAI JSON) |
| B-FIX-001b | Per-request timeout | 20s → `request_timeout=60` |
| B-FIX-002a | Prompt cap per probe | None (256 prompts) → `prompt_cap=50` |
| B-FIX-002b | rc=1 handling | Error → Success (vulnerabilities found) |

---

## SECTION 2: USER DECISIONS (CONFIRMED)

These decisions were confirmed by the user and govern all remaining work:

| # | Decision | Answer | Impact |
|---|----------|--------|--------|
| **D-Q1** | Agent-Guardian definition | **Deferred** — build PyRIT first, Agent-Guardian later | AG1–AG6 skipped for now |
| **D-Q2** | PyRIT LLM scorer | **Strictly offline** — no LLM judge dependency | Limits scorers to substring/regex/refusal |
| **D-Q3** | Fix 3 failing garak tests | **Yes** — fix now for clean baseline | Pre-requisite before P1 |
| **D-Q4** | Phase numbering | Phase 3 = ALL engines, Phase 4 = Normalization only after user go-ahead | Confirmed |

---

## SECTION 3: HARD SCOPE RULES

These rules are NON-NEGOTIABLE throughout all engine work:

1. **Phases 5–11** (Intelligence, Reporting, Deploy, UI, Website, Testing, Launch) belong to another team. Do NOT build, stub, plan, or edit anything for them.
2. Do not touch other people's code, branches, or any file unrelated to the engine.
3. No change to shared schemas/contracts without flagging and waiting for approval.
4. No new external network call, no new required manual setup step.
5. No new paid/API-key dependency without flagging and waiting for approval.
6. Never assume a field name, API signature, or output shape from memory — run it, inspect it, show the real output.
7. PyRIT's API has changed drastically between versions — everything must be verified against the installed package.

---

## SECTION 4: EXECUTION ORDER

```
COMPLETED:
  ✅ Pre-requisite: Fixed 3 failing garak tests (all 82 passing)
  ✅ PART 1 — PyRIT Engine: P1 → P2 → P3 → P4 → P5 → P6 (all 66 tests passing, DoD passed)
  ✅ Third-Party Licenses: THIRD_PARTY_LICENSES.md created & verified
  ✅ Decisions Log: D-021, D-022, D-023 recorded in context/decisions.md

CURRENT DECISION POINT:
  Option A (Recommended): PART 3 — Engine Unification:
    U1 (design only) → U2 (implement) → U3 (docs + sign-off)
    Standardizes Garak and PyRIT under unified EngineAdapter protocol.

  Option B: PART 2 — Agent-Guardian Engine:
    AG1 → AG2 → AG3 → AG4 → AG5 → AG6
    (DEFERRED until user defines what Agent-Guardian is)

  Option C: Phase 4 — Normalization Layer:
    Extract VulnerabilityFinding to core/schema.py, build Deduplicator, EvidenceCollector.
```

---

## SECTION 5: PyRIT ENGINE PROMPTS (P1–P6)

### P1 — PyRIT Environment & Real Integration Pattern

```
=== P1 — PyRIT Environment & Real Integration Pattern ===

NON-NEGOTIABLE RULE: Never assume PyRIT's API shape from memory or docs
familiarity. PyRIT's API has changed drastically between versions (e.g.
"orchestrators" vs "attack/executor" naming, PromptSendingOrchestrator vs
PromptSendingAttack, etc.). Actually install it, import it, inspect the
real objects, and show me the real output before writing any code.

TASKS:
1. Check what version of pyrit-ai is currently installed (if any).
   Check what the latest available version is. Compare against the
   pinned version in pyproject.toml (0.5.0). Report findings.

2. Install pyrit-ai (the version we decide on). If install fails or has
   dependency conflicts, document them exactly.

3. From the REAL installed package, discover:
   a. How to define a "target" for PyRIT (the object that represents
      our OpenAI-compatible REST endpoint)
   b. What scorer types exist and which ones work WITHOUT an LLM judge
      (e.g. substring match, regex, exact match, refusal detection)
   c. What attack/prompt datasets ship with PyRIT out-of-the-box
   d. How results/memory are stored (SQLite? In-memory? Files?)
   e. How to run a single attack programmatically (not CLI)

4. Start a fake HTTP server (same pattern as Garak B1). Run ONE trivial
   PyRIT attack against it. Show me:
   - The exact Python code used
   - The raw result objects (type, fields, values)
   - The memory/storage records if any
   - Any files created

5. Report:
   - API-key / LLM-dependency implications (which features need an LLM,
     which work fully offline)
   - The real class names and import paths (not guessed)
   - Any surprises vs what pyproject.toml assumed

EXIT CONDITION: One real PyRIT run completed + documented real result
structure shown. Then STOP and wait for my go-ahead.
```

---

### P2 — PyRIT Category Mapping

```
=== P2 — PyRIT Category Mapping ===

PREREQUISITE: P1 complete and approved.

TASKS:
1. Pull PyRIT's ACTUAL current datasets/attacks/scorers from the
   installed package. List every attack type and dataset that ships
   with it.

2. Map our existing 6 AI-SENTRY categories to PyRIT equivalents:
   - prompt_injection
   - jailbreak
   - encoding_injection
   - data_leakage
   - malware_generation
   - toxicity

   For each mapping, document:
   a. The PyRIT attack class / dataset name (real import path)
   b. The scorer(s) that work WITHOUT an LLM judge
   c. Whether an LLM judge scorer would add meaningful coverage
   d. "no_llm_needed" flag: true/false

3. Verify each mapping works against the fake server individually.
   Run one attack per category, show the raw result.

4. Report:
   - Categories PyRIT CANNOT cover without an LLM judge
   - Categories where PyRIT adds coverage Garak LACKS
     (e.g. multi-turn attacks, adaptive follow-ups)
   - Any categories both engines cover (overlap is expected and good)

5. Build the PYRIT_CATEGORY_MAP dict (same shape as CATEGORY_PROBE_MAP
   in garak_engine.py): { category_name: [attack_specs] }

EXIT CONDITION: Verified category map with one real run per category.
Then STOP and wait for my go-ahead.
```

---

### P3 — PyRIT Production Adapter (`core/pyrit_engine.py`)

```
=== P3 — PyRIT Production Adapter ===

PREREQUISITE: P2 complete and approved.

Build core/pyrit_engine.py following the EXACT same shape as
core/garak_engine.py. Required components:

1. PYRIT_CATEGORY_MAP — the verified P2 mapping
2. Depth profiles — match Garak's profile names/semantics:
   quick (1 attack/cat), standard (2/cat), deep (all)
3. PyRITEngine class with:
   a. __init__(target_url, output_dir, api_key, timeout, generations,
      depth, model_name, ...) — same param pattern as GarakEngine
   b. run(categories) → PyRITScanResult (same shape as GarakScanResult)
   c. _run_attack(spec, category) → AttackRunResult (same shape as
      ProbeRunResult)
   d. Result parser → VulnerabilityFinding objects
      IMPORT VulnerabilityFinding from core.garak_engine — do NOT
      move, copy, or edit it (that's Phase 4 work)
   e. Timeout handling — per-attack timeout, clean error messages
   f. Per-scan isolated memory — no cross-scan state or stale files.
      Clean up temp files after each scan.
   g. Progress reporting — PyRIT runs programmatically, so report
      progress between attack/prompt runs. Document the mechanism.

4. DO NOT:
   - Log raw harmful payloads beyond what Garak adapter already does
   - Add any new required manual setup step
   - Add any paid/API-key dependency without flagging it
   - Invent values for VulnerabilityFinding fields that PyRIT doesn't
     provide — flag them with a comment and set to sensible defaults

EXIT CONDITION: core/pyrit_engine.py exists, imports clean, basic
structural review. Then STOP and wait for my go-ahead.
```

---

### P4 — PyRIT CLI Wiring

```
=== P4 — PyRIT CLI Wiring ===

PREREQUISITE: P3 complete and approved.

TASKS:
1. Add _run_pyrit_scan() in cli/main.py, mirroring _run_garak_scan():
   - Severity-grouped output to console
   - Summary file written to output directory
   - Same progress reporting pattern

2. Add --engine flag to the scan command:
   --engine garak  (default, current behavior)
   --engine pyrit
   --engine both   (runs garak then pyrit independently)

   In "both" mode:
   - Run them sequentially (garak first, pyrit second)
   - Report results separately (two blocks of output)
   - NO merging, dedup, or cross-engine scoring (that is Phase 4+)

3. Verify with a dry-run or fake-server test that all three modes work.

EXIT CONDITION: CLI wired, all three engine modes functional. Then STOP.
```

---

### P5 — PyRIT Unit Tests

```
=== P5 — PyRIT Unit Tests ===

PREREQUISITE: P4 complete and approved.

TASKS:
1. Create tests/test_pyrit_engine.py matching test_garak_engine.py
   in rigor. Must include:
   - Category map validation (all 6 categories present)
   - Depth profile tests (quick/standard/deep slice counts)
   - Attack runner tests (mocked — no real PyRIT needed)
   - Result parser tests (from sample data)
   - Timeout handling tests
   - Error path tests (import failure, invalid spec, crash)
   - Cleanup/isolation tests (temp files removed after scan)
   - VulnerabilityFinding field mapping tests

2. All tests must be FULLY MOCKED — no real PyRIT execution needed.

3. Add ONE optional integration test against the fake server, marked
   with @pytest.mark.integration so it can be skipped:
   @pytest.mark.skipif(not FAKE_SERVER_AVAILABLE, ...)

4. Run full test suite (garak + pyrit + consent) and report results.

EXIT CONDITION: All tests pass. Full test suite output shown.
```

---

### P6 — PyRIT Definition of Done

```
=== P6 — PyRIT Definition of Done ===

PREREQUISITE: P5 complete and approved.

Run the same checklist as Garak B6, plus PyRIT-specific items:

CHECKLIST:
[x] >=6 categories mapped, each with at least 1 attack spec (PASS — 12 attack specs across 6 categories)
[x] Progress visible mid-scan, mechanism documented (PASS — streaming progress in _run_pyrit_scan)
[x] Output matches existing VulnerabilityFinding schema (all fields) (PASS — 12/12 fields match 1:1)
[x] run() works, produces visibly different results per target (PASS — 6 findings on vuln server vs 0 on resilient)
[x] Category map verified against fake server (each category runs) (PASS — 6/6 categories verified)
[x] Depth profiles match Garak semantics (quick/standard/deep) (PASS — quick=6, standard=12, deep=12)
[x] Timeout handling works (attack killed cleanly on timeout) (PASS — timed out tasks cancelled cleanly)
[x] Cleanup: no stale temp files after scan completes (PASS — in-memory SQLite, 0 temp files left)
[x] Dependency impact documented (PASS — pyrit 1.1.0 MIT license recorded; D-021, D-022)
[x] THIRD_PARTY_LICENSES updated from the real package license (PASS — app/backend/THIRD_PARTY_LICENSES.md)
[x] decisions.md updated with new D-0XX entries (PASS — D-021, D-022, D-023 recorded)

EXIT CONDITION: All items checked with real evidence (verified in tests/p6_output.txt). P1–P6 COMPLETE.
```

---

## SECTION 6: AGENT-GUARDIAN ENGINE (AG1–AG6) — DEFERRED

**BLOCKED:** Agent-Guardian is deferred until PyRIT (P1–P6) is complete and the user defines what Agent-Guardian is.

Questions that must be answered before AG work begins:
- What IS Agent-Guardian? (existing tool? custom code? library?)
- What does it test? Which vulnerability categories?
- What is its integration model? (CLI subprocess? Python SDK? REST API?)
- Is there a repo/docs URL?

**Placeholder structure (to be filled after user's answer):**

| Step | Name | Mirrors |
|------|------|---------|
| AG1 | Environment & Real Integration Pattern | P1 / Garak B1 |
| AG2 | Category/Test Mapping | P2 / Garak B2 |
| AG3 | Production Adapter (`core/agent_guardian_engine.py`) | P3 / Garak B3 |
| AG4 | CLI Wiring | P4 / Garak B4 |
| AG5 | Unit Tests | P5 / Garak B5 |
| AG6 | Definition of Done | P6 / Garak B6 |

---

## SECTION 7: ENGINE UNIFICATION (U1–U3)

### U1 — Common Interface Design

```
=== U1 — Common Engine Interface Design ===

PREREQUISITE: P6 + AG6 both complete and approved.

TASKS:
1. Before writing code, show me a SHORT design document (one page max):
   - A thin common interface (e.g. EngineAdapter protocol/ABC)
   - Both/all adapters expose the same run/progress/finding contract
   - A registry or entry point that selects engines by name
   - Minimal — NO refactor of Garak internals beyond what is strictly
     needed to match the interface

2. Show:
   - The interface methods and their signatures
   - How GarakEngine and PyRITEngine (and AgentGuardianEngine) would
     implement it
   - How the CLI/orchestrator would use it

3. DO NOT implement yet. Just the design. WAIT for my approval.

EXIT CONDITION: One-page design document shown. Then STOP.
```

---

### U2 — Engine Unification Implementation

```
=== U2 — Engine Unification Implementation ===

PREREQUISITE: U1 design approved.

TASKS:
1. Implement the approved common interface.
2. Update GarakEngine, PyRITEngine, and AgentGuardianEngine to
   conform to it.
3. Update cli/main.py to use the registry/interface for engine selection.
4. Verify with real runs against the fake server:
   - garak only
   - pyrit only
   - agent-guardian only
   - all engines
5. Show test output for each mode.

EXIT CONDITION: All engine modes work. Real verification output shown.
```

---

### U3 — Documentation & Final Sign-Off

```
=== U3 — Documentation Update & Engine Sign-Off ===

PREREQUISITE: U2 complete and approved.

TASKS:
1. Update context files:
   - architecture.md: full PyRIT section + Agent-Guardian section +
     engine-layer diagram showing all 3 adapters
   - decisions.md: new numbered D-0XX entries for EVERY decision made
   - known_issues.md: any new issues discovered
   - current_phase.md: Phase 3 FULLY COMPLETE (all engines)
   - next_steps.md: Phase 4 is NEXT

2. Final engine sign-off checklist with evidence:
   [ ] All engines produce VulnerabilityFinding objects
   [ ] All engines run independently via CLI
   [ ] "both/all" mode runs engines sequentially, reports separately
   [ ] All unit tests pass (garak + pyrit + agent-guardian + consent)
   [ ] No cross-engine state leakage
   [ ] No new paid/API-key dependency added without approval
   [ ] Documentation is consistent across all context files
   [ ] pyproject.toml dependencies are correct

3. Then STOP. Do NOT start Phase 4 until explicitly told.

EXIT CONDITION: All items checked. Full test suite output.
Phase 3 declared COMPLETE. Awaiting Phase 4 go-ahead.
```

---

## SECTION 8: KNOWN ISSUES TO FIX

| ID | Issue | Severity | Target |
|----|-------|----------|--------|
| KI-FIX-1 | 3 failing garak unit tests (T2–T4 changes) | ⚠️ Must fix | Pre-P1 |
| KI-008 | `dan.Ablation_Dan_11_0` times out on slow models | Medium | Phase 3 |
| KI-009 | `lmrc.Bullying` produces 0 records in garak 0.17 | Medium | Phase 3 |
| C-1→C-8 | 8 contradictions between context files | Low | U3 |

---

## SECTION 9: FILE MAP

```
app/backend/
├── core/
│   ├── __init__.py
│   ├── garak_engine.py        ← ✅ Garak adapter (654 lines)
│   ├── pyrit_engine.py        ← ✅ PyRIT adapter (470 lines)
│   ├── consent.py             ← ✅ User consent gate
│   ├── health.py              ← ✅ Health check
│   ├── input_handler.py       ← ✅ API input validation
│   └── local_handler.py       ← ✅ Local model handler
├── cli/
│   └── main.py                ← ✅ CLI entry (Garak + PyRIT wired)
├── tests/
│   ├── test_garak_engine.py   ← ✅ 69 unit tests (all passing)
│   ├── test_pyrit_engine.py   ← ✅ 66 unit tests (all passing)
│   ├── test_consent.py        ← ✅ 13 tests (all passing)
│   ├── b1–b6, t2–t4, p1–p6    ← ✅ Validation scripts
│   └── *_output dirs          ← ✅ Captured run outputs
├── THIRD_PARTY_LICENSES.md    ← ✅ Third-party licenses documented
└── pyproject.toml             ← ✅ Dependencies defined (garak==0.17.0, pyrit==1.1.0)
```

---

## SECTION 10: PHASE ROADMAP (FULL)

```
Phase 0a — Idea Design                          ✅ COMPLETE
Phase 0b — Documentation Foundation             ✅ COMPLETE
Phase 0c — System Execution Design              ✅ COMPLETE
Phase 0d — Website Design                       ✅ COMPLETE
Phase 0e — Gap Analysis                         ✅ COMPLETE
Phase 1  — Project Scaffold                     ✅ COMPLETE
Phase 2  — Model Adapter Layer                  ✅ COMPLETE
Phase 3  — Engine Adapters                      ✅ COMPLETE
  ├── Garak (B1-B6 + T2-T4)                    ✅ COMPLETE
  ├── PyRIT (P1-P6)                             ✅ COMPLETE (66 tests passing, DoD passed)
  ├── Agent-Guardian (AG1-AG6)                  ⏸️ DEFERRED (awaiting user definition)
  └── Unification (U1-U3)                       🔲 NEXT DECISION POINT
Phase 4  — Normalization Layer                  🔲 AFTER Phase 3 + user go-ahead
Phase 5  — Intelligence Layer                   🔲 (other team)
Phase 6  — Report Generator                     🔲 (other team)
Phase 7  — Deployment Advisor + AWS             🔲 (other team)
Phase 8  — Desktop Application UI               🔲 (other team)
Phase 9  — Website                              🔲 (other team)
Phase 10 — Integration Testing                  🔲 (other team)
Phase 11 — Launch Prep                          🔲 (other team)
```
