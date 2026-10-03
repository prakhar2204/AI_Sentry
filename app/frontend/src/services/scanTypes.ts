/**
 * AI-SENTRY -- Scan Event Contract
 * services/scanTypes.ts
 *
 * Typed event/lifecycle definitions for the scan pipeline.
 * This file is the SINGLE SOURCE OF TRUTH for:
 *   - Scan lifecycle stages
 *   - Valid transitions between stages
 *   - Scan progress event shape
 *   - Category execution state
 *
 * The same types are used by:
 *   1. The current frontend simulator (scanService.ts)
 *   2. The future Python backend over Electron IPC
 *   3. ScanContext state management
 *
 * External scanning engines (Garak, PyRIT, etc.) are abstracted
 * behind generic product terminology in user-facing labels.
 */

// ─────────────────────────────────────────────
//  Scan Lifecycle Stages
// ─────────────────────────────────────────────

/**
 * Exhaustive list of scan lifecycle stages.
 * Order defines the expected forward-progression.
 *
 * Transition table:
 *   idle → preparing → validating_target → initializing_scan
 *   → scanning → analyzing → scoring → generating_recommendations
 *   → generating_report → completed
 *
 *   (any active stage) → failed
 *   (any cancellable stage) → cancelling → cancelled
 *
 * "Cancellable" stages: preparing through generating_report.
 * "Active" stages: preparing through generating_report.
 */
export type ScanLifecycleStage =
  | "idle"
  | "preparing"
  | "validating_target"
  | "initializing_scan"
  | "scanning"
  | "analyzing"
  | "scoring"
  | "generating_recommendations"
  | "generating_report"
  | "completed"
  | "cancelling"
  | "cancelled"
  | "failed";

/** Stages where the scan is actively doing work */
export const ACTIVE_STAGES: ReadonlySet<ScanLifecycleStage> = new Set([
  "preparing",
  "validating_target",
  "initializing_scan",
  "scanning",
  "analyzing",
  "scoring",
  "generating_recommendations",
  "generating_report",
]);

/** Stages where cancellation is allowed */
export const CANCELLABLE_STAGES: ReadonlySet<ScanLifecycleStage> = new Set([
  "preparing",
  "validating_target",
  "initializing_scan",
  "scanning",
  "analyzing",
  "scoring",
  "generating_recommendations",
  "generating_report",
]);

/** Terminal stages — no further transitions */
export const TERMINAL_STAGES: ReadonlySet<ScanLifecycleStage> = new Set([
  "completed",
  "cancelled",
  "failed",
]);

/**
 * Valid transitions.
 * Key = current stage, Value = set of stages reachable from it.
 */
export const VALID_TRANSITIONS: Record<ScanLifecycleStage, ReadonlySet<ScanLifecycleStage>> = {
  idle:                       new Set(["preparing"]),
  preparing:                  new Set(["validating_target", "cancelling", "failed"]),
  validating_target:          new Set(["initializing_scan", "cancelling", "failed"]),
  initializing_scan:          new Set(["scanning", "cancelling", "failed"]),
  scanning:                   new Set(["analyzing", "cancelling", "failed"]),
  analyzing:                  new Set(["scoring", "cancelling", "failed"]),
  scoring:                    new Set(["generating_recommendations", "cancelling", "failed"]),
  generating_recommendations: new Set(["generating_report", "cancelling", "failed"]),
  generating_report:          new Set(["completed", "cancelling", "failed"]),
  completed:                  new Set([]),
  cancelling:                 new Set(["cancelled", "failed"]),
  cancelled:                  new Set([]),
  failed:                     new Set([]),
};

/** Validate a stage transition. Returns true if valid. */
export function isValidTransition(
  from: ScanLifecycleStage,
  to: ScanLifecycleStage
): boolean {
  return VALID_TRANSITIONS[from]?.has(to) ?? false;
}

// ─────────────────────────────────────────────
//  Category Execution State
// ─────────────────────────────────────────────

export type CategoryStatus = "queued" | "active" | "complete" | "failed" | "skipped";

export interface CategoryState {
  id: string;
  label: string;
  status: CategoryStatus;
  probes_total: number;
  probes_completed: number;
}

// ─────────────────────────────────────────────
//  Scan Progress Event
// ─────────────────────────────────────────────

/**
 * ScanProgressEvent — the data shape emitted by scanService / IPC.
 *
 * This is the bridge contract. The same shape works for:
 *   - Frontend simulator (deterministic)
 *   - Future Python bridge (real scan)
 *   - Electron IPC transport
 */
export interface ScanProgressEvent {
  /** Lifecycle stage the scan is currently in */
  stage: ScanLifecycleStage;

  /** ISO timestamp when this event was generated */
  timestamp: string;

  /** Number of probes completed so far */
  probes_completed: number;

  /** Total number of probes in this scan */
  probes_total: number;

  /** Currently active category id, or null if between categories */
  active_category: string | null;

  /** Current activity label — safe for user display */
  activity_label: string;

  /** Per-category execution state */
  categories: CategoryState[];

  /** Count of preliminary findings identified so far */
  preliminary_findings: number;

  /** Elapsed time in seconds */
  elapsed_sec: number;
}

// ─────────────────────────────────────────────
//  Scan Activity Log Entry
// ─────────────────────────────────────────────

export type LogSeverity = "info" | "warn" | "error" | "debug";

export interface ScanActivityEntry {
  /** ISO time string (HH:MM:SS) */
  timestamp: string;
  /** Severity level */
  severity: LogSeverity;
  /** Human-readable message (user-safe) */
  message: string;
}

// ─────────────────────────────────────────────
//  Scan Service Contract
// ─────────────────────────────────────────────

/**
 * Configuration passed to the scan service.
 * Matches what EstimatePage collects.
 */
export interface ScanExecutionConfig {
  target: string;
  mode: "api" | "local";
  scan_depth: "quick" | "standard" | "deep";
  categories: string[];
  total_probes: number;
  per_category_probes: Record<string, number>;
}

/**
 * Callbacks the scan service uses to communicate with the UI.
 * The React page registers these; the service calls them.
 *
 * The same contract applies whether the service is a simulator
 * or the real Electron IPC bridge.
 */
export interface ScanEventHandlers {
  onProgress: (event: ScanProgressEvent) => void;
  onActivity: (entry: ScanActivityEntry) => void;
  onComplete: () => void;
  onError: (error: string, details?: string) => void;
}

/**
 * Control handle returned by startScan().
 * Allows cancellation from the UI.
 */
export interface ScanController {
  /** Whether cancellation has been requested */
  readonly cancelled: boolean;
  /** Request cancellation. Safe to call multiple times. */
  cancel: () => void;
}

// ─────────────────────────────────────────────
//  Category Display Labels
//  (User-facing names for internal category IDs)
// ─────────────────────────────────────────────

export const CATEGORY_LABELS: Record<string, string> = {
  prompt_injection: "Prompt Injection",
  jailbreak: "Jailbreak Resistance",
  data_leak: "Data Leakage Detection",
  harmful_output: "Harmful Output Analysis",
};

/** Stage display labels — user-safe descriptions */
export const STAGE_LABELS: Record<ScanLifecycleStage, string> = {
  idle: "Ready",
  preparing: "Preparing scan configuration",
  validating_target: "Validating target endpoint",
  initializing_scan: "Initializing analysis modules",
  scanning: "Executing security probes",
  analyzing: "Analyzing scan results",
  scoring: "Computing risk scores",
  generating_recommendations: "Generating recommendations",
  generating_report: "Compiling security report",
  completed: "Scan complete",
  cancelling: "Cancelling scan",
  cancelled: "Scan cancelled",
  failed: "Scan failed",
};
