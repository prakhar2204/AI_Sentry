# AI-SENTRY — Known Issues & Open Questions

**Last Updated:** 2026-09-13  
**Phase:** 0b — Documentation Foundation  
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

**Status:** 🟡 RISK  
**Phase Discovered:** 0b  
**Affects:** Phase 3 (Engine Adapters)

**Description:**  
PyRIT's red-teaming orchestration requires a secondary "attacker LLM" to generate adversarial follow-up prompts. The decision (D-008) is to default to Phi-3 Mini locally. However, the exact RAM/VRAM requirements to run Phi-3 Mini *alongside* the scan target model on the same machine have not been measured.

**Risk:** On machines with limited RAM (8–16GB), running two models simultaneously may be infeasible.

**Resolution Path:**  
- Phase 3: Benchmark Phi-3 Mini memory footprint on standard developer hardware configurations
- Design fallback: if hardware is insufficient for dual-model operation, PyRIT runs in single-turn mode (no attacker LLM) with coverage reduction noted in report
- Consider offering Phi-3 Mini as an optional API endpoint (HuggingFace hosted) as a middle ground

---

### KI-002: Garak Output Format Stability

**Status:** 🟡 RISK  
**Phase Discovered:** 0b  
**Affects:** Phase 3 (Garak Adapter)

**Description:**  
Garak is an actively developed research tool. Its JSONL output format and CLI interface have changed between versions. AI-SENTRY pins to a specific version, but the pinned version may have known bugs or missing probe categories.

**Risk:** The adapter must be designed for a specific Garak version. The "best current version" must be evaluated before Phase 3 begins.

**Resolution Path:**  
- Phase 3: Evaluate Garak's last 3 releases; choose the version with the most stable output format and broadest probe coverage
- Document the chosen version and its limitations in the adapter
- Build the adapter parser with explicit version checking — fail loudly if the installed Garak version doesn't match

---

### KI-003: DeepTeam Metric Threshold Calibration

**Status:** 🟡 RISK  
**Phase Discovered:** 0b  
**Affects:** Phase 3 (DeepTeam Adapter), Phase 4 (Normalization)

**Description:**  
DeepTeam uses metric scores to identify vulnerabilities (e.g., "bias score > 0.7 = finding detected"). The default thresholds may produce different false-positive rates depending on model type and domain. Thresholds that work well for a general-purpose model may not be appropriate for a domain-specific fine-tuned model.

**Risk:** Too-sensitive thresholds → excessive false positives → user distrust. Too-lenient thresholds → missed real vulnerabilities.

**Resolution Path:**  
- Phase 3: Test DeepTeam defaults against a set of known-clean and known-vulnerable models
- Design thresholds as configurable per scan (Advanced settings)
- Document the default threshold values and their empirical basis in the TRD

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

## Open Questions

| ID | Question | Priority | Target Phase for Resolution |
|---|---|---|---|
| OQ-001 | What is the minimum hardware spec for running PyRIT + Phi-3 Mini simultaneously? | High | Phase 3 |
| OQ-002 | Which version of Garak should be pinned for v1? | High | Phase 3 |
| OQ-003 | What is the exact minimum IAM policy for AWS deployment? | High | Phase 7 |
| OQ-004 | Should the confidence score weights be hardcoded or user-configurable? | Medium | Phase 5 |
| OQ-005 | How should AI-SENTRY handle a model that returns empty responses to all probes? | Medium | Phase 2 |
| OQ-006 | Should probe payloads be stored by default, or only on explicit user opt-in? | Medium | Phase 1 |
| OQ-007 | What is the right default scan depth for first-time users? | Low | Phase 8 (UI) |
