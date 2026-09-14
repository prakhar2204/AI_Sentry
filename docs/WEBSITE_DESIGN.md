# AI-SENTRY — Complete Website System Design

**Document Version:** 1.0
**Phase:** 0d — Website Design
**Status:** Design Only — No Implementation
**Last Updated:** 2026-09-13
**Depends On:** PRD v1.0, TRD v1.0, SYSTEM_EXECUTION_LAYER.md

---

## Table of Contents

1. [Website Purpose](#section-1--website-purpose)
2. [Complete Site Structure](#section-2--complete-site-structure)
3. [Page-by-Page Breakdown](#section-3--page-by-page-breakdown)
4. [Design System](#section-4--design-system)
5. [Download System](#section-5--download-system)
6. [SEO Strategy](#section-6--seo-strategy)
7. [Analytics and Tracking](#section-7--analytics-and-tracking)
8. [Cookie and Privacy System](#section-8--cookie-and-privacy-system)
9. [Performance and Mobile](#section-9--performance-and-mobile)
10. [Tech Stack](#section-10--tech-stack)
11. [Brand Positioning](#section-11--brand-positioning)

---

# SECTION 1 — WEBSITE PURPOSE

## What This Website Is For

The AI-SENTRY website is the primary conversion surface for the product. It has one job above all
others: turn a curious visitor into a download. Everything — the copywriting, the design, the
structure, the animations — serves that single conversion event.

The website is NOT the product. It is the front door. It must:

1. Explain what AI-SENTRY does in under 10 seconds to a developer who has never heard of it
2. Build enough trust for a technical user to click Download and run an installer on their machine
3. Provide the depth a security-conscious buyer (CISO, enterprise team) needs to feel confident
4. Serve as the official home for documentation, changelog, and support

## Primary User Journey

```
Arrive (organic search / conference mention / GitHub referral)
        |
Land on homepage — understand the product in 10 seconds
        |
Scroll or click to understand HOW it works
        |
Trust established — technical depth confirms legitimacy
        |
Navigate to Download page
        |
Download installer — PRIMARY CONVERSION
        |
Return later for documentation, changelog, blog
```

## Primary Conversion Goal

**Download the desktop application** (Windows .exe or Linux .AppImage).

Every page has a visible, persistent Download CTA. Always reachable within one click from any page.
Zero friction to reach the download — no email, no account, no waitlist.

## Secondary Goals (In Priority Order)

1. **Return visits** — Changelog, blog, and documentation bring users back
2. **Trust signals** — Open-source links, engine attribution, security disclosures build institutional trust
3. **Community** — GitHub star prompt, Discord link for early community building
4. **Word of mouth** — Blog content that ranks in search and gets shared by the AI security community

---

# SECTION 2 — COMPLETE SITE STRUCTURE

## Full URL Map

```
ai-sentry.dev/
|
+-- /                           Homepage
+-- /features                   Deep feature breakdown
+-- /how-it-works               4-step visual explainer
+-- /download                   Platform downloads + checksums
|
+-- /docs/
|   +-- /docs/getting-started   Installation + first scan walkthrough
|   +-- /docs/model-support     Supported model types matrix
|   +-- /docs/scan-categories   Probe categories explained
|   +-- /docs/confidence-scoring How confidence scoring works
|   +-- /docs/schema-reference  Vulnerability schema field reference
|   +-- /docs/deployment-guide  AWS deployment walkthrough
|
+-- /roadmap                    Public product roadmap
+-- /changelog                  Version history index
|   +-- /changelog/[version]    Per-version release notes
|
+-- /blog/
|   +-- /blog/[slug]            Individual blog post
|   +-- /blog/tag/[tag]         Posts filtered by tag
|
+-- /about                      Project background and mission
+-- /contact                    Contact form and links
|
+-- /legal/privacy              Privacy Policy
+-- /legal/terms                Terms of Service
+-- /legal/cookies              Cookie Policy
|
+-- /404                        Custom not-found page
+-- /sitemap.xml                Auto-generated sitemap
+-- /robots.txt                 Crawler rules
```

## Navigation Structure

**Primary navigation (top bar, always sticky):**
Features | How It Works | Download | Docs | Roadmap | **[Download]** (primary CTA button, top-right)

**Footer (three-column link grid):**
- Left: Product — Features, How It Works, Download, Changelog, Roadmap
- Center: Developers — Docs, GitHub, Schema Reference, Blog, Changelog
- Right: Legal — Privacy, Terms, Cookies, Contact, About

**Persistent on every page:** Sticky navigation bar, Download CTA in top-right, full footer.

---

# SECTION 3 — PAGE-BY-PAGE BREAKDOWN

---

## Page 1: Homepage ( / )

**Purpose:** Convert first-time visitors. Communicate product value in the first viewport.
Drive toward the Download page.

### Section 1.1 — Hero

**Visual:** Full-viewport dark section. Background: deep navy with subtle animated particle field or
grid. Centered content.

**Animation (the scan visualization):** A looping 6-second CSS/SVG animation:
1. Abstract "LLM" node centered on screen
2. Three colored probe beams extend from Garak, PyRIT, DeepTeam nodes positioned at the edges
3. Beams reach the LLM; vulnerability nodes light up in severity colors (red, amber, gold, mint)
4. A report card slides in from the right, populating with finding counts via counter animation
5. Scene fades softly — loop restarts
Implementation: Pure CSS keyframe animations on SVG elements. No video file. No JS animation library.

**Content:**
```
Tag line:   LLM Security Orchestration Platform

Headline:   Scan Your AI Before You
            Ship Your AI.

Sub-head:   AI-SENTRY runs Garak, PyRIT, and DeepTeam simultaneously,
            normalizes the results, and tells you exactly what is wrong
            and how to fix it. In one tool. No setup.

CTAs:       [Download for Windows]    [Download for Linux]
            v1.0 — Free and Open Source  Windows + Linux
```

### Section 1.2 — Trust Bar

Horizontal strip immediately below hero:
"Powered by: **Garak** (NVIDIA Research) · **PyRIT** (Microsoft) · **DeepTeam** (Confident AI)"
"Built on the same tools used by AI security researchers worldwide."

### Section 1.3 — Problem / Solution (Two Columns)

**Left — The Problem:**
"You are shipping AI you have not tested. Three world-class LLM security scanners exist.
Each has a different format, a different setup, and a different output.
Nobody runs all three. Most teams run none."

**Right — The Solution:**
"One tool. Three engines. One report. AI-SENTRY wraps Garak, PyRIT, and DeepTeam into
a single workflow. Input your model. Get a unified, scored, actionable security report.
Then deploy securely."

### Section 1.4 — Feature Highlights (Three Cards, Stagger-Animated on Scroll)

Card 1: Multi-Engine Scanning
"Three engines. One scan. No duplicates. Full coverage across OWASP LLM Top 10."

Card 2: Explainable Scores
"Severity and confidence shown separately. Every score has a plain-English rationale."

Card 3: Deploy with Confidence
"From vulnerability report to secure AWS deployment in the same workflow. One click."

### Section 1.5 — How It Works Mini Preview

4-step horizontal flow with connecting lines/arrows:
`[1] Connect Your Model` → `[2] Scan — 3 Engines` → `[3] Unified Report` → `[4] Deploy`
Link below: "See the full walkthrough →" → /how-it-works

### Section 1.6 — App Screenshot Mockup

Large, dark-framed "application window" showing the scan progress screen.
Caption: "Live scan progress across all three engines with real-time finding detection."

### Section 1.7 — Target User Callout (Three Persona Blocks)

For Developers: "Know your model is safe before it hits production."
For Security Teams: "Run a standardized scan every team can reproduce."
For Enterprises: "Generate audit-ready reports that satisfy compliance review."

### Section 1.8 — OWASP Coverage Banner

Grid of OWASP LLM Top 10 categories with AI-SENTRY's coverage level per category.
Communicates technical depth without requiring a click.

### Section 1.9 — Final CTA Section

Full-width, gradient accent background:
"Stop guessing. Start scanning."
`[Download AI-SENTRY Free]`
"Windows · Linux · No setup required · No server needed"

---

## Page 2: Features ( /features )

**Purpose:** Provide depth for developers and security professionals.
Convert the curious into confident downloaders.

**Page Header:**
"Everything You Need to Validate an LLM Before Deployment"
"Not a single scanner. An orchestration platform."

**Feature 1 — Universal Model Adapter:**
Visual: supported model type cards connecting into a single AI-SENTRY hub node.
Covers: OpenAI-compatible APIs, Azure OpenAI, Local GGUF via auto-managed llama.cpp,
HuggingFace Inference API, Custom REST endpoints with schema inference wizard.
"No manual configuration. AI-SENTRY detects the model type and configures itself."

**Feature 2 — Three-Engine Orchestration:**
Three panels side-by-side:
- GARAK (NVIDIA Research): Systematic probe-based scanning. 100+ probe types. Reproducible.
- PyRIT (Microsoft): Multi-turn adversarial simulation. Dialogue-dependent vulnerabilities.
- DeepTeam (Confident AI): Metric-driven evaluation. Bias, hallucination, toxicity scored.

**Feature 3 — Normalized Vulnerability Schema:**
Visual: three raw output boxes feeding into one clean finding card.
"Each engine speaks a different language. AI-SENTRY normalizes everything into a single
Vulnerability Finding schema. Deduplicated. Corroboration-counted. OWASP-mapped."
Schema field preview: `vulnerability_class`, `source_engines`, `confidence_score`, `attack_success_rate`

**Feature 4 — Explainable Dual-Axis Scoring:**
Side-by-side Severity card and Confidence card.
"Severity is not Confidence. And we show both."
Severity card: HIGH badge with plain-English rationale.
Confidence card: 0.88/1.0 with five contributing factors and directional indicators.

**Feature 5 — Remediation Engine:**
Finding card expanding to three-level remediation:
- Model Level: fine-tuning and RLHF targeting recommendations
- System Level: output filters, prompt hardening, structured output constraints
- Deploy Level: Bedrock Guardrail settings, CloudWatch alarm recommendations

**Feature 6 — Deployment Advisor:**
Platform comparison table mockup (AWS / Azure / GCP columns).
"Deploy to AWS with one click. No Terraform. No console. Just a plan you review and approve."

**Feature 7 — Reports (PDF, HTML, JSON):**
"Every report includes an OWASP LLM Top 10 coverage map — including what was NOT tested and why."
PDF: share with stakeholders, CISO, compliance reviewers.
HTML: self-contained, embeddable, shareable link.
JSON: CI/CD integration, programmatic consumption.

**Feature 8 — Privacy and Safety Design:**
- API keys stored in OS keychain only — never files, never logs
- Probe content encrypted at rest
- No scan data leaves your machine for local model scanning (fully air-gapped)
- No telemetry by default — opt-in only, clearly documented
- Consent gate before every scan — cost and adversarial content disclosed upfront

**Feature 9 — Comparison Table:**
AI-SENTRY vs. running each engine manually vs. paid red team engagement.
Rows: multi-engine scan, unified report, zero setup, confidence scoring, OWASP mapping,
remediation guidance, cloud deployment, approximate cost.

---

## Page 3: How It Works ( /how-it-works )

**Purpose:** Remove uncertainty. Show exactly what happens. Make the process feel simple and trustworthy.

**Page Header:**
"From Model to Secure Deployment in Four Steps"
"No setup. No terminal. No guesswork."

**Step 1 — Connect Your Model:**
Animated illustration: form being filled, Test Connection clicked, green checkmark appears.
"Paste your API endpoint and key — or drop in your GGUF file.
AI-SENTRY validates the connection and estimates scan cost before anything runs.
Supported: OpenAI, Azure OpenAI, HuggingFace, Local GGUF, Custom REST."

**Step 2 — Configure and Confirm:**
Scan configuration screen mockup with Quick / Standard / Deep preset cards.
"Choose a scan depth or customize probe categories.
AI-SENTRY shows the estimated cost, duration, and exactly what adversarial content
will be sent — before you confirm. Nothing runs without your approval."

**Step 3 — Scan Runs:**
Live scan progress screen with three engine panels and a real-time findings feed.
"Garak, PyRIT, and DeepTeam run in parallel. You watch findings appear in real-time.
The rate limiter protects your API budget.
Pause or cancel at any time. Partial results are always preserved."

**Step 4 — Report and Deploy:**
Split visual: results dashboard left, deployment comparison table right.
"Your unified report arrives fully scored, explained, and actionable.
Every finding has a severity, a confidence breakdown, and three levels of remediation.
The Deployment Advisor reads your risk profile and configures secure cloud infrastructure.
AWS one-click deployment provisions everything in minutes."

**FAQ Accordion (6 questions addressing key objections):**

Q: Does AI-SENTRY send my API key anywhere?
A: Never. Your API key is stored in your OS keychain and used only to send probes to your model.
AI-SENTRY has no server. Nothing is transmitted to us at any point.

Q: How much does it cost?
A: AI-SENTRY itself is free and open source. API-based scans incur your normal API provider costs.
We estimate these upfront before the scan begins — you always know before you commit.

Q: Does it work on local models?
A: Yes. GGUF models up to ~30B parameters on sufficient hardware. We detect your system specs
and tell you exactly what is supported before scanning begins.

Q: Is this a one-time scan or ongoing monitoring?
A: AI-SENTRY is a pre-deployment validator, not a runtime monitor. Run it before you ship.
Repeat it before major model or configuration updates.

Q: What if an engine fails during the scan?
A: The scan continues with the remaining engines. The final report clearly marks which
OWASP LLM Top 10 categories have reduced coverage, and why.

Q: How is this different from running Garak or PyRIT alone?
A: One engine gives you partial coverage in one proprietary output format. AI-SENTRY runs all three,
deduplicates findings across engines, tracks corroboration, scores everything with transparent logic,
adds remediation guidance, and connects to deployment configuration. A different category entirely.

---

## Page 4: Download ( /download )

**Purpose:** Primary conversion page. Maximum clarity, maximum trust, minimum friction.

**Page Header:**
"Download AI-SENTRY"
"Free. Open Source. No setup required."
"Current Version: v1.0.0 — Released 2026-10-01"

**Platform Download Cards (two large cards, side-by-side):**

Windows Card:
```
AI-SENTRY for Windows
Version: 1.0.0  |  AI-Sentry-Setup-1.0.0.exe  |  ~12 MB
Requires: Windows 10 64-bit or later

[↓ Download for Windows]   ← large primary button

SHA256: abc123def456...   [Copy Checksum]

To verify:  CertUtil -hashfile AI-Sentry-Setup-1.0.0.exe SHA256
```

Linux Card:
```
AI-SENTRY for Linux
Version: 1.0.0  |  AI-Sentry-1.0.0.AppImage  |  ~18 MB
Requires: Ubuntu 20.04+ or equivalent glibc

[↓ Download for Linux]   ← large primary button
Also available: .deb (Ubuntu/Debian)

SHA256: 789abc012def...   [Copy Checksum]

To verify:  sha256sum AI-Sentry-1.0.0.AppImage
```

**System Requirements:**
```
Minimum:              Windows 10 64-bit or Ubuntu 20.04+
RAM:                  8 GB minimum (16 GB recommended)
Disk:                 500 MB free

For local GGUF scanning:
  Up to  7B params:   8 GB RAM (no GPU required)
  Up to 13B params:   16 GB RAM recommended
  Up to 30B params:   32 GB RAM or dedicated GPU
  Over 30B params:    Not recommended locally — use API mode
```

**Trust Verification Block:**
```
All releases include:
  ✓  SHA256 checksums published on this page
  ✓  Code-signed (Windows Authenticode certificate)
  ✓  GPG-signed (Linux releases)

View full source on GitHub: [github.com/ai-sentry/ai-sentry]
  Source code · Issue tracker · Build pipeline

Bundled engine versions (v1.0.0):
  Garak: v0.9.0.14  |  PyRIT: v0.5.0  |  DeepTeam: v1.4.0
```

**Previous Versions:**
Collapsible accordion "Show older versions" — last 5 releases with download links + changelog links.

**Post-Download Guidance:**
```
After downloading:
  1. Run the installer (no terminal needed)
  2. Launch AI-SENTRY from your desktop shortcut
  3. Follow the 4-screen guided setup

Need help?  → Getting Started Guide
Found a bug? → Open an Issue on GitHub
```

---

## Page 5: Documentation Hub ( /docs )

**Structure:**
- `/docs` homepage: quick-start box ("5 minutes from install to first scan"), section cards, search bar
- Individual pages: left sidebar navigation (collapsible on mobile), main content, right anchor-link sidebar

**Documentation Sections:**

`/docs/getting-started`
Installation step-by-step for Windows and Linux (with screenshots), first scan walkthrough,
understanding the results dashboard, downloading your first report.

`/docs/model-support`
Supported model types comparison table, OpenAI / Azure OpenAI / HuggingFace setup guides,
local GGUF model setup, hardware requirements matrix by model size, troubleshooting connection errors.

`/docs/scan-categories`
What each of the probe categories tests, which OWASP LLM Top 10 risk it maps to,
which engines provide coverage per category, categories not covered and why, custom category selection.

`/docs/confidence-scoring`
How severity tier is assigned (the SeverityMatrix logic), how confidence is calculated
(all five factors explained individually), how to read dual-axis scores, practical guidance:
"my confidence is 0.52 — should I act on this?", examples of high/low confidence scenarios.

`/docs/schema-reference`
Complete VulnerabilityFinding schema (all fields, types, enums), ScanManifest schema,
Report JSON format, field-by-field definitions, annotated example JSON output.

`/docs/deployment-guide`
How the Deployment Advisor works and how it reads your findings, AWS one-click deployment
full walkthrough with screenshots, exact IAM policy required (copy-pasteable), Azure and GCP
configuration guidance (manual, no one-click in v1), resource cleanup guide (how to tear down
everything AI-SENTRY created in your AWS account).

---

## Page 6: Roadmap ( /roadmap )

**Purpose:** Communicate ambition. Show active development. Manage expectations honestly.

**Layout:** Vertical timeline with phase cards. Status legend at top.
Status indicators: ✅ Complete | 🔄 In Progress | 📋 Planned | 💡 Exploring

```
✅  v1.0 — Foundation (Released October 2026)
    Multi-engine scanning (Garak, PyRIT, DeepTeam)
    Unified normalized report + explainable confidence scoring
    AWS one-click deployment with Bedrock Guardrails
    Windows + Linux desktop application

📋  v1.5 — Developer Workflow (Q1 2027)
    CLI interface for terminal users
    GitHub Actions integration (scan in CI/CD pipeline)
    Azure + GCP one-click deployment
    Scan comparison across runs (regression detection)
    Custom probe category selection (advanced mode)

📋  v2.0 — Platform (Q3 2027)
    SaaS offering with team collaboration and browser access
    Native GitHub App for CI/CD integration
    Model versioning and regression tracking across versions
    Industry benchmark comparison (anonymized)
    Multi-modal scanning (vision-language models)

💡  Future Exploration
    AI-SENTRY Certification mark for vetted models
    Runtime monitoring companion (post-deployment)
    Regulatory compliance report templates (EU AI Act)
    LLM security knowledge graph API
```

Call to action below: "Have a feature request? Open a GitHub Discussion"

---

## Page 7: Changelog ( /changelog )

**Purpose:** Signal that the product is alive and improving. Show version discipline.

**Changelog index** (`/changelog`): chronological list of all versions with release date and one-line summary.

**Per-version page** (`/changelog/1.0.0`):
```
v1.0.0 — October 1, 2026
[↓ Download this version]

New Features
  • Multi-engine orchestration: Garak, PyRIT, DeepTeam run in parallel
  • Unified VulnerabilityFinding schema v1.0 — deduplicated, OWASP-mapped
  • Explainable confidence scoring with five-factor model
  • AWS one-click deployment with Bedrock Guardrail configuration
  • Report export: PDF (local rendering), HTML (self-contained), JSON

Known Issues
  [GH-12] PyRIT scanner may time out on endpoints with >3s average latency
  [GH-19] Linux AppImage requires fuse2 on some older distributions

Breaking Changes
  None (initial release)

SHA256 Checksums
  Windows .exe:    abc123def456...
  Linux AppImage:  789abc012def...
```

---

## Page 8: Blog ( /blog )

**Purpose:** Organic search acquisition. Establish AI-SENTRY as a knowledgeable voice in LLM security.

**Initial Six Posts (launch content):**

| Title | Target Keyword | Persona |
|---|---|---|
| What is Prompt Injection and How Do You Test for It? | prompt injection testing | Developer |
| Jailbreaking LLMs: What DAN Is and Why It Still Works | jailbreak LLM testing | Security researcher |
| How AI-SENTRY Computes Confidence Scores (Full Explanation) | LLM security scoring | Enterprise |
| OWASP LLM Top 10: A Practical Testing Guide | OWASP LLM top 10 | All |
| Garak vs PyRIT vs DeepTeam: What Each Tool Actually Does | Garak vs PyRIT comparison | Developer |
| Securing Your LLM on AWS: Bedrock Guardrails Explained | AWS Bedrock Guardrails LLM | Developer |

**Blog index page layout:**
Card grid — title, tag, author, date, 2-line excerpt, estimated read time.
Filter bar: Security Research | Tutorials | Product | Announcements.

**Individual post page layout:**
Header image, article headline, author/date/read-time metadata, table of contents (sticky on desktop),
full article body, "Related posts" section at bottom, social share links.

---

## Page 9: About ( /about )

**The Problem We Are Solving:**
"LLMs are being deployed into products used by millions of people — and most have never been
seriously tested for adversarial behavior. Not because developers do not care. Because the tooling
was too hard, too fragmented, and too disconnected from the deployment process. AI-SENTRY changes that."

**What We Believe:**
- Security should not require a PhD to perform.
- Every developer deserves to know if their model is safe before it reaches their users.
- Transparency is not optional — every score must show its work.
- "Ship it and see" is not a security posture.

**Built On the Shoulders of Giants:**
"AI-SENTRY does not reinvent LLM security research. We build on top of it:
Garak (NVIDIA Research), PyRIT (Microsoft Security), DeepTeam (Confident AI).
Our contribution is orchestration, normalization, scoring transparency, and deployment intelligence."

**Open Source section** with prominent GitHub link and repository stats (stars, forks, contributors).

---

## Page 10: Contact ( /contact )

```
Get in Touch

Bug reports and feature requests:
  → GitHub Issues   [Open an Issue]

Security vulnerabilities (please do not post publicly):
  → security@ai-sentry.dev
  We respond within 72 hours.

Enterprise inquiries:
  → enterprise@ai-sentry.dev

General feedback:
  → Contact form below
    Name: [optional]
    Email: [optional, used only to reply]
    Message: [required]
    [Send Message]

Community:
  → [Join our Discord]
```

Contact form: honeypot anti-spam field. No CAPTCHA — too much friction for a developer audience.

---

## Legal Pages

**Privacy Policy** (`/legal/privacy`):
Written in plain English, not legalese. Sections: what we collect on the website (aggregate only,
no personal data), what we explicitly do NOT collect, desktop app telemetry (opt-in, default off),
website analytics (Plausible — no personal data, no cookies), data retention, third-party services
list, your GDPR rights, contact email: privacy@ai-sentry.dev.

**Terms of Service** (`/legal/terms`):
Permitted use (testing models you own or are authorized to test), prohibited use (explicitly:
testing systems without authorization), limitation of liability, open-source licensing reference
(MIT or Apache 2.0), changes to terms.

**Cookie Policy** (`/legal/cookies`):
"AI-SENTRY's website uses Plausible Analytics, which sets no cookies and stores no personal data.
We do not use advertising, tracking, or third-party cookies of any kind.
No cookie consent banner is shown on this website because no cookies are set."

---

## System Pages

**Custom 404:**
Dark theme maintained. Subtle animation: a scan beam sweeping and finding nothing.
Headline: "This page doesn't exist. But your LLM vulnerabilities might."
Subtext: "Let's find something useful for you:"
Links: Home, Download, Docs Getting Started.

**robots.txt:**
```
User-agent: *
Allow: /
Disallow: /api/

Sitemap: https://ai-sentry.dev/sitemap.xml
```

**sitemap.xml:**
Auto-generated on every Vercel deployment. Includes all pages, blog posts, doc pages, changelog versions.
Excludes: /api/*, any admin paths.

---

# SECTION 4 — DESIGN SYSTEM

## 4.1 Visual Identity and Tone

**Tone:** Authoritative. Precise. Technical. Not playful, not corporate.
The design should feel like it was built by people who understand security — not a marketing agency.
It must say "we know what we're talking about" without being intimidating.

**Aesthetic:** Sophisticated terminal meets modern SaaS. Similar energy to Vercel's dashboard,
Linear's interface, or Tailscale's website — but with a security/threat-detection layer.

---

## 4.2 Color Palette

**Background System:**
```
Deep Background:    #0A0B0F    (near black, blue-black tint — never pure #000)
Surface:            #111318    (cards, panels, content areas)
Surface Elevated:   #1A1D24    (modals, hover states, dropdowns)
Border Default:     #252831    (subtle dividers, default card borders)
Border Active:      #363B47    (active borders, focus rings, hover borders)
```

**Text System:**
```
Primary:            #F0F2F8    (near white, slightly warm — all body text)
Secondary:          #9499A8    (muted — subtitles, metadata, labels)
Tertiary:           #5C6070    (very muted — placeholders, disabled states)
```

**Accent System:**
```
Primary Accent:     #3D7EFF    (electric blue — trust, action, all primary CTAs)
Accent Hover:       #5590FF    (lightened blue on hover)
Accent Glow:        rgba(61, 126, 255, 0.15)   (ambient glow behind CTA buttons)
```

**Severity Color System (maps to instant cognitive recognition — no legend required):**
```
Critical:           #FF4040    (pure red — immediate action required)
High:               #FF8C00    (amber — serious concern)
Medium:             #FFD700    (gold — caution warranted)
Low:                #3DFF9A    (mint green — minor, informational in nature)
Informational:      #9B9FFF    (lavender — neutral, context only)
```

**Gradient System:**
```
Hero background:    linear-gradient(135deg, #0A0B0F 0%, #0D1525 50%, #0A0B0F 100%)
Primary CTA:        linear-gradient(90deg, #2060CC, #3D7EFF)
Card hover glow:    radial-gradient(circle at 50% 100%, rgba(61,126,255,0.08), transparent 70%)
```

**Design rationale:**
- Deep navy-black (#0A0B0F) avoids the harshness of pure black while maintaining the dark theme
- Electric blue (#3D7EFF) is reserved exclusively for trust and action — not decorative use
- No green as a primary action color — green implies "all clear," exactly the wrong message here
- The severity color system is chosen for instant cognitive legibility without a legend

---

## 4.3 Typography

**Primary Typeface: Inter**
Used by Vercel, Linear, Figma, Stripe — the standard of precision developer tooling.
Excellent legibility at all sizes. Best-in-class number rendering for score displays.

```
Display / Hero Headline:    Inter 700, 56–72px, letter-spacing: -1.5px
Section Headline:           Inter 600, 36–44px, letter-spacing: -0.8px
Subsection Headline:        Inter 600, 24–28px, letter-spacing: -0.3px
Body Large:                 Inter 400, 18px, line-height: 1.7
Body:                       Inter 400, 16px, line-height: 1.6
Label / Tag / Badge:        Inter 500, 13px, letter-spacing: 0.5px, UPPERCASE
```

**Code / Monospace Typeface: JetBrains Mono**
Used for: schema field names, code snippets, score values, terminal-style content blocks,
SHA256 checksums.

```
Code body:                  JetBrains Mono 400, 14px, line-height: 1.5
Score display (prominent):  JetBrains Mono 600, 24px
Checksum display:           JetBrains Mono 400, 13px
```

**Font delivery:** Self-hosted woff2, Latin subset only (~30 KB per font weight vs ~300 KB full).
`font-display: swap` prevents invisible text during load (FOIT).
Preloaded in document `<head>` for fastest LCP.
No Google Fonts dependency — eliminates third-party DNS lookup and privacy concern.

---

## 4.4 UI Component Specifications

**Buttons:**
- Primary: #3D7EFF background, white text, 8px border-radius, subtle drop shadow (0 4px 16px rgba(61,126,255,0.3))
- Hover: brightness increases, scale(1.02), 150ms ease-out
- Secondary: transparent background, 1px solid #3D7EFF border, #3D7EFF text
- Destructive: #FF4040 background — reserved only for irreversible actions

**Cards:**
- Background: #111318 (Surface)
- Border: 1px solid #252831, 12px border-radius
- Hover: border brightens to #363B47, subtle radial glow at bottom edge, 200ms ease

**Form Inputs:**
- Background: #0A0B0F (drops to Deep Background — creates visual inset against Surface)
- Border: 1px solid #252831
- Focus: border transitions to #3D7EFF with soft ambient glow (box-shadow)

**Severity Badges (all use 15% opacity background, full text color, 30% border opacity):**
```
Critical: rgba(255,64,64,0.15) bg / #FF4040 text / rgba(255,64,64,0.30) border
High:     rgba(255,140,0,0.15) bg / #FF8C00 text / rgba(255,140,0,0.30) border
Medium:   rgba(255,215,0,0.15) bg / #FFD700 text / rgba(255,215,0,0.30) border
Low:      rgba(61,255,154,0.15) bg / #3DFF9A text / rgba(61,255,154,0.30) border
Info:     rgba(155,159,255,0.15) bg / #9B9FFF text / rgba(155,159,255,0.30) border
```

---

## 4.5 Animation System

**Core philosophy:** Animations enhance comprehension — they do not exist for novelty.
Every animation communicates something meaningful. Motion is precise, controlled, purposeful.
No bounce physics, no spring animations — security tools feel measured, not playful.

**Scroll-triggered entry animations:**
Elements entering viewport: fade-in + translate-Y (0px from 20px below), opacity 0→1.
Stagger delay between sibling elements: 100–150ms.
Duration: 400–600ms, ease-out cubic-bezier(0.16, 1, 0.3, 1).
Implementation: IntersectionObserver API — no scroll event listeners (better performance).

**Hero scan visualization (looping CSS/SVG, 6-second cycle):**
- Abstract LLM node centered; three engine nodes at edges
- Probe beams animate from each engine toward the LLM in staggered sequence
- Vulnerability markers light up in severity colors as each beam lands
- Report card slides in from right, counts populate via counter animation
- Scene fades softly; loop restarts
- Pure CSS keyframe animations on SVG elements — zero JavaScript animation libraries needed

**Page transitions:** 200ms opacity fade. No sliding panels or dramatic route transitions.
Returning users navigate fast — dramatic transitions are obstacles.

**Hover microinteractions:**
- Cards: border glow eases in over 200ms
- Primary buttons: scale(1.02) + brightness(1.1), 150ms ease-out
- Navigation links: underline animates from left to right (width 0%→100%), 200ms
- Download buttons: arrow icon translates +4px on hover, returns on mouse-leave

**Counter animations:**
Numeric stats count up from 0 when entering viewport. Duration: 800ms, ease-out.
Used for impactful numbers (finding counts, probe counts) — not as decoration.

**Progress/loading states:**
Shimmer sweep animation on progress bars (not spinning circles).
Shimmer communicates linearity and precision — appropriate for a security scanning context.

---

# SECTION 5 — DOWNLOAD SYSTEM

## 5.1 Download Flow

User arrives at `/download`. Sees two platform cards. Clicks download button.
File begins downloading immediately from CDN/GitHub.
No email capture. No account creation. No waitlist. No redirect through a marketing page.

This zero-friction philosophy is deliberate: every additional step between intent and download
is a conversion point where users leave. Security-conscious developers are suspicious of websites
that demand personal information before a free software download.

---

## 5.2 File Hosting Architecture

**Primary host: GitHub Releases**
- Free bandwidth for open-source repositories (no limit)
- Built-in version tagging and release notes
- Community-verifiable source of truth
- Permanent asset URLs per version (prevent link rot)
- Download buttons link directly to the GitHub Release asset for the current version

**Mirror: Cloudflare R2 (or Backblaze B2)**
- Shown as a secondary link below the primary download button
- Used when GitHub has connectivity issues in certain regions
- Contains identical binaries — users can verify with the same published checksum

**Download page shows both options:**
```
[↓ Download from GitHub]   ← primary, large
[Mirror Download]          ← secondary, smaller, below
```

---

## 5.3 Versioning Strategy

Semantic versioning: `MAJOR.MINOR.PATCH`
```
1.0.0  — Initial public release
1.0.1  — Patch release (bug fix only, no feature changes)
1.1.0  — Minor release (new features, backward compatible)
2.0.0  — Major release (breaking changes, migration required)
```

**Version API endpoint:** `GET https://ai-sentry.dev/api/version/latest`
```json
{
  "version": "1.2.0",
  "released_at": "2026-10-01",
  "download_url": "https://ai-sentry.dev/download",
  "release_notes_url": "https://ai-sentry.dev/changelog/1.2.0",
  "sha256_windows": "abc123...",
  "sha256_linux_appimage": "def456...",
  "sha256_linux_deb": "ghi789...",
  "minimum_supported": "1.0.0"
}
```

Rate limited: 10 requests per IP per hour. Returns static JSON. Logs nothing.
Updated manually as part of each release process.

---

## 5.4 Checksum Display and Verification

Both SHA256 checksums displayed on the download page in monospace font.
Each checksum has a `[Copy]` button that copies it to clipboard with a confirmation flash.

Collapsible "How to verify this download" section (collapsed by default to avoid overwhelming
first-time users, available for security-conscious users):

```
Windows:
  CertUtil -hashfile AI-Sentry-Setup-1.0.0.exe SHA256
  Compare the output to the Windows SHA256 shown above.

Linux:
  sha256sum AI-Sentry-1.0.0.AppImage
  Compare the output to the Linux AppImage SHA256 shown above.

If the values match, your download is authentic and unmodified.
```

---

## 5.5 Update Handling in the Desktop App

Desktop app checks `GET /api/version/latest` on each startup (skipped if offline).

**Three possible states:**

1. **Current version** — No notification. Continue normally.

2. **New version available (above minimum_supported):**
   Non-blocking notification bar at top of screen:
   "AI-SENTRY v1.2.0 is available. [What's New] [Download Update]"
   User can dismiss and continue working indefinitely.

3. **Installed version below minimum_supported:**
   Blocking modal (cannot be dismissed):
   "This version is no longer supported. Please update to v1.2.0 to continue."
   Direct link to `/download`. App cannot be used until updated.

**Updates are never automatic.** User always controls when they download and install.
Engine dependency updates (Garak, PyRIT, DeepTeam version bumps) are bundled in each app
release — users never need to separately manage scanning engine versions.

---

# SECTION 6 — SEO STRATEGY

## 6.1 Keyword Targeting

**Primary keywords (high intent, product-specific):**
```
"LLM security scanner"             — homepage, features page
"AI red teaming tool"              — features, how-it-works
"LLM vulnerability assessment"     — homepage, features
"jailbreak testing tool LLM"       — features, blog
"Garak PyRIT scanner"              — features, blog comparison post
```

**Secondary keywords (educational, informational, top-of-funnel):**
```
"what is prompt injection"          — blog post → links to product
"OWASP LLM top 10 testing"         — blog post → links to features
"LLM deployment security"          — how-it-works, deployment guide
"AI safety testing before deployment" — homepage, how-it-works
```

**Long-tail keywords (low competition, high conversion intent):**
```
"how to test LLM for jailbreaks"
"LLM red teaming open source"
"scan AI model for vulnerabilities"
"compare LLM security scanning tools"
"AWS Bedrock Guardrails LLM setup"
```

---

## 6.2 Meta Title Strategy (Per Page)

All titles: 50–65 characters. Unique per page. Primary keyword near the front.

```
Homepage:        AI-SENTRY — LLM Security Scanner | Scan Before You Ship
Features:        AI-SENTRY Features | Multi-Engine LLM Vulnerability Testing
How It Works:    How AI-SENTRY Works | LLM Security in 4 Steps
Download:        Download AI-SENTRY | Free LLM Security Tool for Windows and Linux
Docs Home:       AI-SENTRY Documentation | Getting Started and Reference
Docs Scoring:    How AI-SENTRY Confidence Scores Work | AI-SENTRY Docs
Roadmap:         AI-SENTRY Roadmap | Future LLM Security Platform Features
Changelog:       AI-SENTRY Changelog | Version History and Release Notes
Blog Index:      AI-SENTRY Blog | LLM Security Research and Tutorials
Blog Post:       [Post Title] | AI-SENTRY Blog
About:           About AI-SENTRY | LLM Security Orchestration Platform
Privacy:         Privacy Policy | AI-SENTRY
Terms:           Terms of Service | AI-SENTRY
```

**Title formulas:**
- Homepage: `[Brand] — [Value Prop] | [Primary Keyword]`
- Content pages: `[Primary Keyword or Topic] | [Brand]`
- Documentation: `[Topic Explained] | [Brand] Docs`

---

## 6.3 Meta Description Strategy

All descriptions: 140–160 characters. Unique. Contains primary keyword. Includes an action verb.

```
Homepage (155 chars):
"AI-SENTRY runs Garak, PyRIT, and DeepTeam to find LLM vulnerabilities before you deploy.
Free, open source. Download for Windows and Linux."

Features (152 chars):
"Multi-engine LLM scanning with unified reporting, explainable confidence scores, and one-click
AWS deployment. See everything AI-SENTRY does."

Download (151 chars):
"Download AI-SENTRY free for Windows and Linux. No setup, no terminal required. The complete
LLM security scanner in one installer."

Blog post formula:
"[Hook with primary keyword in first sentence.] [What the reader will learn or be able to do.]"
```

---

## 6.4 URL Structure Rules

```
Rules:
  All lowercase
  Hyphens for word separation (never underscores, never camelCase)
  No trailing slashes (except root /)
  Short and descriptive
  Include primary keyword naturally

Good examples:
  /features
  /how-it-works
  /docs/confidence-scoring
  /blog/what-is-prompt-injection
  /changelog/1.0.0

Bad examples (never use):
  /Features
  /how_it_works
  /docs/confidenceScoring
  /blog?post=prompt-injection
  /changelog?v=1.0.0
```

---

## 6.5 Structured Data (Schema.org)

**Homepage and Download page:** `SoftwareApplication` schema
```json
{
  "@type": "SoftwareApplication",
  "name": "AI-SENTRY",
  "applicationCategory": "SecurityApplication",
  "operatingSystem": "Windows, Linux",
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },
  "description": "Multi-engine LLM security orchestration platform. Scans with Garak, PyRIT, and DeepTeam.",
  "url": "https://ai-sentry.dev"
}
```

**Blog posts:** `Article` schema with `headline`, `datePublished`, `dateModified`, `author`.

**How It Works — FAQ accordion:** `FAQPage` schema with `Question` + `acceptedAnswer` per item.
FAQPage schema makes the FAQ eligible for Google FAQ rich results (expanded SERP entries) — direct
click-through rate improvement without any ranking work.

---

## 6.6 Technical SEO

**Server-side rendering (Next.js):** all content pages deliver full HTML to search bots and users.
Not a blank JavaScript shell requiring client-side execution to render content.

**Core Web Vitals targets:**
```
LCP (Largest Contentful Paint):  < 2.5 seconds
INP (Interaction to Next Paint):  < 200ms
CLS (Cumulative Layout Shift):    < 0.1
FCP (First Contentful Paint):     < 1.5 seconds
TTFB (Time to First Byte):        < 600ms
Total homepage payload:           < 500 KB
```

**Canonical tags:** every page has a self-referencing canonical URL to prevent duplicate content
from URL parameter variants or www/non-www inconsistencies.

**Internal linking strategy:**
- Every blog post links to at least one relevant feature page (funnel visitors to conversion)
- Every doc page links to the Download page (in sidebar or inline)
- How It Works links to Features and Download
- Features page has multiple Download CTAs

**Sitemap.xml:** auto-generated on every Vercel deployment. Submitted to Google Search Console
and Bing Webmaster Tools at launch.

---

# SECTION 7 — ANALYTICS AND TRACKING

## 7.1 Analytics Platform: Plausible Analytics

**Why Plausible:** No cookies set. No personal data collected. GDPR-compliant without a cookie
consent banner. Open-source and auditable. EU-hosted. Consistent with AI-SENTRY's privacy-first
positioning.

**Explicitly not used:** Google Analytics 4, Hotjar, Mixpanel, Segment, FullStory, or any tool
that requires cookie consent or collects personally identifiable information.

---

## 7.2 Tracked Events and Metrics

**Page-level (automatic, built-in):**
- Unique visitors per page (privacy-safe daily hash — not persistent cross-session tracking)
- Page views, session duration estimate, bounce rate per page
- Referrer sources: search / direct / social / GitHub / other (grouped — no individual URLs)
- Device type: mobile / desktop / tablet
- Country: country-level only — no city, no region, no IP address logged
- OS: useful for understanding Windows vs. Linux download distribution

**Custom events (Plausible custom events API):**
```
"Download Windows"         — fired on Windows .exe download button click
"Download Linux AppImage"  — fired on AppImage download button click
"Download Linux deb"       — fired on .deb download button click
"Hero CTA Click"           — fired on homepage hero CTAs (distinguishes from /download page)
"Docs Getting Started"     — fired on getting-started link click from docs homepage
"GitHub Source View"       — fired on any GitHub repository link click
```

**Intentionally NOT tracked:**
- Individual user sessions across pages
- IP addresses (beyond coarse country-level geolocation)
- Any personal identifiers
- Scroll depth, mouse movement, click heatmaps
- Session recordings of any kind

---

## 7.3 Weekly Reporting Dashboard

**Primary KPI:** Downloads per week (tracked via custom events)

**Weekly metrics to review:**
- Download conversion rate: visitors to `/download` who click a download button
- Top referral sources: identifies which channels are working (search vs GitHub vs other)
- Top documentation pages: signals what users struggle with after downloading
- Blog post traffic and downstream navigation to `/download`: content ROI measurement
- OS distribution: Windows vs. Linux ratio (informs engineering priority)

---

# SECTION 8 — COOKIE AND PRIVACY SYSTEM

## 8.1 Cookie Inventory

**Plausible Analytics:** sets zero cookies (uses privacy-preserving daily hashing).
**Website first-party functionality:** no session cookies, no preference cookies, no tracking cookies.
**Contact form:** no cookies set.

**Result: ai-sentry.dev sets ZERO cookies, first-party or third-party.**

---

## 8.2 Cookie Banner Decision: No Banner

Because no cookies are set, EU GDPR and the ePrivacy Directive do not require a consent banner.
Displaying a banner would be actively misleading — implying cookies exist when they do not.

This is a competitive differentiator: most tech websites have friction-adding cookie banners.
AI-SENTRY has none. The Cookie Policy page at `/legal/cookies` explains this explicitly.

---

## 8.3 Data Collection Summary

**Website visitors (aggregate, non-personal):**
Page view counts, country of origin (country only), referrer source (grouped), device type,
OS type, download event counts. Cannot be used to identify an individual. Not linked across sessions.

**Contact form submissions:**
Name (optional), email (optional), message text, submission timestamp.
Stored in team email inbox only. Not processed by a third-party CRM. Not used for marketing.
Deleted on request.

**Desktop app telemetry (opt-in, default OFF):**
If user explicitly opts in via Settings: anonymized scan count, scan depth distribution, OS type.
Never includes: scan results, probe content, model names, API keys, or any PII.
User can disable at any time. Opt-in data deleted on request.

---

## 8.4 GDPR Compliance

| GDPR Requirement | AI-SENTRY Website Status |
|---|---|
| Lawful basis for analytics | Legitimate interest (aggregate, non-personal data, no tracking) |
| Cookie consent | Not required (zero cookies set) |
| Privacy Policy | Published at /legal/privacy in plain English |
| Right to access | Email privacy@ai-sentry.dev |
| Right to deletion | Contact form data deleted on request; analytics data is aggregate only, cannot be tied to individual |
| Data processor agreements | Plausible Analytics (EU-hosted; DPA available on request) |
| Data retention | Aggregate analytics: indefinite; Contact data: until resolved or deleted on request |

---

# SECTION 9 — PERFORMANCE AND MOBILE

## 9.1 Core Web Vitals Targets

| Metric | Target | Threshold |
|---|---|---|
| LCP (Largest Contentful Paint) | < 2.5 seconds | Good |
| INP (Interaction to Next Paint) | < 200ms | Good |
| CLS (Cumulative Layout Shift) | < 0.1 | Good |
| FCP (First Contentful Paint) | < 1.5 seconds | Good |
| TTFB (Time to First Byte) | < 600ms | Good |
| Total homepage payload | < 500 KB | — |

Measured with: PageSpeed Insights, Vercel Web Analytics, Chrome User Experience Report.

---

## 9.2 Image Optimization Strategy

**Format:** All images converted to WebP at build time using Next.js Image optimization.
SVG for all icons and illustrations — scalable, resolution-independent, typically under 5KB each.
PNG and JPG source files are never served to end users directly.

**CLS prevention:** every `<img>` element has explicit `width` and `height` attributes set.
This reserves layout space before the image loads — prevents the page jumping as images appear.

**Lazy loading:**
- Below-fold images: `loading="lazy"` (native browser lazy loading, no JavaScript)
- Above-fold / hero content: `loading="eager"` + `fetchpriority="high"` (preloaded immediately)

**Hero section:** contains zero image files. The scan visualization is pure CSS and SVG.
Zero bytes of image data needed for the most important visual element on the page.

**App mockup screenshots:** served as WebP with srcset at 1x and 2x for retina displays.
Maximum image width always matches its display size — never served wider than shown.

---

## 9.3 Font Loading Optimization

**Self-hosted:** Inter and JetBrains Mono hosted on Vercel, not loaded from Google Fonts.
Eliminates the Google Fonts DNS lookup + connection overhead (typically 50–100ms savings).
Also eliminates the Google Fonts privacy concern (Google logs font requests with IP addresses).

**Subsetting:** Latin character range only. ~30 KB per font weight vs ~300 KB for full Unicode.
Subset generated at build time using `pyftsubset` or equivalent.

**`font-display: swap`:** text renders immediately in a system fallback font, swaps to Inter
when the font loads. Prevents FOIT (Flash of Invisible Text).

**Preloading:** Inter 400, 600, 700 and JetBrains Mono 400 woff2 files are preloaded:
```html
<link rel="preload" href="/fonts/inter-latin-400.woff2" as="font" type="font/woff2" crossorigin>
```

---

## 9.4 JavaScript Minimization

The website is primarily server-rendered HTML. JavaScript is added only where necessary.

**JavaScript used for:**
- Mobile navigation menu toggle (hamburger → drawer)
- Accordion expand/collapse (FAQ, older versions, checksum verification)
- Scroll animation IntersectionObserver (replaces scroll event listeners — more performant)
- Plausible Analytics script (~2 KB, loaded async and deferred after page render completes)
- Copy-to-clipboard buttons (SHA256 checksums)
- Hero SVG animation controller (minimal — just initializes the CSS animation loop)

**JavaScript NOT used for:**
- Content rendering (Next.js server-side rendering handles this)
- Routing (Next.js App Router handles navigation)
- Styling (all CSS, no CSS-in-JS at runtime)
- Form submission (standard HTML form action)

**Target:** Total JavaScript on homepage under 40 KB gzipped.

---

## 9.5 Caching Strategy

**Static assets (fonts, images, CSS, JS):**
```
Cache-Control: public, max-age=31536000, immutable
```
All static assets are content-hashed at build time (filename includes content hash).
Example: `inter-latin-a3b4c5d6.woff2`
Browsers cache aggressively; after deployment, users automatically receive fresh files
because the filename hash changes with content.

**HTML pages:**
```
Cache-Control: public, max-age=3600, stale-while-revalidate=86400
```
Pages revalidated hourly. Users get cached version while fresh version loads in background.

**Version API (`/api/version/latest`):**
```
Cache-Control: public, max-age=3600
```
Version info rarely changes — 1-hour caching reduces origin load significantly.

---

## 9.6 Mobile Responsiveness Design

**Approach:** Mobile-first. Desktop is the enhanced experience, not the default.

**Breakpoints:**
```
Mobile:   ≤ 768px   — primary design target
Tablet:   769–1024px — enhanced mobile layout
Desktop:  ≥ 1025px  — full multi-column layouts
```

**All text sizes:** set in `rem` with fluid scaling using `clamp()`.
Example: `font-size: clamp(2.25rem, 5vw, 4.5rem)` for the hero headline.
No fixed pixel font sizes that overflow or become unreadably small.

**Mobile-specific layout changes:**
```
Navigation:         Hamburger → full-height slide-in drawer from right
Download cards:     Two columns → stacked single column
Feature sections:   Two columns → single column
Hero headline:      clamp scales from 36px (mobile) to 72px (desktop)
Comparison table:   Horizontal table → stacked cards per platform
Sticky bottom:      "Download AI-SENTRY" bar fixed to screen bottom on mobile
```

**Touch interaction requirements:**
- Minimum touch target: 44×44 CSS pixels (WCAG 2.1 AA)
- No hover-only interactions — every hover state has a tap equivalent
- Swipe-friendly carousel for How It Works steps on mobile
- `user-scalable=yes` in viewport meta (never disable user zoom)

---

# SECTION 10 — TECH STACK

## 10.1 Framework: Next.js 14 with App Router

**Primary rationale:**

**Server-side rendering by default.** All content pages deliver full HTML to search bots and users.
Not a blank JavaScript shell requiring client execution — critical for SEO.

**Static generation where appropriate.** Pages that don't change per-request (About, legal, changelog
entries) are statically generated at build time — zero server load, instant delivery from CDN edge.

**Built-in Image component.** Handles WebP conversion, lazy loading, srcset, and explicit dimensions
automatically — removes manual optimization effort.

**Route Handlers.** The `/api/version/latest` endpoint lives in the same codebase and deployment —
no separate API service to maintain.

**React Server Components.** Reduces the amount of JavaScript shipped to the client — less
downloaded, faster INP.

**Why not alternatives:**

| Alternative | Reason Not Chosen |
|---|---|
| Gatsby | Slower builds on growing content sites; community momentum behind Next.js |
| Astro | Excellent for content, but team investing in React for Tauri UI — same language for both |
| Remix | Strong framework; smaller ecosystem and community at time of decision |
| Plain HTML/CSS | No build pipeline = no image optimization, no content hashing, manual maintenance |
| Vite + React SPA | Client-side rendering only — bots see empty HTML; unacceptable for SEO |

---

## 10.2 Hosting: Vercel

**Primary rationale:**

- Next.js is developed by Vercel — zero-configuration deployment with native framework optimizations
- Free tier provides 100 GB bandwidth per month (sufficient for early-stage open-source launch)
- Edge CDN with 100+ global PoPs — excellent TTFB worldwide without DevOps configuration
- Automatic preview deployments on every pull request — review website changes before merge
- Automatic HTTPS via Let's Encrypt (zero configuration required)
- Vercel's Image Optimization CDN handles WebP transformation at the edge
- Zero ongoing DevOps overhead — no servers, no Nginx config, no Kubernetes maintenance

**Domain:** `ai-sentry.dev` configured via Vercel Domains dashboard or external registrar
with CNAME/A records pointing to Vercel's edge network.

---

## 10.3 Content Management: Markdown in Repository

**Blog posts and documentation:** `.md` and `.mdx` files in the Git repository.
No external CMS, no third-party API dependency, no monthly subscription.

**Advantages of markdown-in-repo:**
- Full git history for every word of content — complete audit trail
- Pull request workflow for content review and peer editing
- Docs and code are always in sync — same repository, same deployment pipeline
- MDX (Markdown + JSX) allows embedding React components in documentation pages
  (example: the confidence score breakdown widget embedded in the scoring doc)
- No CMS vendor lock-in. No outage risk from a third-party service

**Content directory structure:**
```
/content/blog/[slug].mdx              — blog posts
/content/docs/[section]/[page].mdx   — documentation pages
/content/changelog/[version].mdx     — per-version release notes
```

---

## 10.4 Supporting Services

| Service | Purpose | Choice | Rationale |
|---|---|---|---|
| Analytics | Privacy-respecting page tracking | Plausible Analytics (cloud) | No cookies, GDPR-compliant |
| Email | Contact form, team notifications | Resend or Postmark | Reliable transactional email API |
| File hosting | Release binaries | GitHub Releases + Cloudflare R2 | Free + reliable CDN mirror |
| Docs search | Full-text search in documentation | Algolia DocSearch | Free for open-source, excellent UX |
| Error tracking | Website runtime error monitoring | Sentry (free tier) | Ironic, but appropriate |

---

# SECTION 11 — BRAND POSITIONING

## 11.1 The Core Brand Tension and Its Resolution

**The tension:** AI-SENTRY is a security tool used by developers — not exclusively by security experts.

- **Too technical:** developers without a security background feel excluded → downloads drop
- **Too accessible:** security professionals don't trust it → enterprise adoption fails

**The resolution:** Precision with clarity.
Language is technically correct and precise. Every technical term is explained in plain English
the first time it appears. Design is serious and professional — but not intimidating. Tone is
confident — but never arrogant. Every claim is verifiable by design.

---

## 11.2 Trust Signals and How They Work

**Engine Attribution — Trust Signal #1:**
The trust bar immediately below the hero names NVIDIA Research, Microsoft, and Confident AI with
proper attribution. Message: we stand on the shoulders of established research. We do not pretend
to have invented everything.

**Open Source — Trust Signal #2:**
"View on GitHub" appears in the navigation, download page, and About page.
Every claim is verifiable. Source code is auditable. Build pipeline is visible.
For a developer audience, "don't trust us — verify us" is the highest possible trust statement.

**Checksum Publication — Trust Signal #3:**
SHA256 checksums with OS-specific verification commands on the download page communicate that
security is not just the product's subject — it is the product's practice. A team that doesn't
verify their own binaries cannot credibly sell security tooling.

**Honest Coverage Gaps — Trust Signal #4:**
Explicitly showing what AI-SENTRY does NOT test (and why) is a meaningful differentiator.
Most security tools oversell coverage. Honest gaps build more trust than overclaiming.

**Consent-First Language — Trust Signal #5:**
The How It Works page features the consent gate as a product feature, not a fine-print disclaimer.
This proactively addresses the unspoken concern: "will this tool start sending requests to my API
without my knowledge?" The explicit answer is no, and here is exactly how the consent system works.

---

## 11.3 Technical Credibility Communication

**Specificity of language (high-signal indicator of domain expertise):**
- Say "Garak, PyRIT, and DeepTeam" — not "multiple scanning engines"
- Say "DAN-style jailbreak probes" — not "adversarial inputs"
- Say "OWASP LLM Top 10" — not "industry standards"
- Say "attack_success_rate of 0.78 across 18 probe variants" — not "high success rate"
- Specificity signals mastery. Vague language signals surface-level knowledge.

**Schema field preview on Features page:**
Showing field names like `vulnerability_class`, `corroboration_count`, and `confidence_factors`
signals a thoughtfully designed data model underneath — not just a UI layer on top of one engine.

**Five-factor confidence score breakdown:**
Showing the formula with named factors and their rationale communicates that scoring is real,
reproducible, inspectable work — not a made-up number calibrated for marketing appeal.

**Engine-specific contribution sections:**
Explaining what Garak, PyRIT, and DeepTeam each uniquely contribute (not just listing them)
communicates genuine domain knowledge, not just a list of third-party integrations.

---

## 11.4 Innovation Signals

**The scan visualization animation:**
The hero animation visually represents something new: three-engine parallel scanning with
real-time finding detection. Target visitor reaction: "Wait, it runs all three simultaneously?"
If that question arises, the animation has done its job.

**Dual-axis scoring (Severity + Confidence):**
The side-by-side score cards introduce a mental model that most security tools skip entirely.
Target reaction: "I never thought about these separately before, but that's obviously right."
This is the strongest product innovation signal — a better mental model for an existing problem.

**The deployment gap:**
"From risk report to secure deployment — in the same workflow" names a gap that users live
but haven't articulated as a specific problem. Target reaction: "I always had to figure this out
as a completely separate, painful project." Naming an unarticulated problem is the highest form
of product positioning.

**Pre-deployment framing:**
"Scan before you ship" positions AI-SENTRY as filling a gap in the development lifecycle,
not as another standalone security audit tool that produces a PDF and then has no role in
what happens next.

---

## 11.5 Copywriting Voice Guidelines

These rules apply to all website copy, documentation, blog content, and in-app text:

| Rule | Bad Example | Good Example |
|---|---|---|
| Precise, not vague | "Advanced AI security" | "Three-engine LLM vulnerability scanning" |
| Active, not passive | "Vulnerabilities are detected" | "AI-SENTRY finds vulnerabilities" |
| Honest, not hype | "The most powerful AI security tool" | "The only tool that runs all three engines" |
| Specific numbers | "Many probe types" | "100+ probe categories across 3 engines" |
| Developer-first | "Secure your AI" | "Test your model before you ship it" |
| Respect intelligence | "It's super easy to use!" | "No manual setup required." |
| Confident, not arrogant | "Better than everything else" | "One tool instead of three." |

**Sentence structure:** Short sentences. Fragments acceptable for emphasis. No marketing fluff.
No exclamation points on feature descriptions — reserved only for genuine achievement moments
(e.g., "Deployment complete!"). Never use: "cutting-edge," "revolutionary," "game-changing,"
"best-in-class," "seamless," "robust," or "powerful."

---

## 11.6 Navigation as Brand Communication

The navigation structure itself makes brand statements:

- **"How It Works" in primary nav:** transparency is a first-class product value, not an afterthought
- **"Download" always in top-right:** the product is free; downloading is the natural next action
- **"Docs" in primary nav:** we take technical users seriously; documentation is not buried in a footer
- **Legal pages in footer but complete:** obligations are not hidden; privacy policy is reachable
- **No "Pricing" page in primary nav:** free means free. No "contact us for enterprise pricing." Developers distrust tools that hide the price.

---

## Summary: Website Design System Complete

This document defines the complete website system for AI-SENTRY v1.0.

**All 11 sections defined:**

| Section | What Was Defined |
|---|---|
| 1. Purpose | Primary conversion goal (download), full user journey, secondary goals |
| 2. Structure | Complete URL map (15+ pages), all navigation systems |
| 3. Pages | Detailed breakdown of every page — sections, content, layout |
| 4. Design System | Color palette (12 semantic colors), typography, components, animation philosophy |
| 5. Download System | GitHub Releases hosting, versioning, checksum display, update handling |
| 6. SEO Strategy | Keyword targeting, per-page meta titles/descriptions, structured data, URL rules |
| 7. Analytics | Plausible setup, custom download events, weekly KPI dashboard |
| 8. Cookie/Privacy | Zero cookies, no consent banner needed, GDPR compliance table |
| 9. Performance | Core Web Vitals targets, image/font/JS optimization, mobile responsiveness |
| 10. Tech Stack | Next.js 14 + Vercel, markdown-in-repo, Algolia, supporting services |
| 11. Brand Positioning | Trust signals, technical credibility, innovation framing, copywriting voice |

**Key decisions made in this document:**

```
Framework:          Next.js 14 (App Router) deployed on Vercel
Analytics:          Plausible Analytics (no cookies, no consent banner required)
Content:            Markdown-in-repo via MDX (no CMS dependency)
File hosting:       GitHub Releases (primary) + Cloudflare R2 (mirror)
Downloads:          Zero friction — no email, no account, no waitlist
Cookie banner:      None (zero cookies set on this website)
Docs search:        Algolia DocSearch (free for open-source projects)
Font hosting:       Self-hosted woff2, Latin subset only (no Google Fonts)
Error tracking:     Sentry (free tier) for website runtime errors
```

*End of Website Design Document v1.0*
