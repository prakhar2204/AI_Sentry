# Sentryɸ -- Current Phase

**Last Updated:** 2026-10-28
**Current Phase:** P3 — Real File Export (COMPLETE)
**Previous Phase:** P2c — Frontend IPC Integration (COMPLETE)
**Next Phase:** P4 — Garak Engine Adapter

---

## Phase Status

| Phase | Name | Status |
|---|---|---|
| 0a-0e | Design & Documentation Foundation | COMPLETE |
| 1a-1d | Input Layer (consent, validation, probe) | COMPLETE |
| 2a-2d | Manifest System | COMPLETE |
| 3a-3c | Orchestration Layer (estimation, guard, engine) | COMPLETE |
| 5a | Scoring Engine | COMPLETE |
| 5b | Recommendation Engine | COMPLETE |
| 6a | Report Generation + Integration | COMPLETE |
| 6b | UI Architecture Document | COMPLETE |
| 6c | Design System + Theme | COMPLETE |
| S1 | Agreement Screen (Screen 1) | COMPLETE |
| S2 | Input Screen (Screen 2) | COMPLETE |
| S3 | Configuration Screen (Screen 3) | COMPLETE |
| S4 | Estimate Screen (Screen 4) | COMPLETE |
| S5 | Scan Progress Screen (Screen 5) | COMPLETE -- Phase 6d |
| S6 | Results Dashboard (Screen 6) | COMPLETE -- Phase 6e |
| S7 | Recommendations / Actions (Screen 7) | COMPLETE -- Phase 6f |
| S8 | Export Report (Screen 8) | COMPLETE -- Phase 6g |
| S9 | Deploy Configuration (Screen 9) | COMPLETE -- Phase 6h |
| S10 | Cloud Compare (Screen 10) | COMPLETE -- Phase 6i |
| S11 | Deploy Execution (Screen 11) | COMPLETE -- Phase 6j |

---

## Phase 6j -- Deploy Execution (Screen 11) + Navigation Repair

### Pre-Implementation Audit

| Item | Finding |
|---|---|
| **Navigation gap** | `ExportPage` had NO `onProceedToDeploy` prop — users could not reach Screen 9 from Screen 8 |
| **App.tsx deploy-execute** | Route existed but pointed to `PlaceholderPage` |
| **DeployExecutePage** | Did not exist |
| **dryRunTypes.ts** | Did not exist — no dry-run plan engine |
| **Cloud API calls** | Confirmed absent per D-022, D-023 |
| **Azure/GCP provisioning** | Plan-only per D-022 |

### Part A — Navigation Repair (Screen 8 → Screen 9)

**Root cause:** `ExportPage.tsx` had `onBackToResults` and `onBackToActions` props but
no way for users to proceed forward into the deployment workflow.

**Fix:**
- Added `onProceedToDeploy: () => void` prop to `ExportPage`
- Added "Continue to Deployment Planning →" primary button in export actions row
- Updated `App.tsx` to wire `ExportPage` → `handleNavigate("deploy-config")`
- Added `deploy-config`, `deploy-compare`, `deploy-execute` to `STEP_NAV_SCREENS`
  so the stepper is visible on all deployment screens

### Part B — Screen 11: Deploy Execution (Dry-Run Only)

**Architecture:** Local plan generation only. Pure functions. No cloud API calls.

**Safety invariants enforced:**
- `deployed` remains `false` — never set to true anywhere in Screen 11
- No AWS/Azure/GCP API calls — `buildDryRunPlan()` is a pure function
- No credentials stored or used
- Plan ID uses `drp-` prefix — never looks like a real cloud resource ID
- `provenance.source` is always `"local-simulation"`
- Azure/GCP providers show plan-only state — cannot enter simulation
- All plan content is labelled DRY RUN / SIMULATION ONLY
- Stale plan detection via `isDryRunPlanStale()` — config changes invalidate plan
- Final disclaimer explicitly states no cloud resources created

### Files Created

| File | Purpose |
|---|---|
| `src/services/dryRunTypes.ts` | Pure dry-run plan engine (preflight checks, stage builders, plan builder) |
| `src/pages/DeployExecutePage.tsx` | Screen 11 UI — preflight checklist, plan generation, stage display |
| `tests/test_deploy_execute_phase6j.py` | 52-test Phase 6j backend suite |

### Files Modified

| File | Change |
|---|---|
| `src/pages/ExportPage.tsx` | Added `onProceedToDeploy` prop + "Continue to Deployment Planning →" button |
| `src/App.tsx` | Wired `ExportPage` nav, imported `DeployExecutePage`, replaced placeholder |
| `src/index.css` | Appended Screen 11 CSS (~350 lines) + export-page actions layout fix |

### Test Results

| Check | Result |
|---|---|
| `npx tsc --noEmit` | **0 errors** |
| `pytest tests/test_deploy_execute_phase6j.py -v` | **52/52 passed** |
| `pytest tests/ -q` | **971/971 passed** |
| Dev server running | **http://localhost:3000/** |
| HMR hot updates confirmed | All 4 changed files updated live |

### Navigation Flow (fully connected)

```
S1 Agreement → S2 Input → S3 Config → S4 Estimate → S5 Scan
  → S6 Results → S7 Recommendations → S8 Export
  → [NEW] S9 Deploy Config → S10 Cloud Compare → S11 Deploy Execution
```

---

## Phase 6i -- Cloud Compare (Screen 10)

### Pre-Implementation Audit

| Item | Finding |
|---|---|
| **Pricing engine** | None — `estimator.py` is scan-probe cost only (GPT-3.5 tokens), NOT a cloud deployment estimator |
| **`deploy-compare` route** | Existed as `PlaceholderPage` in App.tsx |
| **DeployContext phase** | `"comparing"` state existed in schema but unused |
| **Live cloud pricing API** | None — no AWS/Azure/GCP API calls anywhere |
| **Azure/GCP provisioning** | Confirmed absent per D-022 |
| **Scan bypass** | Did not exist — `ScanPage` had no way to skip to results for testing |

### Files Created / Modified

| File | Change | Purpose |
|---|---|---|
| `frontend/src/services/compareTypes.ts` | **NEW** | Typed comparison model, static illustrative pricing, `buildComparison()`, `isComparisonStale()` |
| `frontend/src/pages/CloudComparePage.tsx` | **NEW** | Screen 10 — Cloud Compare |
| `frontend/src/pages/ScanPage.tsx` | **UPDATED** | Added DEV MODE scan bypass button |
| `frontend/src/App.tsx` | **UPDATED** | Imported + wired `CloudComparePage` replacing placeholder |
| `frontend/src/index.css` | **EXTENDED** | ~350 lines: Screen 10 CSS + dev bypass button styling |
| `backend/tests/test_cloud_compare_phase6i.py` | **NEW** | 41 backend contract + regression tests |

### Pricing Philosophy (§5 compliance)

| Requirement | Implementation |
|---|---|
| No fabricated exact prices | ✅ All values are ILLUSTRATIVE ranges from static table |
| Source URLs provided | ✅ AWS Pricing URLs in `PRICING_SOURCE_METADATA` |
| Data-as-of date | ✅ `"2024-Q4 (illustrative)"` on all entries |
| Exclusions listed | ✅ Data transfer, storage, CloudWatch, support all listed |
| Bedrock: per-token, no estimate | ✅ `monthlyLow: null, monthlyHigh: null` — "Token-based" label |
| SageMaker: illustrative range | ✅ hourly rate × 24h × 30d × replicas, explicitly stated |
| Lambda: consumption-based range | ✅ $0–$25/mo with assumptions shown |
| Partial estimates flagged | ✅ `isPartial: true` + `partialReason` on all estimates |
| "Not a provider quote" | ✅ Explicit in disclaimer text and CSS label |

### Comparison Logic

| Rule | Implementation |
|---|---|
| Only selected option shows cost | `isSelectedConfig` flag — other options show "Select this mode to see estimate" |
| Azure/GCP always plan-only | `provisioningCap: "plan-only"`, dashed border, plan notice |
| Incompatible options dimmed | `opacity: 0.65` + incompatibility badge |
| Recommendation withheld when incomplete | `recommendedId: null` when provider/modelId/region missing |
| Recommendation withheld for Azure/GCP | Explicit rationale — no automated provisioning |
| Stale detection | `isComparisonStale(result, config)` — compares `lastModifiedAt` |
| Config changes rebuild comparison | `useMemo([config])` — rebuilt on every config change |

### Screen 11 Handling

The "Proceed to Deploy Execution" button is **disabled** with `aria-disabled="true"` and a "Coming soon" label. No fake deployment action exists.

### Scan Bypass (DEV MODE)

Added to `ScanPage` for development testing only:
- Red dashed border box labeled "DEV MODE"
- "⚡ Skip Scan (inject simulated report)" button
- Calls `buildSimulatedReport()` → dispatches `SET_REPORT` → `SCAN_COMPLETE` → `onComplete()`
- Allows testing Screens 6-10 without a working backend scan engine

### Test Results

| Command | Result |
|---|---|
| `npx tsc --noEmit` | ✅ **Exit 0 — zero type errors** |
| `pytest tests/test_cloud_compare_phase6i.py -v` | ✅ **41/41 passed** |
| `pytest tests/ -q` | ✅ **919/919 passed — zero regressions** |

### Known Limitations

- No live cloud pricing — static illustrative ranges only
- Bedrock cost estimate unavailable (token-based pricing requires request volume)
- SageMaker pricing assumes always-on (24h/day) — not representative of auto-scaled deployments
- Region pricing variations not captured (us-east-1 rates only)
- Azure/GCP pricing completely unavailable — "See provider pricing page" shown
- Screen 11 (Deploy Execution) not implemented — Proceed button disabled

---

## Phase 6h -- Deploy Configuration (Screen 9)

### Pre-Implementation Audit

| Item | Finding |
|---|---|
| **Cloud backend modules** | None exist — no deploy/cloud/AWS code in `core/` or `services/` |
| **DeployContext** | NOT YET CREATED (only stub actions in `actions.ts`) |
| **Screen 9 route** | `"deploy-config"` existed as `PlaceholderPage` |
| **Supported providers** | AWS (provisioning); Azure/GCP (config docs only) — per D-022 |
| **Credentials** | No IPC/keychain bridge at this stage — no credential handling needed |
| **Desktop runtime** | Browser-only Vite dev server — no Electron/Tauri IPC available |

### Files Created / Modified

| File | Change | Purpose |
|---|---|---|
| `frontend/src/services/deployTypes.ts` | NEW | Typed config model, validation functions, static region/mode/instance lists |
| `frontend/src/store/DeployContext.tsx` | NEW | useReducer + React Context for deploy config state |
| `frontend/src/pages/DeployConfigPage.tsx` | NEW | Screen 9 configuration form |
| `frontend/src/App.tsx` | UPDATED | Import + wire DeployProvider, replace placeholder case |
| `frontend/src/index.css` | EXTENDED | ~390 lines Screen 9 CSS |
| `backend/tests/test_deploy_config_phase6h.py` | NEW | 30 backend contract + regression tests |

### Supported Providers

| Provider | Support | Notes |
|---|---|---|
| **AWS** | Full configuration | Bedrock, SageMaker, Lambda modes |
| **Azure** | Configuration plan only | No automated provisioning in v1 (D-022) |
| **GCP** | Configuration plan only | No automated provisioning in v1 (D-022) |

### AWS Deployment Modes

| Mode | Description |
|---|---|
| `bedrock` | Amazon Bedrock managed model endpoint — no inference infra needed |
| `sagemaker` | SageMaker real-time inference endpoint — custom model artifacts + GPU |
| `lambda` | API Gateway + Lambda — serverless, lightweight |

### Configuration Model (DeployConfig)

Fields: `provider`, `mode`, `region`, `modelId`, `modelLabel`, `instanceType`, `replicas`,
`endpointScope`, `requireAuth`, `enableLogging`, `enableGuardrails`, `budgetMonthlyUsd`,
`sourceScanId`, `isSimulated`, `lastModifiedAt`, `deployed: false`

**Credentials: NEVER stored** (D-017). `deployed` is a literal `false` type — no provisioning in Phase 6h.

### Validation Rules

| Rule | Status |
|---|---|
| Provider required | Blocking |
| Mode required (AWS) | Blocking |
| Region required | Blocking |
| Model ID required (≥3 chars) | Blocking |
| Instance type required (SageMaker) | Blocking |
| Replicas ≥ 1 | Blocking |
| Public endpoint + no auth | Blocking |
| Budget ≤ 0 | Blocking |
| Azure/GCP selection | Unverified (not blocking) |
| Bedrock mode + non-Bedrock region | Unverified (not blocking) |
| Budget amount | Informational — not a provider-enforced cap |
| Region availability | Unverified — static list, disclaimer shown |

### Security Implementation

- `endpointScope` defaults to `"private"` — never silently public
- `requireAuth` defaults to `true`
- Public endpoint without auth is a **blocking** validation error
- Credentials (access key, secret key, tokens) are **never** collected or stored
- Budget is labeled informational — no billing alert created
- Provider change resets `mode`, `region`, `instanceType` — no stale incompatible state
- `deployed: false` literal type enforced throughout

### State Architecture

- `DeployContext` is separate from `ReportContext` — scan report is never mutated
- Config patch always reruns `validateDeployConfig()` — no stale Valid state
- Session-only: no localStorage or file persistence
- `DeployProvider` wraps the app alongside `ScanProvider` + `ReportProvider`

### Navigation

- Entry: Screen 8 (Export) → Screen 9
- Back: `onBack` → `navigateTo("export")`
- Proceed: `onProceed` → `navigateTo("deploy-compare")` (only when `canProceed=true`)
- Screen 10 (`deploy-compare`) remains a `PlaceholderPage` — not yet implemented

### Test Results

| Command | Result |
|---|---|
| `pytest tests/test_deploy_config_phase6h.py -v` | 30/30 passed |
| `pytest tests/ -q` | 878/878 passed (zero regressions) |
| `npx tsc --noEmit` | Exit 0 — zero type errors |

### Known Limitations

- No native save dialog / IPC bridge — browser-only at this stage
- Region availability is a static list — not verified against live AWS APIs
- Bedrock model ID format is labeled "unverified" — no ARN validation library
- Screen 10 (Cloud Compare) not yet implemented — Proceed button routes to PlaceholderPage

---

## Phase 6g -- Export Report (Screen 8)

### Files Created / Modified

| File | Change | Purpose |
|---|---|---|
| `frontend/src/pages/ExportPage.tsx` | NEW | Screen 8 report preview + download |
| `frontend/src/App.tsx` | UPDATED | Replaced PlaceholderPage with ExportPage |
| `frontend/src/index.css` | EXTENDED | Screen 8 CSS (~230 lines) |
| `backend/tests/test_export_phase6g.py` | NEW | 49 focused export tests |

### Pre-Implementation Audit

| Item | Finding |
|---|---|
| **Supported formats (backend)** | `json` + `txt` only (line 358 rejects all others) |
| **PDF** | NOT supported -- no backend exporter, no frontend PDF library |
| **HTML** | NOT in backend exporter -- implemented safely in frontend |
| **Desktop save dialog** | No IPC bridge at this stage (report_service.py notes "When Electron app is built") |
| **Save mechanism** | Browser Blob + `<a download>` |
| **Export state** | EXPORT_START/SUCCESS/FAILED/RESET + fields already in ReportContext -- reused |
| **Provenance** | `scan_id.startsWith("sim-")` confirmed in buildSimulatedReport |

### Formats Offered

| Format | Generator | Notes |
|---|---|---|
| JSON | `JSON.stringify(report, null, 2)` | Canonical schema, exact to_dict() equivalent |
| Plain Text | `serializeToTxt()` in ExportPage.tsx | Mirrors backend format_txt_report() |
| HTML | `serializeToHtml()` in ExportPage.tsx | Standalone offline document, fully escaped |
| PDF | NOT OFFERED | Future enhancement -- safely unachievable without a dependency |

### Security Implementation

- All untrusted content (evidence, target, probe_id, source, actions) passed through `escapeHtml()`
- `escapeHtml()` replaces `&`, `<`, `>`, `"`, `'` -- no `dangerouslySetInnerHTML` used anywhere
- No report data transmitted externally
- `output_dir` path NOT exposed in preview or HTML export
- `triggerDownload()` creates Blob in-browser and revokes URL after 5s
- Export guarded by `exportingFmt` state (prevents double-click duplicate downloads)

### Architecture Decisions

- HTML is generated entirely in the frontend (no IPC bridge to backend exporter)
- TXT mirrors backend format but re-generated in frontend (no IPC at this stage)
- Simulated reports detected by `scan_id.startsWith("sim-")` -- disclaimer shown in all outputs
- Back navigation: `onBackToResults` to results, `onBackToActions` to actions (hub branch returns)
- Reuses existing ReportContext EXPORT_* actions -- no state duplication

### Test Results

| Command | Result |
|---|---|
| `python -m pytest tests/test_export_phase6g.py -v` | 49/49 passed |
| `python -m pytest tests/ -v` | 848/848 passed (zero regressions) |
| `npx tsc --noEmit` | Exit 0 -- zero type errors |

### Known Limitations

- No native save dialog (browser download only -- no IPC bridge at this stage)
- No PDF export (not safely implementable without a dependency)
- TXT format is frontend-generated (mirrors backend but not byte-identical)
- Download success inferred from no thrown error (browser popup blocker may interfere)

---

## Phase 6f -- Recommendations / Actions (Screen 7)

### Files Created / Modified

| File | Change | Purpose |
|---|---|---|
| `frontend/src/pages/ActionsPage.tsx` | NEW | Screen 7 recommendation workspace |
| `frontend/src/store/actions.ts` | EXTENDED | Added TOGGLE_REC_REVIEW, SET_REC_REVIEWED, CLEAR_REC_REVIEWS |
| `frontend/src/store/ReportContext.tsx` | EXTENDED | Added rec_reviewed: Record\<string, boolean\> to state + reducer |
| `frontend/src/App.tsx` | UPDATED | Replaced PlaceholderPage with ActionsPage |
| `frontend/src/index.css` | EXTENDED | Full Screen 7 CSS (~400 lines) |

### Recommendation Schema (Confirmed from recommender.py)

```
Recommendation.to_dict() = { category: string, severity: string, actions: string[] }
```
- No `priority` field -- severity IS the priority (backend sorts HIGH → MED → LOW)
- No `rationale` field -- actions[] is the only remediation content
- No `verification` field -- not in backend contract, not fabricated
- No probe_id link -- recommendations are category-scoped only

### Architecture Decisions

- `rec_reviewed: Record<string, boolean>` in ReportState -- keyed by category
- Toggled ONLY by explicit user action (TOGGLE_REC_REVIEW dispatch)
- Cleared on new report load -- never persisted, session-only
- Marking reviewed ≠ fix applied or verified (review note shown in UI)
- Finding association is category-only (no stable probe_id in Recommendation)
- Filter/sort state is local useState in ActionsPage (no global dispatch needed)
- "Back" uses navigateTo("results") -- hub branch rule from UI_ARCHITECTURE.md §2

### Test Results

| Check | Result |
|---|---|
| `npx tsc --noEmit` | ✅ Zero errors |
| Vite dev server | ✅ Ready \<400ms |
| Browser live test | ⚠ Browser session closed during scan wait (infrastructure issue, not code) |

### Known Limitations

- Review state session-only (no localStorage persistence)
- No rationale/verification text (not in backend Recommendation schema)
- Category-only finding association (no probe_id link available)
- Export from Screen 7 navigates to placeholder Screen 8 (not yet implemented)

---

## Phase 6d -- Scan Progress Screen (Screen 5)

### Files Created / Modified

| File | Purpose |
|---|---|
| `frontend/src/services/scanTypes.ts` | NEW: Typed event contract -- lifecycle stages, progress events, activity entries |
| `frontend/src/services/scanService.ts` | REWRITE: Tick-based simulation (no async/await in probe loop) |
| `frontend/src/store/ScanContext.tsx` | EXTENDED: scan_execution state, SCAN_PROGRESS_EVENT, SCAN_ACTIVITY_EVENT |
| `frontend/src/store/actions.ts` | EXTENDED: SCAN_PROGRESS_EVENT, SCAN_ACTIVITY_EVENT action types |
| `frontend/src/pages/ScanPage.tsx` | NEW: Screen 5 -- full scan progress UI |
| `frontend/src/App.tsx` | UPDATED: scan_active navigation protection |
| `frontend/src/index.css` | EXTENDED: complete scan page CSS (categories, feed, dialog, etc.) |

### Architecture Decisions (Phase 6d)

#### Scan Service: Tick-Based State Machine
- Previous approach used `async/await + sleep()` which stalls in background browser tabs (browser throttles setTimeout to ≥1000ms)
- New approach: single `tick()` function advances state machine by PROBES_PER_TICK probes per call
- `scheduleTick()` reschedules with `setTimeout(100ms)` — degrades gracefully to ~1/sec in background
- State held in plain JS object (`SimState`), not React state — no re-render loops

#### Scan Event Contract (scanTypes.ts)
- `ScanLifecycleStage`: 13 discrete stages with validated transitions
- `ScanProgressEvent`: full snapshot per tick (stage, probes, categories, findings, elapsed)
- `ScanActivityEntry`: timestamped log lines with severity (info/warn/error/debug)
- `VALID_TRANSITIONS`: enforced state machine — prevents invalid stage jumps
- All user-facing labels are generic security terms — no external engine names (Garak, PyRIT etc.)

#### ScanContext Extension
- `scan_execution: ScanExecutionState | null` — full execution state added to existing ScanState
- `scan_active: boolean` — used by App.tsx to block StepNav navigation during scan
- `activity_log: ScanActivityEntry[]` — capped at MAX_LOG_ENTRIES=200 (prevents memory growth)
- Backward compatible — all existing fields and actions preserved

#### ScanPage Layout
- Region A: PageHeader — title "Security Scan", subtitle = target URL
- Region B: Progress bar — percentage, probes count, elapsed time
- Region C: Current Stage label (CURRENT STAGE + activity_label)
- Region D: Category Progress table — per-category badge (Queued/Active/Complete/Failed)
- Region E: Activity Feed — monospace scrollable log, auto-scrolls, 220px max height
- Region F: Preliminary Findings count (shown only when findings > 0, amber color)
- Region G: Cancel Scan button → confirmation dialog → safe cancellation

#### Navigation Protection
- `state.scan_active = true` during scan phases
- App.tsx `handleStepNavClick` checks `scan_active` and blocks navigation
- Only `ScanPage.onComplete` and `ScanPage.onCancel` can exit the scan screen
- Cancel requires explicit confirmation in modal dialog (per UI_ARCHITECTURE.md rule 6)

### Lifecycle States (ScanPage)

```
Mount → auto-start scan (useEffect, hasStartedRef guard)
     → runSimulation() → tick() loop every 100ms
     → dispatch SCAN_PROGRESS_EVENT → ScanContext → re-render
     → dispatch SCAN_ACTIVITY_EVENT → activity_log grows

onComplete → setIsCompleting(true) → 1.5s pause → navigate to results
onCancel → setShowCancelConfirm(true) → confirm → controller.cancel() → navigate to config
onError → SCAN_FAILED dispatch → error banner + retry button

Unmount → mountedRef.current = false → controller.cancel() → tick() stops
```

### CSS Classes Added (index.css)

| Class | Purpose |
|---|---|
| `.scan-page__progress-track/fill` | Progress bar |
| `.scan-page__progress-fill--complete` | Success color on 100% |
| `.scan-page__status-row` | Current stage + findings row |
| `.scan-page__cat-list/row/label/probes/badge` | Category progress table |
| `.scan-page__cat-badge--queued/active/complete/failed` | Category status badges |
| `.scan-page__feed` | Activity feed scrollable container |
| `.scan-page__feed-entry--info/warn/error/debug` | Activity entry severity colors |
| `.scan-page__overlay + dialog` | Cancel confirmation modal |
| `.scan-page__error-block/cancelled-block` | Terminal state displays |

---

## Screen 1 -- Agreement Page

### Files Created

| File | Purpose |
|---|---|
| `frontend/src/store/actions.ts` | Action type constants for all 3 contexts |
| `frontend/src/store/ScanContext.tsx` | Scan lifecycle state, consent persistence |
| `frontend/src/hooks/useScan.ts` | ScanContext consumer hook |
| `frontend/src/hooks/useNavigation.ts` | Step-based wizard navigation |
| `frontend/src/components/layout/PageHeader.tsx` | Consistent page header |
| `frontend/src/pages/AgreementPage.tsx` | Screen 1: consent gate |
| `frontend/src/App.tsx` | Root component + screen router |
| `frontend/src/main.tsx` | React 18 entry point |

### Architecture Decisions

- **No external UI library**: All components are vanilla React + TypeScript
- **BEM class naming**: `agreement-page__section-title`, `button--primary`
- **Consent in localStorage**: Key `aisentry_consent_given`, corruption-safe reads
- **onAccept callback**: Page does not own navigation; parent router decides where to go
- **In-memory router**: No URL-based routing; ScreenRouter uses switch/case on ScreenId

---

## Full CLI Pipeline (unchanged -- 13 steps)

```
Step 1:  Consent gate          core/consent.py
Step 2:  Manifest load+merge   core/manifest.py
Step 3:  Manifest validation   core/manifest_validator.py
Step 4:  Estimate              core/estimator.py
Step 5:  Safety guard          core/scan_guard.py
Step 6:  Display + confirm     core/manifest_display.py
Step 7:  Connection validate   core/validator.py
Step 8:  Endpoint probe        core/input_handler.py or core/local_handler.py
Step 9:  Scan engine           core/engine_runner.py
Step 10: Risk scoring          core/scorer.py
Step 11: Recommendations       core/recommender.py
Step 12: Report generation     core/report_generator.py + services/report_service.py
Step 13: File export           core/report_generator.py :: export_report()
```

## Current Test Count: 799 (backend only -- frontend tests pending)

---

## Frontend File Structure (current)

```
app/frontend/
+-- src/
|   +-- main.tsx                       # React 18 entry
|   +-- App.tsx                        # Root + ScreenRouter + ReportProvider
|   +-- index.css                      # Master stylesheet (token-based)
|   +-- styles/
|   |   +-- design-tokens.css          # Spacing, font, shadow, timing tokens
|   |   +-- theme.css                  # Semantic color tokens (dark/light)
|   +-- pages/
|   |   +-- AgreementPage.tsx          # Screen 1 (DONE)
|   |   +-- InputPage.tsx              # Screen 2 (DONE)
|   |   +-- ConfigPage.tsx             # Screen 3 (DONE)
|   |   +-- EstimatePage.tsx           # Screen 4 (DONE)
|   |   +-- ScanPage.tsx               # Screen 5 (DONE -- Phase 6d)
|   |   +-- ResultsPage.tsx            # Screen 6 (DONE -- Phase 6e)
|   +-- store/
|   |   +-- actions.ts                 # Action type constants (SCAN, REPORT, DEPLOY)
|   |   +-- ScanContext.tsx            # Scan state + reducer
|   |   +-- ReportContext.tsx          # NEW: Report state + filter/sort + sim builder
|   +-- hooks/
|   |   +-- useScan.ts                 # ScanContext consumer
|   |   +-- useNavigation.ts           # Wizard navigation
|   +-- components/
|   |   +-- layout/
|   |   |   +-- PageHeader.tsx         # Page header component
|   |   |   +-- StepNav.tsx            # Step navigation bar
|   |   |   +-- ThemeToggle.tsx        # Dark/light mode toggle
|   |   +-- forms/
|   |   |   +-- TextInput.tsx          # Text field
|   |   |   +-- RadioGroup.tsx         # Radio options
|   |   |   +-- CheckboxGroup.tsx      # Multi-select checkboxes
|   |   |   +-- FileDropZone.tsx       # Drag-and-drop file input
|   |   +-- feedback/
|   |       +-- AlertBanner.tsx        # Warning/error/info banner
|   +-- services/
|       +-- estimatorService.ts        # Scan estimation (simulated IPC)
|       +-- scanTypes.ts               # Phase 6d: event contract types
|       +-- scanService.ts             # Phase 6d: tick-based simulator
|       +-- reportTypes.ts             # NEW Phase 6e: ScanReport type contract
```

---

## Context Notes for AI Tools

- Frontend uses TypeScript + React (no external state libs, no UI frameworks)
- Class names follow BEM convention
- ScanContext initializer reads localStorage once at mount
- Navigation is in-memory (useState), not URL-based
- `scan_active` flag in ScanContext blocks StepNav during active scan
- Scan simulator uses tick-based state machine (no async/await in probe loop)
- scanTypes.ts is the BRIDGE CONTRACT between simulator and future IPC backend
- Do NOT commit or push to GitHub -- user handles commits manually
