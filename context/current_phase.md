# Sentryɸ -- Current Phase

**Last Updated:** 2026-10-03
**Current Phase:** Screen 5 -- Scan Progress Page (Phase 6d -- COMPLETE)
**Previous Phase:** Screen 4 -- Estimate Page (COMPLETE)
**Next Phase:** Screen 6 -- Results Dashboard (Phase 6e)

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
| S6 | Results Dashboard (Screen 6) | NOT STARTED -- READY |
| S7+ | Remaining Screens (7-11) | NOT STARTED |

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
|   +-- App.tsx                        # Root + ScreenRouter + nav protection
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
|   +-- store/
|   |   +-- actions.ts                 # Action type constants
|   |   +-- ScanContext.tsx            # Scan state + reducer (extended Phase 6d)
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
|       +-- scanTypes.ts               # NEW (Phase 6d): event contract types
|       +-- scanService.ts             # REWRITE (Phase 6d): tick-based simulator
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
