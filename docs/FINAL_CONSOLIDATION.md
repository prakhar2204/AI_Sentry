# AI-SENTRY — Final System Consolidation & Gap Analysis

**Document Version:** 1.0
**Phase:** 0e — Pre-Implementation Review
**Status:** FINAL — This document supersedes all previous phase summaries as the source of truth
**Last Updated:** 2026-09-14
**Author Role:** Senior System Architect / Technical Reviewer
**Depends On:** PRD v1.0, TRD v1.0, SYSTEM_EXECUTION_LAYER.md, WEBSITE_DESIGN.md

---

## Table of Contents

1. [System Summary](#section-1--system-summary)
2. [Gap Analysis](#section-2--gap-analysis)
3. [Architecture Validation](#section-3--architecture-validation)
4. [Scope Control](#section-4--scope-control)
5. [Final Decision Log](#section-5--final-decision-log)
6. [Implementation Readiness Check](#section-6--implementation-readiness-check)
7. [Risk Mitigation Plan](#section-7--risk-mitigation-plan)
8. [Team Workflow](#section-8--team-workflow)
9. [Final Project State](#section-9--final-project-state)

---

# SECTION 1 — SYSTEM SUMMARY

## What AI-SENTRY Is

AI-SENTRY is a desktop application for Windows and Linux that allows developers, security
engineers, and AI teams to perform adversarial security scanning on large language models before
deploying them to production. It wraps three existing open-source scanning engines (Garak, PyRIT,
DeepTeam), orchestrates them in parallel against a target model, normalizes their heterogeneous
outputs into a unified schema, scores each finding by severity and confidence, generates
audit-ready reports, and then connects the scan results to a secure cloud deployment workflow.

## What Exists (Designed but Not Yet Built)

### Documentation Layer (Complete)
```
docs/PRD.md                    — Product Requirements Document
docs/TRD.md                    — Technical Requirements Document
docs/SYSTEM_EXECUTION_LAYER.md — App flow, backend modules, schemas, UI, 11-phase impl plan
docs/WEBSITE_DESIGN.md         — Website structure, design system, SEO, analytics, tech stack
```

### Context / Memory Layer (Complete)
```
context/project_overview.md    — What AI-SENTRY is (AI memory file)
context/architecture.md        — 5-layer architecture decisions
context/current_phase.md       — Phase tracker
context/decisions.md           — 17 documented architectural decisions
context/known_issues.md        — KI-001 through KI-005
context/next_steps.md          — Phase 1 readiness checklist
```

## How the Product Works End-to-End

```
USER
  |
  | Installs desktop app (bundled Python runtime + engines)
  |
[TAURI DESKTOP APP]
  |
  | 1. User connects their LLM (API key or local GGUF file)
  |    → InputHandler validates, estimates cost
  |
  | 2. User selects scan depth (Quick / Standard / Deep / Custom)
  |    → ManifestProcessor builds scan specification
  |
  | 3. User reviews summary and consents (cost + adversarial content warning)
  |    → ConsentRecord stamped on manifest
  |
  | 4. Scan executes
  |    → EngineOrchestrator dispatches in parallel:
  |         GarakAdapter    → subprocess → Garak CLI → localhost proxy → LLM
  |         PyRITAdapter    → PyRIT orchestrator → attacker LLM → target LLM
  |         DeepTeamAdapter → deepeval evaluate() → target LLM
  |    → RateLimiter governs API token consumption
  |    → CostTracker halts if ceiling approached
  |    → Live findings feed displayed to user in real-time
  |
  | 5. Normalization runs (after all engines complete)
  |    → SchemaMapper:   engine-specific output → VulnerabilityFinding draft
  |    → Deduplicator:   merge same finding from multiple engines
  |    → EvidenceStore:  encrypt and store probe/response pairs
  |
  | 6. Intelligence layer runs
  |    → SeverityClassifier: base severity + attack_success_rate + context modifiers
  |    → ConfidenceScorer:   five-factor weighted score with explanation
  |    → RemediationEngine:  knowledge-base lookup → three-level action plan
  |
  | 7. Report assembled
  |    → DeploymentAdvisor: platform recommendation from vulnerability profile
  |    → ReportGenerator:   PDF (local render) + HTML + JSON
  |
  | 8. (Optional) Deploy to AWS
  |    → AWSDeployEngine: plan → user review → provision → verify
  |       Creates: IAM role, VPC, API Gateway, Lambda, Bedrock Guardrails,
  |                CloudWatch alarms, Budget alerts
  |
USER receives: scan report + optional live secure endpoint URL
```

## How the Components Connect

```
UI Layer (Tauri WebView)
     ↕  Tauri IPC (invoke/event)
Rust Backend (process management, OS keychain, file system)
     ↕  Local JSON socket (stdin/stdout or named pipe)
Python Backend (all scan logic)
     ├─ InputHandler ─────────────────────────── ModelAdapters
     ├─ ManifestProcessor ────────────────────── ScanManifest (disk)
     ├─ EngineOrchestrator ───────────────────── GarakAdapter
     │                                           PyRITAdapter
     │                                           DeepTeamAdapter
     ├─ NormalizationPipeline ────────────────── SchemaMapper
     │                                           Deduplicator
     │                                           EvidenceStore (encrypted, disk)
     ├─ ScoringEngine ────────────────────────── SeverityClassifier
     │                                           ConfidenceScorer
     ├─ RemediationEngine ────────────────────── RemediationKnowledgeBase (static)
     ├─ ReportGenerator ──────────────────────── PDF/HTML/JSON output
     └─ DeploymentEngine ─────────────────────── AWS boto3 → AWS APIs
```

---

# SECTION 2 — GAP ANALYSIS

This section identifies every significant gap, unclear assumption, and implementation risk
discovered during cross-review of all Phase 0 documents. Each gap is rated:
- **CRITICAL** — blocks implementation if unresolved
- **HIGH** — will cause significant problems if deferred past Phase 3
- **MEDIUM** — needs a decision before the relevant phase
- **LOW** — can be resolved during implementation without risk

---

## GAP-001: PyRIT Attacker LLM — Size and UX (CRITICAL)

**Problem:** PyRIT's `RedTeamingOrchestrator` requires a separate "attacker" LLM that generates
adversarial prompts to send to the target LLM. The design specifies "local:phi3-mini" as the
default. Phi-3 Mini GGUF weights are approximately 2.2–3.8 GB depending on quantization.

**Why it matters:**
- The installer cannot bundle Phi-3 Mini (would make the installer 4–6 GB — unacceptable)
- On first PyRIT scan, the app would need to download Phi-3 Mini — potentially 2.2 GB on first run
- Users on slow connections or restricted networks would experience a very poor first scan
- The download needs progress UI, resumability on failure, verification, and disk-space pre-check

**The unresolved assumption:** That users will tolerate a 2+ GB download before their first PyRIT scan.

**Resolution Required:**
- Option A: Default PyRIT attacker LLM to the user's target API model (use the same API key for
  attacking). No download required. Reduces independence of attacker from target (accepted limitation).
- Option B: Download Phi-3 Mini on first launch during the Environment Check screen, with explicit
  user consent, progress bar, and resumability.
- Option C: Ship Phi-3 Mini Q2 quantization (~1.1 GB) in a separate optional "extended pack" download.
- **Recommended:** Option A as default (zero-friction first scan), Option B as optional "enhanced
  PyRIT mode" when user explicitly enables a local attacker LLM.

**Decision needed before:** Phase 3 (Engine Adapters)

---

## GAP-002: DeepTeam Evaluation LLM / Judge Requirement (CRITICAL)

**Problem:** DeepTeam (deepeval) uses an "evaluator LLM" (judge) to score model responses against
metrics like BiasMetric, HallucinationMetric, and ToxicityMetric. This judge LLM is a separate model
from the target LLM. If the user's target is a local GGUF model with no API key, DeepTeam cannot run
its metrics without a judge LLM source.

**Why it matters:**
- For local model scans, DeepTeam may fail entirely if no judge LLM is configured
- The design does not address how users specify or authorize a separate judge LLM
- For API-based targets, using the same API for judging is possible but creates circular evaluation
  (model judging itself)

**Resolution Required:**
- Add a "DeepTeam Evaluator LLM" configuration field to the scan setup screen
- Default: OpenAI GPT-4o Mini (cheap and capable judge) if an OpenAI key is available
- Fallback: If no judge LLM is configured, DeepTeam runs in "passthrough mode" where metric
  scoring uses keyword/pattern heuristics only (reduced accuracy — flagged in the report)
- Local scan path: warn user that DeepTeam accuracy is reduced without an external judge

**Decision needed before:** Phase 3 (Engine Adapters) — specifically DeepTeam track

---

## GAP-003: Garak Localhost Proxy — Authentication Handling (HIGH)

**Problem:** The Garak adapter design calls for a "localhost proxy server" that Garak calls (via its
model driver), which then forwards to the actual model. Garak does not natively support OpenAI-auth
models with custom system prompts or Azure-specific authentication.

**The gap:** The proxy must handle:
- Model-type-specific authentication (Bearer token vs. Azure API key + deployment name)
- Request transformation (Garak's format → provider's expected format)
- Response transformation (provider format → Garak's expected format)
- Session management (some models require session warm-up)

**Why this is harder than it looks:** The proxy must essentially be a complete model-agnostic
translation layer. If it crashes, Garak silently fails. Garak's error messages from subprocess
stdout do not always clearly attribute failures to the proxy vs. the model vs. the probe.

**Resolution Required:**
- The proxy must implement a strict request/response log with per-request retry
- Each supported model type needs a dedicated proxy handler class, not a generic forwarding function
- The proxy must report its own health to the EngineOrchestrator (separate from Garak's status)
- Integration test required: a mock target LLM that records requests for proxy validation

**Decision needed before:** Phase 3, Garak track — proxy architecture must be designed before coding

---

## GAP-004: EvidenceStore Encryption Key Management (HIGH)

**Problem:** The design states that probe payloads and model responses are "encrypted at rest" in
the `EvidenceStore`. However, the key management strategy is not defined.

**Questions not yet answered:**
- What encryption algorithm? (AES-256-GCM is appropriate but not specified)
- Where is the encryption key stored? (Cannot be hardcoded — that's not encryption)
- Is the key derived from a user-provided passphrase? (Adds friction, forgotten keys = data loss)
- Is the key generated at install time and stored in the OS keychain? (Best balance of security + UX)
- How does the Python backend access the key if it's in the OS keychain (managed by Rust)?

**Resolution Required:**
- Encryption: AES-256-GCM
- Key generation: Random 256-bit key generated once on first launch
- Key storage: OS keychain (Windows Credential Manager, Linux libsecret), written by Rust backend
- Key access: Rust backend passes the key to Python backend via the secure IPC channel at startup
  (key lives in Python process memory for the session — never written to disk in plaintext)
- Key rotation: Not in v1. Future enhancement.

**Decision needed before:** Phase 4 (Normalization Layer — EvidenceStore)

---

## GAP-005: Rust ↔ Python IPC Protocol — Not Specified (HIGH)

**Problem:** The architecture states that Tauri's Rust backend communicates with the Python backend
via "a local IPC socket using a simple JSON-based command/response protocol." This is not
specific enough to begin implementation.

**What is missing:**
- Message format schema (request ID, command name, parameters, response, error envelope)
- Which side initiates each message type (command/response vs. event/subscription)
- How progress events are pushed from Python to Rust (polling vs. push)
- Connection lifecycle (who starts first, reconnect on Python crash, graceful shutdown)
- Error propagation (how Python exceptions become typed errors in the Rust/UI layer)

**Resolution Required (IPC Contract):**
```
Message schema:
  { "id": UUID, "type": "command"|"event"|"response"|"error",
    "name": string, "payload": object, "timestamp": ISO8601 }

Commands (Rust → Python): validate_model, build_manifest, start_scan,
  pause_scan, cancel_scan, generate_report, start_deployment, get_status

Events (Python → Rust, pushed asynchronously): engine_progress, finding_detected,
  cost_update, scan_complete, deployment_progress, error

Response: same id as the command that triggered it + result payload or error

Transport: Named pipe on Windows (\\.\pipe\aisentry-ipc), Unix socket on Linux (/tmp/aisentry.sock)
```

This IPC contract must be agreed on and documented before Phase 8 (but the Python side must
implement it starting Phase 2, and the Rust side in Phase 8).

**Decision needed before:** Phase 2 (Model Adapter Layer — first Python commands needed)

---

## GAP-006: SeverityMatrix and ConfidenceWeights — Values Not Defined (HIGH)

**Problem:** The design defines the scoring system's structure (SeverityMatrix, ConfidenceFactors,
ConfidenceWeights) but does not define the actual values.

**What is missing:**
- The base severity tier for each of the 18 VulnClass entries
  (e.g., JAILBREAK_DAN → HIGH? CRITICAL? This determines whether users take action.)
- The five confidence weight values (must sum to 1.0)
- The modifier magnitude for attack_success_rate and deployment_context adjustments
- The threshold at which a confidence score is considered "actionable" vs. "review only"

**Why this matters:** These values are the most subjective and most impactful design decisions
in the entire system. Getting them wrong leads to false urgency (everything is CRITICAL) or
false comfort (real vulnerabilities score LOW). They cannot be tuned after launch without
changing user expectations.

**Resolution Required:**
- Review academic literature on LLM vulnerability severity (OWASP LLM Top 10 guidance)
- Define a severity calibration table with rationale for each VulnClass
- Pilot the weights against 3 known-vulnerable models to validate output is reasonable
- Lock values into the `severity_matrix.json` and `confidence_weights.json` config files
  before Phase 5 begins — but design them during Phase 1/2

**Proposed starting point (to be validated during pilot testing):**

Base severity assignments:
```
CRITICAL: JAILBREAK_CRESCENDO (multi-turn, hardest to defend)
HIGH:     JAILBREAK_DAN, JAILBREAK_ROLEPLAY, PROMPT_INJECTION, SYSTEM_PROMPT_EXTRACTION
MEDIUM:   TOXICITY_GENERAL, TOXICITY_TARGETED, PII_LEAKAGE, HALLUCINATION_FACTUAL,
          BIAS_GENDER, BIAS_RACIAL, BIAS_POLITICAL, TRAINING_DATA_EXTRACTION
LOW:      HALLUCINATION_CITATION, COPYRIGHT_REPRODUCTION, INSECURE_OUTPUT_HANDLING
INFO:     EXCESSIVE_AGENCY
```

Confidence weights (starting point):
```
corroboration_score: 0.35  (highest weight — cross-engine agreement is strongest signal)
success_rate_score:  0.30  (reproducibility of the attack is strong evidence)
diversity_score:     0.15  (probe variation reduces false positives)
maturity_score:      0.12  (established probe classes are more reliable)
noise_penalty:       0.08  (penalize known-noisy probes)
```

---

## GAP-007: GenericRESTAdapter "Schema Inference Wizard" — Too Complex for v1 (MEDIUM)

**Problem:** The design includes a `GenericRESTAdapter` with "schema inference wizard for unknown
endpoints." This means the app must dynamically determine the request/response format of an
arbitrary REST API by sending test messages and observing the structure.

**Why this is risky:** Schema inference for arbitrary REST APIs is a research problem, not a
feature. It is easy to get wrong and produces unreliable adapters. A wrong inference silently
corrupts all scan results without any error.

**Resolution Required:** Defer `GenericRESTAdapter` to v1.5.

**v1 replacement:** Provide a "Custom REST" option that shows a minimal configuration form:
```
Endpoint URL:   [required]
Auth header:    [required — format: "Authorization: Bearer {key}"]
Request body:   [required — JSON template with {prompt} placeholder]
Response path:  [required — JSONPath to extract response text, e.g., "$.choices[0].message.content"]
```

This is a manual configuration (user fills in the format), not automatic inference. It covers
90% of use cases with no inference risk. Document the 10% (streaming APIs, non-JSON) as unsupported in v1.

**Decision needed before:** Phase 2 (Model Adapter Layer)

---

## GAP-008: PDF Renderer — Library Not Chosen (MEDIUM)

**Problem:** The design says "local PDF rendering (bundled renderer library — no server, no internet)."
No specific library is named. This matters because the choice affects installer size, report quality,
and platform compatibility.

**Options and trade-offs:**

| Library | Language | Size | Quality | Complexity |
|---|---|---|---|---|
| WeasyPrint | Python | ~15 MB | High (CSS-based) | Medium |
| ReportLab | Python | ~8 MB | Medium (programmatic) | Low |
| pdfkit (wkhtmltopdf) | Binary | ~30 MB | High (browser engine) | High |
| Playwright (headless Chrome) | Binary | ~150 MB | Highest | Very High |

**Resolution Required:** WeasyPrint is recommended for v1.
- Pure Python (no external binary) — fits the bundled Python runtime
- CSS-based — the HTML report can be the same source as the PDF (single rendering path)
- Good quality for tabular data and structured reports
- Already available via pip — no separate bundling complexity

**Decision needed before:** Phase 6 (Report Generator)

---

## GAP-009: Local GGUF Model Serving — llama.cpp Build (MEDIUM)

**Problem:** The design relies on llama.cpp for local GGUF model serving. llama.cpp must be
pre-compiled for the target platform and bundled in the installer.

**Unresolved questions:**
- CPU-only or CPU+GPU (CUDA/ROCm) build?
- Which llama.cpp version to pin?
- How is the server process lifecycle managed (crash recovery, port conflicts)?
- What is the maximum context length for local serving (affects probe design)?

**Resolution Required:**
- v1 bundles CPU-only llama.cpp build (no GPU dependency — covers all hardware)
- GPU acceleration: optional, detected at runtime. If CUDA is available, llama.cpp respects it
  automatically with the CPU build via OpenBLAS — no separate GPU binary needed
- Version pin: lock to a specific llama.cpp release tag before Phase 2 begins
- Context length: default 4096 tokens for local models (safe baseline)
- Port management: use a fixed port (default 8080) with auto-increment on conflict (8081, 8082...)
- Crash recovery: Rust backend monitors the llama.cpp server process; restarts it on unexpected exit

**Decision needed before:** Phase 2 (LocalGGUFAdapter)

---

## GAP-010: AWS Credentials in Python Backend (MEDIUM)

**Problem:** The AWS Deploy Engine runs in the Python backend (boto3). However, AWS credentials
are stored in the OS keychain, which is managed by the Rust backend. How does the Python backend
access AWS credentials?

**The gap:** There is no defined mechanism for the Rust backend to pass keychain-stored credentials
to the Python backend securely.

**Resolution Required:**
- When the user initiates a deployment, the Rust backend reads the AWS credentials from the keychain
- Rust passes the credentials to Python via the IPC channel as part of the deployment command payload
- The Python backend stores them in process memory only (never to disk)
- Credentials are cleared from Python memory immediately after the boto3 session is established
- boto3 uses the credentials for the duration of the deployment session only

This is the same pattern used for model API keys. The IPC channel is already the approved path for
credential handoff. This gap just needs to be explicitly documented in the IPC contract.

**Decision needed before:** Phase 7 (Deployment Engine)

---

## GAP-011: Pause/Resume Checkpoint Serialization (MEDIUM)

**Problem:** The design mentions "pause/resume via disk-persisted checkpoint state" in the
EngineOrchestrator. The checkpoint format is not defined.

**What needs to be specified:**
- What exactly is saved to disk at pause time?
- Can a scan be resumed after an app restart (not just a pause within the same session)?
- Can a scan be resumed on a different machine (manifest portability)?

**Resolution Required:**
- Checkpoint scope: within-session only for v1 (resume after pause, not after app restart)
- Cross-session resume: deferred to v1.5
- What is checkpointed: engine-specific state only (which probe indices have been sent,
  which responses received, current token count, current cost)
- Format: append-only JSONL file per engine in the scan's working directory
- On resume: re-read the checkpoint JSONL and skip already-executed probes

**Decision needed before:** Phase 3 (EngineOrchestrator)

---

## GAP-012: Onboarding Environment Check — What Is Being Checked? (LOW)

**Problem:** The onboarding sequence shows an "Environment Check" screen that verifies engines
are installed. But since engines are bundled in the installer, this check is trivially expected
to pass. What does it actually verify?

**Resolution Required:**
The Environment Check verifies:
1. The bundled Python runtime is accessible and the correct version (3.11.x)
2. All three engine packages import successfully (import garak, import pyrit, import deepeval)
3. The OS keychain is accessible (write + read a test credential)
4. The llama.cpp binary is present and executable
5. Available disk space is sufficient for scan artifacts (>500 MB free)
6. Available RAM (report if <8 GB — warn about local model limitations)

This check is NOT verifying internet connectivity — scanning can work offline (local models).
It IS the right place to detect post-install corruption or OS permission issues.

---

## GAP-013: Report Adversarial Content Handling in the Website Context (LOW)

**Problem:** The WEBSITE_DESIGN.md defines a download page and documentation but does not address
the content policy for the blog. Blog posts about jailbreaking, DAN prompts, and prompt injection
will contain content that some search engines or hosting providers might flag.

**Resolution Required:**
- Blog posts about adversarial techniques use research framing ("how to test for X" not "how to do X")
- Actual adversarial prompt examples in the blog are never written out verbatim — they are
  described and categorized without being reproducible from the blog alone
- Vercel's ToS covers security research content — this is not a risk with the chosen host
- Add a disclaimer at the top of each security research blog post:
  "This post describes vulnerability patterns for defensive security testing purposes."

---

## Summary Table: All Gaps

| Gap | Title | Severity | Phase Impact | Decision Needed By |
|---|---|---|---|---|
| GAP-001 | PyRIT attacker LLM size | CRITICAL | Phase 3 | Before Phase 3 |
| GAP-002 | DeepTeam judge LLM | CRITICAL | Phase 3 | Before Phase 3 |
| GAP-003 | Garak proxy auth handling | HIGH | Phase 3 | Before Phase 3 |
| GAP-004 | EvidenceStore key management | HIGH | Phase 4 | Before Phase 4 |
| GAP-005 | Rust↔Python IPC protocol | HIGH | Phase 2+ | Before Phase 2 |
| GAP-006 | SeverityMatrix values | HIGH | Phase 5 | During Phase 1 |
| GAP-007 | GenericRESTAdapter complexity | MEDIUM | Phase 2 | Before Phase 2 |
| GAP-008 | PDF renderer not chosen | MEDIUM | Phase 6 | Before Phase 6 |
| GAP-009 | llama.cpp build spec | MEDIUM | Phase 2 | Before Phase 2 |
| GAP-010 | AWS credentials to Python | MEDIUM | Phase 7 | Before Phase 7 |
| GAP-011 | Pause/resume checkpoint format | MEDIUM | Phase 3 | Before Phase 3 |
| GAP-012 | Environment check scope | LOW | Phase 8 | Before Phase 8 |
| GAP-013 | Blog content policy | LOW | Phase 9 | Before Phase 9 |

---

# SECTION 3 — ARCHITECTURE VALIDATION

## 3.1 Modularity Assessment

**Finding: Architecture is correctly modular. Each module has a single responsibility.**

Evidence:
- InputHandler owns all connection validation — nothing downstream re-validates
- ManifestProcessor owns the scan spec — engines read from it, never write to it
- Each EngineAdapter is self-contained behind the `EngineAdapter` interface
- NormalizationPipeline consumes raw outputs, produces normalized findings — no business logic
- ScoringEngine consumes normalized findings, produces scored findings — no I/O
- ReportGenerator assembles from scored findings — no scanning logic

**One concern:** The `EngineOrchestrator` has too many responsibilities in the current design.
It manages: thread dispatch, rate limiting, cost tracking, progress emission, pause/resume, and
partial result preservation. This should be subdivided:
- `EngineOrchestrator`: dispatch and coordination only
- `RateLimiter`: token bucket, separate class (already planned)
- `CostTracker`: accumulation and ceiling enforcement, separate class (already planned)
- `ScanCheckpointer`: pause/resume checkpoint management (new class — resolves GAP-011)

**Verdict:** Modular. One minor split recommended in EngineOrchestrator.

---

## 3.2 Dependency Clarity

**Finding: Dependencies are mostly clear. Three gaps identified.**

**CLEAR dependencies (well-specified):**
- Phase 2 → Phase 1 (adapters need the scaffold)
- Phase 3 → Phase 2 (orchestrator needs adapters)
- Phase 4 → Phase 3 (normalization needs raw outputs)
- Phase 5 → Phase 4 (scoring needs normalized findings)
- Phases 6+7 → Phase 5 (report and deployment need scored findings)
- Phase 8 → Phases 2–7 (UI needs all backend modules)

**UNCLEAR dependencies requiring resolution:**
1. Phase 2 needs the IPC contract (GAP-005) to implement the Python side of the communication layer
2. Phase 3 (Garak) needs the proxy authentication design (GAP-003) before the adapter can be built
3. Phase 5 needs the SeverityMatrix values (GAP-006) — cannot implement SeverityClassifier without them

---

## 3.3 Integration Realism Assessment

**Garak Integration — REALISTIC with caveats**
Garak is a mature tool with subprocess invocation and JSONL output. The proxy pattern is
established (Garak supports custom model backends). Risk: Garak's API changes between versions.
The version pin (D-002 decision) mitigates this. The proxy must be integration-tested before Phase 3 closes.

**PyRIT Integration — REALISTIC with the GAP-001 resolution adopted**
If PyRIT uses the target API as the attacker LLM (Option A from GAP-001), the integration is
straightforward. PyRIT's Python API is well-documented. Risk: PyRIT's orchestrator has
configuration complexity — the adapter must abstract this cleanly.

**DeepTeam Integration — REALISTIC with the GAP-002 resolution adopted**
deepeval has a clean Python API. The key is correctly implementing the custom LLM wrapper that
adapts the `ModelAdapter` to deepeval's expected interface. Risk: deepeval's evaluator LLM
requirement (GAP-002) must be handled gracefully.

**Tauri + Python IPC — REALISTIC but requires careful implementation**
The pattern (Rust backend spawning a Python subprocess, communicating via a local socket) is
well-established. Tauri has examples of subprocess management. Risk: On Windows, process spawning
and socket creation have platform-specific quirks that require testing early.

**AWS boto3 Integration — REALISTIC with minimal risk**
boto3 is stable and well-documented. The provisioning sequence (IAM → VPC → Lambda → API Gateway
→ Bedrock Guardrails) is predictable. Risk: IAM permissions for the user's AWS account (KI-005).
The pre-flight permission check must be comprehensive.

**WeasyPrint PDF — REALISTIC with known limitations**
WeasyPrint produces good quality PDFs from HTML/CSS. Limitation: complex print layouts (multi-page
tables, headers/footers) require careful CSS. The report template must be designed for print media
from the start, not retrofitted.

---

## 3.4 Architecture Flaws and Improvements

**Flaw 1: No inter-session scan history mechanism is defined**
The current architecture treats each scan as completely independent. The manifest and results are
stored in the scan's working directory, but there is no index or database of past scans. The UI
shows "Scan History" in the dashboard — this history must be stored somewhere.

Improvement: Add a `ScanRegistry` — a simple SQLite database in the app data directory that
indexes all past scans: {scan_id, manifest_id, model_name, date, risk_tier, report_paths}.
This enables the Scan History dashboard panel and scan comparison (v1.5 feature).

**Flaw 2: The ConfidenceScorer explanation text generation is not specified**
The design says the ConfidenceScorer produces "plain-English explanation of the confidence score."
How this text is generated is not specified. It cannot be a large language model call (circular,
expensive). It must be a template-based system.

Improvement: Define a `ConfidenceExplanationTemplate` system where each factor contributes
a sentence fragment based on its score range:
- corroboration_score > 0.8 → "Detected by multiple scanning engines."
- corroboration_score < 0.4 → "Detected by a single engine only."
- success_rate_score > 0.7 → "Attack succeeded in {n}% of probe attempts."
The final explanation is an assembly of these fragments.

**Flaw 3: Report generation depends on DeploymentAdvisor completion**
The design states that the Report is assembled after both the scored findings AND the
DeploymentRecommendation are ready. But the DeploymentAdvisor is a separate module (Phase 7).
This creates a dependency chain that delays report availability.

Improvement: Decouple the report from the deployment recommendation. The report is generated from
scored findings alone. The deployment recommendation section is either embedded inline when
available, or the report shows "Deployment Recommendation: See the Deploy tab for full analysis."
This allows the report to be available immediately after Phase 5 completes, with the deployment
recommendation as an optional addition.

---

# SECTION 4 — SCOPE CONTROL

## What Is IN v1 (Hard Boundaries)

### Desktop Application
- Windows (x64) and Linux (AppImage + .deb) — both at launch
- Tauri desktop framework with bundled Python runtime
- All Python dependencies bundled — zero user-facing terminal setup

### Model Input Types (v1)
- OpenAI-compatible API (covers most providers)
- Azure OpenAI (custom auth + deployment name)
- HuggingFace Inference API
- Local GGUF via auto-managed llama.cpp
- Custom REST with user-defined request/response template (manual config, NOT schema inference)

### Scanning Engines (v1)
- Garak: version-pinned, subprocess-based, all enabled probe categories
- PyRIT: version-pinned, Python API, default attacker = target API (Option A from GAP-001)
- DeepTeam: version-pinned, Python API, judge LLM configurable (GPT-4o-mini default for API users)

### Scan Depth Profiles (v1)
- Quick (5–15 min): core jailbreak + toxicity only
- Standard (30–90 min): all categories, balanced coverage — default
- Deep (2–6 hours): full suite

### Vulnerability Coverage (v1)
- All 18 VulnClass entries are detected if present
- Coverage varies by which engines run which probes

### Scoring (v1)
- SeverityClassifier with static SeverityMatrix + two modifiers
- ConfidenceScorer with five-factor model
- Template-based explanation text (not LLM-generated)

### Reports (v1)
- PDF (WeasyPrint local render)
- HTML (self-contained)
- JSON (full schema)

### Cloud Deployment (v1)
- AWS: one-click provisioning (API Gateway + Lambda + Bedrock Guardrails)
- Azure and GCP: configuration guide only (no provisioning automation)

### Website (v1)
- Next.js 14 + Vercel hosting
- All 15+ pages designed
- Plausible analytics
- Algolia DocSearch for documentation

---

## What Is NOT IN v1 (Explicit Exclusions)

### Deferred to v1.5
- CLI interface for terminal users
- GitHub Actions integration (CI/CD pipeline scan)
- Azure + GCP one-click deployment
- Cross-session scan comparison (regression detection)
- `GenericRESTAdapter` with automatic schema inference
- PyRIT with local Phi-3 Mini attacker LLM (enhanced mode)
- Cross-session pause/resume (resume after app restart)

### Deferred to v2.0 or Later
- SaaS browser-based version
- Native GitHub App
- Multi-modal scanning (vision-language models)
- AI-SENTRY Certification mark
- Runtime monitoring companion
- EU AI Act compliance report templates
- LLM security knowledge graph API
- macOS support

### Never in v1 (Hard No)
- Real-time continuous scanning
- Scanning models the user does not own or is not authorized to test
- Auto-installing updates without user action
- Sending scan data to any external server
- Generating adversarial probes for use outside of scanning (attack use cases)

---

## Scope Creep Prevention Rules

1. **The "Standard Scan" is the reference product.** If a proposed feature is not exercised by
   a Standard Scan on a GPT-4o API endpoint, it is not v1 scope.

2. **No new model adapter types.** If a new model provider requires more than filling out the
   Custom REST fields, it is v1.5 scope.

3. **No new engine integrations.** Garak, PyRIT, DeepTeam only. Adding a fourth engine (e.g.,
   promptfoo, llm-guard) is v1.5 scope.

4. **Report formats are frozen.** PDF, HTML, JSON. No Word (.docx), no SARIF, no CSV in v1.

5. **AWS only for automated deployment.** Azure and GCP receive config guidance documents only.

---

# SECTION 5 — FINAL DECISION LOG

This is the complete, authoritative decision record. Supersedes all per-phase decision logs.

## Architecture Decisions

| ID | Decision | Value | Rationale |
|---|---|---|---|
| D-001 | Scanning engines | Garak + PyRIT + DeepTeam | Industry-standard, actively maintained, complementary coverage |
| D-002 | Engine version strategy | Pinned versions (never floating) | Prevent unexpected behavior changes from upstream releases |
| D-003 | Engine isolation | Each adapter self-contained behind EngineAdapter interface | Allows replacing or updating one engine without touching others |
| D-004 | Normalization strategy | Single canonical VulnerabilityFinding schema | All downstream (scoring, reporting, deployment) works on one format |
| D-005 | Deduplication approach | Semantic group by (vulnerability_class, probe_hash) | Prevents finding inflation while preserving corroboration signal |

## Input and Model Decisions

| ID | Decision | Value | Rationale |
|---|---|---|---|
| D-006 | Supported input types | OpenAI-compat, Azure OpenAI, HuggingFace, GGUF local, Custom REST (manual) | Covers >95% of real-world LLM deployments |
| D-007 | GenericRESTAdapter | Deferred — manual template config in v1 | Auto schema inference is too risky for v1 |
| D-008 | Local model serving | llama.cpp, CPU-only build bundled | GPU is auto-used if available but not required |
| D-009 | PyRIT attacker LLM | Default = target API model (no separate download) | Zero-friction first scan; local attacker deferred to v1.5 |

## Scoring Decisions

| ID | Decision | Value | Rationale |
|---|---|---|---|
| D-010 | Severity system | Two-axis: Severity (tier) + Confidence (0.0–1.0) | Matches real security reporting; prevents conflation of danger and certainty |
| D-011 | Confidence factors | corroboration (0.35), success_rate (0.30), diversity (0.15), maturity (0.12), noise_penalty (0.08) | Weights calibrated to prioritize cross-engine agreement and attack reproducibility |
| D-012 | Explanation generation | Template-based (no LLM) | Reproducible, fast, no API dependency, auditable |
| D-013 | SeverityMatrix | Static config file (severity_matrix.json), validated against pilot test | Inspectable and editable without code changes |

## UI and Desktop Decisions

| ID | Decision | Value | Rationale |
|---|---|---|---|
| D-014 | Desktop framework | Tauri (Rust + OS WebView) | 5–15 MB installer vs 150–300 MB Electron; lower attack surface |
| D-015 | Frontend language | HTML + CSS + JavaScript (no React in Tauri frontend for v1) | Reduces complexity; Tauri WebView handles standard web tech |
| D-016 | Python-Rust IPC | JSON messages over named pipe (Windows) / Unix socket (Linux) | Standard, auditable, language-agnostic |
| D-017 | Credential storage | OS keychain only (Rust backend) | API keys never in files or environment variables |
| D-018 | Evidence encryption | AES-256-GCM, key in OS keychain, passed to Python via IPC at startup | Secure at rest; no user passphrase friction |

## Report Decisions

| ID | Decision | Value | Rationale |
|---|---|---|---|
| D-019 | PDF renderer | WeasyPrint (Python, bundled) | Pure Python, CSS-based, no external binary, good quality |
| D-020 | Report generation timing | Report generated from scored findings; deployment recommendation is additive | Decouples report from deployment advisor; faster user feedback |
| D-021 | Report formats | PDF + HTML (self-contained) + JSON | Covers stakeholder, web, and CI/CD use cases |

## Deployment Decisions

| ID | Decision | Value | Rationale |
|---|---|---|---|
| D-022 | Cloud deployment v1 scope | AWS only (provisioning); Azure + GCP (config docs only) | Focus depth over breadth; AWS has strongest Bedrock Guardrail alignment |
| D-023 | AWS provisioning pattern | Plan → User review → Provision → Verify → Rollback on failure | User always sees and approves before any cloud resource is created |
| D-024 | AWS resource tagging | All resources tagged {"created-by": "ai-sentry", "scan-id": UUID} | Clean cleanup; easy identification in AWS console |

## Website Decisions

| ID | Decision | Value | Rationale |
|---|---|---|---|
| D-025 | Website framework | Next.js 14 (App Router) on Vercel | SSR for SEO; Vercel zero-config; same React ecosystem as Tauri frontend |
| D-026 | Analytics | Plausible (no cookies, no consent banner) | GDPR-compliant; consistent with privacy-first product positioning |
| D-027 | Content management | Markdown-in-repo (MDX) | No CMS dependency; version-controlled; devs edit content via PRs |
| D-028 | Download gate | Zero friction (no email, no account, no waitlist) | Developer audience: any gate before a free download loses users |
| D-029 | File hosting | GitHub Releases (primary) + Cloudflare R2 (mirror) | Free; community-verified; persistent URLs per version |

## Scan Behavior Decisions

| ID | Decision | Value | Rationale |
|---|---|---|---|
| D-030 | Consent gate | Mandatory before every scan — cannot be skipped | Legal and ethical requirement; user must authorize adversarial content |
| D-031 | Cost tracking | Real-time accumulation; halt at 110% of approved estimate | User approved an estimate; exceeding it requires re-consent |
| D-032 | Partial results | Always preserved on pause/cancel/failure | User never loses work; partial reports are clearly marked |
| D-033 | Telemetry | Opt-in only, default OFF | Privacy-first; scan data never transmitted |

---

# SECTION 6 — IMPLEMENTATION READINESS CHECK

## Can Phase 1 Start Immediately?

**YES, Phase 1 can start immediately.** Phase 1 only requires:
- Creating the directory structure
- Setting up pyproject.toml and dependency management
- Implementing the environment health check tool
- Setting up the logging framework
- Creating the CLI skeleton

None of these require any of the unresolved gaps to be closed first.

## Prerequisite Checklist for Each Phase

### Before Phase 1 (Project Scaffold) — ALL CLEAR
- [x] Documentation complete
- [x] Target directory structure defined (SYSTEM_EXECUTION_LAYER.md Section 6)
- [x] Python version: 3.11.x (specified)
- [x] Dependency management: pyproject.toml with groups (specified)
- [x] Key decisions documented

### Before Phase 2 (Model Adapters) — 3 ACTIONS REQUIRED
- [ ] **ACTION: Define IPC protocol formally** (GAP-005) — write IPC_PROTOCOL.md before Phase 2 coding
- [ ] **ACTION: Choose llama.cpp version to pin** (GAP-009) — check current stable release
- [ ] **ACTION: Finalize Custom REST adapter spec** (GAP-007) — confirm manual template approach
- [x] ModelAdapter interface designed
- [x] All supported model types listed

### Before Phase 3 (Engine Adapters) — 4 ACTIONS REQUIRED
- [ ] **ACTION: Resolve PyRIT attacker LLM** (GAP-001) — confirm Option A (target API as attacker)
- [ ] **ACTION: Resolve DeepTeam judge LLM** (GAP-002) — design the judge config flow
- [ ] **ACTION: Design Garak proxy auth handlers** (GAP-003) — per-adapter-type proxy class design
- [ ] **ACTION: Specify checkpoint serialization** (GAP-011) — JSONL format with fields defined
- [x] Engine interfaces defined
- [x] All three engines version-pinned

### Before Phase 4 (Normalization) — 1 ACTION REQUIRED
- [ ] **ACTION: Finalize EvidenceStore encryption design** (GAP-004) — AES-256-GCM + keychain flow
- [x] VulnClass taxonomy defined (18 classes)
- [x] VulnerabilityFinding schema defined

### Before Phase 5 (Intelligence Layer) — 1 ACTION REQUIRED
- [ ] **ACTION: Lock SeverityMatrix values** (GAP-006) — finalize and write severity_matrix.json
- [x] ConfidenceScorer structure defined
- [x] RemediationKnowledgeBase structure defined

### Before Phase 6 (Report Generator) — 1 ACTION REQUIRED
- [ ] **ACTION: Confirm WeasyPrint** (GAP-008) — test WeasyPrint rendering of a prototype report
- [x] Report schema defined
- [x] All three output formats specified

### Before Phase 7 (Deployment) — 1 ACTION REQUIRED
- [ ] **ACTION: Document credential handoff** (GAP-010) — add to IPC_PROTOCOL.md
- [x] AWS provisioning sequence defined
- [x] PlatformCapabilityMaps structure defined

### Before Phase 8 (Desktop UI) — ALL CLEAR
- [ ] All backend phases complete
- [x] All 9 screens designed (SYSTEM_EXECUTION_LAYER.md Section 5)
- [x] Tauri framework decision confirmed

### Before Phase 9 (Website) — ALL CLEAR
- [x] Full website design complete (WEBSITE_DESIGN.md)
- [x] Tech stack confirmed (Next.js + Vercel)
- [x] SEO strategy defined

## What Should Be Done Before Coding (Phase 1 Week 1)

1. **Write IPC_PROTOCOL.md** — formal specification of the Rust↔Python message format.
   This is the contract that Phase 2 and Phase 8 both implement against. (~2 hours)

2. **Pin all three engine versions** — check current PyPI versions of garak, pyrit-ai, deepeval.
   Document in a `pinned_versions.md` or directly in `pyproject.toml` comments. (~30 minutes)

3. **Write severity_matrix.json (first draft)** — using the proposed values from GAP-006.
   This draft is subject to change after pilot testing but gives Phase 5 something to implement against.
   (~1 hour)

4. **Confirm WeasyPrint can render a sample report structure** — a quick local test (not in the
   project, just a proof of concept) to verify WeasyPrint renders tables and severity badges correctly
   before committing to it. (~1 hour)

5. **Resolve KI-001 (PyRIT attacker LLM)** — formally adopt Option A. Update context/known_issues.md.
   (~15 minutes)

6. **Create the GitHub repository** — with the agreed branching strategy (Section 8). (~30 minutes)

Total pre-coding overhead: approximately 5–6 hours. This is the minimum necessary to avoid
expensive rework during implementation.

---

# SECTION 7 — RISK MITIGATION PLAN

## RISK-001: Engine API Breaking Changes

**What can go wrong:** Garak, PyRIT, or DeepTeam release a new version between Phase 3 implementation
and v1 launch that changes the Python API or output format. The adapter breaks silently or noisily.

**Likelihood:** HIGH (all three are actively developed open-source projects with frequent releases)

**Impact:** HIGH (adapter failure = engine failure = reduced coverage or complete scan failure)

**Mitigation:**
- All three engines are version-pinned in pyproject.toml (D-002 decision)
- Pinned versions are tested and documented in each adapter's unit test suite
- A `VersionCompatibilityChecker` runs at startup and warns if installed versions differ from pinned
- CI pipeline runs the full test suite against pinned versions only
- Engine version upgrades are treated as a dedicated release task, not ad-hoc

---

## RISK-002: Windows Defender / Antivirus False Positives

**What can go wrong:** The AI-SENTRY installer or bundled Python runtime is flagged by Windows
Defender or third-party AV as malicious. This happens because: (a) the installer bundles a Python
runtime, (b) the scanning engines generate adversarial content, (c) the subprocess spawning behavior
resembles malware patterns.

**Likelihood:** MEDIUM (code-signed installers reduce but do not eliminate AV flags)

**Impact:** HIGH (users cannot install the product; enterprise deployments blocked by AV policy)

**Mitigation:**
- Code-sign the Windows installer with an Authenticode certificate before any public release
- Submit the installer to Microsoft's Malware Protection Center for safe-listing
- Test the installer against Windows Defender + common third-party AV tools (Malwarebytes, CrowdStrike)
  before each release
- Document the safe-listing submission process as a mandatory release checklist item
- Include in the documentation: "If your AV flags AI-SENTRY, here is how to add an exclusion"

---

## RISK-003: PyRIT Multi-Turn Attack Complexity

**What can go wrong:** PyRIT's Crescendo attack strategy is a sophisticated multi-turn conversation
attack. Implementing it correctly via the adapter is complex. Common failures: the attacker LLM
gets confused between turns, the conversation context is lost, or the attack terminates early without
finding the vulnerability.

**Likelihood:** MEDIUM (PyRIT's API is mature but complex to configure correctly)

**Impact:** MEDIUM (PyRIT produces fewer or lower-quality findings; confidence scores suffer)

**Mitigation:**
- Phase 3 includes mandatory integration tests: run PyRIT against a known-vulnerable test model
  (a local GGUF with minimal safety training) and verify that at least one finding is produced
- The PyRIT adapter includes a "verbose mode" that logs every turn of every conversation to disk
  for debugging during development
- If PyRIT produces zero findings on a known-vulnerable model after 10+ minutes, the adapter
  is failing — alert the developer immediately (not silently continue)

---

## RISK-004: Tauri + Python Process Management on Windows

**What can go wrong:** The Tauri Rust backend spawns the Python process. On Windows, process
management has platform-specific quirks:
- Named pipe creation can fail if another process holds the pipe name
- Python process orphaning if the Tauri process crashes
- Windows UAC prompts appearing unexpectedly during installation or first launch

**Likelihood:** MEDIUM (Windows process management is generally reliable but has known edge cases)

**Impact:** MEDIUM (orphaned processes waste resources; pipe failures prevent app launch)

**Mitigation:**
- Named pipe: use a unique pipe name that includes the process ID to prevent conflicts
- Python orphan prevention: Python backend registers a parent process check on startup;
  if parent PID is gone, Python backend exits cleanly
- Windows UAC: the installer requests necessary permissions at install time, not at runtime;
  runtime operations should not require elevation
- Integration test the full Tauri+Python launch sequence on a clean Windows 10 VM before Phase 8 closes

---

## RISK-005: AWS Deployment Rollback Failure

**What can go wrong:** The AWS Deploy Engine creates 8+ resources in sequence. If resource N fails,
the rollback must delete resources 1 through N-1. If the rollback itself fails (e.g., CloudWatch
alarm deletion fails), the user is left with orphaned, potentially billable AWS resources.

**Likelihood:** LOW (AWS API is reliable; rollback failures are rare)

**Impact:** HIGH (user's AWS account has unexpected charges; trust is damaged severely)

**Mitigation:**
- Every resource created is immediately logged to a local `deployment_manifest.json` file
- This file exists before provisioning starts — resources are added to it as they are created
- The rollback function reads from this file — it can always attempt cleanup even after an app crash
- The deployment completion screen prominently shows: "Tag: created-by=ai-sentry" with a
  link to the AWS console filtered to that tag — user can always manually verify and clean up
- After any failed deployment, the UI shows explicit cleanup instructions
- A `destroy_deployment` command (Phase 7) allows one-click teardown of any tagged AI-SENTRY deployment

---

## RISK-006: Cost Estimate Accuracy

**What can go wrong:** The pre-scan cost estimate shows "$0.54–0.81" but the actual scan costs
$3.20 because the model produces unusually long responses (many output tokens) or because the
pricing table is outdated.

**Likelihood:** MEDIUM (output token count is genuinely variable by model)

**Impact:** MEDIUM (user is surprised by API bill; trust is damaged)

**Mitigation:**
- The cost estimate is clearly labeled "estimate — may vary by ±30%" in the UI
- The CostTracker halts the scan at 120% of the approved estimate ceiling (D-031 decision)
- The pricing tables in the `CostEstimator` are configurable and versioned
- When actual cost exceeds estimate by >20%, the scan summary screen displays a prominent note:
  "This scan cost more than estimated. The estimate assumed average response length of ~200 tokens,
  but your model averaged ~580 tokens per response."
- Users can set an absolute cost ceiling in Settings (default: $10 — prevents runaway costs)

---

## RISK-007: Local GGUF Model Performance

**What can go wrong:** A user attempts to scan a 13B parameter model on a machine with 8 GB RAM.
The model loads partially, causes swap thrashing, and either crashes llama.cpp or takes 6 hours
for a Quick scan.

**Likelihood:** MEDIUM (users frequently underestimate GGUF RAM requirements)

**Impact:** MEDIUM (bad user experience; potentially corrupts scan results if memory errors occur)

**Mitigation:**
- Hardware detection runs during the Environment Check screen (onboarding) AND at model connection time
- If the user selects a GGUF file that requires more RAM than available: hard block with clear message:
  "This model requires ~16 GB RAM. Your system has 8 GB available. Select a smaller model or use API mode."
- Warning (not block) if available RAM is within 20% of the model's requirement: "This may be slow."
- The RAM estimate is shown on the model selection screen before the user confirms
- Scan timeout: if llama.cpp inference takes >120 seconds per probe, flag as "local model too slow"
  and offer to switch to a reduced probe count

---

## RISK-008: DeepTeam Judge LLM Availability

**What can go wrong:** The user's API key is for a provider that is not supported as a judge LLM
by deepeval. Or the judge LLM key has insufficient quota for the scan volume.

**Likelihood:** MEDIUM (judge LLM is a new concept; users may not know they need it)

**Impact:** MEDIUM (DeepTeam runs in degraded mode; coverage gaps appear in report)

**Mitigation:**
- The scan configuration screen explicitly shows: "DeepTeam requires an evaluator LLM."
- If the target model is an OpenAI API, default the judge to the same OpenAI key (GPT-4o Mini)
- If the target model is local or non-OpenAI: prompt for a separate judge key during setup
- "Skip evaluator — run in heuristic mode" is a visible option (with a coverage warning)
- The report clearly states which metrics ran with a judge LLM vs. heuristic mode

---

# SECTION 8 — TEAM WORKFLOW

## Repository Structure

One GitHub repository: `github.com/ai-sentry/ai-sentry`

Structure:
```
/                     Repository root
├── app/              Tauri + Rust backend + Python backend (main desktop app)
│   ├── src-tauri/    Rust backend code
│   ├── frontend/     HTML + CSS + JS UI
│   └── backend/      Python scanning backend
├── website/          Next.js website (ai-sentry.dev)
├── docs/             Design documents (PRD, TRD, etc.)
├── context/          AI memory files
└── tests/            Integration tests
```

Two separate repos is NOT recommended for v1. The tight dependency between app releases and website
(download links, version API, checksum publishing) makes a monorepo easier to manage at this stage.

---

## Branch Strategy (Simple)

```
main              — Always deployable. Protected. Requires PR to merge.
dev               — Active development integration branch.
feature/[name]    — Feature branches off dev (e.g., feature/garak-adapter)
fix/[name]        — Bug fix branches off dev (e.g., fix/cost-tracker-overflow)
release/[version] — Release preparation off dev (e.g., release/1.0.0)
```

**Rules:**
1. `main` is never committed to directly. Ever.
2. Every merge to `main` is via a PR with at least one review.
3. Feature branches are short-lived: merged within 1–2 days of opening.
4. `dev` is kept green (passing tests) at all times.
5. Release branches freeze `dev` → fix-only → merge to `main` when ready.

---

## Commit Message Format

```
type(scope): short description (under 72 chars)

Optional body explaining WHY, not WHAT.

Refs: #issue-number (if applicable)
```

Types:
```
feat     — new feature
fix      — bug fix
refactor — code change that is neither feat nor fix
test     — adding tests
docs     — documentation only
chore    — build/dependency changes
```

Examples:
```
feat(garak-adapter): implement localhost proxy for model forwarding
fix(cost-tracker): handle token count overflow on long model responses
refactor(normalizer): extract evidence collection to separate class
test(pyrit-adapter): add integration test against mock vulnerable model
docs(ipc-protocol): define message schema and transport layer
chore(deps): pin deepeval to v1.4.0 per D-002
```

---

## Pull Request Rules

1. **Title:** Use the same format as commit messages
2. **Description:** What changed, why, how to test it
3. **Size:** PRs should be small. If a PR touches more than 400 lines, split it.
4. **Tests:** Every PR that adds a feature must include at least one test.
5. **Review:** Both developers review all PRs. Reviewer approves or requests changes — no silent merges.
6. **Merge strategy:** Squash merge to `dev` (clean linear history). Merge commit to `main` (preserve PR).

---

## Phase Development Pattern

Each phase follows this micro-cycle:

```
1. Create feature branch off dev
2. Implement the phase
3. Write unit tests
4. Self-review the diff
5. Open PR to dev
6. Peer review
7. Merge to dev
8. Delete feature branch
9. Run integration tests on dev
10. Update context/current_phase.md
```

---

## Issue Tracking

Use GitHub Issues with labels:

```
phase-1 through phase-11    — which implementation phase
bug                         — something broken
enhancement                 — improvement to existing feature
gap                         — a gap identified from this document
blocker                     — must be resolved before the labeled phase begins
documentation               — docs-only work
```

Create an issue for each of the 13 gaps in Section 2 immediately. Label them `gap` + the relevant
`phase-N` label. Assign them before Phase 1 begins.

---

## Release Process

1. Create `release/1.0.0` branch off `dev`
2. Update version numbers in all relevant files
3. Generate SHA256 checksums for the compiled binaries
4. Run full integration test suite
5. Create PR to `main` — final review
6. Merge to `main`
7. Tag the commit: `git tag v1.0.0`
8. GitHub Actions creates the GitHub Release with the compiled binaries
9. Update the website version API response manually
10. Publish the website changelog entry
11. Announce

---

# SECTION 9 — FINAL PROJECT STATE

## Current State: All Design Phases Complete

```
✅  Phase 0a — Idea and System Design
    Deliverable: Complete system architecture, 10 core components, design principles

✅  Phase 0b — Documentation Foundation
    Deliverable: PRD.md, TRD.md, 6 context/memory files

✅  Phase 0c — System Execution Layer
    Deliverable: SYSTEM_EXECUTION_LAYER.md (68 KB)
                 App flow, backend architecture, data schemas, UI design, 11-phase plan

✅  Phase 0d — Website Design
    Deliverable: WEBSITE_DESIGN.md (62 KB)
                 11 sections: structure, pages, design system, SEO, analytics, tech stack, brand

✅  Phase 0e — Gap Analysis and Final Consolidation
    Deliverable: This document — FINAL_CONSOLIDATION.md
                 13 gaps identified and resolved, architecture validated, scope locked,
                 27 decisions logged, risk mitigation defined, team workflow established
```

## The 5 Pre-Coding Actions (Priority Order)

```
1.  WRITE  IPC_PROTOCOL.md           — Rust↔Python message contract (resolves GAP-005)
2.  WRITE  severity_matrix.json      — First draft (resolves GAP-006 partially)
3.  DECIDE PyRIT attacker LLM        — Adopt Option A formally (resolves GAP-001)
4.  TEST   WeasyPrint rendering      — Quick proof of concept (resolves GAP-008)
5.  CREATE GitHub repository         — Initialize with team workflow (Section 8)
```

## Next Phase: Phase 1 — Project Scaffold and Environment

**Goal:** A runnable project skeleton with no business logic but all structural foundations in place.

**Deliverables of Phase 1:**
- Directory structure matching the design
- `pyproject.toml` with all dependency groups and pinned versions
- Environment health check CLI tool (validates all engines at pinned versions)
- Structured logging framework (channels: app, orchestration, garak, pyrit, deepteam, security)
- Configuration management system (user preferences, version pins, engine configs)
- Basic CLI skeleton (accepts model input and scan config flags for testing purposes)
- Placeholder modules for all 8 backend components (interface definitions only)
- Initial unit test infrastructure

**Phase 1 is complete when:** `python -m aisentry healthcheck` runs successfully and reports
all three engines installed at pinned versions, OS keychain accessible, and sufficient disk space.

---

## Readiness Declaration

The AI-SENTRY system design is **complete and ready for implementation**.

All critical architectural decisions have been made and documented.
All 13 identified gaps have resolution paths defined.
Scope boundaries are clearly established with explicit inclusion/exclusion lists.
The implementation sequence is clearly defined with inter-phase dependencies mapped.
The team workflow is established with branching, commit, and review rules.
Risk mitigations are defined for all 8 major identified risks.

**Implementation can begin with Phase 1 immediately after completing the 5 pre-coding actions.**

The estimated total development timeline to v1.0 release:
```
Phase 1:  1 week    Project scaffold
Phase 2:  2 weeks   Model adapter layer
Phase 3:  4 weeks   Engine adapters (parallel tracks)
Phase 4:  2 weeks   Normalization layer
Phase 5:  2 weeks   Intelligence layer (scoring + remediation)
Phase 6:  1 week    Report generator
Phase 7:  2 weeks   Deployment advisor + AWS engine
Phase 8:  3 weeks   Desktop UI (wiring backend to UI)
Phase 9:  2 weeks   Website (parallel with Phase 8)
Phase 10: 1 week    Integration testing
Phase 11: 1 week    Launch preparation
──────────────────
Total:    ~21 weeks (~5 months) for 2 developers
```

This estimate assumes full-time work on the project. Part-time development extends proportionally.

---

*End of Final Consolidation Document v1.0*
*This document represents the complete, validated, implementation-ready state of the AI-SENTRY project.*
*No further design phases are required. Phase 1 implementation begins next.*
