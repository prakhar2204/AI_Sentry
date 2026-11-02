# AI-SENTRY — Project Overview

**Last Updated:** 2026-11-02  
**Phase:** 3 — Engine Adapters (Garak & PyRIT Complete)  
**Status:** Implementation in progress — Phases 0-2 complete, Phase 3 complete (Garak B1–B6, T2–T4, PyRIT P1–P6; 148 tests passing), Next: Engine Unification / Phase 4 Normalization

---

## What Is This Project?

AI-SENTRY is a **multi-engine LLM security orchestration platform** delivered as a desktop application (Windows + Linux). It automates the process of scanning any LLM for known security vulnerabilities using industry-grade engines (Garak CLI subprocess + PyRIT Python SDK), normalizes their outputs into a unified report with severity and confidence scores, and guides the user through secure cloud deployment.

## Core Value Proposition

> *Most teams ship LLMs they have never meaningfully tested for adversarial behavior. AI-SENTRY is the pre-deployment security gate that changes this — for any developer, not just security experts.*

## The Problem Being Solved

Two excellent open-source LLM security tools exist (Garak, PyRIT) but:
- They have incompatible output formats
- They require complex individual setup
- They provide no unified scoring or deployment guidance

AI-SENTRY wraps them, normalizes their outputs, adds scoring and remediation, and connects to cloud deployment.

**Note:** DeepTeam was originally planned as a third engine but was dropped (D-018) due to its hard dependency on paid API keys. PyRIT was fully integrated in Phase 3 alongside Garak. Agent-Guardian is deferred.

## Product Delivery

| Component | Description |
|---|---|
| Desktop Application | The core product — Windows + Linux installer, auto-configures environment, full scan-to-deploy workflow |
| Website | Marketing + documentation site — dark themed, animated, download-focused |

## Core Technical Approach

**"Wrap, don't rebuild"** — AI-SENTRY does not reimplement scanning logic. It orchestrates existing tools through a layered pipeline:

```
Input → Orchestration → Engines (Garak/PyRIT) → Normalization → Intelligence → Output
```

## Key Differentiators

1. Multi-engine orchestration in a single workflow
2. Unified normalized vulnerability schema
3. Explainable confidence scoring (not a black box)
4. Pre-deployment validation gate concept
5. Deployment advisory with one-click AWS provisioning

## v1 Scope Boundaries

**In v1:** Desktop app, dual scanning engines (Garak + PyRIT), unified report, AWS one-click deployment  
**Out of v1:** Runtime monitoring, Azure/GCP deployment, SaaS, CI/CD integration, multi-modal scanning

## Repository Structure (Target)

```
ai-sentry/
├── docs/               ← PRD, TRD, design documents
├── context/            ← AI memory system (this file lives here)
├── src/
│   ├── adapters/       ← Model adapters + engine adapters
│   ├── orchestration/  ← Engine manager, task queue
│   ├── normalization/  ← Schema mapper, deduplicator
│   ← intelligence/    ← Scoring, remediation
│   ├── output/         ← Report generator, deployment advisor
│   ├── deploy/         ← AWS deploy engine
│   └── ui/             ← Desktop application UI
├── tests/
└── website/            ← Marketing website
```

## Primary References

- PRD: `docs/PRD.md`
- TRD: `docs/TRD.md`
- Architecture: `context/architecture.md`
- Decisions: `context/decisions.md`
- Current Phase: `context/current_phase.md`
