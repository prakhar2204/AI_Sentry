# Sentryɸ — Project Overview

**Last Updated:** 2026-10-10
**Phase:** Active development
**Status:** Implementation in progress

---

## Canonical Naming Convention

| Context | Name |
|---|---|
| **Display / branding** | `Sentryɸ` (U+0278 LATIN SMALL LETTER PHI) |
| **ASCII / technical identifiers** | `SentryPhi` |
| **Domain / hostname** | `sentryphi` |
| **CLI command** | `sentryphi` (legacy: `ai-sentry`, `aisentry`) |
| **Python package** | `sentryphi` |

> **Rule:** Use `Sentryɸ` in all user-visible text. Use `SentryPhi` only where Unicode is technically unsuitable (filenames, package IDs, class names). Do not use `SentryΦ`, `Sentryφ`, `SentryPhi` as display text, or the old name `AI-SENTRY`.

---

## What Is This Project?

Sentryɸ is a **multi-layer LLM pre-deployment security platform** delivered as a desktop application (Windows + Linux). It automates the process of scanning any LLM for known security vulnerabilities, normalizes results into a unified report with severity and confidence scores, and guides the user through secure cloud deployment.

## Core Value Proposition

> *Most teams ship LLMs they have never meaningfully tested for adversarial behavior. Sentryɸ is the pre-deployment security gate that changes this — for any developer, not just security experts.*

## The Problem Being Solved

LLM security tools exist but:
- They have incompatible output formats
- They require complex individual setup
- They provide no unified scoring or deployment guidance

Sentryɸ orchestrates multiple security analysis layers, normalizes their outputs, adds scoring and remediation, and connects to cloud deployment.

## Product Delivery

| Component | Description |
|---|---|
| Desktop Application | The core product — Windows + Linux installer, auto-configures environment, full scan-to-deploy workflow |
| Website | Marketing + documentation site — dark themed, animated, download-focused |

## Core Technical Approach

**"Wrap, don't rebuild"** — Sentryɸ does not reimplement scanning logic. It orchestrates existing tools through a layered pipeline:

```
Input → Orchestration → Engines → Normalization → Intelligence → Output
```

## Key Differentiators

1. Multi-layer security orchestration in a single workflow
2. Unified normalized vulnerability schema
3. Explainable confidence scoring (not a black box)
4. Pre-deployment validation gate concept
5. Deployment advisory with one-click AWS provisioning

## v1 Scope Boundaries

**In v1:** Desktop app, multi-engine orchestration, unified report, AWS one-click deployment
**Out of v1:** Runtime monitoring, Azure/GCP deployment, SaaS, CI/CD integration, multi-modal scanning

## Repository Structure

```
AI_Sentry/
├── docs/               ← PRD, TRD, design documents
├── context/            ← Project memory files (this file)
├── app/
│   ├── backend/        ← Python CLI + core engine
│   └── frontend/       ← React/Vite desktop UI
└── website/            ← Next.js marketing website
```

## Primary References

- PRD: `docs/PRD.md`
- TRD: `docs/TRD.md`
- Architecture: `context/architecture.md`
- Decisions: `context/decisions.md`
- Current Phase: `context/current_phase.md`
