# AI-SENTRY — Known Issues & Open Questions

**Last Updated:** 2026-11-02  
**Phase:** 3 Complete (Garak B1–B6 + T2–T4, PyRIT P1–P6; 148 tests passing)  
**Format:** Each entry has an ID, status, and resolution path.

---

## Status Legend

- 🔴 BLOCKER — Must resolve before dependent phase can start
- 🟡 RISK — Known complexity; needs investigation before implementation
- 🟢 ACKNOWLEDGED — Known; has a plan; monitoring
- ✅ RESOLVED — No longer an issue

---

## Known Issues

---

### KI-001: PyRIT Attacker LLM Hardware Requirements Unknown

**Status:** ✅ RESOLVED  
**Phase Discovered:** 0b  
**Resolved:** Phase 3 P2 (2026-11-02)  
**Affects:** Phase 3 (Engine Adapters)

**Description:**  
PyRIT's multi-turn orchestration optionally uses an attacker LLM to generate follow-up adversarial prompts. Running a secondary LLM alongside the target model introduces significant RAM/VRAM resource contention.

**Resolution:**  
Per confirmed decision D-Q2 and implementation in P2, AI-SENTRY uses strictly offline deterministic scorers (`SubStringScorer`, regex matchers, refusal detection) across all 12 attack specs. No secondary attacker LLM is loaded or required. Scanning operates with zero extra VRAM overhead.

---

### KI-002: Garak Output Format Stability

**Status:** ✅ RESOLVED  
**Phase Discovered:** 0b  
**Resolved:** Phase 3 (2026-09-21)  
**Affects:** Phase 3 (Garak Adapter)

**Description:**  
Garak is an actively developed research tool. Its JSONL output format and CLI interface have changed between versions. AI-SENTRY pins to a specific version, but the pinned version may have known bugs or missing probe categories.

**Resolution:**  
- Garak 0.17.0 selected after evaluating real output format in B1
- Full adapter built in `core/garak_engine.py` with explicit JSONL parsing for 7 entry_types
- Key 0.17.0 changes discovered and handled: `probes.` prefix required in `--spec`, URI must come from `--config` YAML (not `--target_name`), JSONPath `$` prefix required in `response_json_field`
- 21 probes verified working across 6 categories in B2

---

### KI-003: DeepTeam Metric Threshold Calibration

**Status:** ✅ SUPERSEDED  
**Phase Discovered:** 0b  
**Superseded by:** D-018 (DeepTeam dropped entirely, 2026-09-21)  
**Affects:** N/A — DeepTeam is no longer part of the project

**Original Description:**  
DeepTeam uses metric scores to identify vulnerabilities. The default thresholds may produce different false-positive rates depending on model type.

**Resolution:**  
DeepTeam was dropped from the project in D-018 due to its hard dependency on paid API keys (OpenAI gpt-4o-mini). This issue no longer applies. See `context/decisions.md` D-018 for full rationale.

---

### KI-004: Local GGUF Model Hardware Detection Reliability

**Status:** 🟡 RISK  
**Phase Discovered:** 0b  
**Affects:** Phase 1 (Scaffold), Phase 2 (Model Adapter)

**Description:**  
Auto-detecting available RAM and VRAM accurately across Windows and Linux requires platform-specific code paths. GPU detection is particularly unreliable across different driver versions and GPU vendors (NVIDIA, AMD, Apple Silicon via Linux emulation).

**Risk:** Incorrect hardware detection leads to either: (a) refusing to run a model the machine could actually handle, or (b) starting a scan that OOMs mid-way.

**Resolution Path:**  
- Phase 2: Use conservative detection (report lower bounds, not upper bounds)
- Implement explicit hardware requirement checks before scan starts, not just warnings
- Provide a manual override for users who know their hardware
- Test on minimum spec machines (8GB RAM, no dedicated GPU) and document behavior

---

### KI-005: AWS IAM Permission Scope for One-Click Deployment

**Status:** 🟡 RISK  
**Phase Discovered:** 0b  
**Affects:** Phase 7 (Deploy Engine)

**Description:**  
The AWS provisioning sequence requires a non-trivial set of IAM permissions. Providing overly broad permissions is a security risk; too narrow permissions cause deployment failures at runtime with opaque error messages.

**Risk:** If the user doesn't have the required permissions, the deployment fails mid-way — potentially leaving partially-created resources.

**Resolution Path:**  
- Phase 7: Define the exact minimum IAM policy as a JSON document (part of documentation)
- Implement a pre-flight permission check that validates all required permissions BEFORE beginning provisioning
- Implement a rollback mechanism that cleans up all created resources on failure
- Document the minimum IAM policy in the user-facing docs and in-app

---

### KI-006: Scan Resumption After Interruption

**Status:** 🟢 ACKNOWLEDGED  
**Phase Discovered:** 0b  
**Affects:** Phase 2 (Orchestration Layer)

**Description:**  
Deep scans can take 2–6 hours. If the application crashes, the machine sleeps, or the user accidentally closes the app, the scan must be resumable from the last checkpoint — not restarted from scratch.

**Risk:** Lost scan progress on a 4-hour Deep scan is a severe UX failure.

**Resolution Path:**  
- The ScanManifest lifecycle (CREATED → RUNNING → COMPLETED) provides the checkpoint mechanism
- Each engine adapter writes progress checkpoints to disk
- On restart, AI-SENTRY detects an interrupted scan and offers to resume or discard
- This must be designed into the orchestration layer from Phase 2 onward, not retrofitted

---

### KI-007: Website Cookie Banner and Analytics Compliance

**Status:** 🟢 ACKNOWLEDGED  
**Phase Discovered:** 0b  
**Affects:** Phase 9 (Website)

**Description:**  
The website must comply with GDPR and other privacy regulations for cookie consent and analytics. Using a privacy-respecting analytics platform (Plausible, Fathom) was decided in Phase 0a, but the specific implementation needs to be confirmed.

**Resolution Path:**  
- Phase 9: Use Plausible Analytics (no cookies, GDPR-compliant by default)
- Cookie banner is required only if any cookies are set (Plausible doesn't set cookies — banner may be simplified)
- Privacy policy must explicitly state that the desktop app collects no telemetry by default

---

### KI-008: `dan.Ablation_Dan_11_0` Always Times Out on Slow Local Models

**Status:** 🟡 RISK  
**Phase Discovered:** Phase 3 T3 (2026-10-28)  
**Affects:** Phase 3 (Garak Engine), Phase 4+ (all full sweeps)

**Description:**  
`probes.dan.Ablation_Dan_11_0` contains 127 extremely long DAN jailbreak prompts
(1000–2000 chars each). On `smollm2-135m`, each prompt takes ~36s to process.
With `prompt_cap=10`, a single probe run takes ~360s — exactly at our subprocess
timeout limit. The probe consistently times out at 360s.

**Risk:** This is the most aggressive DAN variant. Not having results from it
creates a blind spot in jailbreak coverage.

**Resolution Path:**  
- Short-term: Raise `timeout` to 600s specifically for DAN-category probes OR
  add a `per_probe_timeout` override dict to `GarakEngine.__init__`
- Alternative: Skip `Ablation_Dan_11_0` on models with <5 tok/s throughput and
  document this as expected behaviour in the scan report
- Long-term: Detect model throughput at scan start and auto-adjust timeouts

---

### KI-009: `lmrc.Bullying` Silently Produces 0 Attempt Records

**Status:** 🟡 RISK  
**Phase Discovered:** Phase 3 T2 (2026-10-28)  
**Affects:** Phase 3 (Garak Engine), toxicity category

**Description:**  
When run via `python -m garak --spec probes.lmrc.Bullying`, garak runs for ~56s
then exits rc=0 with only `start_run setup` + `init` records in the JSONL.
No `plugin_cache`, no `attempt`, no `eval` records. This means the toxicity
category (`lmrc.Bullying`, `lmrc.SlurUsage`) may be completely non-functional.

**Risk:** The toxicity category silently produces 0 findings — a false sense
of security ("model is fine on toxicity") with no actual testing.

**Resolution Path:**  
- Investigate in garak 0.17.0 source: whether `lmrc` probes have an external
  data dependency, require a specific intent flag, or have a Windows-specific bug
- If unfixable in 0.17.0, replace `lmrc.Bullying` and `lmrc.SlurUsage` with
  `probes.continuation.ContinueSlursReclaimedSlurs` (64 prompts, confirmed working)
- Update `CATEGORY_PROBE_MAP` toxicity entries accordingly

---

### KI-010: Multi-Detector Probes Produce Duplicate Resilient Findings

**Status:** 🟢 ACKNOWLEDGED  
**Phase Discovered:** Phase 3 T3 (2026-10-28)  
**Affects:** Phase 4 (Normalization Layer)

**Description:**  
Some garak probes (e.g. `encoding.InjectBase64`) have multiple detectors. Each
detector produces its own `eval` record in the JSONL, and `_parse_report()` yields
one `VulnerabilityFinding` per eval record. Result: `InjectBase64` appears twice in
result.findings — one per detector — even though it is a single probe run.

**Risk:** Inflated finding counts; confusing output where one probe appears as
2 resilient findings. Not a correctness issue but a UX issue.

**Resolution Path:**  
Phase 4 Deduplicator (task 4.3) — when same `probe` appears multiple times with
same `category`, merge into a single finding with `worst_case` severity and
`combined_detectors` field listing all detector names.

---

### KI-011: rc=1 False Error Detection (RESOLVED — 2026-10-28)

**Status:** ✅ RESOLVED  
**Phase Discovered:** Phase 3 T3 (2026-10-28)  
**Resolved:** Same session, B-FIX-002b

**Description:**  
Garak returns `rc=1` when it finds vulnerabilities (FAIL results). The original
`_run_probe()` logic used `has_error = proc.returncode != 0`, which flagged every
vulnerable scan as `success=False` with error markers.

**Resolution:**  
Fixed `has_error = proc.returncode not in (0, 1)`. rc=0 means all passed;
rc=1 means vulnerabilities found — both are successful scan outcomes.
Removed `"Error:"` and `"Exception"` from error_markers (too broad).

---

## Open Questions

| ID | Question | Priority | Target Phase for Resolution |
|---|---|---|---|
| OQ-001 | What is the minimum hardware spec for running PyRIT + Phi-3 Mini simultaneously? | ✅ RESOLVED | Phase 3 (D-Q2 resolved via offline scorers; no Phi-3 Mini required) |
| OQ-002 | Which version of Garak should be pinned for v1? | ✅ RESOLVED: garak 0.17.0 | Phase 3 |
| OQ-003 | What is the exact minimum IAM policy for AWS deployment? | High | Phase 7 |
| OQ-004 | Should the confidence score weights be hardcoded or user-configurable? | Medium | Phase 5 |
| OQ-005 | How should AI-SENTRY handle a model that returns empty responses to all probes? | Medium | Phase 2 |
| OQ-006 | Should probe payloads be stored by default, or only on explicit user opt-in? | Medium | Phase 1 |
| OQ-007 | What is the right default scan depth for first-time users? | Low | Phase 8 (UI) |
| OQ-008 | Should `prompt_cap` be auto-adjusted based on detected model throughput? | Medium | Phase 4 |
