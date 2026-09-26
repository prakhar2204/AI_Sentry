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

---

### D-025: Manifest Validator Does NOT Auto-Correct

**Date:** 2026-09-21  **Phase:** 2c  **Status:** Active

validate_manifest() never silently fixes invalid values (no lowercasing, no aliasing 'full'->'deep'). Strict rejection only. If the manifest is invalid, it is rejected with a specific error. This prevents silent behavior drift and ensures the scan engine always receives exactly what the user specified.

---

### D-026: Three Validation Layers, Three Distinct Responsibilities

**Date:** 2026-09-21  **Phase:** 2c  **Status:** Active

Phase 1d (validator.py): validates raw CLI strings before manifest creation. Phase 2b (manifest.py): validates JSON file structure during loading. Phase 2c (manifest_validator.py): validates the final resolved ScanManifest object after merging. Each layer has a single responsibility and inputs from a different source. No layer duplicates another.

---

### D-027: scan_depth valid values are quick/standard/deep (not basic/full)

**Date:** 2026-09-21  **Phase:** 2c  **Status:** Active

The TRD (Section 2.1, F-03) specifies Quick/Standard/Deep. 'basic' and 'full' are NOT valid and are explicitly rejected by Phase 2c. This decision resolves a contradiction between a Phase 2c user prompt (which mentioned 'basic'/'full') and the TRD.

---

### D-028: Display + Confirm Before Connection Probe (not after)

**Date:** 2026-09-21  **Phase:** 2d  **Status:** Active

The manifest display and pre-scan confirmation (Phase 2d) runs in Step 4, BEFORE the endpoint probe (Step 6). This means no network activity occurs until the user has explicitly confirmed. Previously the display was shown after probing -- this was incorrect.

---

### D-029: User Declining Confirmation is Code 0 (not an error)

**Date:** 2026-09-21  **Phase:** 2d  **Status:** Active

If the user types 'no' or presses Ctrl-C at the pre-scan confirmation, the process exits with code 0. Declining is a deliberate user action, not an error. This keeps CI/CD pipelines from treating a user decision as a failure.

---

### D-030: 3-Attempt Limit on Invalid Confirmation Input

**Date:** 2026-09-21  **Phase:** 2d  **Status:** Active

If the user gives invalid input (not yes/no) more than _MAX_ATTEMPTS times, confirm_execution() returns False (exits cleanly). This prevents infinite loops in piped or automated contexts. Same pattern used in Phase 1a consent gate.

---

### D-031: Estimator Constants Are Derived From TRD Probe Taxonomy

**Date:** 2026-09-21  **Phase:** 3a  **Status:** Active

BASE_PROBES_PER_CATEGORY counts (45/50/55/45) are calibrated from TRD Section 2.3 probe taxonomy and Garak baseline probe set sizes. DEPTH_MULTIPLIERS (0.5/1.0/2.0) map to Quick/Standard/Deep scan profiles. TIME_PER_PROBE (1.5s API, 0.8s local) assumes sequential execution.

---

### D-032: Estimation Displayed Before Confirmation (Not After)

**Date:** 2026-09-21  **Phase:** 3a  **Status:** Active

The user's prompt positioned estimation AFTER confirmation. This was corrected: estimation is shown BEFORE the yes/no prompt so the user can make an informed decision about cost and time before committing. This matches the principle that no network activity occurs until after explicit confirmation.

---

### D-033: Safety Guard Uses Strict Greater-Than (Not >=)

**Date:** 2026-09-24  **Phase:** 3b  **Status:** Active

is_heavy_scan() uses > (not >=) to compare against thresholds. A scan with exactly 300 probes or exactly 300 seconds is NOT heavy. This prevents false warnings on scans that are right at the recommended limits.

---

### D-034: Heavy Scan Warning is Advisory, Never Auto-Cancel

**Date:** 2026-09-24  **Phase:** 3b  **Status:** Active

The safety guard NEVER auto-cancels a scan. It always asks the user. This respects user autonomy -- the warning exists to inform, not to block. Even scans with 1000+ probes can proceed if the user says yes.

---

### D-035: Heavy Guard is a Separate Confirmation From Normal Confirm

**Date:** 2026-09-24  **Phase:** 3b  **Status:** Active

Heavy scans require TWO confirmations: (1) 'Proceed with heavy scan?' from scan_guard.py (Step 5), and (2) 'Proceed with scan?' from manifest_display.py (Step 6). This is intentional -- the heavy warning fires before the user even sees the full config display, giving them an early exit point. Light scans only see confirmation (2).

---

### D-036: ScanFinding Validates Severity and Confidence on Construction

**Date:** 2026-09-24  **Phase:** 3c  **Status:** Active

ScanFinding.__post_init__() rejects invalid severity (must be low/medium/high) and out-of-range confidence (must be 0.0-1.0) with ValueError. This is fail-fast by design -- invalid findings can never enter the pipeline.

---

### D-037: Engine Errors Wrapped in ScanResult, Not Exceptions

**Date:** 2026-09-24  **Phase:** 3c  **Status:** Active

Engines must never raise exceptions to the CLI. If an engine fails, it returns ScanResult(error='...') and the CLI checks result.ok. This keeps the pipeline predictable and avoids uncaught exception crashes.

---

### D-038: MockEngine is Default Until Real Engines Are Integrated

**Date:** 2026-09-24  **Phase:** 3c  **Status:** Active

engine_runner.run_engine() currently always uses MockEngine. When Garak/PyRIT/DeepTeam adapters are built, this function will select the engine based on a registry or manifest configuration. The mock engine remains as a fallback and testing tool.

---

### D-039: MAX_POSSIBLE_SCORE = 120 (Configurable Ceiling)

**Date:** 2026-09-25  **Phase:** 5a  **Status:** Active

Normalization ceiling is 4 categories * 3 findings * HIGH weight(10) * 1.0 confidence = 120. Scans with raw scores above 120 still cap at 100/100. This constant can be tuned as real engines produce different finding volumes.

---

### D-040: Risk Thresholds Are Inclusive on Lower Bound

**Date:** 2026-09-25  **Phase:** 5a  **Status:** Active

0-30 = LOW (<=30), 31-70 = MEDIUM (<=70), 71-100 = HIGH. Score of exactly 30 is LOW, exactly 70 is MEDIUM, exactly 71 is HIGH. These are the boundaries. No gaps, no overlaps.

---

### D-041: Recommendations Are Severity-Tiered, Not Cumulative

**Date:** 2026-09-26  **Phase:** 5b  **Status:** Active

Each category has separate action lists for high/medium/low severity. The tier selected matches the category's max_severity from the scorer. Higher tiers are NOT cumulative (they don't include lower-tier actions) -- they are independently curated lists that may share some actions but are designed for the specific severity context.

---

### D-042: Recommendations Only Include Categories With Findings

**Date:** 2026-09-26  **Phase:** 5b  **Status:** Active

If a category has zero findings, it gets zero recommendations. No generic 'best practice' padding. This keeps the output actionable and focused on what was actually detected.

---

### D-043: ScanReport is the Single Source of Truth for All Report Data

**Date:** 2026-09-26  **Phase:** 6a  **Status:** Active

All downstream consumers (CLI display, file export, Electron UI) read from the same ScanReport object. No component should reconstruct report data from lower-level objects (ScanResult, RiskReport, etc.) -- they all go through generate_full_report().

---

### D-044: JSON Report Schema is UI-Ready (No Frontend Transformation)

**Date:** 2026-09-26  **Phase:** 6a  **Status:** Active

The JSON schema returned by ScanReport.to_dict() is the exact structure the React frontend will consume. Field names, nesting, and types are designed for direct binding. No BFF (backend-for-frontend) transformation layer is needed.

---

### D-045: Reports Auto-Export to --output Directory

**Date:** 2026-09-26  **Phase:** 6a  **Status:** Active

After every scan, CLI Steps 12-13 automatically export both JSON and TXT reports to the --output directory (default: ./aisentry-report/). Files are named report_<scan_id>.json and report_<scan_id>.txt. Parent directories are created if missing.
