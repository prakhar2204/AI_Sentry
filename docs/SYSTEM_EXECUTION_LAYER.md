# AI-SENTRY — System Execution Layer
## Complete App Flow, Backend Design & Implementation Plan

**Document Version:** 1.0  
**Phase:** 0c — System Execution Design  
**Status:** Active — Design Only, No Implementation  
**Last Updated:** 2026-09-13  
**Depends On:** PRD v1.0, TRD v1.0, context/decisions.md

---

## Table of Contents

1. [Section 1 — User Flow](#section-1--user-flow)
2. [Section 2 — Application Flow](#section-2--application-flow)
3. [Section 3 — Backend Architecture](#section-3--backend-architecture)
4. [Section 4 — Data Schemas](#section-4--data-schemas)
5. [Section 5 — UI/UX Design](#section-5--uiux-design)
6. [Section 6 — Implementation Plan](#section-6--implementation-plan)
7. [Section 7 — Desktop App Strategy](#section-7--desktop-app-strategy)
8. [Section 8 — Website Integration](#section-8--website-integration)

---

# SECTION 1 — USER FLOW

## The Complete User Experience, Step by Step

---

## 1.1 First-Time Experience

### Step 1.1.1 — Download

User visits the AI-SENTRY website. They see the download page:
- Windows (.exe installer)
- Linux (.AppImage or .deb)

Each download shows: file size, SHA256 checksum, version number, release date. User clicks download. Nothing else happens server-side.

---

### Step 1.1.2 — Installation (Windows)

User runs the .exe installer. A visual progress bar runs through:

```
[1/6] Checking system requirements...
      OS version ✓ | Available RAM ✓ | Disk space ✓

[2/6] Installing AI-SENTRY application...

[3/6] Setting up bundled Python runtime...

[4/6] Installing scanning engine dependencies...
      Garak (v0.x.x) ✓ | PyRIT (v0.x.x) ✓ | DeepTeam ✓

[5/6] Configuring local environment...

[6/6] Creating application shortcuts...

Installation complete.  [Launch Now]  [Close]
```

The user does **not** open a terminal. They do **not** pip install anything. Everything is bundled and self-contained.

**If a step fails:** The installer shows a specific failure message and offers to retry or skip (with warning). The app launches with the failing engine marked "Unavailable."

---

### Step 1.1.3 — First Launch & Onboarding

The application opens to a full-screen onboarding sequence:

**Screen 1/4 — Welcome**
```
AI-SENTRY
LLM Security Orchestration Platform

Before you ship your AI — know what it's capable of doing wrong.

                                         [Get Started →]
```

**Screen 2/4 — How It Works**
```
Three steps to a safer LLM deployment:

  [1] Connect your model      API endpoint or local file
  [2] Scan with three engines  Garak · PyRIT · DeepTeam
  [3] Deploy with confidence   Unified report + cloud deployment

                                              [Next →]
```

**Screen 3/4 — What You Should Know**
```
⚠  Important Before You Begin

AI-SENTRY sends adversarial content to your model during scanning.
This includes jailbreak attempts, harmful prompts, and manipulative text.
This is intentional — it is how we find vulnerabilities.

You must:
  • Own or have authorization to test the model you connect
  • Accept that API-based scans cost money (we estimate first)
  • Understand that results are probabilistic, not absolute

                              [I Understand — Continue →]
```

**Screen 4/4 — Environment Check**
```
Checking your environment...

  ✓  Python runtime: 3.11.x
  ✓  Garak: v0.x.x (ready)
  ✓  PyRIT: v0.x.x (ready)
  ✓  DeepTeam: v0.x.x (ready)
  ✓  System keychain: accessible
  ⚠  GPU: Not detected — local models limited to ≤7B parameters

Your system is ready for API-based and small local model scanning.

                                        [Enter AI-SENTRY →]
```

User lands on the main dashboard for the first time.

---

## 1.2 Input Stage

### Step 1.2.1 — Model Selection

User sees three clearly separated options on the "Connect Your Model" screen:

**Option A — API Endpoint**
```
Provider:    [OpenAI ▼]  [Azure OpenAI]  [HuggingFace]  [Custom]
API Key:     [•••••••••••••••••] [Show] [Paste from clipboard]
Endpoint:    [https://api.openai.com/v1]  (auto-filled for known providers)
Model Name:  [gpt-4o ▼]

                                            [Test Connection]
```

**Option B — Local Model**
```
Model File:  [Browse...]  or  [Drag & Drop .gguf file here]

Detected:    mistral-7b-instruct-v0.2.Q4_K_M.gguf
Size:        4.1 GB
Needs RAM:   ~6 GB
Your RAM:    16 GB  ✓

                                              [Verify File]
```

**Option C — HuggingFace Hosted**
```
Model ID:    [meta-llama/Llama-2-7b-chat-hf]
HF Token:    [•••••••••••••••••] [Show]

                                           [Load Model Info]
```

---

### Step 1.2.2 — Connection Validation

After clicking validate, the user sees a live sequence:

```
Validating connection...

  → Checking endpoint reachability...    ✓  (142ms)
  → Authenticating credentials...        ✓
  → Sending test prompt...               ✓  (891ms)
  → Parsing response format...           ✓
  → Estimating token encoding...         ✓

Connection successful.
Average response latency: 891ms

                                 [Continue to Scan Setup →]
```

**On failure:**
```
Connection failed.
Issue: API key rejected (HTTP 401)

Suggestions:
  • Verify your API key is correct and not expired
  • Confirm billing is active for this API

                          [Try Again]  [Use Different Model]
```

---

## 1.3 Manifest Stage

### Three Paths Available:

**Path A — Upload Existing Manifest**
```
Upload Manifest:  [Browse...]  (.json from a previous AI-SENTRY scan)

Loaded: customer_service_bot_scan.json
Created: 2026-08-15 | Engines: Garak + PyRIT | Depth: Standard

             [Review & Run]  [Modify This Manifest]  [Start Fresh]
```

**Path B — Presets**
```
Choose a scan profile:

  ○  Quick Check     5–15 min   Core jailbreak + toxicity probes only
  ●  Standard Scan   30–90 min  Balanced coverage — all categories   ← Recommended
  ○  Deep Audit      2–6 hours  Full suite — enterprise compliance
```

**Path C — Custom Configuration**
```
Probe Categories:
  ☑ Jailbreak Attempts       ☑ Toxicity Generation
  ☑ PII / Data Leakage       ☑ System Prompt Extraction
  ☑ Hallucination            ☑ Bias Detection
  ☐ Copyright Reproduction   ☐ Excessive Agency

Engines:
  ☑ Garak    ☑ PyRIT    ☑ DeepTeam

Deployment Context (optional — improves remediation specificity):
  [Customer Service ▼]
```

---

## 1.4 Pre-Scan Estimation

A mandatory gate before any scan runs:

```
───────────────────────────────────────────────────────────
  SCAN SUMMARY — REVIEW BEFORE STARTING
───────────────────────────────────────────────────────────

  Model:       gpt-4o (OpenAI API)
  Depth:       Standard
  Engines:     Garak · PyRIT · DeepTeam
  Categories:  8 of 10 selected

  ── Estimates ─────────────────────────────────────────────
  Probe Count:    ~420 prompts
  API Tokens:     ~180,000 (estimated)
  API Cost:       ~$0.54 – $0.81 USD

  Duration:       ~35–50 minutes

  ── Adversarial Content Warning ───────────────────────────
  This scan sends: jailbreak attempts, requests for harmful
  content, social engineering patterns, toxic text.
  This is intentional and necessary.

  ── Authorization ─────────────────────────────────────────
  ☐  I own or have explicit authorization to test this model.
  ☐  I understand API cost estimates may vary by ±20%.
  ☐  I accept the AI-SENTRY Terms of Service.

───────────────────────────────────────────────────────────

  [← Back]                              [Begin Scan →]
                      (disabled until all boxes checked)
```

---

## 1.5 Scan Execution

```
AI-SENTRY — Scan in Progress
───────────────────────────────────────────────────────────
  Model: gpt-4o    Started: 10:32:14    Elapsed: 00:08:22
  Depth: Standard  Est. remaining: ~28 min

  ── Engine Status ─────────────────────────────────────────
  GARAK     ████████████░░░░░░░░  62%  Running
            Current: jailbreak.Dan.Dan11
            Findings so far: 3

  PYRIT     ██████░░░░░░░░░░░░░░  31%  Running
            Current: Crescendo attack (turn 4/8)
            Findings so far: 1

  DEEPTEAM  ████████████████████ 100%  Complete ✓
            Findings: 5

  ── Live Findings (preliminary — not yet scored) ──────────
  🔴 HIGH    Jailbreak via DAN11 prompt          [Garak]
  🔴 HIGH    Gender bias in advice context       [DeepTeam]
  🟡 MEDIUM  Citation hallucination              [DeepTeam]
  🟡 MEDIUM  Conditional hate speech             [DeepTeam]
  🟡 MEDIUM  Political framing detected          [DeepTeam]
  🟢 LOW     System prompt partial extraction    [PyRIT]

  ── API Usage ─────────────────────────────────────────────
  Tokens used: 68,421 / ~180,000 est.
  Cost so far: $0.21 / ~$0.54–0.81 est.

                                      [Pause]  [Cancel Scan]
```

**Pause:** Halts after current probe. Checkpoints manifest to disk. Resumable.  
**Cancel:** Confirmation dialog → partial results preserved → partial report available.

---

## 1.6 Results Dashboard

Scan completes. Normalization and scoring run (seconds). User sees:

**Summary Bar**
```
  Risk Tier: ● HIGH    |  gpt-4o (OpenAI)  |  Standard scan
  CRITICAL: 0   HIGH: 3   MEDIUM: 4   LOW: 2   INFO: 1
  Duration: 42 min 18 sec   |   API Cost: $0.67
```

**OWASP Coverage Map**
```
  LLM01: Prompt Injection       ████ TESTED  — 1 finding (High)
  LLM02: Insecure Output        ████ TESTED  — 0 findings
  LLM03: Training Data Poison   ░░░░ NOT TESTED (requires model internals)
  LLM06: Sensitive Info         ████ TESTED  — 1 finding (Medium)
  LLM09: Overreliance           ████ TESTED  — 1 finding (Medium)
  ...
```

**Finding Cards (sorted by severity)**
```
  ┌─────────────────────────────────────────────────────┐
  │  🔴 HIGH  ·  Confidence: 0.88                        │
  │  Jailbreak via DAN-Style Prompt                      │
  │                                                      │
  │  Detected by: Garak, PyRIT    Success rate: 78%      │
  │  OWASP: LLM01 — Prompt Injection                     │
  │                                                      │
  │  The model reliably abandons system instructions     │
  │  under DAN-style role framing. 78% of 18 probe       │
  │  variants succeeded.                                 │
  │                                                      │
  │  [View Evidence]  [See Remediation]  [Export]        │
  └─────────────────────────────────────────────────────┘
```

**"View Evidence" expands:**
- Probe payload (behind "Show adversarial content" click-through)
- Exact model response
- Probe variant success breakdown

**"See Remediation" expands:**
- Model-level: fine-tuning recommendations
- System-level: prompt hardening, output filters
- Deployment-level: guardrails, access controls

---

## 1.7 Report View and Download

```
  AI-SENTRY Security Assessment
  Model: gpt-4o  ·  Scan: Standard  ·  Date: 2026-09-13

  Contents:
    1. Executive Summary
    2. Vulnerability Catalog (10 findings)
    3. Confidence Analysis
    4. OWASP Coverage Map
    5. Remediation Roadmap
    6. Deployment Recommendation
    7. Appendix: Raw Engine Outputs

  [Preview Report]  [Download PDF]  [Download HTML]  [Download JSON]

  ⚠ Reports contain adversarial probe content in the Appendix.
    Share only with authorized parties.
```

PDF generation runs locally — no server, no internet required.

---

## 1.8 Deployment Flow (AWS v1)

**Step 1 — Platform Selection**
```
  Deployment Advisor:  Based on 3 High + 4 Medium findings:

  ┌──────────────┬──────────┬──────────┬──────────┐
  │              │  AWS ★   │  Azure   │  GCP     │
  ├──────────────┼──────────┼──────────┼──────────┤
  │ Security fit │ High     │ High     │ Medium   │
  │ Controls     │ Bedrock  │ Content  │ Vertex   │
  │              │ Guardrls │ Safety   │ AI       │
  │ Est. $/month │ $142     │ $158     │ $131     │
  └──────────────┴──────────┴──────────┴──────────┘

  AWS recommended: Bedrock Guardrails directly mitigates
  your top 3 findings.

          [Deploy to AWS →]    [Get Azure Config]    [Get GCP Config]
```

**Step 2 — AWS Credentials & Config**
```
  AWS Access Key:    [AKIA...] [Load from keychain] [Enter new]
  AWS Secret Key:    [••••••••••]
  Region:            [us-east-1 ▼]

  Deployment Type:
  ●  API Gateway + Lambda (proxy)   ← Recommended
  ○  SageMaker Endpoint (host model directly)

  Expected requests/month: [100,000]
  Updated estimate: $89/month

                                  [Generate Infrastructure Plan →]
```

**Step 3 — Infrastructure Plan Review**
```
  ─── INFRASTRUCTURE PLAN ─── Nothing created yet ───────────

  IAM Role: ai-sentry-llm-role (least privilege)
  VPC: 10.0.0.0/16  +  2 private subnets
  Security Group: 443 outbound only
  API Gateway: ai-sentry-llm-gateway (REST)
  Lambda: ai-sentry-llm-proxy (512MB, 30s timeout)
  Bedrock Guardrails:
    Jailbreak [High]  →  Content filter: BLOCK
    Toxicity [Medium] →  Content filter: BLOCK
    PII [Medium]      →  Sensitive info: MASK
  CloudWatch: Error alarms + latency alarms
  Budget Alert: at $120/month

  All resources tagged: { "created-by": "ai-sentry" }
  Estimated cost: $89/month at 100K requests

  ───────────────────────────────────────────────────────────
  ☐  I have reviewed this plan and authorize AI-SENTRY to
     create these resources in my AWS account.

  [← Back]   [Download Plan as JSON]   [Deploy ✓]
```

**Step 4 — Live Provisioning**
```
  [████████████████████░░░░] 78%  Configuring Bedrock Guardrails...

  ✓  IAM Role created            (2.1s)
  ✓  VPC + Subnets               (5.3s)
  ✓  Security Group              (1.2s)
  ✓  Lambda deployed             (8.7s)
  ✓  API Gateway configured      (4.1s)
  ◌  Bedrock Guardrails...       (in progress)
  ○  CloudWatch alarms
  ○  Budget alert
```

**Step 5 — Deployment Complete**
```
  Deployment Complete ✓

  Endpoint: https://abc123.execute-api.us-east-1.amazonaws.com/prod/chat
  Resources: 12 created  |  Region: us-east-1

  Active security controls:
  ✓  Bedrock Guardrails (jailbreak, toxicity, PII)
  ✓  VPC network isolation
  ✓  CloudWatch monitoring
  ✓  Budget alerts at $120/month

  [Copy Endpoint]  [View in AWS Console]  [Download Deployment Report]
```

---

# SECTION 2 — APPLICATION FLOW

## Internal System Flow (System-Level, Not UI-Level)

---

## 2.1 Input Reception

```
USER_INPUT → ModelConfig {type, credentials, endpoint_url, model_name}
     │
     ▼
InputHandler.receive(ModelConfig)
     ├─ Validate schema completeness
     ├─ Detect model_type → select ModelAdapter subclass
     ├─ ModelAdapter.validate() → ConnectionStatus
     ├─ If LOCAL_GGUF: spawn llama.cpp server → health check
     ├─ ModelAdapter.estimate_cost(probe_count) → CostEstimate
     └─ Return: ValidatedModelContext
```

---

## 2.2 Manifest Processing

```
USER_INPUT → ScanConfig {depth, categories, deployment_context, engines}
     │
     ▼
ManifestProcessor.build(ValidatedModelContext, ScanConfig)
     ├─ Generate manifest_id (UUID v4)
     ├─ Resolve probe_categories from depth OR explicit list
     ├─ Build engine_configs per engine from probe_categories
     ├─ Calculate probe_count and cost_estimate per engine
     ├─ Persist ScanManifest {status: CONSENT_PENDING} to disk
     └─ Return: ScanManifest

USER confirms consent
     │
     ▼
ManifestProcessor.approve(ScanManifest, ConsentRecord)
     ├─ Append ConsentRecord (with timestamp + approved cost_estimate)
     ├─ Update manifest status: APPROVED
     ├─ Re-persist manifest to disk
     └─ Emit: manifest_approved → EngineOrchestrator
```

---

## 2.3 Engine Orchestration

```
EngineOrchestrator.run(ScanManifest, ModelAdapter)
     │
     ├─ Update manifest status: RUNNING
     ├─ Initialize TaskQueue + RateLimiter + CostTracker
     ├─ Dispatch in parallel:
     │    ├─ Thread A: GarakAdapter.run(garak_config, ModelAdapter)
     │    ├─ Thread B: PyRITAdapter.run(pyrit_config, ModelAdapter)
     │    └─ Thread C: DeepTeamAdapter.run(deepteam_config, ModelAdapter)
     │
     ├─ RateLimiter: token-bucket across all threads
     │    └─ Enforces API rate limits; prevents simultaneous bursts
     ├─ CostTracker: accumulates actual spend; halts at ceiling
     ├─ ProgressEmitter: fires every 5s → UI event bus
     │
     ├─ On engine completion → store raw_output in manifest (encrypted)
     ├─ On engine failure   → log error; mark FAILED; continue others
     │    └─ Set manifest.coverage_reduced = true
     │
     └─ On all engines done (or global timeout reached):
          ├─ Update manifest status: COMPLETED (or FAILED)
          └─ Emit: scan_complete → NormalizationPipeline
```

---

## 2.4 How Each Engine Is Invoked

**Garak:**
```
GarakAdapter.run()
  ├─ Generate garak_config.yaml from GarakEngineConfig
  ├─ Start ModelAdapter proxy on localhost:PORT
  │    (Garak calls this proxy; proxy calls actual model)
  ├─ subprocess("garak --config garak_config.yaml")
  ├─ Monitor subprocess stdout for progress
  ├─ On exit: parse output JSONL files
  └─ Return: GarakRawOutput
```

**PyRIT:**
```
PyRITAdapter.run()
  ├─ Wrap ModelAdapter as PyRIT PromptTarget
  ├─ Initialize attacker LLM (Phi-3 Mini local or user API)
  ├─ Configure RedTeamingOrchestrator with attack strategies
  ├─ Run orchestrator against target
  ├─ Monitor PyRIT's internal SQLite DB for progress
  ├─ On completion: query conversation results from DB
  └─ Return: PyRITRawOutput
```

**DeepTeam:**
```
DeepTeamAdapter.run()
  ├─ Wrap ModelAdapter as deepeval LLM class
  ├─ Build test cases for each enabled metric category
  ├─ deepeval.evaluate(test_cases, metrics)
  ├─ Collect metric results with failing test cases
  └─ Return: DeepTeamRawOutput
```

---

## 2.5 Normalization Pipeline

```
NormalizationPipeline.process([GarakOutput, PyRITOutput, DeepTeamOutput])
     │
     ├─ STEP 1: Schema Mapping
     │    For each engine output:
     │    SchemaMapper.map(engine, raw_output)
     │    → draft VulnerabilityFinding per detected issue
     │    → map engine vulnerability names → canonical VulnClass
     │
     ├─ STEP 2: Deduplication
     │    Deduplicator.process(all_drafts)
     │    ├─ Group by (vulnerability_class, semantic_probe_hash)
     │    ├─ Merge groups into single finding
     │    ├─ Set source_engines = all confirming engines
     │    ├─ Set corroboration_count
     │    └─ Select best evidence from merged group
     │
     ├─ STEP 3: Evidence Collection
     │    EvidenceCollector.attach(deduplicated_findings)
     │    ├─ Attach probe_payload + model_response (encrypted reference)
     │    ├─ Calculate attack_success_rate from variant results
     │    └─ Attach raw_engine_output references
     │
     └─ Return: list[NormalizedFinding]
```

---

## 2.6 Scoring

```
ScoringEngine.score(NormalizedFindings, ScanManifest)
     │
     For each finding:
     │
     ├─ SeverityClassifier.classify(finding)
     │    ├─ Base severity from SeverityMatrix[vulnerability_class]
     │    ├─ + attack_success_rate modifier
     │    ├─ + deployment_context modifier (if set)
     │    └─ Set: finding.severity + finding.severity_rationale
     │
     └─ ConfidenceScorer.score(finding)
          ├─ corroboration_score   (from source_engines count)
          ├─ success_rate_score    (from attack_success_rate)
          ├─ diversity_score       (from probe_variant_count)
          ├─ maturity_score        (from engine+probe_class ratings)
          ├─ noise_penalty         (for known-noisy probe classes)
          ├─ final_confidence      (weighted combination)
          └─ Set: finding.confidence_score + confidence_text
```

---

## 2.7 Remediation & Report Assembly

```
RemediationEngine.annotate(ScoredFindings, deployment_context)
     For each finding:
     ├─ Look up vulnerability_class in RemediationKnowledgeBase
     ├─ Filter actions by deployment_context
     └─ Set: finding.remediation {model_level, system_level, deploy_level}

DeploymentAdvisor.recommend(AnnotatedFindings, UserPreferences)
     ├─ Load PlatformCapabilityMaps
     ├─ Match platform controls to detected VulnClasses
     ├─ Score + rank platforms
     ├─ Generate cost comparison at query_volume
     └─ Return: DeploymentRecommendation

ReportGenerator.generate(AnnotatedFindings, ScanManifest, DeploymentRec)
     ├─ Compute overall_risk_tier
     ├─ Aggregate finding counts
     ├─ Build OWASP coverage map
     ├─ Sort findings by severity
     ├─ Render PDF  (local, no server)
     ├─ Render HTML (self-contained)
     ├─ Serialize JSON
     └─ Return: ScanReport + file paths
```

---

# SECTION 3 — BACKEND ARCHITECTURE

---

## Module 3.1: Input Handler

**Purpose:** Accept raw user input, validate it, and produce a trusted, typed context object that all downstream modules can rely on.

**Inputs:** Raw model connection parameters from the UI (unvalidated strings).  
**Outputs:** `ValidatedModelContext`, `ConnectionStatus`, `CostEstimate`.

**Key responsibilities:**
- Model type detection → adapter selection
- Live connectivity test with timeout and retry
- Hardware compatibility check for local GGUF models
- Token-based cost estimation before any probe is sent
- Fail-safe: any validation failure returns a typed error with corrective suggestion — no partial states pass downstream

**Dependencies:** `ModelAdapters` (one per type), OS hardware detection, tokenizer libraries.

---

## Module 3.2: Manifest Processor

**Purpose:** Build the complete, reproducible scan specification and manage its lifecycle from creation through completion.

**Inputs:** `ValidatedModelContext`, `ScanConfig`, `ConsentRecord`.  
**Outputs:** `ScanManifest` (persisted to disk), `manifest_approved` event.

**Key responsibilities:**
- UUID-based manifest identity
- Probe category resolution (depth enum → specific probe lists per engine)
- Per-engine configuration generation
- Consent record stamping (timestamp, app version, approved estimate)
- Disk persistence (encrypted, versioned schema)
- Status lifecycle management

**Critical invariant:** After APPROVED status, the manifest is append-only. No in-place modification. Post-scan metadata is supplementary.

---

## Module 3.3: Engine Orchestrator

**Purpose:** Coordinate parallel execution of all enabled engines. Handle rate limiting, timeouts, progress reporting, and graceful degradation.

**Inputs:** `ScanManifest` (status: APPROVED), `ModelAdapter`.  
**Outputs:** `RawEngineOutputs` (one per engine), progress events, `ScanExecutionSummary`.

**Key responsibilities:**
- Parallel thread dispatch (one thread per engine)
- Shared token-bucket rate limiter across all engine threads
- Real-time cost tracking — halt if approaching approved ceiling
- Per-engine timeout (configurable; default 2× estimated duration)
- Progress event emission every 5 seconds
- Graceful degradation: continue on engine failure; flag coverage_reduced
- Pause/resume via disk-persisted checkpoint state
- Cancel with partial result preservation

---

## Module 3.4: Engine Adapters

**Purpose:** Translate AI-SENTRY's internal interface to each engine's native interface. Execute the engine. Return typed raw output.

**Standard interface every adapter implements:**
```
EngineAdapter:
  run(engine_config, model_adapter) → RawEngineOutput
  get_progress()                    → EngineProgress
  pause()                           → CheckpointState
  resume(checkpoint)                → None
  cleanup()                         → None
```

**Garak Adapter:**
- Spawns a localhost proxy server (Garak's model driver calls this)
- Generates YAML config from `GarakEngineConfig`
- Invokes Garak via subprocess; monitors stdout
- Parses JSONL report files on exit

**PyRIT Adapter:**
- Configures and manages attacker LLM (Phi-3 Mini local or user API)
- Wraps `ModelAdapter` as a PyRIT `PromptTarget`
- Runs `RedTeamingOrchestrator` with configured attack strategies
- Queries PyRIT's SQLite DB for conversation results on completion

**DeepTeam Adapter:**
- Wraps `ModelAdapter` as a deepeval custom `LLM` class
- Builds `EvaluationTestCase` objects per metric category
- Runs `deepeval.evaluate()` and collects metric results
- Returns typed metric objects with failing test cases as evidence

---

## Module 3.5: Normalization Layer

**Purpose:** Convert heterogeneous raw engine outputs into uniform `VulnerabilityFinding` objects. Deduplicate across engines. Attach evidence.

**Inputs:** `RawEngineOutputs`, `ScanManifest`.  
**Outputs:** `list[NormalizedFinding]`.

**SchemaMapper:** Maintains per-engine field mapping tables. Maps engine-specific vulnerability names to canonical `VulnClass` taxonomy. Handles missing fields without crashing.

**Deduplicator:** Groups findings by `(vulnerability_class, semantic_probe_hash)` across engines. Merges groups preserving all `source_engine` references. Selects highest-quality evidence. Does not merge findings of different classes even if triggered by the same probe.

**EvidenceCollector:** Retrieves probe payloads and model responses from raw outputs. Calculates `attack_success_rate`. Stores evidence encrypted via `EvidenceStore` (not inline in finding objects).

---

## Module 3.6: Scoring Engine

**Purpose:** Assign severity tier and confidence score to each normalized finding using transparent, reproducible, documented logic.

**Inputs:** `list[NormalizedFinding]`, `ScanManifest`.  
**Outputs:** `list[ScoredFinding]`.

**SeverityClassifier:**
- `SeverityMatrix`: `{VulnClass → base_severity_tier}` — static config file
- Modifiers applied in order: attack_success_rate → deployment_context
- Always produces `severity_rationale` in plain English

**ConfidenceScorer:**
- Five factor scores, all 0.0–1.0
- Weights defined in an inspectable config file (not hardcoded)
- Produces `explanation_text` — plain English breakdown users can read and verify
- Score is reproducible: same inputs always produce same output

---

## Module 3.7: Report Generator

**Purpose:** Assemble the complete `ScanReport` from all scored and annotated findings. Render in all three output formats locally.

**Inputs:** `list[AnnotatedFinding]`, `ScanManifest`, `DeploymentRecommendation`.  
**Outputs:** `ScanReport` object, PDF file, HTML file, JSON file.

**Key responsibilities:**
- Executive summary text generation
- OWASP coverage map assembly (tested + not-tested with reasons)
- Finding sort and grouping
- Local PDF rendering (bundled renderer — no server, no internet)
- Self-contained HTML (all CSS and evidence embedded in single file)
- Full JSON serialization (machine-readable; includes all schema fields)

---

## Module 3.8: Deployment Engine

**Purpose:** Recommend deployment configurations and (for AWS) execute one-click provisioning.

**Sub-component A — Deployment Advisor (all platforms):**

**Inputs:** `ScanReport`, `UserDeploymentPreferences`.  
**Outputs:** `DeploymentRecommendation` with platform configs and cost comparison.

Logic:
1. Load static `PlatformCapabilityMaps` (what controls each platform offers)
2. Match platform controls against detected VulnClasses
3. Apply hard constraints filter (compliance, region)
4. Score remaining platforms (cost + security coverage + model size support)
5. Select recommendation with rationale; generate cost estimates

**Sub-component B — AWS Deploy Engine (v1 execution):**

**Inputs:** `AWSDeployConfig`, AWS credentials from OS keychain.  
**Outputs:** `DeploymentResult`, streaming status events.

Four-phase execution:
1. **PLAN** — Generate complete resource list; no AWS API calls
2. **APPROVE** — Show plan to user; require explicit confirmation
3. **PROVISION** — Execute AWS API calls in dependency order
4. **VERIFY** — Health check endpoint; return resource summary
5. **ROLLBACK** (on failure) — Delete all resources created in this session

---

# SECTION 4 — DATA SCHEMAS

---

## 4.1 Input Schema

```
ModelConfig
  model_type         enum      OPENAI_COMPAT | AZURE_OPENAI | LOCAL_GGUF |
                               HUGGINGFACE | GENERIC_REST
  endpoint_url       string?   null for local models
  api_key_ref        string?   keychain reference ID (never the key itself)
  model_name         string    e.g. "gpt-4o"
  azure_deployment   string?   Azure deployment name (Azure only)
  hf_model_id        string?   e.g. "meta-llama/Llama-2-7b"
  local_file_path    string?   absolute path to .gguf file
  max_tokens         integer   max tokens per response; default 512
  temperature        float     default 0.7
  request_timeout    integer   seconds; default 30

ConnectionStatus
  success            boolean
  latency_ms         integer?
  error_code         string?   machine-readable error type
  error_message      string?   human-readable explanation
  model_metadata     ModelMetadata?

ModelMetadata
  provider           string
  model_name         string
  context_length     integer?
  pricing_input      float?    USD per 1M input tokens
  pricing_output     float?    USD per 1M output tokens
  supports_system_prompt  boolean

CostEstimate
  probe_count        integer   estimated number of prompts
  input_tokens       integer   estimated input tokens
  output_tokens      integer   estimated output tokens
  cost_low_usd       float     lower bound
  cost_high_usd      float     upper bound
  cost_basis         string    plain English estimate methodology
```

---

## 4.2 Manifest Schema

```
ScanManifest
  manifest_id        UUID      globally unique
  scan_id            UUID      same as manifest_id in v1
  schema_version     string    "1.0" — for future migrations

  created_at         ISO8601
  approved_at        ISO8601?
  started_at         ISO8601?
  completed_at       ISO8601?

  status             enum      CREATED | CONSENT_PENDING | APPROVED |
                               RUNNING | COMPLETED | FAILED | CANCELLED

  model_config       ModelConfig
  model_metadata     ModelMetadata

  scan_depth         enum      QUICK | STANDARD | DEEP | CUSTOM
  probe_categories   string[]  list of category IDs
  deployment_context string?   e.g. "healthcare", "customer_service"

  engine_configs
    garak            GarakEngineConfig?
    pyrit            PyRITEngineConfig?
    deepteam         DeepTeamEngineConfig?

  cost_estimate      CostEstimate
  duration_estimate  { min_minutes: int, max_minutes: int }
  consent_record     ConsentRecord?

  engine_statuses
    garak            enum      PENDING | RUNNING | COMPLETE | FAILED | SKIPPED
    pyrit            enum      (same)
    deepteam         enum      (same)

  coverage_reduced   boolean   true if any engine failed
  actual_cost_usd    float?    populated after completion
  actual_duration_s  integer?  seconds

ConsentRecord
  consented_at          ISO8601
  app_version           string
  items_acknowledged    string[]    list of consent item IDs acknowledged
  cost_estimate_shown   CostEstimate   the estimate the user approved

GarakEngineConfig
  version_pinned     string    e.g. "0.9.0.14"
  probes             string[]  e.g. ["garak.probes.jailbreak.Dan"]
  detectors          string[]
  generations        integer   repetitions per probe variant; default 5

PyRITEngineConfig
  version_pinned     string
  attack_strategies  string[]  e.g. ["crescendo", "pair", "prompt_sending"]
  attacker_llm       string    "local:phi3-mini" or "api:openai:gpt-4o-mini"
  max_turns          integer   default 8

DeepTeamEngineConfig
  version_pinned     string
  metrics            string[]  e.g. ["BiasMetric", "HallucinationMetric"]
  threshold          float     score below which = finding; default 0.7
  num_test_cases     integer   per metric; default 25
```

---

## 4.3 Raw Engine Output Schemas

```
GarakResult (one per probe attempt)
  probe              string    e.g. "garak.probes.jailbreak.Dan"
  detector           string
  passed             boolean   false = vulnerability detected
  output             string    model's response text
  trigger            string    the probe input sent to the model
  score              float     0.0 = fully vulnerable
  attempt_n          integer   which repetition

PyRITConversationLog
  conversation_id    UUID
  strategy           string    e.g. "crescendo"
  turns              Turn[]
  final_outcome      enum      SUCCESS | FAILURE | PARTIAL
  harm_category      string
  score              float

Turn
  role               enum      ATTACKER | TARGET
  content            string
  turn_number        integer

DeepTeamMetricResult
  metric_name        string    e.g. "BiasMetric"
  score              float     0.0 = most harmful
  passed             boolean   false = finding detected
  reason             string    why the metric failed
  test_case          { input: string, actual_output: string }
```

---

## 4.4 Normalized & Scored Finding Schema

```
VulnerabilityFinding
  finding_id          UUID
  scan_id             UUID
  schema_version      string    "1.0"

  vulnerability_class  VulnClass   (canonical enum — see below)
  title                string
  description          string
  owasp_category       string    e.g. "LLM01: Prompt Injection"
  cwe_reference        string?   e.g. "CWE-20"

  source_engines       Engine[]  engines that detected this
  corroboration_count  integer   1, 2, or 3

  evidence_id          UUID      reference to EvidenceStore (not inline)
  attack_success_rate  float     0.0–1.0
  probe_variant_count  integer

  context_sensitive    boolean
  context_notes        string?

  severity             enum      CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL
  severity_rationale   string    plain English

  confidence_score     float     0.0–1.0
  confidence_factors   ConfidenceFactors
  confidence_text      string    plain English breakdown

  remediation          RemediationPlan?
  raw_evidence_refs    { engine: string }   per-engine raw output reference

VulnClass (enum)
  PROMPT_INJECTION | JAILBREAK_DAN | JAILBREAK_ROLEPLAY | JAILBREAK_CRESCENDO
  TOXICITY_GENERAL | TOXICITY_TARGETED | PII_LEAKAGE | SYSTEM_PROMPT_EXTRACTION
  TRAINING_DATA_EXTRACTION | HALLUCINATION_FACTUAL | HALLUCINATION_CITATION
  BIAS_GENDER | BIAS_RACIAL | BIAS_POLITICAL | COPYRIGHT_REPRODUCTION
  EXCESSIVE_AGENCY | INSECURE_OUTPUT_HANDLING

ConfidenceFactors
  corroboration_score   float    0.0–1.0  (source_engines count)
  success_rate_score    float    0.0–1.0  (from attack_success_rate)
  diversity_score       float    0.0–1.0  (from probe_variant_count)
  maturity_score        float    0.0–1.0  (engine + probe_class ratings)
  noise_penalty         float    0.0–1.0  (known-noisy probe classes; subtracted)
  final_confidence      float    weighted combination

Evidence (stored encrypted in EvidenceStore)
  evidence_id              UUID
  probe_payload            string  (encrypted at rest)
  model_response           string  (encrypted at rest)
  multi_turn_log           Turn[]?
  probe_variant_results    { variant_id: string, success: boolean }[]

RemediationPlan
  model_level         RemediationAction[]
  system_level        RemediationAction[]
  deployment_level    RemediationAction[]
  priority            enum      IMMEDIATE | SHORT_TERM | LONG_TERM

RemediationAction
  action_id           string
  description         string
  references          string[]
  effort              enum      LOW | MEDIUM | HIGH
  addresses_finding   UUID
```

---

## 4.5 Report Schema

```
ScanReport
  report_id            UUID
  scan_id              UUID
  manifest_id          UUID
  schema_version       string
  generated_at         ISO8601
  app_version          string

  model_summary        ModelMetadata

  overall_risk_tier    enum   CRITICAL | HIGH | MEDIUM | LOW | CLEAN
  finding_counts       { critical, high, medium, low, informational, total: integer }
  executive_summary    string   2–3 sentence plain English summary

  findings             VulnerabilityFinding[]   sorted by severity desc

  owasp_coverage       OWASPCoverageItem[]
  tested_categories    string[]
  untested_categories  { category: string, reason: string }[]

  engine_summaries
    garak              EngineRunSummary?
    pyrit              EngineRunSummary?
    deepteam           EngineRunSummary?

  deployment_recommendation   DeploymentRecommendation

  scan_duration_seconds   integer
  actual_cost_usd         float
  probe_count_actual      integer

OWASPCoverageItem
  category             string    e.g. "LLM01: Prompt Injection"
  tested               boolean
  finding_count        integer
  highest_severity     SeverityTier?
  not_tested_reason    string?

EngineRunSummary
  engine               Engine
  status               enum    COMPLETE | FAILED | PARTIAL
  probes_sent          integer
  findings_raw         integer   before deduplication
  duration_seconds     integer
  error_message        string?

DeploymentRecommendation
  recommended_platform  enum    AWS | AZURE | GCP | LOCAL
  rationale             string
  platform_configs      { aws, azure, gcp, local: PlatformConfig? }
  cost_comparison       CostComparisonItem[]
  security_controls_map { VulnClass: SecurityControl[] }
  compliance_notes      ComplianceNote[]

PlatformConfig
  platform              enum    AWS | AZURE | GCP | LOCAL
  architecture          string  e.g. "API Gateway + Lambda"
  security_controls     SecurityControl[]
  estimated_monthly_usd float
  setup_complexity      enum    LOW | MEDIUM | HIGH
  one_click_available   boolean
```

---

# SECTION 5 — UI/UX DESIGN

## Screen-by-Screen Conceptual Design

---

## Screen 1: Onboarding / Consent (First Launch Only)

**What the user sees:**
A full-screen, immersive 4-step sequence. Dark background. Clean typography. No sidebars, no menus — pure focused content. A step indicator shows progress (1/4, 2/4, etc.).

Steps: Welcome → How It Works → What You Should Know → Environment Check.

The "What You Should Know" screen has a strong visual warning indicator. The text is honest, not legally evasive. The Environment Check screen uses a terminal-style output with color-coded status icons (✓ green, ⚠ amber, ✗ red).

**What the user does:**
Reads each screen. Clicks "Next." On the Warning screen, must actively click "I Understand." On the Environment Check screen, sees automatic results — no user action needed. Clicks "Enter AI-SENTRY."

**Design principle:** This sequence is shown only once. After that, the user lands directly on the main dashboard.

---

## Screen 2: Main Dashboard

**What the user sees:**
A persistent left sidebar with navigation: Dashboard, New Scan, Scan History, Reports, Deploy, Settings.

The main panel on first use shows a large, centered "Start Your First Scan" prompt with a brief tagline. After scans exist: a summary of recent scans (model name, date, risk tier, quick action links).

A persistent top bar shows: app name, current version, connection status indicator.

**What the user does:**
Clicks "New Scan" to begin. Or selects a previous scan to review.

---

## Screen 3: Connect Model (Input Screen)

**What the user sees:**
A clean two-column layout. Left column: model type selector (three clearly labeled cards — API Endpoint, Local Model, HuggingFace). Right column: the form fields for the selected type — they switch based on selection.

Below the form: a disabled "Test Connection" button that activates once required fields are filled.

**What the user does:**
Selects model type (one click). Fills in credentials or file path. Clicks "Test Connection." Sees live validation result. Clicks "Continue to Scan Setup."

---

## Screen 4: Manifest / Scan Configuration

**What the user sees:**
Three clearly separated sections:

*Top section:* Three preset cards (Quick / Standard / Deep) with duration and coverage summaries. The recommended one is visually highlighted.

*Middle section:* "Customize" toggle — expands to show probe category checkboxes and engine toggles. Collapsed by default.

*Bottom section:* "Upload manifest" option — a smaller, secondary link below the presets.

Deployment context dropdown: optional, clearly labeled as "improves remediation advice."

**What the user does:**
Picks a preset (one click) or customizes. Optionally sets deployment context. Clicks "Review & Confirm."

---

## Screen 5: Pre-Scan Confirmation (Consent Gate)

**What the user sees:**
A full-page summary card. Two columns: left shows scan details (model, depth, engines, categories); right shows estimates (probe count, token count, cost range, duration range).

A clearly boxed warning section about adversarial content.

Three checkboxes below — Authorization, Cost acceptance, ToS. The "Begin Scan" button is visually disabled (grey) until all three are checked.

**What the user does:**
Reviews the summary. Checks three boxes. Clicks "Begin Scan."

---

## Screen 6: Scan Progress

**What the user sees:**
A live dashboard with three engine status panels arranged horizontally. Each panel shows: engine name, progress bar, current probe name, and a live finding counter.

Below the engine panels: a live findings feed — new cards appear as findings are detected. Each card shows severity icon, brief title, detecting engine.

Bottom of screen: API usage bar (tokens used vs. estimate, cost so far vs. estimate). Pause and Cancel buttons.

**What the user does:**
Watches progress. Optionally pauses or cancels. No other action needed during scan.

---

## Screen 7: Results Dashboard

**What the user sees:**
A summary banner at the top (risk tier, finding counts, scan metadata). Below it, the OWASP coverage map — a grid showing each LLM Top 10 category with tested/not-tested status and finding count. Below that, finding cards sorted by severity.

Each finding card shows: severity badge, confidence score, title, detecting engines, success rate, one-line description. Action buttons: View Evidence, See Remediation, Export.

Expanded "View Evidence" panel: probe payload (behind click-through warning), model response, probe variant breakdown.

Expanded "See Remediation" panel: three-level action list with effort indicators.

**What the user does:**
Reviews findings. Drills into evidence and remediation for any finding. Navigates to Report tab or Deploy tab.

---

## Screen 8: Report View

**What the user sees:**
A full-page document preview of the report, rendered in-app. Navigation sidebar on the left shows report sections (Executive Summary, Vulnerability Catalog, Coverage Map, etc.) — clicking jumps to that section.

Action bar at the top: Download PDF, Download HTML, Download JSON.

A small info box notes that the report contains adversarial content in the Appendix.

**What the user does:**
Previews the report. Scrolls through sections. Clicks download in preferred format.

---

## Screen 9: Deployment Screen

**What the user sees:**
Three-panel layout for platform comparison (AWS, Azure, GCP as columns, attributes as rows). The recommended platform is highlighted. Each column has a "Get Config" button; AWS has a "Deploy Now" button.

Clicking "Get Config" for Azure or GCP shows a pre-filled configuration guide (read-only, no provisioning).

Clicking "Deploy to AWS" enters a two-step wizard: credentials + config input, then infrastructure plan review.

**Infrastructure plan review:** A styled document showing every resource that will be created, including the Bedrock Guardrail mappings. A single checkbox and "Deploy" button at the bottom.

**Live deployment:** Progress list with checkmarks. Cannot be closed during execution.

**Completion screen:** Endpoint URL, resource summary, active security controls. Copy/export actions.

**What the user does:**
Reviews platform comparison. Selects platform. For AWS: enters credentials, reviews plan, approves, watches deployment, copies endpoint.

---

# SECTION 6 — IMPLEMENTATION PLAN

## Phase-by-Phase Build Sequence

---

## Phase 0 — Design & Documentation (COMPLETE)

**0a:** System design, architecture, design principles  
**0b:** PRD, TRD, context system  
**0c:** This document — system execution layer, schemas, UI design, implementation plan

**Output:** Zero code. Complete specification. All schemas defined. All decisions documented.

---

## Phase 1 — Project Scaffold & Environment

**Goal:** Runnable project skeleton. No business logic. Foundation for all later phases.

**Deliverables:**
- Directory structure matching target layout from `project_overview.md`
- Python project configuration (`pyproject.toml` with dependency groups)
- Pinned engine dependencies: garak, pyrit-ai, deepeval
- Environment health check tool (validates all engines installed at correct versions)
- Configuration management system (user preferences, engine version pins)
- Structured logging framework (channels: app, orchestration, engine-specific, security)
- Basic CLI skeleton accepting model input and scan config flags
- Auto-install script for first-run dependency setup

**Dependencies of this phase:** None — starts here.  
**What phase 2 needs from this:** Working project structure, config system, logging.

---

## Phase 2 — Model Adapter Layer

**Goal:** AI-SENTRY can connect to any supported model type, validate connectivity, estimate cost, and send test prompts. No scanning yet.

**Deliverables:**
- `ModelAdapter` abstract interface (the contract all adapters implement)
- `OpenAICompatibleAdapter` (covers OpenAI, most third-party APIs)
- `AzureOpenAIAdapter` (Azure-specific auth + deployment name handling)
- `LocalGGUFAdapter` (llama.cpp auto-spawn, health check, local server management)
- `HuggingFaceAdapter` (HF Inference API)
- `GenericRESTAdapter` (schema inference wizard for unknown endpoints)
- Hardware detection module (RAM, VRAM, CPU)
- `ScanManifest` data model + `ManifestProcessor`
- `CostEstimator` (token count models per provider)
- `InputHandler` module tying it all together
- Input validation and error response system

**Dependencies:** Phase 1 (scaffold, config, logging).  
**What phase 3 needs from this:** Working `ModelAdapter` interface + `ScanManifest`.

---

## Phase 3 — Engine Adapters

**Goal:** All three scanning engines can be invoked against a target model and return typed raw output. No normalization yet — raw output only.

**Deliverables (can be built in parallel tracks within this phase):**

*Track A — Garak Adapter:*
- `GarakAdapter` implementing `EngineAdapter` interface
- YAML config generator from `GarakEngineConfig`
- Localhost proxy server (Garak → AI-SENTRY → Target model)
- Subprocess management + stdout monitoring
- JSONL output parser → `GarakRawOutput`

*Track B — PyRIT Adapter:*
- `PyRITAdapter` implementing `EngineAdapter` interface
- Attacker LLM setup (Phi-3 Mini auto-download + local serving)
- PyRIT `PromptTarget` wrapper around `ModelAdapter`
- `RedTeamingOrchestrator` configuration
- SQLite result extractor → `PyRITRawOutput`

*Track C — DeepTeam Adapter:*
- `DeepTeamAdapter` implementing `EngineAdapter` interface
- deepeval custom LLM class wrapping `ModelAdapter`
- Test case builder per metric category
- `evaluate()` runner + result collector → `DeepTeamRawOutput`

*Track D — Engine Orchestrator:*
- `EngineOrchestrator` (parallel dispatch, rate limiting, progress events)
- `RateLimiter` (token bucket implementation)
- `CostTracker` (real-time accumulation + ceiling enforcement)
- `ProgressEmitter` (5-second event interval → UI event bus)
- Pause/resume checkpoint system

**Dependencies:** Phase 2 (`ModelAdapter`, `ScanManifest`).  
**What phase 4 needs:** All three `RawEngineOutput` types.  
**Critical known issue to resolve:** KI-001 (PyRIT attacker LLM hardware), KI-002 (Garak version pin).

---

## Phase 4 — Normalization Layer

**Goal:** Raw outputs from all three engines are converted into a single, deduplicated, evidence-attached collection of `VulnerabilityFinding` objects.

**Deliverables:**
- `SchemaMapper` with per-engine field mapping tables
- `VulnClass` taxonomy enum + mapping tables from engine-specific names
- `Deduplicator` (semantic hashing + merge logic)
- `EvidenceStore` (encrypted local storage for probe/response content)
- `EvidenceCollector` (attach evidence to findings, calculate success rates)
- `NormalizationPipeline` (orchestrates all three steps)
- Schema validation for `VulnerabilityFinding`

**Dependencies:** Phase 3 (all three `RawEngineOutput` types).  
**What phase 5 needs:** `list[NormalizedFinding]` with all fields populated.

---

## Phase 5 — Intelligence Layer (Scoring + Remediation)

**Goal:** Every normalized finding receives a severity tier (with rationale) and a confidence score (with explanation). Every finding gets a remediation plan.

**Deliverables:**
- `SeverityMatrix` configuration file (VulnClass → base tier)
- `SeverityClassifier` module (matrix lookup + modifier application)
- `ConfidenceWeights` configuration file (factor weights — inspectable)
- `ConfidenceScorer` module (five-factor computation + explanation generation)
- `ProbeClassNoiseRatings` configuration file
- `RemediationKnowledgeBase` (VulnClass → remediation action templates)
- `RemediationEngine` module (knowledge base lookup + context filtering)
- `ScoringEngine` orchestrating classifier + scorer

**Dependencies:** Phase 4 (`list[NormalizedFinding]`).  
**What phase 6 needs:** `list[AnnotatedFinding]` with severity + confidence + remediation.

---

## Phase 6 — Report Generator

**Goal:** A complete, accurate, multi-format security report is generated from scan results. PDF, HTML, and JSON all work.

**Deliverables:**
- `ScanReport` data model
- Executive summary generator
- OWASP coverage map assembler
- Finding sort and grouping logic
- `OWASPCoverageItem` assembly from manifest + findings
- PDF renderer (local, bundled renderer library)
- HTML renderer (self-contained, single file output)
- JSON serializer (full schema, machine-readable)
- Report preview in-app (render HTML in embedded WebView)

**Dependencies:** Phase 5 (`list[AnnotatedFinding]`), Phase 7 (`DeploymentRecommendation`).  
**Note:** Phase 6 and Phase 7 can be developed in parallel; report is assembled once both are ready.

---

## Phase 7 — Deployment Advisor + AWS Deploy Engine

**Goal:** The Deployment Advisor produces a recommendation. The AWS Deploy Engine provisions real AWS infrastructure from that recommendation.

**Deliverables:**

*Part A — Deployment Advisor:*
- `PlatformCapabilityMaps` (static config: platform → available security controls)
- Platform scoring algorithm
- Cost estimation model per platform at query volume
- `DeploymentRecommendation` assembly

*Part B — AWS Deploy Engine:*
- AWS credentials management (OS keychain read/write)
- IAM policy templates (minimum permission sets)
- VPC + networking provisioning logic
- API Gateway + Lambda deployment logic
- SageMaker endpoint deployment logic (alternative path)
- Bedrock Guardrails configuration from vulnerability findings
- CloudWatch alarm setup
- Budget alert setup
- Resource tagging
- Pre-flight permission check
- Rollback mechanism (cleanup all resources on failure)
- Streaming status events to UI

**Dependencies:** Phase 5 (`ScanReport`).  
**Critical known issue to resolve:** KI-005 (IAM permission scope).

---

## Phase 8 — Desktop Application UI

**Goal:** Full working UI in the chosen framework. All backend modules are wired to UI screens. The complete end-to-end workflow works in the desktop app.

**Deliverables:**
- All 9 screens implemented (Onboarding through Deployment)
- Backend-to-UI event bridge (progress events, live findings feed)
- Onboarding flow (first-launch detection, 4-screen sequence)
- Environment check screen (reads from health check module)
- Model input forms with live validation feedback
- Scan configuration screen (presets + custom)
- Consent gate screen (disabled button logic)
- Live scan progress dashboard (real-time updates)
- Results dashboard (finding cards, OWASP map, drill-down panels)
- Evidence viewer (click-through warning, encrypted content display)
- Report preview + export buttons
- Deployment advisor screen (comparison table)
- AWS deployment wizard (credentials → plan → live provisioning)
- Settings screen (preferences, engine versions, keychain management)
- Error screens for all failure paths

**Dependencies:** Phases 2–7 (all backend modules).

---

## Phase 9 — Website

**Goal:** Public website is live. Downloads work. Documentation is accessible. SEO is implemented.

**Deliverables:**
- Homepage with animated hero section (scan visualization)
- Features page (deep dive on capabilities)
- How It Works page (4-step visual)
- Roadmap page (public roadmap matching this plan)
- Documentation site (model support matrix, schema reference, scan categories)
- Download page (Windows + Linux, checksums, system requirements)
- Changelog page (version history)
- Blog (initial posts: "What is prompt injection?", "How AI-SENTRY scores confidence")
- Legal pages: Privacy Policy, Terms of Service
- Cookie banner (minimal — Plausible Analytics requires none)
- SEO: meta tags, structured data, sitemap, robots.txt
- Update API endpoint (desktop app polls this for new versions)

**Dependencies:** Can be developed in parallel with Phase 8 after design is locked.

---

## Phase 10 — Integration Testing

**Goal:** End-to-end test suite passes. Known-vulnerable test models produce expected findings. Known-clean models pass. AWS deployment succeeds from a clean account.

**Test suite components:**
- Unit tests for every module (schema validation, scoring logic, mapping tables)
- Integration tests: full scan pipeline against test fixtures
- Regression tests: known-vulnerable models must produce ≥1 High finding
- False-positive tests: known-clean models must not produce Critical/High findings
- AWS deployment test: full deployment from clean account, resource verification, cleanup
- Performance tests: scan duration vs. estimates within expected range
- Security tests: credentials never appear in logs; probe content encrypted

**Dependencies:** Phases 1–9 complete.

---

## Phase 11 — Launch Preparation

**Goal:** Ready for public release.

**Deliverables:**
- Windows installer signed (code signing certificate)
- Linux packages signed (GPG)
- SHA256 checksums published
- GitHub release created with all artifacts
- Website live with download links pointing to release
- Product Hunt and community launch posts prepared
- Documentation complete and reviewed
- Support channel established (GitHub Issues + Discord)
- Monitoring: website analytics, download tracking, error reporting (opt-in)

---

# SECTION 7 — DESKTOP APP STRATEGY

## Framework Decision and Rationale

---

## 7.1 The Decision: Tauri (Rust + WebView)

After evaluating three options — Electron, Tauri, and PySide6 — the recommendation is **Tauri**.

### Why Not Electron?

Electron bundles a full Chromium browser + Node.js runtime into every installation. This results in:
- Installer size: 150–300 MB minimum, before any application code
- RAM usage: 200–500 MB at idle
- Security surface: Chromium + Node.js have substantial attack surface
- For a security tool, shipping a bloated, high-attack-surface runtime is a contradiction

### Why Not PySide6 (Python GUI)?

PySide6 would give us a Python-native GUI with no separate runtime. However:
- UI quality ceiling is significantly lower than web-based UIs
- The animations, data visualizations, and polished design required for AI-SENTRY are painful to build in PySide6
- Developer talent pool for PySide6 UI work is much smaller
- Cross-platform behavior inconsistencies require significant work to resolve

### Why Tauri?

**Tauri uses the OS's native WebView** (WebView2 on Windows, WebKit on macOS/Linux) instead of bundling Chromium. The result:
- Installer size: 5–15 MB (compared to 150–300 MB for Electron)
- RAM usage: 50–100 MB at idle
- The Rust backend is memory-safe and performant
- The frontend is standard HTML + CSS + JavaScript — any web developer can contribute
- Security model: Tauri has an allowlist system that restricts what the frontend can call — appropriate for a security tool

**Trade-off acknowledged:** Tauri's Rust backend requires Rust knowledge for the IPC layer. The Python backend (scanning engines, orchestration) communicates with Rust via a local IPC bridge (documented below).

---

## 7.2 Architecture: How Frontend, Rust Backend, and Python Backend Connect

```
┌──────────────────────────────────────────────────────┐
│  TAURI FRONTEND (HTML + CSS + JS)                    │
│  All UI screens live here                            │
│  Calls Tauri commands via invoke()                   │
└───────────────────┬──────────────────────────────────┘
                    │  Tauri IPC (invoke / events)
┌───────────────────▼──────────────────────────────────┐
│  TAURI RUST BACKEND                                  │
│  Handles: file system, OS keychain, window mgmt      │
│  Spawns and manages Python backend process           │
│  Bridges: Tauri commands ↔ Python process            │
└───────────────────┬──────────────────────────────────┘
                    │  Local IPC (stdin/stdout JSON or
                    │  Unix socket / named pipe)
┌───────────────────▼──────────────────────────────────┐
│  PYTHON BACKEND PROCESS                              │
│  All scan logic lives here:                          │
│  InputHandler, ManifestProcessor, Orchestrator,      │
│  Normalization, Scoring, Reporting, Deployment       │
└──────────────────────────────────────────────────────┘
```

**Why this separation?**

The Python backend cannot be replaced with Rust — the scanning engines (Garak, PyRIT, DeepTeam) are Python libraries. They must run in Python. The Rust backend manages OS-level operations (keychain, file system, spawning processes) more safely than Python.

**IPC Protocol:** The Rust backend spawns the Python backend on startup. They communicate via a local socket using a simple JSON-based command/response protocol. Progress events from Python are pushed to Tauri as events, which are then emitted to the frontend as Tauri event listeners.

---

## 7.3 How Installation Works

**Windows:**

The installer is an NSIS or WiX-based .exe. It contains:
- The Tauri application (Rust binary + WebView2 dependency)
- A bundled Python runtime (embedded Python 3.11, not installed to system PATH)
- All Python dependencies pre-installed in a virtual environment within the bundle
- The scanning engines (Garak, PyRIT, DeepTeam) pre-installed in the bundled venv
- llama.cpp binary (pre-compiled for the target platform)

On install:
1. Tauri application files extracted to `%APPDATA%\AI-SENTRY\`
2. Bundled Python runtime extracted to `%APPDATA%\AI-SENTRY\runtime\`
3. Desktop shortcut created
4. Start Menu entry created
5. (Optional) Windows Defender exclusion suggested — scanning engines may trigger AV heuristics due to adversarial content generation

**Linux:**

Distributed as an AppImage. The AppImage contains everything — no host Python required. User makes it executable and runs it. No system-level installation required.

Additionally, a .deb package for Debian/Ubuntu users who prefer system-level installation.

---

## 7.4 Auto-Update Strategy

The desktop app checks for updates on launch (if internet is available). It calls the AI-SENTRY update API endpoint:

```
GET https://ai-sentry.dev/api/version/latest
→ { version: "1.2.0", download_url: "...", release_notes_url: "...", sha256: "..." }
```

If a new version is available, the app shows a non-blocking notification: "AI-SENTRY v1.2.0 is available. [Download Update] [Later]"

Clicking "Download Update" opens the download page in the system browser. The app does not auto-install updates — the user controls installation.

For engine dependency updates (Garak, PyRIT, DeepTeam version upgrades), these are bundled in each new app release. Users do not separately update engines.

---

# SECTION 8 — WEBSITE INTEGRATION

## How the Website Connects to the Ecosystem

---

## 8.1 Website Structure and Purpose

The website serves three functions:
1. **Discovery and conversion:** Explain what AI-SENTRY does; convert visitors to downloaders
2. **Trust establishment:** Documentation, changelog, security disclosures, legal pages
3. **Infrastructure:** Version API, download hosting, analytics

The website does **not** process scan data. It does **not** receive any information from the desktop app during scans. It is a static+minimal-API site.

---

## 8.2 Page Architecture

```
ai-sentry.dev/
├── /                      Hero + CTA + brief feature overview
├── /features              Deep capability breakdown
├── /how-it-works          4-step visual explainer
├── /roadmap               Public phase roadmap
├── /docs/                 Documentation site
│   ├── /docs/getting-started
│   ├── /docs/model-support
│   ├── /docs/scan-categories
│   ├── /docs/schema-reference
│   └── /docs/deployment-guide
├── /download              Platform downloads + checksums
├── /changelog             Version history
├── /blog/                 Security content
├── /legal/privacy         Privacy policy
└── /legal/terms           Terms of service
```

---

## 8.3 Download Page Design

The download page is a trust-critical surface. It must communicate:

**For each platform (Windows, Linux):**
- Download button (primary CTA)
- File size
- SHA256 checksum (displayed, copyable)
- System requirements (OS version, RAM minimum)
- "Verified engines" section: Garak vX.X, PyRIT vX.X, DeepTeam vX.X

**Below the downloads:**
- Installation instructions (brief, clear)
- "Something not working?" → link to GitHub Issues
- Link to changelog for this version

---

## 8.4 Version API (Desktop App Integration)

A minimal API endpoint the desktop app calls to check for updates:

```
Endpoint: GET https://ai-sentry.dev/api/version/latest
Response: {
  "version": "1.2.0",
  "released_at": "2026-10-01",
  "download_url": "https://ai-sentry.dev/download",
  "release_notes_url": "https://ai-sentry.dev/changelog/1.2.0",
  "sha256_windows": "abc123...",
  "sha256_linux_appimage": "def456...",
  "minimum_supported": "1.0.0"
}
```

This endpoint:
- Returns JSON with no authentication required
- Is rate-limited to 10 requests per IP per hour (prevents abuse)
- Does not log any user data — only serves static version info
- Is updated manually as part of the release process

---

## 8.5 Analytics Strategy

**Tool:** Plausible Analytics (self-hosted or cloud plan)

**Why Plausible:**
- No cookies — GDPR compliant without a consent banner
- No personal data collected — counts pageviews and unique visitors by country only
- Open source, auditable
- Does not slow down page load (lightweight script)
- For a privacy-first security tool, using Google Analytics would be hypocritical

**What is tracked:**
- Page views per page
- Download button clicks (custom events: "Download Windows", "Download Linux")
- Referrer traffic sources

**What is NOT tracked:**
- Individual users
- Any data from the desktop application
- Scan results or model names

---

## 8.6 Website to Desktop App Communication

There is intentionally **no direct communication** from the website to the desktop app.

The desktop app calls the website's version API (one direction only). The website never pushes anything to the desktop app. There is no websocket, no telemetry upload, no analytics beacon from the app to the website.

This is a deliberate privacy and security design decision. A security tool that phones home silently would undermine user trust fundamentally.

**The only optional connection:** If the user opts into telemetry (default: off), the app sends an anonymized, aggregated summary (scan count, scan depth distribution, OS type) to a separate analytics endpoint. This is opt-in, clearly described in Settings, and can be disabled at any time.

---

## 8.7 SEO Strategy

**Target keywords and content:**
- "LLM security scanner" → Homepage meta description
- "AI red teaming tool" → Features page H1
- "jailbreak testing LLM" → Blog: "What is prompt injection and how to test for it"
- "LLM vulnerability assessment" → How It Works page
- "AI deployment security" → Deployment documentation

**Technical SEO:**
- Static site generation (no client-side rendering for content pages)
- Sitemap.xml auto-generated on each deploy
- Schema.org structured data on download page (SoftwareApplication schema)
- All pages have unique title tags and meta descriptions
- Open Graph tags for social sharing (with a generated preview image per page)

**Content strategy:** Two blog posts per month during launch period, targeting technical audiences who are already searching for LLM security solutions. Each post ranks for a specific vulnerability class (prompt injection, jailbreaking, bias testing).

---

## Summary: System Execution Layer Complete

This document defines the complete execution design for AI-SENTRY. The system is ready for Phase 1 implementation.

**Key decisions resolved in this document:**
- Desktop framework: **Tauri** (Rust + WebView + Python backend via IPC)
- Installation model: **fully bundled** — no user-facing Python setup
- Update model: **user-controlled** — notification only, no auto-install
- Website analytics: **Plausible** — no cookies, GDPR-compliant, privacy-first
- Telemetry: **opt-in only**, default off, clearly documented in Settings

**What remains before Phase 1 starts:**
- Resolve KI-001: PyRIT attacker LLM hardware benchmarking plan
- Resolve KI-002: Select the specific Garak version to pin
- Final sign-off on Tauri as the framework (no objections)

*End of System Execution Layer v1.0*
