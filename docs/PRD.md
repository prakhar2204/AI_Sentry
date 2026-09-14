# AI-SENTRY — Product Requirements Document (PRD)

**Document Version:** 1.0  
**Phase:** 0b — Documentation Foundation  
**Status:** Active  
**Last Updated:** 2026-09-13  
**Audience:** Developers, Judges, Stakeholders, AI Tools

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Problem Statement](#2-problem-statement)
3. [Target Users](#3-target-users)
4. [Use Cases](#4-use-cases)
5. [Core Features](#5-core-features)
6. [Non-Goals (v1 Scope Boundaries)](#6-non-goals-v1-scope-boundaries)
7. [User Journey](#7-user-journey)
8. [Constraints](#8-constraints)
9. [Risks](#9-risks)
10. [Success Criteria](#10-success-criteria)

---

## 1. Product Overview

### What Is AI-SENTRY?

AI-SENTRY is a **multi-engine LLM security orchestration platform** delivered as a desktop application. It enables developers, AI engineers, and security teams to:

- Connect any LLM (via API endpoint or local model file)
- Run systematic vulnerability scans using three industry-grade adversarial testing engines simultaneously: **Garak**, **PyRIT**, and **DeepTeam**
- Receive a single, unified, normalized security report with severity and confidence scores
- Get actionable remediation guidance per vulnerability
- Receive deployment architecture recommendations with cost comparisons
- Execute one-click deployment to AWS (v1), with Azure and GCP on the roadmap

### One-Line Description

> *AI-SENTRY is the pre-deployment security gate for LLMs — scan before you ship.*

### Product Positioning

| Dimension | Position |
|---|---|
| Category | LLM Security / AI Red Teaming |
| Delivery | Desktop Application (Windows + Linux) |
| Stage | Pre-deployment (not runtime monitoring) |
| Core Value | Multi-engine orchestration + unified reporting + deployment advisory |
| Pricing Model | Free/open-source tool (v1); SaaS model planned for v2 |

---

## 2. Problem Statement

### The Core Gap

Large Language Models are being deployed into production at a pace that has far outrun the development of practical security tooling. Security practitioners have three good open-source engines (Garak, PyRIT, DeepTeam), but no practical way to:

1. Run all three together without significant setup complexity
2. Compare their results (each uses a different output format and taxonomy)
3. Translate findings into deployment-ready risk mitigation

The result: most teams either test inadequately (one tool, partially) or skip LLM security testing entirely.

### Why This Matters Now

- **Regulatory pressure is increasing.** The EU AI Act, US NIST AI RMF, and emerging sector-specific guidance are beginning to require demonstrable safety assessments for high-risk AI deployments.
- **The attack surface is novel.** LLMs are not vulnerable to traditional code-level exploits — they are vulnerable to semantic manipulation, emergent behavior, and multi-turn context exploitation. Existing security tooling cannot assess this.
- **Business consequences are severe.** An LLM that assists in harmful activities, leaks PII, or produces dangerous outputs creates legal liability, reputational harm, and compliance failures.

### The Gap in Specific Terms

| Current State | Desired State (AI-SENTRY) |
|---|---|
| 3 separate tools with separate setups | One tool that orchestrates all three |
| 3 incompatible output formats | One unified normalized report |
| No cross-engine severity ranking | Transparent severity + confidence scores |
| "Here's what's wrong" — no next step | Remediation guidance + deployment advisory |
| Expert-only tooling | Accessible to any developer |

---

## 3. Target Users

### Primary Personas

#### P1: AI Developer / ML Engineer
- **Profile:** Builds LLM-powered product features; strong Python/ML background; limited security expertise
- **Goal:** Know if their model is "safe enough" before shipping; get clear, actionable results
- **Pain:** Doesn't know which tools to use, how to set them up, or what results mean
- **Trigger:** Pre-launch checklist, security review request from manager

#### P2: AI Security Researcher
- **Profile:** Expert in adversarial ML and red-teaming; needs maximum coverage and data depth
- **Goal:** Comprehensive vulnerability surface analysis; access to raw probes and responses
- **Pain:** Too much time integrating tools; not enough time analyzing results
- **Trigger:** Model evaluation assignment; research paper; client engagement

#### P3: Enterprise Security Team / CISO Office
- **Profile:** Responsible for organizational AI risk posture and compliance
- **Goal:** Standardized, auditable security assessment process for every LLM deployment
- **Pain:** No standardized LLM security audit process exists; existing security tooling doesn't apply
- **Trigger:** AI deployment proposal from engineering; regulatory inquiry; internal policy mandate

#### P4: Startup / Product Team
- **Profile:** Moving fast; deploying LLM features without a dedicated security function
- **Goal:** A single tool that gives a clear pass/fail signal; low friction
- **Pain:** Cannot afford specialized security expertise; needs automation
- **Trigger:** Approaching launch date; investor due diligence; customer trust concern

#### P5: Regulated Industry Practitioner (Healthcare, Finance, Legal)
- **Profile:** Deploying LLMs in high-stakes contexts where errors carry real-world consequences
- **Goal:** Demonstrable, documented due diligence suitable for regulatory review
- **Pain:** Regulators are starting to ask "how did you test this?" with no standard answer
- **Trigger:** Compliance audit; product approval process; procurement security questionnaire

---

## 4. Use Cases

### UC-01: Pre-Launch Jailbreak and Toxicity Scan (P1, P4)
**Scenario:** A startup is launching a customer-service chatbot. The PM asks: "Can users make it say something harmful?"

**Flow:** User inputs OpenAI endpoint → selects Standard scan → approves estimated cost ($12–18) → Garak + PyRIT run → 2 High-severity jailbreaks found with evidence → remediation guide provides system-prompt hardening steps → Deployment Advisor recommends AWS Bedrock with Guardrails.

**Value:** Prevents shipping a model that can be easily manipulated into producing harmful content.

---

### UC-02: Enterprise Model Audit Before Procurement (P3, P5)
**Scenario:** A hospital evaluates an LLM vendor for clinical documentation. CISO needs a formal security assessment.

**Flow:** Security team inputs vendor API endpoint → Deep scan over ~4 hours → Unified PDF report with OWASP LLM Top 10 coverage map → submitted to procurement risk review.

**Value:** Documented, reproducible evidence of security posture suitable for regulatory review.

---

### UC-03: Security Regression After Fine-Tuning (P2, P1)
**Scenario:** Team fine-tuned a base model on proprietary data. Need to know if fine-tuning introduced vulnerabilities.

**Flow:** Scan base model → save report (v1) → scan fine-tuned model → save report (v2) → compare: identifies new High-severity PII extraction risk from fine-tuning data.

**Value:** Catches vulnerabilities introduced during fine-tuning before production.

---

### UC-04: Local Model Assessment (P2)
**Scenario:** Security researcher evaluates a locally-hosted Mistral 7B GGUF before recommending to a client.

**Flow:** User selects Local Model → provides GGUF path → AI-SENTRY spawns llama.cpp server → full scan against localhost → no data leaves machine → full evidence report exported.

**Value:** Complete assessment with zero external API calls or data exposure.

---

### UC-05: Cloud Deployment Advisory (P1, P4)
**Scenario:** Developer has scan results but doesn't know how to securely deploy to cloud.

**Flow:** Deployment Advisor reads vulnerability profile → generates AWS/Azure/GCP comparison → user selects AWS → one-click deploy provisions VPC, SageMaker, Bedrock Guardrails, CloudWatch → user approves plan → done.

**Value:** Secure deployment tailored to the model's specific risk profile, in the same workflow.

---

### UC-06: CI/CD Pipeline Integration (P1, P2) — v1.5 Target
**Scenario:** Team wants automatic LLM security checks on every model update.

**Flow:** AI-SENTRY CLI runs as GitHub Actions step → compares results against configurable threshold → blocks PR if Critical finding detected → security report uploaded as CI artifact.

**Value:** LLM security becomes a mandatory pipeline gate, not an afterthought.

---

## 5. Core Features

### F-01: Universal Model Adapter
Supports: OpenAI-compatible APIs, Azure OpenAI, Local GGUF (auto-managed llama.cpp), HuggingFace Inference API, Generic REST endpoints.  
Provides: unified `send_prompt → response` interface; handles auth, retries, rate limiting.

### F-02: Consent & Safety Gate
Non-bypassable pre-scan screen showing: probe categories, estimated cost, authorization acknowledgment. No scan starts without explicit user confirmation.

### F-03: Multi-Engine Orchestration
Simultaneously runs Garak, PyRIT, DeepTeam with three scan depths:

| Level | Coverage | Duration | Use Case |
|---|---|---|---|
| Quick | Core probes only | 5–15 min | Rapid iteration |
| Standard | Balanced | 30–90 min | Pre-launch |
| Deep | Full suite | 2–6 hours | Enterprise audit |

### F-04: Normalization Layer
Maps all engine outputs to a unified Vulnerability Schema. Deduplicates and merges corroborated findings. Maps to OWASP LLM Top 10.

### F-05: Severity Classification
Tiers: Critical / High / Medium / Low / Informational. Criteria shown alongside every score. Never a black box.

### F-06: Explainable Confidence Scoring
Score (0.0–1.0) per finding with natural-language explanation of contributing factors: cross-engine corroboration, success rate, probe diversity, engine maturity. Reproducible and auditable.

### F-07: Remediation Engine
Per-finding guidance at three levels: model-level (fine-tuning targets), system-level (guardrails, filters), deployment-level (runtime hooks, access controls).

### F-08: Deployment Advisor
Platform recommendation (AWS / Azure / GCP / Local) with architecture specs, security controls mapped to findings, side-by-side cost comparison, compliance notes.

### F-09: Unified Report Generator
Outputs: Executive summary, full vulnerability catalog with evidence, confidence breakdowns, OWASP coverage map, remediation roadmap, deployment recommendation. Formats: PDF, HTML, JSON.

### F-10: One-Click AWS Deployment
Provisions: IAM roles (least-privilege), VPC, SageMaker endpoint or API Gateway+Lambda, Bedrock Guardrails, CloudWatch monitoring. Shows full plan before any provisioning. Requires explicit approval.

---

## 6. Non-Goals (v1 Scope Boundaries)

| Out of Scope | Future Phase |
|---|---|
| Runtime monitoring / production traffic analysis | v2+ separate product |
| Azure / GCP one-click deployment | v1.5+ |
| Multi-modal scanning (images, audio) | v2 |
| CI/CD pipeline integration | v1.5 (CLI first) |
| SaaS / cloud-hosted version | v2 |
| Model training / fine-tuning | Never — AI-SENTRY tests, not trains |
| Comparison reports across scan runs | v1.5 |
| Certification / badge system | v2+ post peer review |
| Custom probe authoring | v1.5 |
| Team collaboration / multi-user | v2 SaaS |

---

## 7. User Journey

```
STEP 1 — LAUNCH
Open desktop app. First launch: auto-config wizard.
Hardware detected, engine dependencies verified.
Land on main dashboard.

STEP 2 — MODEL INPUT
Select model type: API endpoint / Local GGUF / HuggingFace.
Enter credentials or file path.
Model Adapter validates connectivity.
Cost estimate shown for API models.

STEP 3 — SCAN CONFIGURATION
Select scan depth (Quick / Standard / Deep).
Select probe categories (or use "All" default).
Set deployment context (optional — informs remediation).

STEP 4 — CONSENT GATE
Review: what will be tested, adversarial content warning,
estimated API cost, authorization confirmation.
Explicit confirmation required. Non-bypassable.

STEP 5 — SCAN EXECUTION
Live progress dashboard:
  - Per-engine status (Running / Complete / Error)
  - Live finding count
  - Estimated time remaining
  - Pause / cancel option

STEP 6 — NORMALIZATION & SCORING (automated)
Progress indicator shown. Seconds to minutes.

STEP 7 — RESULTS DASHBOARD
Summary: Overall risk tier, finding counts by severity,
confidence distribution, OWASP coverage map.
Drill-down per finding: evidence, confidence breakdown,
remediation guidance.

STEP 8 — DEPLOYMENT ADVISOR
Platform comparison table.
Select platform → detailed architecture recommendation.
Cost estimate at customizable query volume.

STEP 9 — ONE-CLICK DEPLOY (optional, AWS)
Review complete infrastructure plan.
Approve → provisioning with live status.
Completion summary with resource ARNs.

STEP 10 — REPORT EXPORT
Export as PDF / HTML / JSON.
Full findings, evidence, scoring rationale, deployment rec.
```

### Error Paths

| Situation | System Behavior |
|---|---|
| Model unreachable | Clear error with diagnostic; scan does not proceed |
| One engine fails mid-scan | Scan continues; report notes reduced coverage |
| API cost exceeds pre-approved limit | Scan pauses; user approves additional spend or reduces depth |
| Insufficient hardware for local model | Clear message with requirements; suggests API mode |
| User cancels mid-scan | Partial results preserved; report from completed engines available |

---

## 8. Constraints

### Technical Constraints

| Constraint | Impact |
|---|---|
| Local models >30B require high-end GPU | Must be communicated upfront; cannot be auto-resolved |
| API scans incur real financial cost | Pre-scan cost estimation mandatory |
| Garak/PyRIT/DeepTeam are external dependencies | Version pinning required; upstream changes can break adapters |
| LLMs are stochastic | Same probe may succeed or fail on repetition; confidence scoring must account for this |
| Deep scans can take hours | UX must support background operation |

### Business Constraints

| Constraint | Impact |
|---|---|
| v1 is desktop-only, no server | No server infrastructure in v1; limits team collaboration |
| AWS-only one-click deployment | Azure/GCP users get advisory only |
| Relies on upstream probe libraries | New attack research requires engine updates, not AI-SENTRY updates |

---

## 9. Risks

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| R-01 | Upstream engine breaking changes | High | Version pinning; adapter isolation; upstream monitoring |
| R-02 | False negatives (missed real vulnerabilities) | Critical | Coverage map in every report; explicit risk reduction disclaimer |
| R-03 | User scans unauthorized models | High | Consent gate authorization acknowledgment; ToS enforcement |
| R-04 | API cost overrun | Medium | Pre-scan estimate; incremental alerts; configurable spending limits |
| R-05 | Probe content exposure | High | Probes not displayed in main UI; logs encrypted at rest |
| R-06 | Confidence score misinterpretation | Medium | In-app tooltips; scores always shown with explanatory text |
| R-07 | Hardware detection failure | Medium | Conservative detection; fail-fast with clear requirements |
| R-08 | Cloud deployment mishap | High | Full plan review before provisioning; dry-run mode; resource tagging |

---

## 10. Success Criteria

### v1 Launch (Minimum Bar)

| Criterion | Measurement |
|---|---|
| All three engines complete end-to-end | Integration test with known-vulnerable test model passes |
| Unified report generated for all scan depths | Report complete, evidence-backed, correctly formatted |
| Confidence scores are explainable | Every score has visible natural-language breakdown |
| No false all-clear on deliberately vulnerable models | Test suite of known-vulnerable models all produce ≥1 High finding |
| One-click AWS deployment succeeds | Completes from clean AWS account without manual steps |
| Desktop app installs without manual setup | Fresh machine install + first scan with zero CLI usage |

### Product Success (3-Month Post-Launch)

| Criterion | Target |
|---|---|
| Downloads (Windows + Linux) | 1,000+ |
| Scans completed | 500+ |
| GitHub Stars | 300+ |
| Zero critical security incidents | Zero confirmed unauthorized scanning cases |

### Strategic Success (Long-Term)

- Cited in at least one published AI security paper or blog post
- At least one enterprise team uses AI-SENTRY in their formal AI deployment process
- The unified vulnerability schema referenced by a third-party tool

---

*End of PRD v1.0*
