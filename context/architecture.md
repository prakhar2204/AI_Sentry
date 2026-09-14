# AI-SENTRY — Architecture Reference

**Last Updated:** 2026-09-13  
**Phase:** 0b — Documentation Foundation  
**Status:** Conceptual — No implementation yet

---

## Architectural Style

**Layered Pipeline Architecture** — unidirectional data flow, strict layer separation, no backward calls.

Each layer has one responsibility. Layers communicate only downward through defined interfaces.

---

## The Five Layers

```
LAYER 1: INPUT
  Model Adapter | Manifest System | Consent Gate
         ↓
LAYER 2: ORCHESTRATION
  Engine Manager | Task Queue | Rate Limiter | Logger
         ↓
  ┌──────┬──────────┬──────────┐
  ↓      ↓          ↓          
GARAK  PYRIT    DEEPTEAM   (engine adapters — parallel)
  └──────┴──────────┴──────────┘
         ↓
LAYER 3: NORMALIZATION
  Schema Mapper | Deduplicator | Evidence Collector
         ↓
LAYER 4: INTELLIGENCE
  Severity Classifier | Confidence Scorer | Remediation Engine
         ↓
LAYER 5: OUTPUT
  Report Generator | Deployment Advisor | AWS Deploy Engine
```

---

## Core Data Objects

### ScanManifest
The contract for a scan. Created before execution. Persisted to disk.
- Fields: manifest_id, model_config, scan_depth, probe_categories, cost_estimate, consent_record
- Lifecycle: CREATED → CONSENT_PENDING → APPROVED → RUNNING → COMPLETED|FAILED|CANCELLED

### VulnerabilityFinding
The central normalized data object. Produced by Normalization, enriched by Intelligence, consumed by Output.
- Fields: finding_id, vulnerability_class, source_engines, corroboration_count, probe_payload, model_response, attack_success_rate, severity, confidence_score, confidence_factors, remediation
- Schema version: 1.0 (any changes are versioned)

### ScanReport
The final assembled output artifact.
- Fields: overall_risk_tier, finding counts, findings list, OWASP coverage map, deployment_recommendation, engine run summaries

---

## Engine Integration Strategy

| Engine | Method | Output | Key Dependency |
|---|---|---|---|
| Garak | Subprocess (CLI) | JSONL files | Garak Python package (pinned) |
| PyRIT | Python SDK | SQLite + objects | PyRIT package + attacker LLM |
| DeepTeam | Python SDK | Metric result objects | deepeval package (pinned) |

**Version pinning is mandatory for all three engines.**

---

## Model Adapter Interface

All model types are abstracted behind:
```
ModelAdapter:
  validate() → ConnectionStatus
  send_prompt(text) → ModelResponse
  estimate_cost(probe_count) → CostEstimate
  get_metadata() → ModelMetadata
```

Supported types: OpenAI-compatible API, Azure OpenAI, Local GGUF (via llama.cpp), HuggingFace API, Generic REST.

---

## Confidence Scoring Formula (Conceptual)

Score (0.0–1.0) based on weighted combination of:
- Cross-engine corroboration (highest weight)
- Attack success rate
- Probe variant diversity
- Engine maturity for probe class
- Known false-positive rate for probe class (penalty)

All weights and factors are documented and exposed to users. No opaque scoring.

---

## Security Architecture

- **Credentials:** OS keychain only — never plaintext files
- **Probe content:** Encrypted at rest; not displayed in main UI
- **Network:** HTTPS only; TLS enforced; no self-signed cert bypass
- **Local server:** llama.cpp binds to localhost (127.0.0.1) only
- **AWS provisioning:** Full plan shown before any API call; all resources tagged

---

## Deployment Advisory Architecture

**Input:** ScanReport + UserPreferences  
**Logic:** Filter by constraints → Score platforms → Rank → Recommend with rationale  
**Output:** Platform configs for AWS/Azure/GCP/Local + cost comparison + compliance notes

**AWS Deploy Sequence:** PLAN (no API calls) → User Approves → PROVISION → VERIFY → ROLLBACK on failure

---

## Key Design Decisions

(See `context/decisions.md` for full decision log)

1. Desktop-first (not SaaS) — privacy, local model support, no server infrastructure in v1
2. Wrap, don't rebuild — orchestrate existing engines, don't reimplement probe logic
3. Unified schema as central contract — all components agree on VulnerabilityFinding
4. Severity ≠ Confidence — two separate axes, never collapsed into one score
5. AWS-first deployment — validate one platform deeply before adding others
