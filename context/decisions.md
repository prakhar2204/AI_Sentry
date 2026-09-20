# AI-SENTRY — Architecture & Design Decisions

**Last Updated:** 2026-09-13  
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

### D-014: ASCII-Only CLI Output

**Date:** 2026-09-14  **Phase:** 1a/1b  **Status:** Active

All CLI output uses plain ASCII. No Unicode box-drawing or em-dashes. Windows cp1252 crashes otherwise.

---

### D-015: Validator is Pure Functions, No I/O

**Date:** 2026-09-17  **Phase:** 1d  **Status:** Active

core/validator.py contains only pure functions. No HTTP, no file access. Fail-fast validation is instantaneous.

---

### D-016: ValidationError is a Dataclass, Not an Exception

**Date:** 2026-09-17  **Phase:** 1d  **Status:** Active

validator.py returns ValidationError dataclass instances (with .field, .message, .hint). Never raises for validation failures.

---

### D-017: Manifest as Central Pipeline Contract

**Date:** 2026-09-20  **Phase:** 2a  **Status:** Active

ScanManifest is the single configuration object through the entire pipeline. No hardcoded scan parameters exist below the manifest layer. Same manifest => same scan, every time.

---

### D-018: ProbeCategory (user-facing) vs VulnClass (engine-facing)

**Date:** 2026-09-20  **Phase:** 2a  **Status:** Active

Manifest exposes 4 coarse ProbeCategory values. Engine adapters (Phase 3) map these to TRD's 17-value VulnClass taxonomy. Users never see engine internals.

---

### D-019: Manifest Status is a Strict State Machine

**Date:** 2026-09-20  **Phase:** 2a  **Status:** Active

advance_status() enforces legal transitions. Terminal states are immutable. Cannot skip consent (CREATED -> RUNNING raises ValueError).

---

### D-020: CLI Flag Priority Over Manifest File

**Date:** 2026-09-20  **Phase:** 2a  **Status:** Active

Priority: CLI flag > JSON file > built-in default. Enables: ai-sentry scan --manifest base.json --target \

---

### D-021: ManifestLoadResult Over Raw Exceptions

**Date:** 2026-09-20  **Phase:** 2b  **Status:** Active

get_final_manifest() returns ManifestLoadResult (ok, manifest, error, hint, source) instead of raising exceptions. CLI calls one function and pattern-matches on .ok. Errors never leak stack traces to users.

---

### D-022: validate_manifest_structure() is Pure Shape Check

**Date:** 2026-09-20  **Phase:** 2b  **Status:** Active

validate_manifest_structure() only checks JSON shape (types, required keys). Enum value validity (mode=cloud) is checked later by create_manifest(). Two-stage validation: structure first, semantics second.

---

### D-023: Comment Keys Stripped Before Parsing

**Date:** 2026-09-20  **Phase:** 2b  **Status:** Active

Any JSON key starting with _ is treated as a comment and silently stripped before parsing. Allows {_comment: ..., target: ...} without breaking validation. Follows JSON5 community convention.

---

### D-024: --target Made Optional in CLI

**Date:** 2026-09-20  **Phase:** 2b  **Status:** Active

--target is no longer required=True in argparse. It can be omitted if --manifest provides the target. get_final_manifest() enforces that at least one source provides a target, and returns a clear error if neither does.
