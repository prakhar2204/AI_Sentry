/**
 * Sentryɸ — IPC Scan Service
 * services/ipcScanService.ts
 *
 * Bridges the React scan pipeline to the Python backend via Electron IPC.
 * Provides the SAME public API as scanService.ts:
 *   startScan(config, handlers) → ScanController
 *   buildScanConfig(...)        → ScanExecutionConfig
 *
 * When called inside Electron: spawns Python ipc_server.py and streams
 * real scan events to the UI via window.electronAPI.
 *
 * When called in browser mode (window.electronAPI unavailable): throws
 * an error — callers should fall back to scanService.ts instead.
 *
 * Event mapping (Python IPC → ScanProgressEvent):
 *   Python "progress" → onProgress (maps percent/stage/message)
 *   Python "finding"  → onProgress (increments preliminary_findings)
 *   Python "activity" → onActivity (maps severity/message/timestamp)
 *   Python "stage"    → onProgress (updates lifecycle_stage)
 *   Python "complete" → onComplete (passes report to ReportContext)
 *   Python "error"    → onError
 */

import {
  type ScanExecutionConfig,
  type ScanEventHandlers,
  type ScanController,
  type ScanProgressEvent,
  type ScanActivityEntry,
  type CategoryState,
  type ScanLifecycleStage,
  CATEGORY_LABELS,
} from "./scanTypes";
import type { ScanReport } from "./reportTypes";

// ─────────────────────────────────────────────
//  Stage mapping: Python stage strings → ScanLifecycleStage
// ─────────────────────────────────────────────

const PYTHON_STAGE_MAP: Record<string, ScanLifecycleStage> = {
  init:             "preparing",
  manifest:         "initializing_scan",
  scanning:         "scanning",
  analyzing:        "analyzing",
  scoring:          "scoring",
  recommendations:  "generating_recommendations",
  complete:         "generating_report",
};

function mapPythonStage(stage: string): ScanLifecycleStage {
  return PYTHON_STAGE_MAP[stage] ?? "scanning";
}

// ─────────────────────────────────────────────
//  Severity mapping: Python severity → LogSeverity
// ─────────────────────────────────────────────

function mapSeverity(sev: string): ScanActivityEntry["severity"] {
  if (sev === "warning" || sev === "warn") return "warn";
  if (sev === "error") return "error";
  if (sev === "debug") return "debug";
  return "info";
}

// ─────────────────────────────────────────────
//  Build initial category state
// ─────────────────────────────────────────────

function buildCategoryStates(categories: string[]): CategoryState[] {
  return categories.map((id) => ({
    id,
    label: CATEGORY_LABELS[id] ?? id,
    status: "queued" as const,
    probes_total: 0,
    probes_completed: 0,
  }));
}

// ─────────────────────────────────────────────
//  Main IPC scan runner
// ─────────────────────────────────────────────

/**
 * Start a scan via the Electron IPC → Python bridge.
 *
 * @param config  - The scan execution config (from buildScanConfig)
 * @param handlers - Progress/activity/complete/error callbacks
 * @param onReport - Called with the full ScanReport when scan completes
 * @returns ScanController with cancel() method
 */
export function startIpcScan(
  config: ScanExecutionConfig,
  handlers: ScanEventHandlers,
  onReport?: (report: ScanReport) => void
): ScanController {
  const api = window.electronAPI;
  if (!api) {
    handlers.onError("Electron API unavailable — cannot start IPC scan", "Not running in Electron");
    return { cancelled: false, cancel: () => {} };
  }

  let isCancelled = false;
  let preliminaryFindings = 0;
  let lifecycleStage: ScanLifecycleStage = "preparing";
  let probesDone = 0;
  let probesTotal = config.total_probes || 1;
  let elapsedSec = 0;
  let activeCategory: string | null = null;
  const categoryStates = buildCategoryStates(config.categories);

  // ── Cleanup functions to unsubscribe IPC listeners ──
  let unsubProgress: (() => void) | null = null;
  let unsubComplete: (() => void) | null = null;
  let unsubError: (() => void) | null = null;

  function cleanup() {
    unsubProgress?.();
    unsubComplete?.();
    unsubError?.();
  }

  function emitProgress(overrides: Partial<ScanProgressEvent> = {}) {
    const event: ScanProgressEvent = {
      stage: lifecycleStage,
      timestamp: new Date().toISOString(),
      probes_completed: probesDone,
      probes_total: probesTotal,
      active_category: activeCategory,
      activity_label: overrides.activity_label ?? "Running...",
      categories: categoryStates,
      preliminary_findings: preliminaryFindings,
      elapsed_sec: elapsedSec,
      ...overrides,
    };
    handlers.onProgress(event);
  }

  // ── Subscribe to scan:progress (covers progress/finding/activity/stage) ──
  unsubProgress = api.onScanProgress((rawData) => {
    if (isCancelled) return;
    const data = rawData as Record<string, unknown>;

    switch (data.type) {
      case "progress": {
        const pct = (data.percent as number) ?? 0;
        probesDone = (data.probes_done as number) ?? probesDone;
        probesTotal = (data.probes_total as number) || probesTotal;
        elapsedSec = Math.round(((data.elapsed_ms as number) ?? 0) / 1000);
        const stage = mapPythonStage((data.stage as string) ?? "scanning");
        lifecycleStage = stage;

        // Update category state: mark active category
        const catName = activeCategory;
        if (catName) {
          const catIdx = categoryStates.findIndex((c) => c.id === catName);
          if (catIdx >= 0) {
            categoryStates[catIdx] = {
              ...categoryStates[catIdx],
              status: "active",
              probes_completed: probesDone,
            };
          }
        }

        emitProgress({
          activity_label: (data.message as string) ?? PYTHON_STAGE_MAP[data.stage as string] ?? "Running...",
        });
        break;
      }

      case "finding": {
        preliminaryFindings += 1;
        const catId = (data.category as string) ?? "";
        activeCategory = catId;

        // Update category state
        const catIdx = categoryStates.findIndex((c) => c.id === catId);
        if (catIdx >= 0) {
          categoryStates[catIdx] = {
            ...categoryStates[catIdx],
            status: "active",
            probes_completed: (categoryStates[catIdx].probes_completed ?? 0) + 1,
          };
        }

        emitProgress({
          activity_label: `Finding: ${(data.title as string) ?? catId} (${(data.severity as string)?.toUpperCase()})`,
        });
        break;
      }

      case "activity": {
        const entry: ScanActivityEntry = {
          timestamp: (data.timestamp as string) ?? new Date().toLocaleTimeString(),
          severity: mapSeverity(data.severity as string),
          message: (data.message as string) ?? "",
        };
        handlers.onActivity(entry);
        break;
      }

      case "stage": {
        const stage = mapPythonStage((data.stage as string) ?? "scanning");
        lifecycleStage = stage;

        // When we enter a new scanning stage, detect which category is active
        const msg = (data.message as string) ?? "";
        const matchedCat = config.categories.find((c) =>
          msg.toLowerCase().includes(c.replace("_", " "))
        );
        if (matchedCat) {
          activeCategory = matchedCat;
          // Mark previous categories complete
          const catIdx = categoryStates.findIndex((c) => c.id === matchedCat);
          if (catIdx >= 0) {
            // Mark all previous as complete
            for (let i = 0; i < catIdx; i++) {
              if (categoryStates[i].status === "active") {
                categoryStates[i] = { ...categoryStates[i], status: "complete" };
              }
            }
            categoryStates[catIdx] = { ...categoryStates[catIdx], status: "active" };
          }
        }

        emitProgress({ activity_label: msg || stage });
        break;
      }
    }
  });

  // ── Subscribe to scan:complete ──
  unsubComplete = api.onScanComplete((rawData) => {
    if (isCancelled) return;
    cleanup();

    const data = rawData as Record<string, unknown>;
    const report = data.report as ScanReport | undefined;

    // Mark all categories complete
    for (const cat of categoryStates) {
      cat.status = "complete";
    }
    lifecycleStage = "completed";
    emitProgress({ activity_label: "Scan complete" });

    // Deliver the real Python report
    if (report && onReport) {
      onReport(report);
    }

    handlers.onComplete();
  });

  // ── Subscribe to scan:error ──
  unsubError = api.onScanError((rawData) => {
    if (isCancelled) return;
    cleanup();

    const data = rawData as Record<string, unknown>;
    const msg = (data.message as string) ?? "Unknown scan error";
    const code = (data.code as string) ?? "SCAN_ERROR";

    lifecycleStage = "failed";
    handlers.onError(msg, code);
  });

  // ── Start the scan via IPC ──
  const ipcConfig = {
    target:     config.target,
    mode:       config.mode,
    scan_depth: config.scan_depth,
    categories: config.categories,
  };

  api.startScan(ipcConfig).then((result) => {
    if (!result.started) {
      cleanup();
      handlers.onError(result.error ?? "Failed to start Python scan", "START_FAILED");
    }
  }).catch((err: Error) => {
    cleanup();
    handlers.onError(err.message ?? "IPC start error", "IPC_ERROR");
  });

  // ── Initial progress event ──
  emitProgress({ activity_label: "Connecting to Python backend..." });

  return {
    get cancelled() { return isCancelled; },
    cancel() {
      if (!isCancelled) {
        isCancelled = true;
        cleanup();
        api.cancelScan().catch(() => {});
      }
    },
  };
}

// ─────────────────────────────────────────────
//  Re-export buildScanConfig (same as scanService)
// ─────────────────────────────────────────────

export { buildScanConfig } from "./scanService";
