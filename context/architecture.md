# Sentryɸ — Architecture Reference

**Last Updated:** 2026-11-02  
**Phase:** 3 — Engine Adapters Complete (Garak & PyRIT)  
**Status:** Phases 1-3 complete (Garak B1-B6 + T2-T4, PyRIT P1-P6; 148 tests passing)

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
  ┌──────┬──────────┐
  ↓      ↓          
GARAK  PYRIT     (engine adapters — parallel)
  └──────┴──────────┘
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

**Note:** DeepTeam was removed from the engine set (D-018). Garak is the primary engine; PyRIT is planned for future integration.

---

## Core Data Objects

### ScanManifest
The contract for a scan. Created before execution. Persisted to disk.
- Fields: manifest_id, model_config, scan_depth, probe_categories, cost_estimate, consent_record
- Lifecycle: CREATED → CONSENT_PENDING → APPROVED → RUNNING → COMPLETED|FAILED|CANCELLED

### VulnerabilityFinding
The central normalized data object. Produced by engine adapters, enriched by Intelligence, consumed by Output.
- Fields: finding_id, engine, category, probe, detector, passed, failed, total, pass_rate, severity, confidence, raw_eval
- Schema version: 1.0 (any changes are versioned)
- Currently defined in `core/garak_engine.py` — will move to `core/schema.py` in Phase 4

### GarakScanResult
Aggregate result from a full GarakEngine.run() call.
- Fields: run_id, target_url, started_at, finished_at, categories, probe_results, findings, all_ok, errors

### PyRITScanResult
Aggregate result from a full PyRITEngine.run() call.
- Fields: run_id, target_url, started_at, finished_at, categories, attack_results, findings, all_ok, errors

### ScanReport
The final assembled output artifact.
- Fields: overall_risk_tier, finding counts, findings list, OWASP coverage map, deployment_recommendation, engine run summaries

---

## Garak Engine Integration (Phase 3 — Implemented)

### Integration Model

Garak is invoked as an **external subprocess** (`python -m garak`), NOT as a Python library import. This is by design:
- Garak modifies global state on import (logging, config singletons)
- Subprocess isolation prevents garak internals from affecting AI-SENTRY
- Consistent with garak's own recommended usage (CLI-first tool)

### How It Works

```
1. AI-SENTRY writes a temporary YAML config file:
   plugins.generators.rest.RestGenerator:
     uri: <target_url>
     method: post
     response_json: true
     response_json_field: "$.choices[0].message.content"
     req_template: "$INPUT"

2. For each probe spec, runs:
   python -m garak --target_type rest --config <yaml> --spec <probe_spec> --generations 1

3. Garak produces a JSONL report file (one per run)

4. AI-SENTRY parses the JSONL, extracts `eval` and `attempt` records,
   and maps them into VulnerabilityFinding objects
```

### JSONL Report Structure (Observed from garak 0.17.0)

| entry_type | Purpose | Key Fields |
|---|---|---|
| `start_run setup` | Full config snapshot | run_id, config_files, target_type, probe_spec |
| `init` | Run metadata | garak_version, start_time, run (UUID) |
| `plugin_cache` | Loaded plugin info | run, plugin_cache |
| `attempt` | Individual probe attempt | uuid, probe_classname, prompt, outputs, detector_results, goal, intent |
| `eval` | Probe evaluation result | probe, detector, passed, fails, total_evaluated, intents |
| `probe_summary` | Per-probe aggregate | probe, inference_counts, detection_counts |
| `completion` | Run end marker | end_time, run |
| `digest` | Full run summary | meta, eval (scores by probe group), technique_intent_matrix |

**Finding extraction:** A finding exists when `eval.fails > 0`. Evidence is linked via matching `probe_classname` in `attempt` records.

### Category-to-Probe Mapping (21 probes, 6 categories)

| AI-SENTRY Category | Garak Probes |
|---|---|
| prompt_injection | promptinject.HijackHateHumans, HijackKillHumans, HijackLongPrompt |
| jailbreak | dan.Ablation_Dan_11_0, dan.AutoDANCached, dan.DanInTheWild |
| encoding_injection | encoding.InjectBase64, InjectROT13, InjectHex, InjectMorse |
| data_leakage | leakreplay.GuardianCloze, GuardianComplete, sysprompt_extraction.SystemPromptExtraction |
| malware_generation | malwaregen.Evasion, Payload, SubFunctions, TopLevel |
| toxicity | continuation.ContinueSlursReclaimedSlurs, lmrc.Bullying, lmrc.SlurUsage, grandma.Slurs |

### Depth Profiles

| Depth | Probes per Category | Total Probes |
|---|---|---|
| quick | 1 | 6 |
| standard | 2 | 12 |
| deep | all | 21 |

### Severity Derivation

Severity (1-5) is derived from the attack success rate and probe tier:
- severity=1 (Informational): attack_rate=0 (all attempts passed)
- severity=2-5: scaled from attack success rate and the probe's inherent risk tier

### Confidence Derivation

Confidence (0.0-1.0) is derived from sample size:
- <3 samples: 0.25
- 3-9 samples: 0.45
- 10-29 samples: 0.65
- 30-99 samples: 0.85
- 100+ samples: 1.0

---

## PyRIT Engine Integration (Phase 3 — Implemented)

### Integration Model

PyRIT is invoked directly via the **Python SDK** (`pyrit==1.1.0`), using isolated in-memory storage:
- `initialize_pyrit_async(memory_db_type=IN_MEMORY)` guarantees zero cross-scan state and no temporary database files.
- `OpenAIChatTarget(endpoint=..., api_key=..., model_name=...)` connects to any OpenAI-compatible target.
- Attacks are dispatched asynchronously via `PromptNormalizer.send_prompt_async()`.
- Scoring uses deterministic offline scorers (`SubStringScorer`, regex, refusal) to avoid secondary LLM dependency (D-Q2).

### Category-to-Attack Mapping (12 attack specs across 6 categories)

- **prompt_injection**: System prompt leak prompt, instruction override prompt
- **jailbreak**: Classic developer mode, hypothetical scenario bypass
- **encoding_injection**: Base64 obfuscated payload, ROT13 obfuscated payload
- **data_leakage**: PII exfiltration probe, API key extraction probe
- **malware_generation**: Reverse shell generation probe, keylogger generation probe
- **toxicity**: Hate speech generation probe, harassment probe (fills Garak `lmrc.Bullying` gap)

### Depth Profiles

- `quick`: 1 attack spec per category (6 total)
- `standard`: 2 attack specs per category (12 total)
- `deep`: all attack specs

---

## Engine Integration Strategy

| Engine | Method | Output | Status |
|---|---|---|---|
| Garak | Subprocess (CLI) | JSONL files | **IMPLEMENTED** (Phase 3, garak 0.17.0) |
| PyRIT | Python SDK | In-memory SQLite + `VulnerabilityFinding` | **IMPLEMENTED** (Phase 3, pyrit 1.1.0) |
| Agent-Guardian | TBD | TBD | **DEFERRED** (Awaiting user definition) |
| DeepTeam | — | — | **DROPPED** (D-018) |

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
6. DeepTeam dropped, Garak primary (D-018) — no paid API key dependency for scanning
7. Garak as subprocess, not library import — isolation from garak's global state modifications
