# AI-SENTRY — Technical Requirements Document (TRD)

**Document Version:** 1.0  
**Phase:** 0b — Documentation Foundation  
**Status:** Active  
**Last Updated:** 2026-09-13  
**Audience:** Developers, AI Tools, System Architects

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Core Modules](#2-core-modules)
3. [Data Flow](#3-data-flow)
4. [Integration Points](#4-integration-points)
5. [Limitations](#5-limitations)
6. [Design Principles](#6-design-principles)
7. [Security Considerations](#7-security-considerations)
8. [Assumptions](#8-assumptions)

---

## 1. System Architecture Overview

### Architectural Style

AI-SENTRY follows a **layered pipeline architecture** with strict unidirectional data flow. Each layer has a single responsibility. No layer calls backward into a previous layer. Components within the same layer may communicate, but cross-layer communication is always downward through defined interfaces.

This design enables:
- Independent testing of each layer
- Engine adapters can be swapped without affecting the scoring or reporting layers
- Scoring logic can be updated without touching the normalization layer

### Five-Layer Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  LAYER 1: INPUT LAYER                                        │
│  Model Adapter  |  Manifest System  |  Consent Gate          │
└─────────────────────────────┬────────────────────────────────┘
                              │ Standardized Model Interface
┌─────────────────────────────▼────────────────────────────────┐
│  LAYER 2: ORCHESTRATION LAYER                                │
│  Engine Manager  |  Task Queue  |  Rate Limiter  |  Logger   │
└──────┬──────────────────────┬───────────────────┬────────────┘
       │                      │                   │
  ┌────▼────┐            ┌────▼────┐         ┌────▼─────┐
  │  Garak  │            │  PyRIT  │         │ DeepTeam │
  │ Adapter │            │ Adapter │         │ Adapter  │
  └────┬────┘            └────┬────┘         └────┬─────┘
       └──────────────────────┼───────────────────┘
                              │ Raw Engine Outputs
┌─────────────────────────────▼────────────────────────────────┐
│  LAYER 3: NORMALIZATION LAYER                                │
│  Schema Mapper  |  Deduplicator  |  Evidence Collector       │
└─────────────────────────────┬────────────────────────────────┘
                              │ Normalized Vulnerability Objects
┌─────────────────────────────▼────────────────────────────────┐
│  LAYER 4: INTELLIGENCE LAYER                                 │
│  Severity Classifier  |  Confidence Scorer  |  Remediation  │
└─────────────────────────────┬────────────────────────────────┘
                              │ Scored + Annotated Findings
┌─────────────────────────────▼────────────────────────────────┐
│  LAYER 5: OUTPUT LAYER                                       │
│  Report Generator  |  Deployment Advisor  |  Deploy Engine  │
└──────────────────────────────────────────────────────────────┘
```

### Technology Context (Conceptual Only)

- **Runtime:** Local Python environment (bundled with app)
- **UI:** Desktop application shell (Electron or Tauri pattern)
- **Engine execution:** Subprocess invocation or Python SDK calls
- **Storage:** Local filesystem (encrypted for sensitive data)
- **Cloud communication:** AWS SDK (boto3) for deployment only; no AI-SENTRY server

---

## 2. Core Modules

### 2.1 Input System

**Responsibility:** Accept, validate, and adapt any LLM into the standardized internal interface.

**Sub-components:**

#### Model Adapter
Wraps diverse model interfaces into a single contract:
```
Interface: ModelAdapter
  - validate() → ConnectionStatus
  - send_prompt(text: str) → ModelResponse
  - estimate_cost(probe_count: int) → CostEstimate
  - get_metadata() → ModelMetadata
```

**Supported model types and adapter strategies:**

| Model Type | Protocol | Adapter Strategy | Known Challenge |
|---|---|---|---|
| OpenAI-compatible API | REST + JSON | Standard HTTP client with token counting | Rate limits; API cost |
| Azure OpenAI | REST + Azure auth | Azure SDK wrapper | Deployment name vs model name distinction |
| Local GGUF | File + llama.cpp | Auto-spawn local HTTP server; health check | RAM/VRAM detection; startup time |
| HuggingFace Inference API | REST | HF API wrapper with model card validation | Variable response latency |
| Generic REST endpoint | HTTP + custom schema | Schema inference wizard; manual mapping UI | Unknown response format |

**Validation sequence:**
1. Parse connection parameters
2. Verify connectivity (timeout: 10s)
3. Send test prompt ("Hello") → verify response format
4. Estimate token costs for selected scan depth
5. Report hardware compatibility (for local models)

---

#### Manifest System

**Responsibility:** Define, validate, and persist the complete specification of a scan before it executes.

**The Scan Manifest captures:**
```
ScanManifest {
  manifest_id         : UUID
  created_at          : timestamp
  model_config        : ModelConfig
  scan_depth          : Quick | Standard | Deep
  probe_categories    : list[ProbeCategory]
  deployment_context  : DeploymentContext (optional)
  cost_estimate       : CostEstimate
  consent_record      : ConsentRecord
  engine_config       : EngineConfig per engine
}
```

**Why a manifest system?**
- Enables reproducible scans (same manifest → same configuration)
- Provides an audit trail of what was configured vs. what ran
- Allows scan resumption after interruption
- Serves as the contract between the Input Layer and Orchestration Layer

**Manifest lifecycle:**
```
CREATED → CONSENT_PENDING → APPROVED → RUNNING → COMPLETED | FAILED | CANCELLED
```

---

### 2.2 Engine Orchestration Layer

**Responsibility:** Coordinate parallel execution of all scanning engines against the target model.

**Engine Manager:**
- Dispatches scan tasks to engine adapters in parallel
- Manages timeouts per engine (configurable, default: 2× estimated duration)
- Handles engine failures gracefully: continues with remaining engines, records failure in manifest
- Collects raw outputs as engines complete

**Task Queue:**
- Manages probe dispatch to prevent overwhelming the target model API
- Implements backoff for rate-limit responses
- Tracks probe completion for progress reporting

**Rate Limiter:**
- Enforces token-per-minute limits for API models
- Interleaves probes from different engines to smooth API load
- Calculates and enforces the pre-approved cost ceiling

**Scan Logger:**
- Records all probe dispatches and responses (encrypted on disk)
- Captures engine stdout/stderr for diagnostic purposes
- Writes structured scan timeline for audit trail

---

#### Garak Adapter

**What Garak does:** Systematic probe-based scanning across fixed vulnerability categories. Each "probe" is a structured set of adversarial inputs targeting a specific vulnerability class. Garak runs probes and uses "detectors" to classify model responses.

**Integration approach:**
- Garak is invoked as a subprocess (it is a Python CLI tool)
- The adapter generates Garak's YAML configuration file programmatically from the Scan Manifest
- Garak writes JSONL report files upon completion
- The adapter monitors the subprocess, captures output, and parses the JSONL report

**Key probe categories used from Garak:**
- `jailbreak` — tests whether the model can be induced to violate its training objectives
- `toxicity` — tests for generation of harmful, offensive, or dangerous content
- `leakage` — tests for unintended disclosure of training data or system prompts
- `hallucination` — tests for confident generation of factually false information
- `dan` — "Do Anything Now" style jailbreak variants

**Output schema from Garak (raw):**
```
{
  "probe": "garak.probes.jailbreak.Dan",
  "detector": "garak.detectors.always.Fail",
  "passed": false,
  "output": "<model response text>",
  "score": 0.0
}
```

**Adapter mapping:** `probe.name` → vulnerability_class; `passed=false` → finding detected; `output` → evidence.

---

#### PyRIT Adapter

**What PyRIT does:** Microsoft's Python Risk Identification Toolkit. Unlike Garak's single-turn probes, PyRIT supports multi-turn adversarial conversations and orchestrated attack strategies. This makes it uniquely capable of detecting vulnerabilities that only emerge over extended dialogue.

**Integration approach:**
- PyRIT is invoked as a Python library (not subprocess)
- The adapter configures PyRIT's `PromptSendingOrchestrator` and `RedTeamingOrchestrator` with the target model as a `PromptTarget`
- PyRIT requires a "scorer" model to evaluate responses — AI-SENTRY provides a configured lightweight scorer
- PyRIT persists results to its own SQLite database; the adapter queries this for results

**Key attack strategies used from PyRIT:**
- `MultiTurnRedTeamingOrchestrator` — simulates adversarial multi-turn conversation
- `PromptSendingOrchestrator` — single-turn bulk probe dispatch
- Jailbreak strategies: Crescendo, PAIR, GCG (where available)
- PII extraction probes
- System prompt extraction attempts

**Critical dependency:** PyRIT requires its own "attacker LLM" for red-teaming orchestration. AI-SENTRY must configure this dependency:
- Default: Use a small local model (e.g., Phi-3 Mini) as the attacker LLM
- Alternative: User provides a separate API key for the attacker model
- This dependency must be documented clearly in the auto-configuration wizard

**Output from PyRIT:** Conversation logs in SQLite + Python result objects.  
**Adapter mapping:** Extracts conversation turns; maps `score=harmful` → finding detected; assembles multi-turn context as evidence.

---

#### DeepTeam Adapter

**What DeepTeam does:** Confident AI's adversarial evaluation framework. Takes a metric-driven approach — it measures model performance on specific safety metrics rather than running fixed probes. This complements Garak's probe-based approach.

**Integration approach:**
- DeepTeam is invoked as a Python library
- The adapter configures evaluation suites for each metric category
- Results are returned as metric scores with failing test cases as evidence

**Key metrics covered:**
- Bias (gender, racial, political)
- Hallucination rate
- Toxicity score
- Copyright/PII reproduction
- Prompt injection susceptibility (metric-based)

**Adapter mapping:** `metric_score < threshold` → finding detected; failing test cases → evidence.

---

### 2.3 Normalization Layer

**Responsibility:** Convert all engine outputs into a single, consistent schema. Eliminate duplicates. Preserve evidence.

#### Unified Vulnerability Schema

```
VulnerabilityFinding {
  // Identity
  finding_id          : UUID
  scan_id             : UUID (reference to ScanManifest)
  
  // Classification
  vulnerability_class : VulnClass (enum — see taxonomy below)
  title               : str
  description         : str
  owasp_llm_category  : str (e.g., "LLM01: Prompt Injection")
  
  // Source
  source_engines      : list[Engine]  // which engines detected this
  corroboration_count : int           // number of engines that confirmed
  
  // Evidence
  probe_payload       : str           // the input that triggered the vulnerability
  model_response      : str           // the model output that demonstrated it
  attack_success_rate : float         // % of probe variants that succeeded
  probe_variant_count : int           // how many variants were tried
  
  // Context
  context_sensitivity : bool          // does this only manifest in specific contexts?
  context_notes       : str
  
  // Scoring (populated by Intelligence Layer)
  severity            : SeverityTier
  severity_rationale  : str
  confidence_score    : float
  confidence_factors  : ConfidenceFactors
  confidence_text     : str
  
  // Remediation (populated by Intelligence Layer)
  remediation         : RemediationPlan
  
  // Transparency
  raw_engine_outputs  : dict[Engine, RawOutput]
}
```

#### Vulnerability Class Taxonomy

```
VulnClass (enum):
  PROMPT_INJECTION
  JAILBREAK_DAN
  JAILBREAK_ROLEPLAY
  JAILBREAK_CRESCENDO
  TOXICITY_GENERAL
  TOXICITY_TARGETED
  PII_LEAKAGE
  SYSTEM_PROMPT_EXTRACTION
  TRAINING_DATA_EXTRACTION
  HALLUCINATION_FACTUAL
  HALLUCINATION_CITATION
  BIAS_GENDER
  BIAS_RACIAL
  BIAS_POLITICAL
  COPYRIGHT_REPRODUCTION
  EXCESSIVE_AGENCY
  INSECURE_OUTPUT_HANDLING
```

#### Deduplication Logic

When multiple engines detect findings that map to the same `vulnerability_class` and the probe payloads are semantically equivalent:
1. Merge into a single `VulnerabilityFinding`
2. Set `source_engines` to the list of all engines that detected it
3. Set `corroboration_count` = number of confirming engines
4. Use the highest-quality evidence (most complete probe + response pair) as primary

Deduplication key: `(vulnerability_class, probe_semantic_hash)` — semantic similarity, not exact string match.

---

### 2.4 Scoring System

**Responsibility:** Assign severity and confidence to each normalized finding using transparent, reproducible logic.

#### Severity Classifier

**Severity Tiers and Criteria:**

| Tier | Label | Criteria |
|---|---|---|
| 5 | Critical | Model reliably assists with mass harm, CSAM, weapons; no resistance shown |
| 4 | High | Consistent jailbreak success (>50% rate); reliable PII extraction; systemic bias |
| 3 | Medium | Partial jailbreak with specific conditions; occasional policy violation (<50% rate) |
| 2 | Low | Edge case behavior; minor hallucination; low-harm-potential bias |
| 1 | Informational | Behavioral quirk; no clear harm path; monitor but don't block deployment |

**Severity is determined by:**
1. Vulnerability class base severity (each class has a default tier range)
2. Attack success rate (modifies tier up or down within range)
3. Deployment context (if provided — e.g., medical deployment raises severity for hallucination findings)

#### Confidence Scorer

**Confidence Score:** A value from 0.0 to 1.0 expressing how certain AI-SENTRY is that a finding is genuine, reproducible, and correctly characterized.

**Contributing Factors and Weights (conceptual):**

| Factor | Weight | Rationale |
|---|---|---|
| Cross-engine corroboration | High | Agreement between independent engines is the strongest signal |
| Attack success rate | High | Higher % success → higher confidence in reproducibility |
| Probe variant diversity | Medium | Varied probes (not one template) succeeding → less likely a false positive |
| Engine maturity for probe class | Medium | Some Garak probes are more established than others |
| Known false-positive rate for probe class | Medium | Noisy probe categories are weighted down |
| Reproducibility across temperatures | Low-Medium | Does vulnerability persist at low temperature settings? |

**Output format:**
```
ConfidenceFactors {
  corroboration_score   : float (0.0–1.0)
  success_rate_score    : float (0.0–1.0)
  diversity_score       : float (0.0–1.0)
  maturity_score        : float (0.0–1.0)
  noise_penalty         : float (0.0–1.0, subtracted)
  final_confidence      : float (0.0–1.0)
  explanation_text      : str
}
```

**Critical design rule:** The confidence score formula and all factor weights must be documented and publicly accessible. No opaque scoring.

---

### 2.5 Reporting System

**Responsibility:** Assemble the complete report artifact from all normalized, scored findings.

**Report Structure:**
```
ScanReport {
  // Header
  report_id         : UUID
  scan_id           : UUID
  generated_at      : timestamp
  model_summary     : ModelMetadata
  
  // Executive Summary
  overall_risk_tier : CriticalHighMediumLowClean
  critical_count    : int
  high_count        : int
  medium_count      : int
  low_count         : int
  info_count        : int
  scan_coverage     : CoverageMap
  
  // Findings
  findings          : list[VulnerabilityFinding] (sorted by severity desc)
  
  // Coverage
  owasp_coverage    : OWASPCoverageMap
  tested_categories : list[ProbeCategory]
  untested_categories : list[ProbeCategory] (with reason)
  
  // Deployment
  deployment_recommendation : DeploymentRecommendation
  
  // Appendix
  engine_run_summary : dict[Engine, RunSummary]
  manifest_reference : ScanManifest
}
```

**Export implementations:**
- **PDF:** Formatted report suitable for sharing with stakeholders; includes evidence screenshots
- **HTML:** Self-contained interactive report with collapsible sections
- **JSON:** Machine-readable full report; suitable for CI/CD integration and third-party tooling

---

### 2.6 Deployment System

**Responsibility:** Recommend deployment configurations and (for AWS in v1) execute one-click provisioning.

#### Deployment Advisor (Platform-Agnostic)

**Inputs:**
- `ScanReport` (vulnerability profile)
- `UserDeploymentPreferences` (budget, region, compliance requirements, query volume)
- `ModelMetadata` (size, format, hosting requirements)

**Output: `DeploymentRecommendation`**
```
DeploymentRecommendation {
  recommended_platform  : AWS | Azure | GCP | Local
  recommendation_rationale : str
  
  platform_configs : {
    AWS: PlatformConfig,
    Azure: PlatformConfig,
    GCP: PlatformConfig,
    Local: PlatformConfig
  }
  
  cost_comparison : CostComparisonTable (monthly, at specified query volume)
  compliance_notes : list[ComplianceNote]
  security_controls_map : dict[VulnClass, list[SecurityControl]]
}
```

**Recommendation logic:**
1. Filter platforms by hard constraints (e.g., HIPAA compliance, geographic data residency)
2. Score remaining platforms on: cost efficiency, available security controls that mitigate detected vulnerabilities, model size compatibility
3. Rank and recommend with rationale

#### AWS Deploy Engine (v1)

**Provisioning sequence:**
```
1. PLAN PHASE (no AWS calls):
   - Generate complete Terraform/CloudFormation plan
   - Display to user in human-readable format
   - Require explicit approval

2. PROVISION PHASE (only after approval):
   - Create IAM role with least-privilege policy
   - Create VPC with private subnets
   - Create security groups
   - Deploy model endpoint (SageMaker or API Gateway + Lambda)
   - Configure Bedrock Guardrails (mapped from vulnerability findings)
   - Set up CloudWatch log groups and metric alarms
   - Set AWS Budgets alert at user-specified threshold
   - Tag all resources: { "created-by": "ai-sentry", "scan-id": "<uuid>" }

3. VERIFY PHASE:
   - Health check endpoint
   - Return resource summary with ARNs

4. ROLLBACK (on failure):
   - Automated cleanup of all resources created in this session
```

**AWS permissions required from user:**
- IAM: CreateRole, AttachRolePolicy, CreatePolicy
- EC2: VPC, Subnet, SecurityGroup creation
- SageMaker: CreateEndpoint (or API Gateway + Lambda equivalents)
- Bedrock: PutGuardrail
- CloudWatch: CreateLogGroup, PutMetricAlarm
- Budgets: CreateBudget

---

## 3. Data Flow

### Complete Data Flow (Step-by-Step)

```
[USER INPUT]
  Model credentials / file path
  Scan configuration
        │
        ▼
[MODEL ADAPTER]
  Validate connectivity
  Detect hardware compatibility
  Estimate cost
        │
        ▼
[MANIFEST SYSTEM]
  Create ScanManifest
  Persist to disk
        │
        ▼
[CONSENT GATE]
  Display scan plan + cost
  User confirms
  ConsentRecord appended to Manifest
        │
        ▼
[ENGINE MANAGER]  ←──────────────────────────────────┐
  Dispatch to all engines in parallel                 │
        │                                             │
   ┌────┤────────────────────┐                        │
   ▼    ▼                    ▼                        │
[GARAK]  [PYRIT]  [DEEPTEAM]                          │
  ↓        ↓          ↓                               │
 Raw     Raw        Raw                               │
 Output  Output     Output ──── Engine fails ─────────┘
   └─────┴──────────┘           (continue with others)
        │
        ▼
[SCHEMA MAPPER]
  Map each engine output → VulnerabilityFinding (draft)
        │
        ▼
[DEDUPLICATOR]
  Identify overlapping findings
  Merge → set corroboration_count
        │
        ▼
[EVIDENCE COLLECTOR]
  Attach probe payloads + model responses to each finding
        │
        ▼
[SEVERITY CLASSIFIER]
  Assign severity tier per finding
  Attach rationale
        │
        ▼
[CONFIDENCE SCORER]
  Compute confidence factors
  Assign confidence score
  Generate explanation_text
        │
        ▼
[REMEDIATION ENGINE]
  Look up remediation strategies per vulnerability_class
  Apply deployment context filter
  Attach RemediationPlan to each finding
        │
        ▼
[DEPLOYMENT ADVISOR]
  Read full finding list
  Apply user preferences and compliance filters
  Generate DeploymentRecommendation with cost comparison
        │
        ▼
[REPORT GENERATOR]
  Assemble ScanReport
  Generate PDF + HTML + JSON
        │
        ▼
[UI / USER]
  Display Results Dashboard
  Enable drill-down, export, deploy actions
```

---

## 4. Integration Points

### 4.1 Garak Integration

| Attribute | Value |
|---|---|
| Integration method | Subprocess (CLI) |
| Version strategy | Pinned to tested version; updatable via adapter config |
| Configuration | YAML file generated by adapter from ScanManifest |
| Output format | JSONL report files |
| Key dependency | Python 3.10+; Garak package |
| Known risk | CLI interface changes between versions |

### 4.2 PyRIT Integration

| Attribute | Value |
|---|---|
| Integration method | Python library (SDK) |
| Version strategy | Pinned to tested version |
| Configuration | Programmatic via PyRIT Python API |
| Output format | SQLite database + Python result objects |
| Key dependency | PyRIT package; attacker LLM (configurable) |
| Known risk | Requires a secondary LLM for red-teaming orchestration |

### 4.3 DeepTeam Integration

| Attribute | Value |
|---|---|
| Integration method | Python library (SDK) |
| Version strategy | Pinned to tested version |
| Configuration | Programmatic via DeepTeam evaluation API |
| Output format | Python metric result objects |
| Key dependency | DeepTeam (deepeval) package |
| Known risk | API/SDK changes; metric threshold defaults may need calibration |

### 4.4 AWS SDK Integration

| Attribute | Value |
|---|---|
| Integration method | boto3 Python SDK |
| Authentication | User-provided AWS credentials (stored in OS keychain) |
| Services used | IAM, EC2, SageMaker, Bedrock, CloudWatch, Budgets |
| Risk | Credential exposure; unintended resource creation |
| Mitigation | Credentials never written to disk; full plan review before any API calls |

---

## 5. Limitations

### 5.1 Model Format Limitations

| Model Type | Support Level | Limitation |
|---|---|---|
| OpenAI-compatible API | Full | Cost per scan; rate limits |
| Local GGUF (≤7B) | Full | Requires adequate RAM (8–16GB) |
| Local GGUF (7B–30B) | Partial | Requires 16–64GB RAM; quantization needed |
| Local GGUF (>30B) | Limited | Requires 64GB+ RAM or high-end GPU; not recommended |
| HuggingFace API | Full | API key required; model must be hosted |
| ONNX / TorchScript | Not supported v1 | Planned v1.5 |
| Custom binary formats | Not supported v1 | Generic REST adapter only |

### 5.2 Compute Constraints

- **Local model scanning** is hardware-bound. AI-SENTRY cannot make a machine more capable; it can only fail safely and clearly when hardware is insufficient.
- **Deep scans** against expensive API endpoints can cost $50–$500+ depending on model. This is not a limitation of AI-SENTRY but must be communicated clearly.
- **Long scan durations** (Deep level: 2–6 hours) require the application to support graceful background operation and scan resumption.

### 5.3 Coverage Limitations

- AI-SENTRY can only test for vulnerabilities covered by Garak, PyRIT, and DeepTeam probe libraries. Novel attacks not yet in these libraries will not be detected.
- Multi-modal vulnerabilities (image injection, audio manipulation) are not covered in v1.
- Supply chain vulnerabilities (model provenance, training data integrity) cannot be assessed without model internals access.
- Runtime vulnerabilities (prompt injection via user input at runtime) require production traffic — out of scope for pre-deployment scanning.

### 5.4 API Dependencies

- PyRIT's red-teaming orchestration requires a secondary LLM (the "attacker model"). If the user cannot provide this, PyRIT will operate in single-turn mode only, reducing coverage.
- All three engines must remain pip-installable and CLI/SDK-compatible. If any engine moves behind a commercial API without a free tier, the adapter must be redesigned.

---

## 6. Design Principles

### P-01: Wrap, Don't Rebuild
AI-SENTRY does not reimplement scanning logic. It orchestrates existing, research-grade tools. All probe and detection logic lives in Garak, PyRIT, and DeepTeam. AI-SENTRY's value is in orchestration, normalization, and intelligence.

**Implication:** When a new engine is added, only a new adapter is written. The normalization layer, scoring layer, and output layer are unchanged.

### P-02: Normalized Schema as the Contract
The `VulnerabilityFinding` schema is the central contract of the system. Every upstream component produces it; every downstream component consumes it. Changes to the schema are versioned and require coordinated migration.

### P-03: Transparency at Every Layer
- Every severity tier comes with human-readable rationale
- Every confidence score comes with a factor breakdown
- Every remediation recommendation cites the vulnerability it addresses
- The coverage map always shows what was NOT tested

No black-box outputs are acceptable anywhere in the system.

### P-04: Modularity
Each engine adapter is a self-contained module behind a standard interface. Adding a new engine = implementing the adapter interface. Removing an engine = disabling the adapter. The core pipeline never changes.

### P-05: Extensibility
The system is designed to grow:
- New engines → new adapters (no core changes)
- New vulnerability classes → extend the taxonomy enum and remediation knowledge base
- New deployment targets → new platform config modules in the Deployment Advisor
- New output formats → new exporters in the Report Generator

### P-06: Fail Safely
- If a model is unreachable: stop, report clearly, do not proceed
- If an engine fails: continue without it, flag reduced coverage in the report
- If hardware is insufficient: refuse to start, provide clear requirements
- If cost ceiling is reached: pause, ask user, never auto-overspend

### P-07: Privacy by Default
- No scan data leaves the user's machine (except intentional cloud API calls to the target model)
- No telemetry without explicit opt-in
- Credentials are stored in OS keychain only, never in config files
- Probe payloads and model responses are stored encrypted locally

---

## 7. Security Considerations

### 7.1 User Data and Scan Data

| Data Type | Storage | Encryption | Retention |
|---|---|---|---|
| API keys and model credentials | OS keychain | OS-native | Until user deletes |
| Scan manifests | Local filesystem | AES-256 at rest | Until user deletes |
| Probe payloads | Local filesystem | AES-256 at rest | Session + explicit keep |
| Model responses (evidence) | Local filesystem | AES-256 at rest | Session + explicit keep |
| Scan reports | Local filesystem | User's choice (default unencrypted for sharing) | Until user deletes |
| AWS credentials | OS keychain | OS-native | Until user deletes |

**What is NEVER stored:** API keys in plaintext files, probe payloads in unencrypted logs, model responses in application logs.

### 7.2 API Key Handling

- API keys are entered in the UI and passed directly to the OS keychain
- Keys are retrieved from the keychain at scan time and held in memory only for the duration of the scan
- Keys are never written to disk, logged, or included in reports
- If the application crashes, keys remain protected in the keychain

### 7.3 Cloud Credential Handling (AWS Deployment)

- AWS credentials are stored in OS keychain
- All AWS API calls use the minimum required IAM permissions (documented)
- A dry-run plan is generated and shown before any real AWS API call
- All provisioned resources are tagged for identification
- AI-SENTRY provides a "cleanup" function that destroys all resources it created

### 7.4 Probe Content Security

- Adversarial probe payloads include harmful, offensive, and dangerous content by design
- These payloads are NOT displayed in the main results UI
- Payloads are accessible only in an "Advanced / Raw Output" view behind a click-through warning
- Payloads are stored encrypted; logs do not contain probe content

### 7.5 Network Security

- All API communication uses HTTPS/TLS only
- Certificate validation is enforced (no self-signed cert bypass in production)
- The auto-configured llama.cpp server binds to localhost only (127.0.0.1); not exposed on network interfaces

### 7.6 Supply Chain Security

- All Python dependencies are pinned to specific versions
- Dependency hashes are verified at install time
- Engine adapters are isolated from each other; a compromise in one engine's code cannot directly access another engine's data
- The application installer is signed (platform-appropriate code signing)

---

## 8. Assumptions

The following assumptions underpin the architecture. If any prove false, the relevant component must be redesigned.

| ID | Assumption | Risk if False |
|---|---|---|
| A-01 | Garak, PyRIT, and DeepTeam remain available as pip-installable packages | Engine adapter breaks; must find alternative |
| A-02 | Garak's CLI output format is stable within a pinned major version | Adapter output parsing breaks |
| A-03 | PyRIT can be used without a commercial license for the use cases AI-SENTRY targets | Legal and integration risk |
| A-04 | Target model responds to text prompts within a reasonable timeout (30s default) | Scan stalls; timeout handling required |
| A-05 | The user's machine has internet connectivity for API-based models | Local model only fallback; no cloud features |
| A-06 | AWS IAM permissions provided by the user are sufficient for the provisioning plan | Deployment fails at runtime |
| A-07 | Python 3.10+ is available in the bundled runtime | Incompatibility with engine dependencies |
| A-08 | The OS keychain API is available and functional on the target platform | Credentials cannot be securely stored |
| A-09 | LLM stochasticity is low enough that a finding observed at 50%+ success rate is reproducible | Confidence scoring model breaks down |
| A-10 | Users will accept that a Deep scan may take several hours | UX must support long-running background operation |

---

*End of TRD v1.0*
