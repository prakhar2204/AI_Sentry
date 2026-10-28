# Sentryɸ — Master Implementation Plan

**Created:** 2026-10-28
**Scope:** All remaining phases from current state (11 screens done, mock pipeline) to v1 shippable product
**Usage:** Each phase section below contains a complete, self-contained AI implementation prompt. Feed them to your AI assistant one at a time, in order.

---

## Quick Reference — Phase Order

| Phase | Name | Dependencies | Est. Effort |
|---|---|---|---|
| **P1** | UI Premium Redesign (3 sub-phases) | None — can start now | Large |
| **P2** | Electron Shell + Python IPC Bridge (3 sub-phases) | P1 complete | Large |
| **P3** | Real File Export (PDF/HTML/JSON) | P2 complete | Medium |
| **P4** | Garak Engine Adapter | P2 complete | Medium |
| **P5** | PyRIT + DeepTeam Adapters | P4 complete | Medium |
| **P6** | Normalization + Deduplication Pipeline | P5 complete | Medium |
| **P7** | AWS Deployment Engine (Optional v1) | P2 complete | Large |
| **P8** | Installer + Distribution | P2 complete, P4+ recommended | Medium |
| **P9** | Frontend Test Suite | P1 complete | Medium |

---

## Important Context for All Phases

**Read these files before starting ANY phase:**
- `context/current_phase.md` — tracks what's done
- `context/decisions.md` — architectural decisions D-001 through D-023
- `context/architecture.md` — 5-layer architecture
- `docs/FINAL_CONSOLIDATION.md` — source of truth for all design decisions
- `docs/SYSTEM_EXECUTION_LAYER.md` — backend module specs
- `docs/UI_ARCHITECTURE.md` — UI design system spec

**Project rules (enforce in every phase):**
- Project name is **Sentryɸ** (or SentryPhi in ASCII-safe contexts). Do NOT use any old names (AI-SENTRY, AI_Sentry, etc.) anywhere in user-visible UI, comments, or new code.
- Do NOT commit or push to Git. The developer handles Git operations manually.
- All existing tests must keep passing (`pytest tests/ -q` in `app/backend`).
- `npx tsc --noEmit` must pass with zero errors after every phase.
- Dark/light theme must work on all new/modified components.
- BEM class naming convention: `.block__element--modifier`

**Current file sizes (for reference):**
- `src/index.css` — 3,342 lines (99KB) — the master stylesheet
- `src/App.tsx` — 239 lines — root component + screen router
- 11 page components in `src/pages/`
- 7 service files in `src/services/`
- 3 state stores in `src/store/`
- 17 Python modules in `app/backend/core/`
- 19 test files, 971 tests passing

---

# ═══════════════════════════════════════════════════════
# PHASE P1 — UI PROFESSIONAL REDESIGN
# ═══════════════════════════════════════════════════════

## Why This Comes First

The current UI is functional but basic. Before packaging as a desktop app, 
it needs to feel like a tool professionals trust — think Linear, Vercel 
Dashboard, or Stripe. NOT an AI-generated template with gradients everywhere.

## Design Philosophy — What We're Building

Inspired by **Linear, Vercel, Raycast, and Stripe Dashboard**:
- **Quiet chrome:** Interface steps back so content takes center stage
- **1px hairline borders** — never heavy shadows or glowing edges
- **Color is for meaning only** — status indicators, severity badges, not decoration
- **Typography hierarchy via weight + opacity** — not size extremes or gradient text
- **High information density** — compact, scannable, efficient
- **Functional animations only** — under 150ms, giving feedback, not decorating
- **No AI-generated clichés:** no purple gradients, no glassmorphism on buttons,
  no floating glow circles, no gradient text, no 3D blobs, no "futuristic" decorations

---

## PHASE P1a — Design System Upgrade + Global Shell Polish

### Prompt

```
# Sentryɸ — Phase P1a: Design System Upgrade + Global Shell Polish

You are working on Sentryɸ, a desktop LLM security assessment application.
The project is at: d:\AI_Sentry\app\frontend

## CRITICAL DESIGN DIRECTION

This app must look like a REAL professional tool — think Linear, Vercel 
Dashboard, Raycast, or Stripe. It must NOT look AI-generated.

FORBIDDEN (these scream "AI-generated"):
- Gradient backgrounds on buttons or cards
- Glassmorphism / backdrop-filter blur on interactive elements
- Floating glow circles or ambient light effects
- Purple/indigo gradient accents
- Gradient text
- Excessive border-radius (>8px on small elements)
- Decorative animations that serve no functional purpose
- "Futuristic" grid/circuit-board background patterns
- Scale transforms on hover (scale(1.01) etc.)

REQUIRED (these signal "built by professionals"):
- Flat, solid color buttons with subtle hover darkening
- 1px hairline borders (rgba overlays, not solid colors)
- Text hierarchy through font-weight (400/500/600) and opacity (100%/60%/40%)
- Tight, dense spacing — no wasteful whitespace
- Color used ONLY for semantic meaning (status, severity, active state)
- Monochromatic UI with ONE accent color used sparingly
- Animations under 150ms, for feedback only (hover states, focus rings)
- Clean, sharp corners (4-6px radius max on cards, 4px on buttons)

## Context

Read these files first:
- `src/styles/design-tokens.css` — current spacing/font/radius/shadow tokens
- `src/styles/theme.css` — dark/light theme color tokens  
- `src/index.css` — master stylesheet (3,342 lines)
- `src/App.tsx` — app root + screen router
- `src/components/layout/StepNav.tsx` — wizard step navigation
- `src/components/layout/PageHeader.tsx` — page header
- `src/components/layout/ThemeToggle.tsx` — theme toggle
- `src/components/Logo.tsx` — SVG shield-phi logo

## Requirements

### 1. Typography Upgrade
- Import Inter font from Google Fonts (add to `index.html`)
- Update `--font-family` in design-tokens.css: Inter as primary
- Add tracking tokens: `--tracking-tight: -0.025em`, `--tracking-normal: 0`
- Add heading sizes: `--font-size-3xl: 28px`, `--font-size-4xl: 34px`
- Body text: 13px base (already set), labels 11-12px, headings 16-20px
- Text opacity tokens: `--text-primary: 1`, `--text-secondary: 0.6`, 
  `--text-tertiary: 0.4` — use these for hierarchy instead of color

### 2. Color System Refinement
Strip out any decorative color. Focus on semantic meaning:

Dark theme adjustments:
- `--bg-app: #0a0a0b` — near-black, not blue-tinted
- `--bg-surface: #141415` — very dark charcoal
- `--bg-raised: #1a1a1c` — subtle lift from surface
- `--bg-hover: #1f1f22` — hover state for rows/items
- `--border-default: rgba(255, 255, 255, 0.06)` — hairline borders
- `--border-strong: rgba(255, 255, 255, 0.1)` — emphasized borders
- Keep `--accent-primary` as the single blue accent (#5b8def)
- Remove any violet/purple secondary accent
- `--fg-default: rgba(255, 255, 255, 0.88)` — not pure white
- `--fg-muted: rgba(255, 255, 255, 0.55)`
- `--fg-faint: rgba(255, 255, 255, 0.35)`

Light theme: similar restraint — off-white backgrounds (#fafafa, #ffffff),
dark text, same single accent color.

Status colors remain as-is (green/amber/red) but used ONLY for status.

### 3. Spacing + Density
- Reduce `--content-padding` from 24px to 20px
- Add `--row-height: 36px` — for list items and table rows
- Add `--section-gap-sm: 16px`, `--section-gap-lg: 32px`
- Ensure buttons are compact: height 32px (small), 36px (default), 40px (large)
- Card padding: 16px, not 24px

### 4. App Shell Redesign
`.app-shell__header`:
- Height: 48px (compact, like Linear's header)
- Background: `--bg-surface`
- Bottom border: 1px solid `--border-default` (single hairline, NOT gradient)
- Logo: use the existing `Logo.tsx` SVG component — render it at 22px, 
  no glow, no ambient effects behind it
- Brand text: 14px, font-weight 600, letter-spacing -0.02em
- Theme toggle: right side, compact
- No backdrop-filter, no blur, no glass effects

### 5. Step Navigation Redesign
`.step-nav` — redesign as a compact horizontal bar (like Vercel's deployment steps):
- Each step: small text label only (no large pills or capsules)
- Step number: 12px circle with number, muted color
- Active step: text becomes `--fg-default` (full opacity), number circle 
  gets accent background
- Completed step: number replaced with a small checkmark, muted green
- Connector: thin 1px line between steps, solid `--border-default`, 
  accent-colored for completed segments
- NO hover lift (translateY), NO glow on active step
- Hover: text goes to full opacity, that's it
- Total height: ~40px, horizontally centered
- On mobile/narrow: hide labels, show numbers only

### 6. Page Transitions
- Simple, fast opacity fade-in: opacity 0 → 1, duration 150ms
- NO slide-in from right, NO translateX — just a clean fade
- Use `@keyframes page-enter { from { opacity: 0 } to { opacity: 1 } }`
- Apply on `.page-container` with animation-duration: 150ms

### 7. Global Component Upgrades
Buttons:
- `.button--primary`: solid `--accent-primary` background, NO gradient.
  Hover: darken by 8% (use a darker shade). Active: darken by 12%.
  Border-radius: 4px. Height: 36px. Padding: 0 16px.
- `.button--secondary`: transparent background, 1px border `--border-strong`.
  Hover: background `--bg-hover`. No ghost/gradient effects.
- `.button--destructive`: muted red background, not bright.

Cards/surfaces:
- 1px border `--border-default`. Border-radius: 6px.
- NO box-shadow on cards. Use border only for definition.
- Background: `--bg-raised`

Focus states:
- `:focus-visible` — 2px solid `--accent-primary` with 2px offset. 
  Clean, visible, functional.

Scrollbars:
- 4px wide, rounded, `--border-default` colored thumb

### 8. Theme Toggle
- Simple icon toggle: sun (☀) / moon (☾) using unicode or simple SVG
- NO rotation animation, NO elaborate transition
- Click toggles instantly with a 100ms opacity crossfade
- 28px button, transparent background, hover: `--bg-hover`

### Constraints
- Do NOT change any component logic or props
- Do NOT change navigation behavior
- Do NOT add decorative elements (patterns, blobs, glows, gradients)
- All 11 screens must continue to render correctly
- Both dark and light themes must look polished
- `npx tsc --noEmit` must pass with zero errors
- Zero regressions in functionality

### Deliverables
1. Updated `design-tokens.css`
2. Updated `theme.css`
3. Updated `index.css` (app shell, step nav, buttons, global sections)
4. Updated `App.tsx` (Logo import if needed)
5. Updated `StepNav.tsx` (compact redesign)
6. Updated `ThemeToggle.tsx` (simple icon toggle)
7. Inter font link in `index.html`
8. Manual browser test — all 11 screens, dark + light themes
```

---

## PHASE P1b — Screen-by-Screen Visual Upgrade (Screens 1–5)

### Prompt

```
# Sentryɸ — Phase P1b: Screen Visual Upgrade — Screens 1 through 5

You are continuing the UI professional redesign of Sentryɸ.
Phase P1a (design system upgrade) is complete.

## CRITICAL DESIGN DIRECTION

Re-read the P1a design rules. This app must look like Linear or Vercel.

FORBIDDEN:
- Gradient buttons or gradient anything
- Glassmorphism / backdrop-filter on cards
- Glow effects on selected states
- Hover lift (translateY) on cards
- Animated background patterns (dot grids, circuit boards)
- Radial progress indicators or conic-gradient gauges
- Shimmer/pulse animations on progress bars
- Staggered reveal animations on page load
- Scale transforms on buttons

REQUIRED:
- Clean, flat surfaces with 1px borders
- Text hierarchy via weight + opacity (not color or size extremes)
- Compact, dense layouts — maximize information per pixel
- Semantic color only (status, severity, not decoration)
- Functional micro-interactions under 150ms

## Context

Read these files first:
- `src/pages/AgreementPage.tsx` — Screen 1: consent gate
- `src/pages/InputPage.tsx` — Screen 2: model input
- `src/pages/ConfigPage.tsx` — Screen 3: scan configuration
- `src/pages/EstimatePage.tsx` — Screen 4: cost estimate
- `src/pages/ScanPage.tsx` — Screen 5: scan progress
- `src/index.css` — master stylesheet
- `src/components/forms/TextInput.tsx`, `RadioGroup.tsx`, `CheckboxGroup.tsx`, `FileDropZone.tsx`

## Requirements per Screen

### Screen 1 — Agreement Page
Current: plain text list with a button. Redesign as a focused, professional gate.
- Centered vertically/horizontally in viewport, max-width 520px
- Sentryɸ logo at top (22px, existing Logo.tsx component), brand name below
- Subtitle: "LLM Security Platform" in --fg-muted, 12px, tracking wider
- Consent sections as a clean ordered list or grouped text blocks — NOT cards
  with icons. Just clean typography with clear headings and concise text.
- Each section: small bold heading (13px, weight 600) + body text (13px, weight 400, --fg-muted)
- Minimal dividers between sections (1px --border-default)
- "I Understand & Accept" button: standard primary button (flat, solid accent color).
  Full width at the bottom of the consent block.
- Version number at bottom: "v0.1.0-dev", 11px, --fg-faint
- NO animated backgrounds, NO staggered reveals, NO decorative patterns

### Screen 2 — Input Page
Current: basic form. Redesign as a clean, dense configuration form.
- Model type selector: segmented control (like Linear's view toggles) — a horizontal
  row of 3 options (API / Local / HuggingFace), flat buttons with 1px border,
  selected state = accent text + subtle accent background (rgba). NOT large visual cards.
- Input fields: clean single-line inputs with:
  - Label above (12px, weight 500, --fg-muted)
  - 36px height input with 1px border, --bg-inset background
  - Focus state: border becomes --accent-primary
  - Error state: border becomes --status-error, error text below in 11px
- API key: monospace font, add a small eye icon button to toggle visibility
- Endpoint URL: inline validation indicator — small dot (green/red) in the right
  padding of the input, not a separate element
- Section spacing: 20px between field groups
- "Test Connection" button: secondary style (border only), compact

### Screen 3 — Configuration Page
Current: radio buttons and checkboxes. Redesign with clear visual hierarchy.
- Scan depth: three options in a VERTICAL stack (not cards, not a grid).
  Each option is a selectable row:
  - Left: radio indicator (custom styled, 14px circle)
  - Middle: name (weight 600) + description (--fg-muted, 12px) on same row or stacked
  - Right: duration estimate badge (12px, monospace, --fg-faint)
  - Selected row: subtle accent-tinted background (rgba, 4-6% opacity), accent left border (2px)
  - NO icons, NO hover lift, NO glow
- Probe categories: compact checkboxes in a 2-column grid
  - Custom checkbox: 14px square, accent fill when checked, smooth 100ms transition
  - Label: 13px, weight 400
  - NOT chips/pills — standard checkboxes, just well-styled
- Summary line at bottom: "Quick scan · 4 categories · ~95 probes" in --fg-muted
- "Continue" button: standard primary button, right-aligned

### Screen 4 — Estimate Page
Current: text with numbers. Redesign as a clean data summary.
- Cost estimate: NOT a "card with big number". Instead, a compact data table:
  | Item | Count | Unit Cost | Total |
  |------|-------|-----------|-------|
  (styled as a clean table with --border-default row separators)
- Total: bold row at bottom of the table, slightly larger text (16px)
- Time estimate: single line below table — "Estimated duration: ~8 minutes" in --fg-muted
- Warning notices: simple inline text with a small ⚠ icon and --status-warning color.
  NOT glass cards, NOT colored backgrounds. Just text.
- "Proceed to Scan" button: standard primary button. No gradient, no confirmation language gimmicks.

### Screen 5 — Scan Page
Current: functional progress UI. Make it more professional and data-dense.
- Progress bar: simple horizontal bar, 4px height, --accent-primary fill.
  NO gradient fill, NO shimmer, NO conic-gradient, NO radial gauge.
  Show percentage as text to the right of the bar (13px, monospace).
- Status line below progress bar: current stage label + elapsed time
  e.g., "Scanning · prompt_injection · 2m 14s" — 12px, --fg-muted
- Category progress: a clean TABLE (not cards in a grid):
  | Category | Status | Probes | Progress |
  Each row 36px tall. Status shown as small colored dot (8px circle) + text:
  Queued (gray), Active (blue), Complete (green), Failed (red)
- Activity feed: monospace text area, --bg-inset background, 1px border.
  12px font, line entries with timestamp + message. Color-coded by severity
  using text color only (not background). Max-height with overflow-y scroll.
- Findings counter: simple text "3 findings" with --status-warning color (if >0).
  No pulsing, no badges, no animation.
- Cancel button: secondary style with --status-error text color.
  Confirmation via simple modal (no elaborate animation).
- NO scanning sweep animation, NO accent line sweeping across page

### Form Components Upgrade (shared)
- `TextInput.tsx`: NO floating labels. Keep label above input (static).
  Focus: border color change to accent (100ms transition). That's it.
  Error: red border + error message below. NO shake animation.
- `RadioGroup.tsx`: custom styled radio circles if used
- `CheckboxGroup.tsx`: custom styled square checkboxes, accent fill when checked
- `FileDropZone.tsx`: dashed border (--border-strong), on drag-over: solid border.
  Simple file icon (unicode 📄) + "Drop file here" text. No animated borders.

### Constraints
- Do NOT change component props, state management, or navigation
- Only modify CSS and JSX markup
- All functionality must remain identical
- `npx tsc --noEmit` must pass
- Both themes must work

### Deliverables
1. Updated page files (S1–S5)
2. Updated form components
3. Updated `index.css`
4. Manual browser test: S1→S5, dark and light themes
```

---

## PHASE P1c — Screen Visual Upgrade (Screens 6–11) + Final Polish

### Prompt

```
# Sentryɸ — Phase P1c: Screen Visual Upgrade — Screens 6 through 11 + Final Polish

You are continuing the UI professional redesign of Sentryɸ.
Phases P1a (design system) and P1b (Screens 1–5) are complete.

## CRITICAL DESIGN DIRECTION

Same rules as P1a/P1b. Think Linear, Vercel, Stripe Dashboard. NOT AI-generated.

FORBIDDEN: gradients, glassmorphism, glow effects, radial gauges, shimmer,
animated backgrounds, decorative patterns, hover lift, scale transforms,
spider/radar charts, gradient banners, animated checkboxes with "satisfying" effects.

REQUIRED: clean tables, 1px borders, text hierarchy via weight/opacity,
semantic color only, compact dense layouts, functional feedback under 150ms.

## Context

Read these files first:
- `src/pages/ResultsPage.tsx` — Screen 6: results dashboard
- `src/pages/ActionsPage.tsx` — Screen 7: recommendations
- `src/pages/ExportPage.tsx` — Screen 8: export report
- `src/pages/DeployConfigPage.tsx` — Screen 9: deploy configuration
- `src/pages/CloudComparePage.tsx` — Screen 10: cloud compare
- `src/pages/DeployExecutePage.tsx` — Screen 11: deploy execution
- `src/store/ReportContext.tsx` — report state
- `src/store/DeployContext.tsx` — deployment state
- `src/services/reportTypes.ts` — report data types
- `src/services/compareTypes.ts` — cloud comparison types
- `src/services/dryRunTypes.ts` — dry-run plan types

## Requirements per Screen

### Screen 6 — Results Dashboard
Most important screen. Must feel like a professional security audit tool.
- Risk score summary: NOT a radial gauge. Instead, a compact header row:
  Left: "Risk Level: HIGH" with a colored dot (8px, semantic color).
  Right: "7 findings · 2 high · 3 medium · 2 low" in --fg-muted.
  Clean, dense, scannable.
- Severity breakdown: a horizontal mini-bar (like GitHub's language bar)
  — thin (6px height), segmented by severity color, with labels below.
  NOT a pie chart, NOT a donut, NOT a gauge.
- Finding list: a SORTABLE TABLE, not cards:
  | Sev. | Finding | Category | Confidence | Engine |
  Severity: small colored dot + text ("HIGH" / "MED" / "LOW")
  Finding: clickable to expand inline (accordion below the row)
  Confidence: plain text "0.92" — NOT an inline progress bar
  Engine: small muted text "garak" or "mock"
  Expanded row: evidence text in monospace, --bg-inset background, 1px border-top
- Filter bar: simple row of small buttons ("All", "High", "Medium", "Low")
  Active filter: accent text + subtle accent background.
  NOT pill-style chips. Simple flat buttons.
- Sort: simple dropdown or clickable column headers with ▲▼ indicators

### Screen 7 — Recommendations / Actions
- Summary line at top: "3 of 8 recommendations addressed" — plain text, --fg-muted
  with the "3" in --accent-primary. NO progress ring.
- Recommendation list: structured as a dense list (like Linear's issue list):
  Each row: priority dot (color) + title + category badge (muted) + status indicator
  Status: three small dots or text ("Not started" / "In progress" / "Done")
  Expandable detail: accordion expands below the row, shows actions per tier
  (Model / System / Deployment) as indented sub-items
- Filter: same style as Screen 6 — small flat filter buttons
- No numbered circles, no large cards with icons

### Screen 8 — Export Report
- Keep it simple. Three options in a selectable list (not large cards):
  Each option: radio-style selection + format name + brief description
  e.g., "○ PDF — Formatted report with branding" (one line per option)
- Selected format gets accent indicator (filled radio dot or accent left border)
- Export button: standard primary button with format name ("Export as PDF")
- Success state: simple green text "✓ Report saved to /path/to/file" — no animated checkmark
- "Continue to Deployment" button: secondary style, below export section

### Screen 9 — Deploy Configuration
- Provider selector: segmented control (like Screen 2's model type selector)
  Three horizontal options: AWS | Azure | GCP
  Selected: accent background + text. Not large cards with logos.
  Below each: small text "(Full support)" or "(Advisory only)" in --fg-faint
- Configuration form: standard form layout matching Screen 2/3 styling
  Region selector: dropdown
  Instance type: dropdown
  Each field: label + input, same style as earlier screens
- Validation: inline indicators (dot + text) matching Screen 2 approach

### Screen 10 — Cloud Compare
- Comparison: a clean DATA TABLE, not a "premium comparison matrix"
  | Feature | AWS | Azure | GCP |
  Clean rows with 1px separators, 36px row height
  Values: text, checkmarks (✓), or dashes (—)
  Cost row: bold, larger text
  Recommended column: subtle accent left-border on the column header cell
- NO radar charts, NO spider charts, NO bar charts
- NO toggle between "Overview" and "Detailed" — show one comprehensive table
- Below table: brief text recommendation, e.g., "Based on your scan results and
  configuration, AWS is recommended for this deployment."

### Screen 11 — Deploy Execution
- Preflight checklist: a simple ordered list with checkboxes
  Each item: standard checkbox + label text. Checked = green checkmark.
  NO timeline/stepper visualization, NO animated checkboxes.
- DRY RUN indicator: a simple inline notice at the top:
  "⚠ Dry Run Mode — No cloud resources will be created"
  Style: 1px border with --status-warning left border (2px), compact.
  NOT a gradient banner, NOT a shimmer animation, NOT a pulse.
- Stage list: a simple table or list:
  | Stage | Description | Status |
  Status: "Planned" / "Simulated" / "N/A" with colored dot
  Each stage is a row, not a card. No pipeline visualization, no dashed connector lines.
- Plan result: simple text block summarizing the dry-run outcome.
  "Dry-run complete. 5 stages planned. No resources provisioned."
- Disclaimer: plain text in --fg-faint at the bottom, small font.
  NOT a warning callout with colored border. Just text.

### Final Polish (applies to all screens)
- Fix any remaining "AI-SENTRY" text anywhere → "Sentryɸ"
- Ensure consistent section spacing across all screens (use --section-gap tokens)
- All interactive elements must have :focus-visible states
- All hover states: background change only (--bg-hover), never lift/scale/glow
- Empty states: simple centered text "No findings" or "No data" in --fg-faint.
  NO illustrations, NO decorative empty state graphics.
- Loading states (if any): simple text "Loading..." or a small spinner (8px circle).
  NO skeleton screens, NO shimmer placeholders.
- Verify the entire flow S1→S11 in both dark and light themes

### Constraints
- Do NOT change component props, state management, or navigation
- Do NOT add ANY decorative elements
- Only modify CSS and JSX markup
- All functionality must remain identical
- `npx tsc --noEmit` must pass
- Both themes must work
- `pytest tests/ -q` must still pass (backend unchanged)

### Deliverables
1. Updated page files (S6–S11)
2. Updated `index.css`
3. Manual browser test: full S1→S11, dark + light
4. Update `context/current_phase.md` — add P1c section
```

---

# ═══════════════════════════════════════════════════════
# PHASE P2 — ELECTRON SHELL + PYTHON IPC BRIDGE
# ═══════════════════════════════════════════════════════

## Why Electron

The codebase already references Electron in comments (`scanTypes.ts` line 14:
"The future Python backend over Electron IPC"). Electron is the best fit because:
- React/Vite frontend stays exactly as-is
- Python subprocess management is well-supported
- File dialog, system tray, auto-update are built in
- `electron-builder` handles installers
- The team already has Node.js/React expertise

---

## PHASE P2a — Electron Main Process + Window

### Prompt

```
# Sentryɸ — Phase P2a: Electron Main Process + Window Setup

You are adding Electron to Sentryɸ to turn it from a browser app into a desktop app.
The project is at: d:\AI_Sentry\app\frontend

## Context

Read these files first:
- `package.json` — current Vite-based frontend config
- `src/App.tsx` — root component
- `src/main.tsx` — React entry point
- `vite.config.ts` — Vite configuration
- `tsconfig.json` — TypeScript config
- `context/decisions.md` — architectural decisions
- `docs/SYSTEM_EXECUTION_LAYER.md` — Section 7 (Desktop App Strategy)

The frontend currently runs as a Vite dev server in a browser. We need to
wrap it in Electron so it runs as a desktop window.

## Architecture Decision

We will use Electron in a DUAL-MODE setup:
- **Development:** Electron loads `http://localhost:5173` (Vite dev server).
  Frontend changes hot-reload via Vite HMR. Python changes take effect on
  next scan invocation.
- **Production:** Electron loads the built `dist/index.html`. Python runtime
  is bundled alongside.

This means: during development, you change any frontend file and it updates
instantly. You change any Python file and the next scan uses the new code.
No rebuild needed during development.

## Requirements

### 1. Install Electron Dependencies
```bash
npm install --save-dev electron electron-builder concurrently wait-on
```

### 2. Create `electron/main.cjs`
The Electron main process file. Must:
- Create a BrowserWindow (1280×800, min 1024×700)
- Set window title to "Sentryɸ — LLM Security Platform"
- Remove the default menu bar (setMenu(null) on Windows)
- In development: load `http://localhost:5173` (Vite dev server)
- In production: load `path.join(__dirname, '../dist/index.html')`
- Detect mode: check for `ELECTRON_DEV` env var or `app.isPackaged`
- Set Content-Security-Policy header for production
- Handle window close gracefully (kill Python subprocess if running)
- Set app icon (we'll create one later — use a placeholder path for now)

### 3. Create `electron/preload.cjs`
The preload script exposes a safe API to the renderer:
```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Scan lifecycle
  startScan: (config) => ipcRenderer.invoke('scan:start', config),
  cancelScan: () => ipcRenderer.invoke('scan:cancel'),
  onScanProgress: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('scan:progress', handler);
    return () => ipcRenderer.removeListener('scan:progress', handler);
  },
  onScanComplete: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('scan:complete', handler);
    return () => ipcRenderer.removeListener('scan:complete', handler);
  },
  onScanError: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('scan:error', handler);
    return () => ipcRenderer.removeListener('scan:error', handler);
  },

  // File operations
  saveReport: (data, format) => ipcRenderer.invoke('report:save', data, format),
  showSaveDialog: (options) => ipcRenderer.invoke('dialog:save', options),

  // System info
  getPythonVersion: () => ipcRenderer.invoke('system:python-version'),
  getAppVersion: () => ipcRenderer.invoke('system:app-version'),

  // Platform detection
  isElectron: true,
  platform: process.platform,
});
```

### 4. Update `package.json`
Add these fields:
```json
{
  "main": "electron/main.cjs",
  "scripts": {
    "dev": "vite",
    "dev:electron": "concurrently \"vite\" \"wait-on http://localhost:5173 && ELECTRON_DEV=1 electron .\"",
    "build": "tsc && vite build",
    "build:electron": "npm run build && electron-builder",
    "preview": "vite preview"
  },
  "build": {
    "appId": "com.sentryphi.app",
    "productName": "Sentryɸ",
    "directories": {
      "output": "release"
    },
    "files": [
      "dist/**/*",
      "electron/**/*"
    ],
    "win": {
      "target": "nsis",
      "icon": "public/icon.ico"
    },
    "linux": {
      "target": "AppImage",
      "icon": "public/icon.png"
    }
  }
}
```

### 5. Update `vite.config.ts`
Add `base: './'` so that built assets use relative paths (required for
Electron's file:// protocol):
```typescript
export default defineConfig({
  base: './',
  plugins: [react()],
  server: { port: 5173 }
})
```

### 6. Create TypeScript Declarations
Create `src/electron.d.ts`:
```typescript
interface ElectronAPI {
  startScan: (config: unknown) => Promise<unknown>;
  cancelScan: () => Promise<void>;
  onScanProgress: (callback: (data: unknown) => void) => () => void;
  onScanComplete: (callback: (data: unknown) => void) => () => void;
  onScanError: (callback: (data: unknown) => void) => () => void;
  saveReport: (data: unknown, format: string) => Promise<string>;
  showSaveDialog: (options: unknown) => Promise<string | null>;
  getPythonVersion: () => Promise<string>;
  getAppVersion: () => Promise<string>;
  isElectron: boolean;
  platform: string;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}
export {};
```

### 7. Create Detection Utility
Create `src/utils/platform.ts`:
```typescript
/** True when running inside Electron, false in browser dev mode */
export const isElectron = (): boolean => {
  return typeof window !== 'undefined' && window.electronAPI?.isElectron === true;
};
```

### 8. Verify It Works
- Run `npm run dev:electron` — Electron window should open showing the Vite app
- All 11 screens should navigate correctly
- Dark/light theme should work
- Run `npm run dev` separately — browser-only mode should still work
- `npx tsc --noEmit` should pass

### Constraints
- Do NOT modify any existing React components in this sub-phase
- The app must continue to work as a browser-only Vite app (`npm run dev`)
- Electron is additive — the browser path is still valid for development
- Do not add Python IPC yet — that's Phase P2b

### Deliverables
1. `electron/main.cjs`
2. `electron/preload.cjs`
3. Updated `package.json`
4. Updated `vite.config.ts`
5. `src/electron.d.ts`
6. `src/utils/platform.ts`
7. Verify `npm run dev:electron` works
8. Verify `npm run dev` (browser-only) still works
9. `npx tsc --noEmit` passes
```

---

## PHASE P2b — Python IPC Bridge (Subprocess + JSON Lines Protocol)

### Prompt

```
# Sentryɸ — Phase P2b: Python IPC Bridge

You are adding the Python ↔ Electron IPC bridge so the React frontend can
invoke the Python backend.

## Context

Read these files first:
- `electron/main.cjs` — Electron main process (created in P2a)
- `electron/preload.cjs` — preload API surface (created in P2a)
- `app/backend/cli/main.py` — existing CLI entry point
- `app/backend/core/engine_runner.py` — scan execution
- `app/backend/core/mock_engine.py` — deterministic mock engine
- `app/backend/core/scorer.py` — severity + confidence scoring
- `app/backend/core/recommender.py` — remediation engine
- `app/backend/core/report_generator.py` — report assembly
- `src/services/scanTypes.ts` — frontend scan event contract
- `src/services/scanService.ts` — current frontend simulator

## Architecture

The IPC bridge works like this:

```
React (renderer)
  → window.electronAPI.startScan(config)
  → ipcRenderer.invoke('scan:start', config)
  → [Electron main process]
  → spawn Python subprocess: `python -m backend.ipc_server`
  → Python reads config from stdin (JSON)
  → Python runs scan pipeline (mock or real engines)
  → Python writes progress events to stdout (JSON Lines, one event per line)
  → Electron main process reads stdout line-by-line
  → ipcMain sends events to renderer via webContents.send('scan:progress', data)
  → React receives via window.electronAPI.onScanProgress(callback)
```

## Requirements

### 1. Create Python IPC Server
Create `app/backend/ipc_server.py`:
- Reads a single JSON object from stdin (the scan configuration)
- Validates the config
- Runs the scan pipeline (using existing core modules)
- Writes progress events to stdout as JSON Lines (one JSON object per line, terminated by \n)
- Each progress event matches the shape expected by `ScanProgressEvent` in scanTypes.ts

Event types to emit:
```python
# Progress event (emit periodically during scan)
{"type": "progress", "stage": "scanning", "percent": 45, "probes_done": 23, "probes_total": 50, "elapsed_ms": 12000, "message": "Running prompt injection probes..."}

# Finding event (emit when a finding is discovered)
{"type": "finding", "category": "prompt_injection", "severity": "high", "confidence": 0.92, "title": "System prompt extraction", "evidence": "..."}

# Activity log event (emit for detailed logging)
{"type": "activity", "severity": "info", "message": "Initializing Garak engine...", "timestamp": "..."}

# Stage change event
{"type": "stage", "stage": "scoring", "message": "Running severity classifier..."}

# Complete event (emit once at end)
{"type": "complete", "report": { ... full report object ... }}

# Error event (emit on failure)
{"type": "error", "message": "...", "code": "ENGINE_FAILED"}
```

The IPC server should:
- Use existing `core/manifest.py` to build the manifest
- Use existing `core/engine_runner.py` to run the scan
- Use existing `core/scorer.py` to score findings
- Use existing `core/recommender.py` to generate recommendations
- Use existing `core/report_generator.py` to build the report
- Flush stdout after each JSON line (important for real-time streaming)
- Handle KeyboardInterrupt for cancellation (Electron will send SIGINT/SIGTERM)
- Exit with code 0 on success, non-zero on error

### 2. Wire IPC Handlers in Electron Main Process
Update `electron/main.cjs` — add ipcMain handlers:

```javascript
const { ipcMain } = require('electron');
const { spawn } = require('child_process');
const readline = require('readline');

let scanProcess = null;

ipcMain.handle('scan:start', async (event, config) => {
  // Find Python executable
  const pythonPath = findPython(); // Try 'python3', 'python', or bundled path
  const backendPath = path.join(__dirname, '../../backend');

  // Spawn Python IPC server
  scanProcess = spawn(pythonPath, ['-m', 'ipc_server'], {
    cwd: backendPath,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  // Send config to Python via stdin
  scanProcess.stdin.write(JSON.stringify(config) + '\n');
  scanProcess.stdin.end();

  // Read stdout line-by-line (JSON Lines protocol)
  const rl = readline.createInterface({ input: scanProcess.stdout });
  rl.on('line', (line) => {
    try {
      const event = JSON.parse(line);
      const win = BrowserWindow.getFocusedWindow();
      if (!win) return;

      switch (event.type) {
        case 'progress':
        case 'finding':
        case 'activity':
        case 'stage':
          win.webContents.send('scan:progress', event);
          break;
        case 'complete':
          win.webContents.send('scan:complete', event);
          break;
        case 'error':
          win.webContents.send('scan:error', event);
          break;
      }
    } catch (e) {
      // Non-JSON output — ignore or log
    }
  });

  // Handle Python process errors
  scanProcess.stderr.on('data', (data) => {
    console.error('[Python stderr]', data.toString());
  });

  scanProcess.on('exit', (code) => {
    if (code !== 0 && code !== null) {
      const win = BrowserWindow.getFocusedWindow();
      if (win) {
        win.webContents.send('scan:error', {
          type: 'error',
          message: `Python process exited with code ${code}`,
          code: 'PROCESS_EXIT'
        });
      }
    }
    scanProcess = null;
  });

  return { started: true };
});

ipcMain.handle('scan:cancel', async () => {
  if (scanProcess) {
    scanProcess.kill('SIGINT');
    scanProcess = null;
  }
  return { cancelled: true };
});
```

### 3. Create Frontend IPC Service
Create `src/services/ipcScanService.ts`:
- Provides the same public API as `scanService.ts` (startScan, buildScanConfig)
- But calls `window.electronAPI.startScan()` instead of running the simulator
- Maps Python IPC events to the `ScanProgressEvent` type used by `ScanContext`
- Falls back to the simulator if `window.electronAPI` is not available

### 4. Update ScanPage to Use IPC When Available
Modify `src/pages/ScanPage.tsx`:
- Import `isElectron()` from `utils/platform.ts`
- If running in Electron: use `ipcScanService` (real Python)
- If running in browser: use existing `scanService` (simulator)
- The ScanPage component doesn't change — only the service it calls changes

### 5. Python Helper: Find Python
Add a `findPython()` utility in `electron/main.cjs` that tries:
1. Bundled Python path (for production)
2. `python3` (Linux/Mac)
3. `python` (Windows)
4. Falls back with a clear error message

### 6. Test the Bridge
- Start the app: `npm run dev:electron`
- Navigate to Screen 5 and start a scan
- Verify: Python mock engine runs, progress events stream to the UI
- Verify: findings appear in the results (Screen 6)
- Verify: the browser-only mode (`npm run dev`) still works with the simulator
- Add backend tests for `ipc_server.py` (test JSON Lines output format)

### Constraints
- The browser-only development path must keep working (fallback to simulator)
- Do NOT modify any existing Python core modules — only ADD ipc_server.py
- Event format must be compatible with existing ScanProgressEvent types
- `npx tsc --noEmit` must pass
- `pytest tests/ -q` must pass (add tests for ipc_server)

### Deliverables
1. `app/backend/ipc_server.py`
2. Updated `electron/main.cjs` (IPC handlers)
3. `src/services/ipcScanService.ts`
4. Updated `src/pages/ScanPage.tsx` (conditional service selection)
5. `app/backend/tests/test_ipc_server.py`
6. Manual test: Electron scan with Python backend
7. Manual test: Browser-only scan with simulator (regression)
```

---

## PHASE P2c — IPC Integration for Remaining Features

### Prompt

```
# Sentryɸ — Phase P2c: Complete IPC Integration

You are completing the Electron IPC bridge for all remaining features
beyond the scan pipeline.

## Context

Read these files first:
- `electron/main.cjs` — Electron main process (scan IPC done in P2b)
- `electron/preload.cjs` — preload API surface
- `src/services/ipcScanService.ts` — scan IPC service (created in P2b)
- `src/services/estimatorService.ts` — cost estimation (currently simulated)
- `src/store/ReportContext.tsx` — report state
- `src/store/DeployContext.tsx` — deployment state
- `app/backend/core/estimator.py` — Python cost estimator
- `app/backend/core/validator.py` — endpoint validator

## Requirements

### 1. Cost Estimation IPC
Add IPC endpoint for real cost estimation:
- `window.electronAPI.estimateCost(config)` → calls Python `estimator.py`
- Update `estimatorService.ts` to call IPC when in Electron, simulate otherwise
- Update `EstimatePage.tsx` to show real estimates in Electron mode

### 2. Endpoint Validation IPC
Add IPC endpoint for real model endpoint validation:
- `window.electronAPI.validateEndpoint(url, apiKey)` → calls Python `validator.py`
- Update `InputPage.tsx` to perform real validation in Electron mode
- Show real connectivity status (reachable / unreachable / auth error)

### 3. Report Data Flow
After a scan completes in Electron mode:
- The `scan:complete` event includes the full report object from Python
- `ReportContext` should receive and store this real report
- Results/Recommendations/Export screens should display real data
- The simulated report builder in ReportContext should only run in browser mode

### 4. System Info
Implement the system info IPC endpoints:
- `getPythonVersion()` → runs `python --version` and returns the string
- `getAppVersion()` → reads from package.json
- Display Python version in the app footer or settings area

### 5. Mode Indicator
Add a small indicator in the app header showing:
- 🟢 "Desktop Mode" (Python connected) when running in Electron
- 🔵 "Browser Mode" (Simulated) when running in browser
- This helps during development to know which mode is active

### Constraints
- Browser-only mode must continue to work with all simulators
- No changes to Python core modules — only ipc_server.py updates
- `npx tsc --noEmit` must pass
- `pytest tests/ -q` must pass

### Deliverables
1. Updated `electron/main.cjs` — new IPC handlers
2. Updated `electron/preload.cjs` — new API methods
3. Updated `src/electron.d.ts` — new type declarations
4. Updated `estimatorService.ts` — IPC integration
5. Updated `InputPage.tsx` — real validation
6. Updated `ReportContext.tsx` — real report data flow
7. Updated `App.tsx` — mode indicator
8. Manual test: full flow in Electron (scan → results → export)
9. Update `context/current_phase.md`
```

---

# ═══════════════════════════════════════════════════════
# PHASE P3 — REAL FILE EXPORT (PDF / HTML / JSON)
# ═══════════════════════════════════════════════════════

### Prompt

```
# Sentryɸ — Phase P3: Real File Export

You are implementing real file export so users can save scan reports to disk.

## Context

Read these files first:
- `electron/main.cjs` — Electron main process
- `electron/preload.cjs` — preload API
- `src/pages/ExportPage.tsx` — Screen 8
- `app/backend/core/report_generator.py` — Python report generator
- `app/backend/services/report_service.py` — report export service
- `app/backend/pyproject.toml` — WeasyPrint dependency listed

## Requirements

### 1. Electron File Save Dialog
When user clicks "Export" in Screen 8:
- Call `window.electronAPI.showSaveDialog()` → opens native file picker
- User chooses location and filename
- Call `window.electronAPI.saveReport(reportData, format)` → sends to Python

### 2. Python Report Writer
Add export functionality to `ipc_server.py` (or create `app/backend/export_handler.py`):
- Receives report data + format (pdf/html/json) + output path
- JSON: write formatted JSON to file
- HTML: generate styled HTML report using a template:
  - Include executive summary, finding table, confidence breakdown
  - Embed CSS inline (no external dependencies)
  - Include the Sentryɸ branding
- PDF: use WeasyPrint to convert HTML → PDF
  - If WeasyPrint not installed, fall back to HTML with a notice
  - PDF should have: cover page, table of contents, findings, recommendations

### 3. IPC Protocol
New IPC message types:
```
Request:  { "action": "export", "format": "pdf", "path": "/path/to/report.pdf", "report": {...} }
Response: { "type": "export_complete", "path": "/path/to/report.pdf", "size_bytes": 12345 }
Error:    { "type": "export_error", "message": "WeasyPrint not installed" }
```

### 4. ExportPage Updates
- Show native file picker when export button is clicked (Electron mode)
- Show progress indicator during export
- Show success state with file path and "Open File" / "Open Folder" buttons
- In browser mode: download the file via browser download API (data URL)
- Support all three formats: PDF, HTML, JSON

### 5. Tests
- Backend tests for report generation (HTML, JSON formats)
- Test WeasyPrint fallback behavior
- Test IPC export protocol

### Constraints
- Browser mode should support HTML and JSON export via download (no PDF without WeasyPrint)
- Do not modify existing report_generator.py logic — extend it
- `npx tsc --noEmit` must pass
- `pytest tests/ -q` must pass

### Deliverables
1. Updated `electron/main.cjs` — export IPC handlers
2. `app/backend/export_handler.py` or updated `ipc_server.py`
3. HTML report template
4. Updated `ExportPage.tsx`
5. Backend tests
6. Manual test: export PDF, HTML, JSON in Electron mode
7. Manual test: export HTML, JSON in browser mode
```

---

# ═══════════════════════════════════════════════════════
# PHASE P4 — GARAK ENGINE ADAPTER
# ═══════════════════════════════════════════════════════

### Prompt

```
# Sentryɸ — Phase P4: Garak Engine Adapter

You are integrating the first real scanning engine — Garak.

## Context

Read these files first:
- `app/backend/core/engine_interface.py` — BaseEngine abstract class, ScanFinding, ScanResult
- `app/backend/core/engine_runner.py` — current mock-only orchestrator
- `app/backend/core/mock_engine.py` — mock engine for reference
- `app/backend/pyproject.toml` — garak==0.9.0.14 listed
- `docs/TRD.md` — Section 2.3 (Engine Adapters spec)
- `docs/FINAL_CONSOLIDATION.md` — D-002 (engine version pinning)

## Architecture

```
engine_runner.py
  ├── MockEngine        (existing — always available)
  └── GarakAdapter      (NEW — calls garak CLI as subprocess)
```

## Requirements

### 1. Create `app/backend/core/adapters/` Package
Create `app/backend/core/adapters/__init__.py`

### 2. Create `app/backend/core/adapters/garak_adapter.py`
A GarakAdapter class that implements BaseEngine:

```python
class GarakAdapter(BaseEngine):
    """
    Runs Garak as a subprocess and maps its output to ScanFinding objects.

    Garak is invoked via its CLI:
      python -m garak --model_type <type> --model_name <name> --probes <probes>

    Output is captured from Garak's JSON report file.
    """

    def run_scan(self, manifest: ScanManifest) -> ScanResult:
        # 1. Build Garak CLI arguments from manifest
        # 2. Run garak as subprocess with timeout
        # 3. Parse Garak's JSON output report
        # 4. Map Garak findings to ScanFinding objects
        # 5. Return ScanResult

    def _build_garak_args(self, manifest) -> list[str]:
        # Map manifest config to garak CLI flags

    def _parse_garak_output(self, report_path: str) -> list[ScanFinding]:
        # Read Garak's JSON report
        # Map each finding to ScanFinding with:
        #   - category (map garak probe names to our categories)
        #   - severity (map garak severity to our tiers)
        #   - confidence (based on success rate)
        #   - evidence (garak's response text)
        #   - probe_id (garak's probe identifier)

    def is_available(self) -> bool:
        # Check if garak is installed and importable
        # Return True/False
```

### 3. Update `engine_runner.py`
- Add engine selection logic:
  - If `use_real_engines=True` in config AND garak is available → use GarakAdapter
  - Otherwise → use MockEngine (fallback)
- The IPC server should pass the engine preference from the frontend config

### 4. Category Mapping
Create a mapping from Garak probe names to Sentryɸ categories:
```python
GARAK_PROBE_CATEGORY_MAP = {
    "promptinject": "prompt_injection",
    "dan": "jailbreak",
    "leakreplay": "data_leak",
    "continuation": "harmful_output",
    # ... more mappings
}
```

### 5. Error Handling
- Garak not installed → graceful fallback to mock with warning
- Garak subprocess timeout → partial results + error message
- Garak crashes → capture stderr, report error, continue with other engines
- Rate limiting → detect and surface to user

### 6. Progress Reporting
- Emit progress events to stdout (for IPC) as Garak runs
- Parse Garak's log output for progress indicators
- Or use time-based estimation (poll subprocess, estimate % done)

### 7. Tests
- Test GarakAdapter with a mock subprocess (don't require real Garak installed)
- Test category mapping
- Test error handling (timeout, crash, not installed)
- Test fallback to MockEngine

### Constraints
- Do NOT require Garak to be installed for tests to pass
- Mock the subprocess in tests
- MockEngine must remain the default fallback
- `pytest tests/ -q` must pass
- The IPC bridge (P2b) must continue to work

### Deliverables
1. `app/backend/core/adapters/__init__.py`
2. `app/backend/core/adapters/garak_adapter.py`
3. Updated `app/backend/core/engine_runner.py`
4. `app/backend/tests/test_garak_adapter.py`
5. Updated `app/backend/ipc_server.py` (engine selection)
6. Manual test: run a scan with Garak against a test endpoint (if available)
```

---

# ═══════════════════════════════════════════════════════
# PHASE P5 — PYRIT + DEEPTEAM ADAPTERS
# ═══════════════════════════════════════════════════════

### Prompt

```
# Sentryɸ — Phase P5: PyRIT + DeepTeam Engine Adapters

You are adding the remaining two scanning engines: PyRIT and DeepTeam.

## Context

Read these files first:
- `app/backend/core/adapters/garak_adapter.py` — Garak adapter (from P4)
- `app/backend/core/engine_interface.py` — BaseEngine interface
- `app/backend/core/engine_runner.py` — orchestrator
- `app/backend/pyproject.toml` — pyrit-ai==0.5.0, deepeval==1.4.0
- `docs/TRD.md` — Section 2.3 (Engine Adapters)

## Requirements

### 1. Create `app/backend/core/adapters/pyrit_adapter.py`
PyRIT is a Python library (not CLI), so the adapter calls it directly:
- Import pyrit and use its Python API
- Map PyRIT's attack strategies to our probe categories
- Handle PyRIT's async execution (it uses asyncio internally)
- Capture findings with evidence (prompt/response pairs)

### 2. Create `app/backend/core/adapters/deepteam_adapter.py`
DeepTeam (deepeval) is also a Python library:
- Use `deepeval.evaluate()` API
- Map deepeval metrics to our categories
- Capture evidence from evaluation results

### 3. Update `engine_runner.py` for Parallel Execution
- Run all available engines in parallel using `concurrent.futures.ThreadPoolExecutor`
- Collect results from all engines
- Handle partial failures (one engine fails, others continue)
- Merge all findings into a single list
- Report which engines ran and which failed

### 4. Progress Reporting
Each engine should report progress independently:
- "Engine 1/3 (Garak): scanning..."
- "Engine 2/3 (PyRIT): scanning..."
- "Engine 3/3 (DeepTeam): scanning..."
- Overall progress = average of individual engine progress

### 5. Tests
- Unit tests for each adapter (mock the engine libraries)
- Integration test for parallel execution
- Test partial failure scenarios
- Test engine availability detection

### Constraints
- Do NOT require real engines to be installed for tests
- Each adapter must check `is_available()` before running
- Missing engines are skipped with a warning, not errors
- `pytest tests/ -q` must pass

### Deliverables
1. `app/backend/core/adapters/pyrit_adapter.py`
2. `app/backend/core/adapters/deepteam_adapter.py`
3. Updated `engine_runner.py` (parallel execution)
4. `app/backend/tests/test_pyrit_adapter.py`
5. `app/backend/tests/test_deepteam_adapter.py`
6. `app/backend/tests/test_parallel_execution.py`
```

---

# ═══════════════════════════════════════════════════════
# PHASE P6 — NORMALIZATION + DEDUPLICATION PIPELINE
# ═══════════════════════════════════════════════════════

### Prompt

```
# Sentryɸ — Phase P6: Normalization + Deduplication Pipeline

You are building the pipeline that normalizes outputs from all three engines
into a unified schema and deduplicates corroborated findings.

## Context

Read these files first:
- `app/backend/core/engine_interface.py` — ScanFinding, ScanResult
- `app/backend/core/scorer.py` — severity + confidence scoring
- `app/backend/core/recommender.py` — remediation engine
- `docs/SYSTEM_EXECUTION_LAYER.md` — normalization pipeline spec
- `docs/FINAL_CONSOLIDATION.md` — D-004 (normalization), D-005 (deduplication)

## Requirements

### 1. Create `app/backend/core/normalizer.py`
SchemaMapper + Deduplicator in one module:

**SchemaMapper:**
- Takes raw findings from all three engines
- Normalizes each to the unified VulnerabilityFinding schema
- Maps to OWASP LLM Top 10 categories
- Assigns a canonical vulnerability ID

**Deduplicator:**
- Identifies findings from different engines that describe the same vulnerability
- Merging criteria: same category + similar evidence text (fuzzy match)
- Merged findings get:
  - Combined engine_sources list ["garak", "pyrit"]
  - Boosted confidence score (cross-engine corroboration)
  - Combined evidence (show evidence from each engine)
  - Severity = max(severity from each engine)

### 2. OWASP LLM Top 10 Mapping
Map each category to OWASP LLM Top 10:
- prompt_injection → LLM01 (Prompt Injection)
- jailbreak → LLM01 (Prompt Injection) + LLM09 (Overreliance)
- data_leak → LLM06 (Sensitive Information Disclosure)
- harmful_output → LLM02 (Insecure Output Handling)
Include the OWASP ID and title in each normalized finding.

### 3. Update Pipeline
Wire the normalizer into the scan pipeline:
engine_runner → normalizer → scorer → recommender → report

### 4. Coverage Map
Generate an OWASP coverage map: which Top 10 categories were tested,
which had findings, which were not covered.

### 5. Tests
- Test deduplication logic (same finding from 2 engines → merged)
- Test confidence boosting on corroboration
- Test OWASP mapping
- Test coverage map generation

### Deliverables
1. `app/backend/core/normalizer.py`
2. Updated `engine_runner.py` or `ipc_server.py` (pipeline integration)
3. `app/backend/tests/test_normalizer.py`
4. Updated `ReportContext` or `reportTypes.ts` (OWASP coverage data)
```

---

# ═══════════════════════════════════════════════════════
# PHASE P7 — AWS DEPLOYMENT ENGINE (Optional v1)
# ═══════════════════════════════════════════════════════

### Prompt

```
# Sentryɸ — Phase P7: AWS Deployment Engine

You are implementing real AWS deployment capability. This is OPTIONAL for v1
and requires careful safety constraints.

## Context

Read these files first:
- `docs/FINAL_CONSOLIDATION.md` — D-022 (AWS deployment scope), D-023 (no Azure/GCP provisioning)
- `src/pages/DeployConfigPage.tsx` — Screen 9
- `src/pages/DeployExecutePage.tsx` — Screen 11
- `src/services/deployTypes.ts` — deployment config types
- `src/services/dryRunTypes.ts` — dry-run plan types
- `app/backend/pyproject.toml` — boto3 dependency listed

## Requirements

### 1. Create `app/backend/core/deploy/aws_engine.py`
Using boto3:
- **Plan generation:** describe what WOULD be created (no actual creation)
- **Dry-run mode:** call AWS describe/validate APIs only
- **Live mode:** actually provision resources (behind explicit user confirmation)

Resources to provision:
1. IAM Role (least-privilege policy for the model endpoint)
2. VPC + Security Group (isolated network)
3. API Gateway + Lambda (for API-based models)
4. CloudWatch Log Group + Alarms
5. Budget Alert (cost protection)

### 2. Safety Constraints (CRITICAL)
- Dry-run is the DEFAULT. Live provisioning requires:
  - AWS credentials present and valid
  - Explicit user confirmation in a modal dialog
  - Plan review screen showing every resource that will be created
  - Cost estimate for provisioned resources
- NEVER store AWS credentials on disk — read from environment or AWS config
- Every provisioned resource must be tagged: `SentryPhi: true`, `ManagedBy: sentryphi`
- Rollback: if any step fails, clean up all created resources

### 3. IPC Integration
New IPC endpoints:
- `window.electronAPI.awsValidateCredentials()` → check if AWS creds are valid
- `window.electronAPI.awsGeneratePlan(config)` → generate deployment plan
- `window.electronAPI.awsDryRun(plan)` → validate plan against AWS APIs
- `window.electronAPI.awsDeploy(plan)` → execute provisioning (with confirmation)

### 4. Update Deploy Screens
- Screen 9: add AWS credentials status indicator
- Screen 11: replace dry-run simulation with real AWS dry-run when available

### Constraints
- This phase is OPTIONAL — the app must work without AWS credentials
- No credentials stored on disk, ever
- Extensive tests with mocked boto3 (moto library)
- Clear rollback on failure

### Deliverables
1. `app/backend/core/deploy/__init__.py`
2. `app/backend/core/deploy/aws_engine.py`
3. Updated IPC handlers
4. Updated deploy screens
5. `app/backend/tests/test_aws_deploy.py` (with moto mocks)
```

---

# ═══════════════════════════════════════════════════════
# PHASE P8 — INSTALLER + DISTRIBUTION
# ═══════════════════════════════════════════════════════

### Prompt

```
# Sentryɸ — Phase P8: Installer + Distribution

You are packaging Sentryɸ as a distributable desktop application.

## Context

Read these files first:
- `package.json` — Electron build config (from P2a)
- `electron/main.cjs` — main process
- `app/backend/pyproject.toml` — Python dependencies
- `docs/SYSTEM_EXECUTION_LAYER.md` — Section 7 (Desktop App Strategy)

## Requirements

### 1. Bundle Python Runtime
Choose one approach:
- **Option A:** Use PyInstaller to create a standalone Python executable
  that includes all core modules and dependencies. Bundle it alongside Electron.
- **Option B:** Use embedded Python (python-embed) and install deps at first launch.
- **Recommended: Option A** — simpler for users, no install step.

Create a build script: `scripts/build-python.py`:
- Runs PyInstaller on `ipc_server.py` with all core module imports
- Outputs a single executable or directory
- Include mock engine (always available)
- Optionally include real engines (garak, pyrit, deepeval) if installed

### 2. Electron Builder Configuration
Update `package.json` build config:
- Include Python bundle in `extraResources`
- Set app icon (create or use existing Logo SVG → convert to .ico and .png)
- Configure NSIS installer for Windows:
  - Install directory: `%LOCALAPPDATA%\Sentryɸ`
  - Desktop shortcut
  - Start menu entry
  - Uninstaller
- Configure AppImage for Linux

### 3. Auto-Update (Optional)
Set up electron-updater for auto-update from GitHub Releases.

### 4. First-Launch Experience
On first launch:
- Check if Python bundle is intact
- Check if scanning engines are available
- Show a status screen: "Checking dependencies... ✓ Python ✓ Garak ⚠ PyRIT (not installed)"
- Allow user to proceed with available engines

### 5. Build Scripts
Create npm scripts:
```
npm run build:python    — bundle Python with PyInstaller
npm run build:electron  — build Electron app
npm run build:all       — build everything
npm run dist            — create installer
```

### 6. Test the Installer
- Build Windows installer
- Install on a clean machine (or clean directory)
- Verify: app launches, scan runs, report exports
- Verify: uninstaller works

### Deliverables
1. `scripts/build-python.py`
2. Updated `package.json` (build config)
3. App icon files (`.ico`, `.png`)
4. Build documentation in `docs/BUILD.md`
5. Working installer for at least one platform (Windows)
```

---

# ═══════════════════════════════════════════════════════
# PHASE P9 — FRONTEND TEST SUITE
# ═══════════════════════════════════════════════════════

### Prompt

```
# Sentryɸ — Phase P9: Frontend Test Suite

You are adding comprehensive frontend tests.

## Context

Read these files first:
- `package.json` — current dev dependencies
- `src/App.tsx` — root component
- All files in `src/pages/`
- All files in `src/store/`
- All files in `src/services/`
- `tsconfig.json`

The project has 971 backend tests but ZERO frontend tests.

## Requirements

### 1. Install Test Dependencies
```bash
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom
npm install --save-dev @testing-library/user-event jsdom
npm install --save-dev playwright @playwright/test   # for E2E
```

### 2. Configure Vitest
Create `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
});
```

Create `src/test/setup.ts`:
```typescript
import '@testing-library/jest-dom';
```

### 3. Unit Tests — State Management
Create tests for each store:
- `src/store/__tests__/ScanContext.test.tsx` — test reducer, actions, initial state
- `src/store/__tests__/ReportContext.test.tsx` — test report actions, filter, sort
- `src/store/__tests__/DeployContext.test.tsx` — test deploy config actions

### 4. Unit Tests — Services
- `src/services/__tests__/scanService.test.ts` — test scan simulator
- `src/services/__tests__/estimatorService.test.ts` — test estimator
- `src/services/__tests__/scanTypes.test.ts` — test valid transitions

### 5. Component Tests — All Pages
Create a test file for each page:
- `src/pages/__tests__/AgreementPage.test.tsx` — renders, accept button works
- `src/pages/__tests__/InputPage.test.tsx` — input validation, navigation
- `src/pages/__tests__/ConfigPage.test.tsx` — depth selection, category toggles
- `src/pages/__tests__/EstimatePage.test.tsx` — estimate display
- `src/pages/__tests__/ScanPage.test.tsx` — progress display, cancel flow
- `src/pages/__tests__/ResultsPage.test.tsx` — findings display, filters
- `src/pages/__tests__/ActionsPage.test.tsx` — recommendations display
- `src/pages/__tests__/ExportPage.test.tsx` — export options
- `src/pages/__tests__/DeployConfigPage.test.tsx` — config form
- `src/pages/__tests__/CloudComparePage.test.tsx` — comparison table
- `src/pages/__tests__/DeployExecutePage.test.tsx` — dry-run flow

### 6. Integration Tests
- `src/__tests__/navigation.test.tsx` — full wizard flow S1→S11
- `src/__tests__/theme.test.tsx` — dark/light toggle works

### 7. E2E Tests (Playwright)
Create `e2e/full-flow.spec.ts`:
- Launch Vite dev server
- Navigate through all 11 screens
- Verify key elements are visible
- Test scan simulation → results → export flow

### 8. CI Script
Add to package.json:
```json
"test": "vitest run",
"test:watch": "vitest",
"test:e2e": "playwright test",
"test:coverage": "vitest run --coverage"
```

### Deliverables
1. `vitest.config.ts`
2. `src/test/setup.ts`
3. All unit test files (stores, services)
4. All component test files (pages)
5. Integration test files
6. E2E test file
7. All tests passing
```

---

# ═══════════════════════════════════════════════════════
# PHASE TRACKING
# ═══════════════════════════════════════════════════════

After completing each phase, update `context/current_phase.md` with:
1. Phase name and status (COMPLETE)
2. Files created/modified
3. Test results
4. Known limitations
5. Next phase reference

---

*End of Implementation Plan v1.0*
*Total phases: 9 major (12 sub-phases)*
*Created: 2026-10-28*
