# AI SENTRY -- UI Architecture Document

**Phase 6b Deliverable**
**Last Updated:** 2026-09-26
**Status:** APPROVED -- Ready for Implementation

---

## Table of Contents

1. [Application Architecture](#1-application-architecture)
2. [Navigation Model](#2-navigation-model)
3. [State Management](#3-state-management)
4. [Data Flow](#4-data-flow)
5. [File Structure](#5-file-structure)
6. [Component System](#6-component-system)
7. [UX Rules](#7-ux-rules)
8. [Edge Case Handling](#8-edge-case-handling)
9. [IPC Contract Reference](#9-ipc-contract-reference)

---

## 1. Application Architecture

### Process Model

```
+--------------------------------------------------------------+
|                     ELECTRON MAIN PROCESS                    |
|                                                              |
|  +--------------+   +--------------+   +------------------+  |
|  |  Window Mgr  |   |  IPC Router  |   |  Python Bridge   |  |
|  |  (BrowserWin) |   |  (handlers)  |   |  (child_process) |  |
|  +--------------+   +--------------+   +------------------+  |
|                           |                     |            |
|                           |              +------+------+     |
|                           |              |  Python      |     |
|                           |              |  Backend     |     |
|                           |              |  (stdin/out) |     |
|                           |              +-------------+     |
+---------------------------+----------------------------------+
                            | contextBridge / preload
+---------------------------+----------------------------------+
|                     RENDERER PROCESS                         |
|                                                              |
|  +--------------+   +--------------+   +------------------+  |
|  |  React App   |   |  IPC Client  |   |  State Store     |  |
|  |  (pages +    |   |  (window.api) |   |  (useReducer)   |  |
|  |   components)|   +--------------+   +------------------+  |
|  +--------------+                                             |
+--------------------------------------------------------------+
```

### Communication Pattern

The Electron main process spawns Python as a **child process**. Communication is JSON-over-stdio:

1. **UI to Main Process**: Renderer calls `window.api.<method>()` (exposed via `contextBridge` in `preload.js`)
2. **Main Process to Python**: Main process writes JSON command to Python's stdin
3. **Python to Main Process**: Python writes JSON response to stdout
4. **Main Process to UI**: Main process resolves the IPC promise, renderer receives plain dict

> [!IMPORTANT]
> The renderer NEVER talks to Python directly. All communication is mediated by the main process IPC router. This enforces the security boundary required by Electron's `contextIsolation`.

### How a Scan is Triggered

```
User clicks "Start Scan"
    |
    v
Renderer: window.api.startScan(manifestConfig)
    |
    v
Main Process: ipcMain.handle('scan:start', ...)
    |
    v
Python Bridge: writes { "command": "scan", "config": {...} } to stdin
    |
    v
Python: executes full 13-step pipeline
    |  (progress events sent as newline-delimited JSON to stdout)
    v
Python: writes { "event": "scan:complete", "report": ScanReport.to_dict() }
    |
    v
Main Process: resolves IPC promise with report dict
    |
    v
Renderer: receives ScanReport, updates state, navigates to Results
```

### How a Report is Returned

The `ScanReport.to_dict()` output from `report_service.py` is the **exact JSON** the UI consumes. No transformation, no BFF layer. The renderer binds directly to:

```
report.meta.target           -> header display
report.summary.risk_score    -> score gauge
report.breakdown             -> severity chart
report.categories            -> category cards
report.findings              -> findings table
report.recommendations       -> action list
report.engine                -> footer metadata
```

---

## 2. Navigation Model

### Screen Flow

The application follows a **linear wizard** pattern with conditional branches. Users progress forward through the workflow and can navigate back to earlier steps (but not skip ahead).

```
+-----------+     +-----------+     +-----------+
| 1. AGREE  |---->| 2. INPUT  |---->| 3. CONFIG |
| (consent) |     | (target)  |     | (manifest)|
+-----------+     +-----------+     +-----------+
                                          |
                                          v
+-----------+     +-----------+     +-----------+
| 6. RESULTS|<----| 5. SCAN   |<----| 4. CONFIRM|
| (dashboard)     | (progress)|     | (estimate)|
+-----------+     +-----------+     +-----------+
      |
      +--------------------+
      v                    v
+-----------+     +-----------+
| 7. ACTIONS|     | 8. EXPORT |
| (recommend)     | (report)  |
+-----------+     +-----------+
                        |
                        v
                  +-----------+     +-----------+
                  | 9. DEPLOY |---->|10. COMPARE|
                  | (config)  |     | (cloud)   |
                  +-----------+     +-----------+
                        |
                        v
                  +-----------+
                  |11. EXECUTE|
                  | (deploy)  |
                  +-----------+
```

### Screen Definitions

| # | Screen ID | Purpose | Entry Condition | Exit Condition |
|---|---|---|---|---|
| 1 | `agree` | Legal consent + disclaimer | App launch (first scan) | User accepts terms |
| 2 | `input` | Target entry (URL, file path, drag-drop) | Consent accepted | Valid target provided |
| 3 | `config` | Scan configuration (mode, depth, categories) | Target validated | Manifest assembled |
| 4 | `confirm` | Estimation display + safety gate + final confirmation | Manifest built | User confirms (incl. heavy scan gate if triggered) |
| 5 | `scan` | Scan progress (probe counter, elapsed time, log) | User confirmed | Pipeline complete or error |
| 6 | `results` | Risk dashboard (score, breakdown, findings) | Scan complete | User navigates to actions/export |
| 7 | `actions` | Recommendations with prioritized fix actions | User clicks from results | User returns or exports |
| 8 | `export` | Report export (JSON, TXT, PDF future) | User clicks from results/actions | File saved or user returns |
| 9 | `deploy-config` | Deployment target selection (AWS, Azure, GCP) | User clicks from results | Config selected |
| 10 | `deploy-compare` | Cloud provider comparison matrix | Config selected | User selects provider |
| 11 | `deploy-execute` | Deployment execution + status | User confirms deployment | Deployment complete/failed |

### Transition Rules

1. **Forward-only during scan**: Once Step 5 (scan) begins, back-navigation is disabled until completion or failure
2. **Back allowed pre-scan**: Steps 1-4 allow free backward navigation
3. **Hub from results**: Step 6 (results) acts as a **hub** -- user can branch to actions, export, or deploy from here
4. **Consent is one-time**: After first acceptance, Step 1 is skipped on subsequent scans within the same session
5. **New scan restarts**: Starting a new scan returns to Step 2 (input), preserving consent

---

## 3. State Management

### Architecture

State is managed via `useReducer` + React Context at the app root. No external state library. Three domain-specific stores:

```
AppStateProvider
  +-- ScanContext       (scan lifecycle + configuration)
  +-- ReportContext     (ScanReport data + UI selections)
  +-- DeployContext     (deployment configuration + status)
```

### ScanContext

```
ScanState {
  // Lifecycle
  phase:          "idle" | "consented" | "configuring" | "confirming"
                  | "scanning" | "complete" | "failed" | "cancelled"

  // Configuration (assembled in Steps 2-3)
  target:         string | null
  mode:           "api" | "local" | null
  scan_depth:     "quick" | "standard" | "deep"
  categories:     string[]             // selected probe categories

  // Progress (updated during Step 5)
  progress: {
    current_probe:  number
    total_probes:   number
    elapsed_sec:    number
    current_step:   string             // e.g. "Running prompt_injection probes..."
  } | null

  // Errors
  error:          string | null

  // Consent
  consent_given:  boolean
}
```

**Transitions:**

| From | Event | To |
|---|---|---|
| `idle` | User accepts consent | `consented` |
| `consented` | User enters target | `configuring` |
| `configuring` | User confirms config | `confirming` |
| `confirming` | User clicks "Start Scan" | `scanning` |
| `scanning` | Pipeline finishes | `complete` |
| `scanning` | Pipeline fails | `failed` |
| `scanning` | User aborts | `cancelled` |
| `complete` | User starts new scan | `consented` |
| `failed` | User starts new scan | `consented` |

### ReportContext

```
ReportState {
  // Data (set once scan completes)
  report:         ScanReport | null    // exact JSON from backend
  report_id:      string | null

  // UI state (user interactions on results/actions screens)
  selected_category:    string | null  // filter for findings view
  selected_severity:    string | null  // filter for findings view
  findings_sort:        "severity" | "category" | "confidence"
  findings_page:        number         // pagination offset

  // Export
  export_status:  "idle" | "exporting" | "success" | "failed"
  export_error:   string | null
  last_export_path: string | null
}
```

### DeployContext

```
DeployState {
  phase:          "idle" | "configuring" | "comparing" | "executing"
                  | "complete" | "failed"

  provider:       "aws" | "azure" | "gcp" | null
  region:         string | null
  config:         object | null        // provider-specific config

  // Execution
  deploy_status:  string | null
  deploy_error:   string | null
}
```

### How State Flows Across Screens

```
Step 1 (Agree)    ->  sets: consent_given = true
Step 2 (Input)    ->  sets: target, mode (auto-detected from URL vs file path)
Step 3 (Config)   ->  sets: scan_depth, categories
Step 4 (Confirm)  ->  reads: full ScanState for estimation display
Step 5 (Scan)     ->  reads+writes: progress (updated via IPC events)
Step 6 (Results)  ->  reads: ReportState.report (set on scan complete)
Step 7 (Actions)  ->  reads: report.recommendations
Step 8 (Export)   ->  reads: report, writes: export_status
Step 9-11 (Deploy)->  reads: report.summary, writes: DeployState
```

---

## 4. Data Flow

### Full Scan Pipeline

```
                    RENDERER                MAIN PROCESS           PYTHON BACKEND
                    --------                ------------           --------------

Step 2-3:  User fills config
                |
                v
           dispatch({type: "SET_CONFIG", payload})
                |
Step 4:    UI shows estimation
           (calculated client-side from
            PROBES_PER_CATEGORY * depth_multiplier)
                |
                v
           User clicks "Start Scan"
                |
                v
           window.api.startScan(config)  -------->  ipcMain.handle('scan:start')
                                                          |
                                                          v
                                                   pythonBridge.send({
                                                     command: "scan",
                                                     config: { target, mode,
                                                       scan_depth, categories }
                                                   })
                                                          |
                                                          v
                                                                         Pipeline Steps 1-13
                                                                               |
                                              <--- progress events ------------+
                                                   { event: "scan:progress",   |
                                                     step: 9,                  |
                                                     probe: 5,                |
                                                     total: 9 }               |
                |                                                              |
                v                                                              |
           dispatch({type: "UPDATE_PROGRESS"})                                 |
                                                                               v
                                              <--- { event: "scan:complete",
                                                     report: ScanReport.to_dict() }
                |
                v
           dispatch({type: "SET_REPORT", payload: report})
                |
                v
           Navigate to Step 6 (Results)
```

### Report Export Flow

```
User clicks "Export JSON"
    |
    v
window.api.exportReport(scan_id, format, path)
    |
    v
ipcMain.handle('report:export')
    |
    v
Python: export_report(report, path, fmt)
    |
    v
Returns ExportResult { ok, path, format, bytes_written, error }
    |
    v
UI updates export_status
```

### Report Retrieval Flow (for history / re-open)

```
User opens report history
    |
    v
window.api.listReports()  ->  report_service.list_report_ids()  ->  [id1, id2, ...]
    |
    v
User clicks a report
    |
    v
window.api.getReport(id)  ->  report_service.get_report_by_id(id)  ->  ScanReport dict
    |
    v
dispatch({type: "SET_REPORT", payload: report})
    |
    v
Navigate to Results
```

---

## 5. File Structure

```
app/
+-- electron/                          # Electron main process
|   +-- main.js                        # App entry, window creation, menu
|   +-- preload.js                     # contextBridge API exposure
|   +-- ipc/                           # IPC handler registration
|   |   +-- scan-handlers.js           # scan:start, scan:abort
|   |   +-- report-handlers.js         # report:get, report:export, report:list
|   |   +-- deploy-handlers.js         # deploy:start, deploy:status
|   +-- python-bridge.js               # Child process spawn + JSON stdio
|
+-- src/                               # React renderer
|   +-- main.jsx                       # React entry point
|   +-- App.jsx                        # Root component + providers + router
|   |
|   +-- pages/                         # One file per screen (step)
|   |   +-- AgreePage.jsx              # Step 1: consent
|   |   +-- InputPage.jsx              # Step 2: target entry
|   |   +-- ConfigPage.jsx             # Step 3: scan configuration
|   |   +-- ConfirmPage.jsx            # Step 4: estimation + confirm
|   |   +-- ScanPage.jsx               # Step 5: progress
|   |   +-- ResultsPage.jsx            # Step 6: risk dashboard
|   |   +-- ActionsPage.jsx            # Step 7: recommendations
|   |   +-- ExportPage.jsx             # Step 8: report export
|   |   +-- DeployConfigPage.jsx       # Step 9: deployment config
|   |   +-- DeployComparePage.jsx      # Step 10: cloud comparison
|   |   +-- DeployExecutePage.jsx      # Step 11: deployment execution
|   |
|   +-- components/                    # Reusable UI components
|   |   +-- layout/
|   |   |   +-- AppShell.jsx           # Main layout (sidebar + content)
|   |   |   +-- StepIndicator.jsx      # Wizard progress indicator
|   |   |   +-- PageHeader.jsx         # Consistent page header
|   |   +-- forms/
|   |   |   +-- TextInput.jsx          # Single-line text field
|   |   |   +-- FileDropZone.jsx       # Drag-and-drop file input
|   |   |   +-- CheckboxGroup.jsx      # Multi-select checkboxes
|   |   |   +-- RadioGroup.jsx         # Single-select options
|   |   |   +-- SelectDropdown.jsx     # Dropdown selector
|   |   +-- feedback/
|   |   |   +-- ProgressBar.jsx        # Determinate progress
|   |   |   +-- StatusBadge.jsx        # Severity/status tags
|   |   |   +-- AlertBanner.jsx        # Warnings and errors
|   |   |   +-- EmptyState.jsx         # No-data placeholder
|   |   +-- data/
|   |   |   +-- ScoreGauge.jsx         # 0-100 risk score display
|   |   |   +-- SeverityChart.jsx      # High/Med/Low breakdown
|   |   |   +-- CategoryCard.jsx       # Per-category summary
|   |   |   +-- FindingRow.jsx         # Single finding in table
|   |   |   +-- FindingsTable.jsx      # Sortable/filterable findings
|   |   |   +-- RecommendationCard.jsx # Category + actions list
|   |   |   +-- EngineInfo.jsx         # Engine metadata footer
|   |   +-- common/
|   |       +-- Button.jsx             # Primary, secondary, danger, ghost
|   |       +-- IconButton.jsx         # Icon-only actions
|   |       +-- Tooltip.jsx            # Contextual help
|   |       +-- Modal.jsx              # Confirmation dialogs
|   |       +-- Divider.jsx            # Section separator
|   |
|   +-- hooks/                         # Custom React hooks
|   |   +-- useScan.js                 # ScanContext consumer
|   |   +-- useReport.js               # ReportContext consumer
|   |   +-- useDeploy.js               # DeployContext consumer
|   |   +-- useIPC.js                  # window.api wrapper + error handling
|   |   +-- useNavigation.js           # Step-based navigation logic
|   |
|   +-- store/                         # State management
|   |   +-- ScanContext.jsx            # ScanState + reducer + provider
|   |   +-- ReportContext.jsx          # ReportState + reducer + provider
|   |   +-- DeployContext.jsx          # DeployState + reducer + provider
|   |   +-- actions.js                 # Action type constants
|   |
|   +-- services/                      # IPC call wrappers
|   |   +-- scan-service.js            # startScan(), abortScan()
|   |   +-- report-service.js          # getReport(), exportReport(), listReports()
|   |   +-- deploy-service.js          # startDeploy(), getDeployStatus()
|   |
|   +-- utils/                         # Pure utility functions
|       +-- format.js                  # Number formatting, time display
|       +-- severity.js                # Severity ordering, label mapping
|       +-- validation.js              # Client-side input checks
|
+-- backend/                           # Python backend (existing)
|   +-- core/                          # Engine, scoring, reporting
|   +-- services/                      # report_service.py
|   +-- cli/                           # CLI entry point
|
+-- package.json
```

---

## 6. Component System

### Component Hierarchy

Each component has a single responsibility. No component directly calls IPC -- they receive data via props or context.

#### Layout Components

| Component | Responsibility | Props |
|---|---|---|
| `AppShell` | Fixed sidebar + scrollable content area. Houses nav and step indicator. | `children` |
| `StepIndicator` | Shows current step in the 11-step workflow. Indicates completed, current, and future steps. | `currentStep`, `totalSteps`, `completedSteps` |
| `PageHeader` | Page title + optional subtitle + optional back button. | `title`, `subtitle?`, `onBack?` |

#### Form Components

| Component | Responsibility | Props |
|---|---|---|
| `TextInput` | Single-line input with label, validation state, helper text. | `label`, `value`, `onChange`, `error?`, `placeholder?`, `disabled?` |
| `FileDropZone` | Drag-and-drop area for manifest files. Shows file name on drop. | `onFile`, `accept`, `error?` |
| `CheckboxGroup` | Multi-select checkboxes with labels. Used for category selection. | `options[]`, `selected[]`, `onChange`, `disabled?` |
| `RadioGroup` | Single-select radio options. Used for scan depth and mode. | `options[]`, `selected`, `onChange`, `disabled?` |

#### Feedback Components

| Component | Responsibility | Props |
|---|---|---|
| `ProgressBar` | Horizontal bar with percentage and optional label. Determinate only. | `value` (0-100), `label?` |
| `StatusBadge` | Inline tag for severity or status. Fixed set of variants. | `variant` ("high" / "medium" / "low" / "ok" / "error"), `label` |
| `AlertBanner` | Full-width banner for warnings, errors, and info messages. Dismissible. | `type` ("warning" / "error" / "info"), `message`, `onDismiss?` |
| `EmptyState` | Centered message when a section has no data. | `title`, `description?` |

#### Data Display Components

| Component | Responsibility | Data Source (from ScanReport) |
|---|---|---|
| `ScoreGauge` | Circular or arc gauge showing 0-100 risk score with level label. | `report.summary.risk_score`, `report.summary.risk_level` |
| `SeverityChart` | Bar or donut chart of HIGH/MEDIUM/LOW counts. | `report.breakdown` |
| `CategoryCard` | Card per category showing count, max severity, avg confidence. | `report.categories[name]` |
| `FindingsTable` | Sortable table of all findings. Columns: #, severity, category, confidence, evidence. | `report.findings` |
| `FindingRow` | Single row in FindingsTable. Expandable to show full evidence. | Single entry from `report.findings` |
| `RecommendationCard` | Card per category with severity tag and numbered action list. | Single entry from `report.recommendations` |
| `EngineInfo` | Footer section showing engine name, probes run, duration. | `report.engine` |

#### Common Components

| Component | Responsibility | Variants |
|---|---|---|
| `Button` | Standard button with consistent sizing. | `primary`, `secondary`, `danger`, `ghost` |
| `Modal` | Overlay dialog for confirmations and warnings. Traps focus. | Content via children; `onConfirm`, `onCancel` |
| `Tooltip` | Hover/focus tooltip for contextual help. | Positioning: top, bottom, left, right |

---

## 7. UX Rules

### Layout Rules

1. **Single-column content flow.** No multi-column layouts within the main content area. Sidebar is fixed; content scrolls vertically.
2. **Maximum content width.** Content area has a maximum width constraint. It does not stretch to fill ultrawide monitors.
3. **Consistent page structure.** Every page follows: `PageHeader` then content blocks then primary action at bottom.
4. **No floating action buttons.** All actions are inline with content flow.

### Interaction Rules

5. **One primary action per screen.** Each step has exactly one primary forward action (e.g., "Next", "Start Scan", "Export"). Secondary actions use ghost or secondary button variants.
6. **Destructive actions require confirmation.** Aborting a scan, clearing results, or overwriting exports trigger a Modal.
7. **No auto-advance.** The app never moves to the next step without explicit user action, except: scan completion auto-navigates to results.
8. **Disable, don't hide.** When an action is unavailable, the button is disabled with a tooltip explaining why. Buttons are never hidden.

### Information Architecture Rules

9. **Progressive disclosure.** Show summary first, details on demand. FindingsTable rows are collapsed by default; user expands for evidence.
10. **Severity is always visible.** Every finding, recommendation, and category card shows its severity level via StatusBadge. The user never has to guess severity.
11. **Numbers are precise.** Confidence shows as percentage (e.g., "92%"). Risk score shows as "32/100". Time shows as "2m 30s". No vague labels.
12. **Evidence is verbatim.** The `evidence` field from findings is shown exactly as returned by the engine. No truncation, no rephrasing.

### Anti-patterns (Explicitly Banned)

13. **No animated backgrounds, particle effects, or decorative motion.** Animations are limited to: page transitions, progress indicators, and micro-interactions (button hover, tooltip appear).
14. **No dashboards with irrelevant metrics.** Every visible number maps to a field in ScanReport. No vanity metrics.
15. **No chat-like interfaces or conversational UI.** This is a tool, not an assistant.
16. **No onboarding carousels or tutorials.** The workflow is self-explanatory. Tooltips provide inline help.
17. **No marketing copy in the UI.** No "Powered by AI", no taglines, no promotional text.

### Density Rules

18. **Tables over cards for lists > 5 items.** Findings are always in a table. Recommendations (max 4) use cards.
19. **Consistent spacing scale.** All spacing uses a fixed 4px base scale (4, 8, 12, 16, 24, 32, 48). No arbitrary values.
20. **Text hierarchy.** Maximum 3 levels of text size per page: heading, body, caption. No more.

---

## 8. Edge Case Handling

### Input Errors

| Scenario | Screen | UX Behavior |
|---|---|---|
| Empty target field | Input (2) | "Next" button disabled. Helper text: "Enter a URL or file path." |
| Invalid URL format | Input (2) | Inline error below field: "Invalid URL. Expected format: https://..." |
| Unreachable endpoint | Input (2) | After probe: AlertBanner (error): "Could not reach [target]. Check the URL and try again." |
| Invalid manifest file | Input (2) | AlertBanner (error): "Invalid manifest file. [specific validation error]." |
| Local model not running | Input (2) | After probe: AlertBanner (error): "No model detected at [target]. Ensure the server is running." |

### Scan Lifecycle Errors

| Scenario | Screen | UX Behavior |
|---|---|---|
| Heavy scan detected | Confirm (4) | AlertBanner (warning): "Heavy scan detected. [X] probes, estimated [Y] min." Extra confirmation Modal: "This scan may take a long time. Proceed anyway?" |
| Scan fails mid-execution | Scan (5) | Progress bar stops. AlertBanner (error): "[engine error message]." Button: "Retry" (returns to Confirm) or "Back to Config." |
| User aborts scan | Scan (5) | Modal: "Abort this scan? Progress will be lost." On confirm: state to `cancelled`, navigate to Input (2). |
| Scan produces zero findings | Results (6) | EmptyState on FindingsTable: "No vulnerabilities detected." ScoreGauge shows 0/100 with "LOW" label. Recommendations section: "No recommendations -- target passed all probes." |
| Scan timeout | Scan (5) | AlertBanner (error): "Scan timed out after [X] minutes." Button: "Retry with Quick depth" or "Back to Config." |

### Export Errors

| Scenario | Screen | UX Behavior |
|---|---|---|
| Invalid export path | Export (8) | Inline error: "Invalid file path." |
| Permission denied | Export (8) | AlertBanner (error): "Permission denied. Choose a different location." |
| Disk full | Export (8) | AlertBanner (error): "Not enough disk space to save the report." |
| Export succeeds | Export (8) | AlertBanner (info): "Report saved to [path] ([size] KB)." Button: "Open Folder." |

### Deployment Errors

| Scenario | Screen | UX Behavior |
|---|---|---|
| Missing credentials | Deploy Config (9) | Form field error: "AWS credentials not configured." Link to configuration docs. |
| Deployment fails | Deploy Execute (11) | AlertBanner (error): "[provider error message]." Button: "Retry" or "Back to Config." |

---

## 9. IPC Contract Reference

### Channels (Main Process <-> Renderer)

These are the exact IPC channel names used in `ipcMain.handle()` and exposed via `contextBridge`:

| Channel | Direction | Payload | Response |
|---|---|---|---|
| `scan:start` | Renderer to Main | `{ target, mode, scan_depth, categories }` | `{ ok: true, scan_id }` or `{ ok: false, error }` |
| `scan:progress` | Main to Renderer | `{ step, probe, total, elapsed_sec, message }` | (event, no response) |
| `scan:complete` | Main to Renderer | `ScanReport.to_dict()` | (event, no response) |
| `scan:error` | Main to Renderer | `{ error: string }` | (event, no response) |
| `scan:abort` | Renderer to Main | `{ scan_id }` | `{ ok: true }` |
| `report:get` | Renderer to Main | `{ scan_id }` | `ScanReport.to_dict()` or `null` |
| `report:latest` | Renderer to Main | (none) | `ScanReport.to_dict()` or `null` |
| `report:list` | Renderer to Main | (none) | `string[]` (scan IDs) |
| `report:export` | Renderer to Main | `{ scan_id, format, path }` | `ExportResult` |
| `deploy:start` | Renderer to Main | `{ provider, region, config }` | `{ ok, deploy_id }` |
| `deploy:status` | Renderer to Main | `{ deploy_id }` | `{ status, error? }` |

### Preload API Shape

```
// Exposed to renderer via contextBridge as window.api
window.api = {
  // Scan
  startScan(config)         -> Promise<{ ok, scan_id }>
  abortScan(scan_id)        -> Promise<{ ok }>
  onScanProgress(callback)  -> void     // registers listener
  onScanComplete(callback)  -> void     // registers listener
  onScanError(callback)     -> void     // registers listener

  // Reports
  getReport(scan_id)        -> Promise<ScanReport | null>
  getLatestReport()         -> Promise<ScanReport | null>
  listReports()             -> Promise<string[]>
  exportReport(scan_id, format, path) -> Promise<ExportResult>

  // Deploy
  startDeploy(config)       -> Promise<{ ok, deploy_id }>
  getDeployStatus(id)       -> Promise<{ status, error? }>

  // System
  selectDirectory()         -> Promise<string | null>  // native dialog
  getAppVersion()           -> Promise<string>
}
```

### Backend JSON Command Protocol

Commands sent to Python via stdin:

```json
{ "command": "scan", "config": { "target": "...", "mode": "api", "scan_depth": "standard", "categories": ["prompt_injection", "jailbreak"] } }
{ "command": "report:get", "scan_id": "abc-123" }
{ "command": "report:list" }
{ "command": "report:export", "scan_id": "abc-123", "format": "json", "path": "/path/to/file.json" }
```

Responses from Python via stdout (newline-delimited JSON):

```json
{ "event": "scan:progress", "step": 9, "probe": 5, "total": 9, "elapsed_sec": 4.2, "message": "Running jailbreak probes..." }
{ "event": "scan:complete", "report": { "...ScanReport.to_dict()..." } }
{ "event": "error", "message": "Connection refused" }
```

---

> [!NOTE]
> This document defines architecture only. No colors, fonts, or visual styling decisions are made here. Those will be defined in a separate Design System document (Phase 8).

> [!IMPORTANT]
> The ScanReport JSON schema (defined in Phase 6a) is the contract between backend and frontend. If the backend schema changes, this document must be updated to match. The renderer must never reshape or re-derive data that already exists in the report.
