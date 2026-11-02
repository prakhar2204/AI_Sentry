# AI-SENTRY — Architecture & Design Decisions

**Last Updated:** 2026-10-09  
**Format:** Decision Log — each entry is permanent. Decisions are never deleted, only superseded.

---

## Decision Log

---

### D-001: Desktop-First Delivery (Not Web SaaS)

**Date:** 2026-09-13  
**Phase:** 0a  
**Status:** Active

**Decision:** AI-SENTRY v1 is delivered as a desktop application, not a web/SaaS product.

**Rationale:**
- Local model scanning requires filesystem access and co-location with the model file — impossible in a browser
- Adversarial probe content and model responses (sensitive data) must never leave the user's machine unnecessarily
- Scanning requires subprocess invocation of Garak CLI — not feasible in a sandboxed web environment
- No server infrastructure to build, secure, or scale in v1
- Desktop delivery eliminates authentication, session management, and data storage compliance concerns

**Trade-offs accepted:**
- No team collaboration features in v1
- No browser-based access
- Platform-specific installer maintenance required

**Future:** SaaS delivery planned for v2 after core workflow is validated.

---

### D-002: "Wrap, Don't Rebuild" Engine Strategy

**Date:** 2026-09-13  
**Phase:** 0a  
**Status:** Active

**Decision:** AI-SENTRY does not reimplement LLM probe or detection logic. It orchestrates Garak, PyRIT, and DeepTeam as external dependencies.

**Rationale:**
- Probe research is expensive and specialized — duplicating it wastes resources
- Existing engines are maintained by expert teams (NVIDIA, Microsoft, Confident AI)
- AI-SENTRY's unique value is in orchestration, normalization, and intelligence — not probe design
- New probe research automatically benefits AI-SENTRY through engine updates

**Trade-offs accepted:**
- AI-SENTRY is dependent on upstream engine health and API stability
- Version pinning is required to prevent unexpected breakage
- New attack types must wait for engine support before AI-SENTRY can detect them

---

### D-003: Unified VulnerabilityFinding as the Central Data Contract

**Date:** 2026-09-13  
**Phase:** 0b  
**Status:** Active

**Decision:** All system components agree on a single VulnerabilityFinding schema. This schema is the output of the Normalization layer and the input to all downstream layers.

**Rationale:**
- Without a shared schema, every downstream component must handle three different engine formats — exponential complexity
- Schema versioning enables controlled evolution
- A shared contract allows independent development of each layer

**Implication:** Changes to VulnerabilityFinding schema require coordinated migration across all consuming components. Schema changes are versioned with a migration path.

---

### D-004: Severity and Confidence Are Separate Axes

**Date:** 2026-09-13  
**Phase:** 0a  
**Status:** Active

**Decision:** Severity (how harmful if exploited) and Confidence (how certain AI-SENTRY is that the finding is real) are never collapsed into a single score.

**Rationale:**
- A Critical-severity finding with Low confidence (detected once, not reproduced) communicates very different risk than Critical + High confidence
- Collapsing into one score would require hiding this distinction — which violates the transparency principle
- Users need both dimensions to make correct remediation prioritization decisions

**Implication:** The UI must always display both scores. Report must always show both. Neither can be omitted.

---

### D-005: Mandatory Consent Gate Before Every Scan

**Date:** 2026-09-13  
**Phase:** 0a  
**Status:** Active

**Decision:** No scan can begin without an explicit, non-bypassable consent screen that shows: probe categories, estimated cost, adversarial content warning, and authorization confirmation.

**Rationale:**
- AI-SENTRY is a dual-use tool — the same probes that test defenses could be misused offensively
- Without explicit authorization confirmation, AI-SENTRY could be used to scan models the user doesn't own
- For API models, cost transparency before execution is an ethical requirement
- Legal protection for the platform depends on clear documented consent

**Implication:** The consent gate cannot be suppressed by configuration, CLI flags, or environment variables in production builds.

---

### D-006: AWS-First One-Click Deployment

**Date:** 2026-09-13  
**Phase:** 0a  
**Status:** Active

**Decision:** One-click deployment in v1 supports AWS only. Azure and GCP are on the roadmap for v1.5.

**Rationale:**
- Building robust, safe, tested one-click deployment for one cloud is better than fragile deployment for three
- AWS has the most complete set of AI/ML security controls (Bedrock Guardrails, SageMaker, comprehensive IAM)
- AWS market share makes it the highest-value first target
- The Deployment Advisor (platform recommendation without provisioning) covers Azure and GCP from day one

**Trade-offs accepted:**
- Azure and GCP users can get recommendations but cannot execute one-click deployment in v1

---

### D-007: Confidence Score Transparency is Non-Negotiable

**Date:** 2026-09-13  
**Phase:** 0a  
**Status:** Active

**Decision:** Every confidence score must be accompanied by a human-readable explanation of the contributing factors. The scoring formula and factor weights must be publicly documented.

**Rationale:**
- Opaque confidence scores erode user trust and can lead to incorrect risk decisions
- If users can't explain a score, they stop believing it
- Reproducibility and auditability are requirements for enterprise and compliance use cases

**Implication:** Confidence scores that cannot be explained with natural language are not acceptable. The scoring algorithm is part of the public documentation.

---

### D-008: PyRIT Requires Secondary "Attacker LLM"

**Date:** 2026-09-13  
**Phase:** 0b  
**Status:** Active — complexity acknowledged, solution pending Phase 3

**Decision:** AI-SENTRY will default to a small local model (e.g., Phi-3 Mini) as the PyRIT attacker LLM. Users can override with their own API key.

**Rationale:**
- PyRIT's multi-turn red-teaming orchestration requires an LLM to generate adversarial follow-up prompts
- Using the same model being tested as the attacker creates a circular dependency
- A small local model keeps costs low and avoids requiring an additional API subscription
- Users with access to a more capable attacker model (e.g., GPT-4o for testing a smaller model) can provide their own

**Open question for Phase 3:** Minimum hardware requirements to run Phi-3 Mini locally alongside the scan target.

---

### D-009: Coverage Map is a Required Report Section

**Date:** 2026-09-13  
**Phase:** 0b  
**Status:** Active

**Decision:** Every generated report must include a coverage map that explicitly shows which OWASP LLM Top 10 categories were tested, which were not, and why.

**Rationale:**
- Without a coverage map, users may believe AI-SENTRY tested everything when it did not
- False completeness is worse than acknowledged incompleteness
- Regulated users need to know the scope boundaries of any security assessment

**Implication:** The coverage map is generated automatically by the Report Generator based on which probe categories ran. It cannot be suppressed.
### D-010: Tauri Selected as Desktop Framework

**Date:** 2026-09-13
**Phase:** 0c
**Status:** Active

**Decision:** The desktop application is built with Tauri (Rust backend + OS WebView frontend).

**Rationale:**
- Electron bundles a full Chromium instance: 150–300 MB installer, 200–500 MB RAM at idle
- PySide6 has a significantly lower UI quality ceiling; complex animations and data visualizations are painful
- Tauri uses the OS native WebView (WebView2 on Windows, WebKit on Linux) — installer is 5–15 MB
- Tauri's Rust backend is memory-safe and has a strict allowlist IPC model (appropriate for a security tool)
- Frontend is standard HTML+CSS+JS — any web developer can contribute UI code
- Python backend is retained for all scanning logic (engines require Python)

**Architecture:** Tauri Rust backend spawns and manages the Python backend process. They communicate via local IPC (JSON over named pipe or Unix socket). Progress events flow: Python → Rust → Tauri event bus → Frontend.

**Trade-offs accepted:** Rust knowledge required for the IPC bridge layer; some Tauri-specific APIs differ from Electron's Node.js APIs.

---

### D-011: Python Backend Runs as a Separate Managed Process

**Date:** 2026-09-13
**Phase:** 0c
**Status:** Active

**Decision:** All scanning logic (InputHandler, Orchestrator, Normalization, Scoring, Reporting, Deployment) runs in a Python process that is spawned and managed by the Tauri Rust backend.

**Rationale:**
- Garak, PyRIT, and DeepTeam are Python libraries — there is no alternative
- Separating the Python process from the Rust process allows independent failure isolation
- The Rust backend can restart the Python process if it crashes, without crashing the UI
- The bundled Python runtime is self-contained (not installed to system PATH)

**IPC Protocol:** JSON-based command/response over a local socket. Commands flow from Rust to Python. Events (progress, findings) flow from Python to Rust via the same socket.

---

### D-012: No Auto-Update Installation (User-Controlled)

**Date:** 2026-09-13
**Phase:** 0c
**Status:** Active

**Decision:** The desktop app notifies users of new versions but does not auto-install updates.

**Rationale:**
- Auto-installing updates to a security tool without user knowledge is itself a security anti-pattern
- Users should control when their security tooling changes, especially in regulated environments
- The notification is non-blocking — users can dismiss and continue working
- Engine dependency updates (Garak, PyRIT, DeepTeam versions) are bundled in each release; users do not separately update engines

**Implementation:** App polls https://ai-sentry.dev/api/version/latest on launch (if network available). If newer version found: non-blocking notification bar with [Download Update] link to website.

---

### D-013: Website Analytics via Plausible (No Cookies)

**Date:** 2026-09-13
**Phase:** 0c
**Status:** Active

**Decision:** The website uses Plausible Analytics. The desktop app uses no analytics by default (opt-in telemetry only).

**Rationale:**
- A privacy-first security tool using Google Analytics (which sets tracking cookies and sends data to Google) is a contradiction
- Plausible requires no cookie consent banner (it uses no cookies)
- Plausible collects only: page views, unique visitors by country, referrer — no personal data
- Desktop app telemetry is opt-in (default off) and clearly documented in Settings

**Implication:** No cookie banner is required on the website. The privacy policy must clearly state that the desktop app collects no telemetry by default.

### D-014: Next.js 14 + Vercel Selected as Website Stack

**Date:** 2026-09-13
**Phase:** 0d
**Status:** Active

**Decision:** The website is built with Next.js 14 (App Router) and deployed on Vercel.

**Rationale:**
- Server-side rendering by default — search bots receive full HTML (critical for SEO)
- Static generation for content that does not change per-request (legal, about, changelog)
- Built-in Image component handles WebP, lazy loading, srcset automatically
- Route Handlers provide /api/version/latest in the same codebase — no separate service
- Next.js is developed by Vercel — zero-configuration deployment with native optimizations
- Vercel free tier provides 100 GB bandwidth/month — sufficient for initial open-source launch

**Rejected alternatives:** Gatsby (slow builds), Astro (team already using React for Tauri UI), Remix (smaller ecosystem), plain HTML (no build pipeline), Vite SPA (client-side rendering fails SEO requirement).

---

### D-015: Plausible Analytics — No Cookie Banner Required

**Date:** 2026-09-13
**Phase:** 0d
**Status:** Active

**Decision:** Plausible Analytics is used for the website. The website sets zero cookies.
No cookie consent banner is displayed.

**Rationale:**
- Plausible uses no cookies and collects no personal data — GDPR-compliant without consent
- No consent banner removes friction and is honest (a banner would imply cookies exist when they do not)
- EU-hosted, open-source, auditable — consistent with AI-SENTRY's privacy positioning
- Google Analytics would require a cookie consent banner and would be hypocritical for a privacy-focused security tool

---

### D-016: Markdown-in-Repository for All Content

**Date:** 2026-09-13
**Phase:** 0d
**Status:** Active

**Decision:** Blog posts, documentation, and changelog entries are MDX files in the Git repository.
No external CMS is used.

**Rationale:**
- Full git history for all content — complete audit trail
- PR-based content review workflow
- Docs and code always in sync — same deployment pipeline
- MDX allows embedding React components in documentation (e.g., confidence score widgets)
- No CMS vendor lock-in, no subscription cost, no third-party outage risk

---

### D-017: Zero Friction to Download

**Date:** 2026-09-13
**Phase:** 0d
**Status:** Active

**Decision:** The download page requires no email, no account, no waitlist, and no registration.
The download begins immediately upon clicking the button.

**Rationale:**
- Any friction before the primary conversion (download) is a direct loss of users
- Developer audience is suspicious of tools that demand personal information for free software downloads
- Email capture before download is common but actively hostile to the target user
- Trust is built by transparency and technical depth — not by gating access to a free tool

---

### D-018: DeepTeam Dropped — Garak Used as Primary Scanning Engine

**Date:** 2026-09-21
**Phase:** 4 (Engine Integration — pivot during implementation)
**Status:** Active
**Supersedes:** D-002 (partially — DeepTeam portion only), KI-003, GAP-002

**Decision:** DeepTeam (and its underlying dependency `deepeval`) has been removed from the project. The scanning engine integration in Phase 4 will be built on **Garak** instead. Garak becomes the primary (and currently sole) scanning engine. PyRIT remains planned for future integration.

**Rationale:**
- DeepTeam requires an auxiliary LLM (OpenAI `gpt-4o-mini` by default) for both attack generation (`simulator_model`) and response judging (`evaluation_model`). This creates a hard dependency on a paid API key for any scan to function.
- The project's design goal is a tool that works without requiring users to provide third-party API keys for the scanning engine's internal operation. Garak does not have this dependency.
- During Sub-phase 1 smoke testing, DeepTeam v1.0.9 (backed by deepeval v4.2.3) was confirmed to import and expose 39 vulnerability classes and the `red_team()` function successfully. However, the mandatory paid-LLM dependency made it unsuitable for the project's "free on its own" constraint.
- Garak operates as a self-contained probe-based scanner (subprocess/CLI) with no auxiliary LLM requirement.

**What was removed:**
- `deepeval==1.4.0` from `pyproject.toml` `[engines]` dependencies
- `deepteam` and `deepeval` packages uninstalled
- 3 throwaway test scripts (`smoke_test_deepteam.py`, `smoke_test_output.txt`, `check_model_options.py`)
- DeepTeam reference in `core/health.py` comment (L15)
- DeepTeam reference in `cli/main.py` healthcheck description (L130)

**What was NOT removed (historical audit trail):**
- All prior decision entries (D-002, etc.) that mention DeepTeam remain in this file — they document the original design intent
- Documentation files (`PRD.md`, `TRD.md`, `FINAL_CONSOLIDATION.md`, `SYSTEM_EXECUTION_LAYER.md`) retain their original DeepTeam references as historical design records
- `context/` files (`architecture.md`, `known_issues.md`, etc.) retain DeepTeam references as Phase 0 design history

**Note for future readers:** Entries D-002, KI-003 (in `known_issues.md`), and GAP-002 (in `FINAL_CONSOLIDATION.md`) reference DeepTeam as an active engine. Those entries reflect the original Phase 0 design. This decision (D-018) supersedes them. The original text is preserved for decision-trail integrity.

---

### D-019: PyRIT Offline-Only Scorers (no LLM judge)

**Date:** 2026-10-28  
**Decision:** All PyRIT scorers used in `core/pyrit_engine.py` must be offline — no scorer may make a secondary LLM call.

**Rationale:** User requirement (D-Q2): AI-SENTRY must work without any external API keys or a running secondary LLM. LLM-based scorers (`SelfAskRefusalScorer`, `SelfAskLikertScorer`, etc.) violate this.

**Chosen scorers (all offline):**
- `SubStringScorer` — keyword match (primary workhorse)
- `StaticPromptInjectionScorer` — regex-based injection pattern detection
- `RegexScorer` — available for future custom patterns

**Explicitly rejected:**
- `SelfAskRefusalScorer`, `SelfAskLikertScorer`, `SelfAskTrueFalseScorer`, `SelfAskCategoryScorer` — all require a `chat_target` (secondary LLM)
- `AzureContentFilterScorer`, `LlamaGuardScorer` — require Azure API or local LlamaGuard model

---

### D-020: PyRIT Package Name Correction

**Date:** 2026-10-28  
**Decision:** The correct PyPI package name is `pyrit`, NOT `pyrit-ai`. Updated `pyproject.toml` from `pyrit-ai==0.5.0` to `pyrit==1.1.0`.

**Rationale:** `pyrit-ai` does not exist on PyPI. `pyrit` is the real package (Microsoft). Version 1.1.0 is the latest as of 2026-10-28.

**API changes vs old assumption (pyrit-ai==0.5.0):**
- `DuckDBMemory` removed → `SQLiteMemory`
- `PromptRequestPiece` / `PromptRequestResponse` → `MessagePiece` / `Message`
- `pyrit.orchestrator` module does not exist → use `PromptNormalizer.send_prompt_async()`
- `fetch_harmbench_examples()` does not exist → use `SeedDatasetProvider`
- `OpenAIChatTarget` requires explicit `model_name` (passing `None` forces env var lookup)
- `endpoint` must be base URL only — no `/chat/completions` suffix

**Dependency conflict:** PyRIT 1.1.0 upgrades `datasets` to 5.1.0, but Garak 0.17.0 requires `datasets<4.0`. Garak subprocess isolation means unit tests still pass (82/82). Real server runs should be re-validated.

### D-021: PyRIT Version Pinned to 1.1.0

**Date:** 2026-11-02
**Phase:** 5 (PyRIT Engine Integration — P1-P6)
**Status:** Active

**Decision:** `pyrit==1.1.0` is pinned in `pyproject.toml` `[engines]`.

**Rationale:**
- 1.1.0 is the latest published version of `pyrit` on PyPI as of 2026-11-02.
- The package was verified installable and functional on Python 3.12.0.
- API surfaces discovered and documented during P1 (environment discovery):
  `SQLiteMemory`, `MessagePiece`, `Message`, `PromptNormalizer.send_prompt_async`,
  `SubStringScorer`, `StaticPromptInjectionScorer`, `initialize_pyrit_async`.
- Pinning prevents silent breakage from upstream API changes (PyRIT 1.x → 2.x).

**Supersedes note:** D-020 corrected the package name from `pyrit-ai` to `pyrit`
and set the initial version. D-021 formalises the P6-era pin.

**Version lock review:** Required before any upgrade. Full test suite
(148 tests) must pass. API surfaces must be re-verified via P1-style inspection.

---

### D-022: Garak/PyRIT datasets Conflict Resolved via Subprocess Isolation

**Date:** 2026-11-02
**Phase:** 5 (PyRIT Engine Integration — P1-P6)
**Status:** Active

**Decision:** `pyrit==1.1.0` and `garak==0.17.0` can coexist in the same
Python environment despite their conflicting `datasets` version requirements
(`datasets>=4.8.0` vs `datasets<4.0`). No workaround or virtual environment
split is required.

**Rationale:**
- Garak is invoked exclusively as a CLI subprocess (`subprocess.run(["garak", ...])`).
  It runs in its own Python interpreter (the system PATH `garak` executable), which
  loads `datasets` independently of the AI-SENTRY process.
- The AI-SENTRY Python process imports `pyrit` directly. PyRIT's `datasets>=4.8.0`
  is satisfied by whatever version pip installs.
- The two `datasets` consumers never share a Python process. There is no runtime
  conflict.

**Evidence:** 148/148 tests pass with both packages installed simultaneously.
Integration tests (P6) confirmed Garak subprocess scans and PyRIT SDK scans
produce correct results from the same environment.

**Future risk:** If AI-SENTRY ever imports Garak as a Python library (not a
subprocess), this isolation guarantee disappears and the conflict must be resolved
by virtualenv splitting or a common-version negotiation.

---

### D-023: PyRIT VulnerabilityFinding Reuse (Shared Schema)

**Date:** 2026-11-02
**Phase:** 5 (PyRIT Engine Integration — P1-P6)
**Status:** Active

**Decision:** `core/pyrit_engine.py` imports `VulnerabilityFinding` from
`core.garak_engine` rather than defining its own. Both engines produce
identical output objects.

**Rationale:**
- D-003 mandates a single shared schema for all engine outputs.
- `VulnerabilityFinding` in `core/garak_engine.py` already matches the Phase 4
  normalization contract (all required fields: `finding_id`, `engine`, `category`,
  `probe`, `detector`, `passed`, `failed`, `total`, `pass_rate`, `severity`,
  `confidence`, `raw_eval`).
- Re-implementing the same dataclass in `pyrit_engine.py` would create drift risk.
- PyRIT findings set `engine="pyrit"`, all other fields populated identically to
  Garak findings — the downstream normalization layer requires zero changes.

**Implementation:** `from core.garak_engine import VulnerabilityFinding`
(line 1 import in `core/pyrit_engine.py`).

**Future:** When Phase 4 normalization is built, `VulnerabilityFinding` will
be extracted to `core/schemas.py` (a neutral module). Both engine files will
then import from there. This is a one-line change in each file; no schema change.

---
