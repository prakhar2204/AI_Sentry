/**
 * AI-SENTRY -- Scan Context
 * store/ScanContext.tsx
 *
 * Manages the scan lifecycle state: consent, configuration,
 * progress, and completion. Used by all screens in the
 * pre-scan wizard (Steps 1-5) and referenced by post-scan
 * screens for metadata.
 *
 * Extended in Phase 6d to support:
 *   - Full scan lifecycle stages (scanTypes.ts)
 *   - Per-category execution state
 *   - Preliminary findings count
 *   - Activity log (capped for performance)
 *   - Scan-active flag for navigation protection
 *
 * State shape follows UI_ARCHITECTURE.md Section 3.
 * Persistence: consent_given is stored in localStorage.
 */

import React, {
  createContext,
  useContext,
  useReducer,
  type ReactNode,
  type Dispatch,
} from "react";
import { SCAN_ACTIONS } from "./actions";
import type {
  ScanLifecycleStage,
  ScanProgressEvent,
  ScanActivityEntry,
  CategoryState,
} from "../services/scanTypes";
import { ACTIVE_STAGES } from "../services/scanTypes";

// ─────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────

export type ScanPhase =
  | "idle"
  | "consented"
  | "configuring"
  | "confirming"
  | "scanning"
  | "complete"
  | "failed"
  | "cancelled";

export type ScanMode = "api" | "local";
export type ScanDepth = "quick" | "standard" | "deep";
export type ScanStrategy = "manifest" | "manual" | "full";

export interface ScanProgress {
  current_probe: number;
  total_probes: number;
  elapsed_sec: number;
  current_step: string;
}

/** Extended scan execution state (Phase 6d) */
export interface ScanExecutionState {
  /** Current lifecycle stage from scanTypes.ts */
  lifecycle_stage: ScanLifecycleStage;
  /** Probes completed so far */
  probes_completed: number;
  /** Total probes */
  probes_total: number;
  /** Elapsed seconds */
  elapsed_sec: number;
  /** User-facing activity description */
  activity_label: string;
  /** Currently active category id */
  active_category: string | null;
  /** Per-category execution state */
  categories: CategoryState[];
  /** Preliminary findings count */
  preliminary_findings: number;
  /** Activity log (capped at MAX_LOG_ENTRIES) */
  activity_log: ScanActivityEntry[];
}

/** Maximum activity log entries retained in state */
const MAX_LOG_ENTRIES = 200;

export interface ScanState {
  phase: ScanPhase;
  target: string | null;
  mode: ScanMode | null;
  scan_depth: ScanDepth;
  scan_strategy: ScanStrategy;
  categories: string[];
  progress: ScanProgress | null;
  error: string | null;
  error_details: string | null;
  consent_given: boolean;
  manifest_file: string | null;
  /** Extended scan execution state (null when not scanning) */
  scan_execution: ScanExecutionState | null;
  /** True when scan is actively running — used for navigation protection */
  scan_active: boolean;
}

// ─────────────────────────────────────────────
//  Initial state
// ─────────────────────────────────────────────

const CONSENT_STORAGE_KEY = "aisentry_consent_given";

function loadConsentFromStorage(): boolean {
  try {
    const stored = localStorage.getItem(CONSENT_STORAGE_KEY);
    return stored === "true";
  } catch {
    return false;
  }
}

function saveConsentToStorage(value: boolean): void {
  try {
    localStorage.setItem(CONSENT_STORAGE_KEY, String(value));
  } catch {
    // Silently fail
  }
}

function createInitialState(): ScanState {
  const consent = loadConsentFromStorage();
  return {
    phase: consent ? "consented" : "idle",
    target: null,
    mode: null,
    scan_depth: "standard",
    scan_strategy: "manual",
    categories: [],
    progress: null,
    error: null,
    error_details: null,
    consent_given: consent,
    manifest_file: null,
    scan_execution: null,
    scan_active: false,
  };
}

// ─────────────────────────────────────────────
//  Action types
// ─────────────────────────────────────────────

type ScanAction =
  | { type: typeof SCAN_ACTIONS.ACCEPT_CONSENT }
  | { type: typeof SCAN_ACTIONS.SET_TARGET; payload: string }
  | { type: typeof SCAN_ACTIONS.SET_MODE; payload: ScanMode }
  | { type: typeof SCAN_ACTIONS.SET_SCAN_DEPTH; payload: ScanDepth }
  | { type: typeof SCAN_ACTIONS.SET_CATEGORIES; payload: string[] }
  | { type: typeof SCAN_ACTIONS.START_CONFIGURING }
  | { type: typeof SCAN_ACTIONS.START_CONFIRMING }
  | { type: typeof SCAN_ACTIONS.START_SCAN }
  | { type: typeof SCAN_ACTIONS.UPDATE_PROGRESS; payload: ScanProgress }
  | { type: typeof SCAN_ACTIONS.SCAN_PROGRESS_EVENT; payload: ScanProgressEvent }
  | { type: typeof SCAN_ACTIONS.SCAN_ACTIVITY_EVENT; payload: ScanActivityEntry }
  | { type: typeof SCAN_ACTIONS.SCAN_COMPLETE }
  | { type: typeof SCAN_ACTIONS.SCAN_FAILED; payload: string; details?: string }
  | { type: typeof SCAN_ACTIONS.SCAN_CANCELLED }
  | { type: typeof SCAN_ACTIONS.RESET_SCAN }
  | { type: typeof SCAN_ACTIONS.SET_ERROR; payload: string }
  | { type: typeof SCAN_ACTIONS.CLEAR_ERROR }
  | { type: typeof SCAN_ACTIONS.SET_MANIFEST_FILE; payload: string | null }
  | { type: typeof SCAN_ACTIONS.SET_SCAN_STRATEGY; payload: ScanStrategy };

// ─────────────────────────────────────────────
//  Reducer
// ─────────────────────────────────────────────

function scanReducer(state: ScanState, action: ScanAction): ScanState {
  switch (action.type) {
    case SCAN_ACTIONS.ACCEPT_CONSENT: {
      saveConsentToStorage(true);
      return {
        ...state,
        consent_given: true,
        phase: "consented",
      };
    }

    case SCAN_ACTIONS.SET_TARGET:
      return { ...state, target: action.payload };

    case SCAN_ACTIONS.SET_MODE:
      return { ...state, mode: action.payload };

    case SCAN_ACTIONS.SET_SCAN_DEPTH:
      return { ...state, scan_depth: action.payload };

    case SCAN_ACTIONS.SET_CATEGORIES:
      return { ...state, categories: action.payload };

    case SCAN_ACTIONS.START_CONFIGURING:
      return { ...state, phase: "configuring" };

    case SCAN_ACTIONS.START_CONFIRMING:
      return { ...state, phase: "confirming" };

    case SCAN_ACTIONS.START_SCAN:
      return {
        ...state,
        phase: "scanning",
        progress: null,
        error: null,
        error_details: null,
        scan_active: true,
        scan_execution: {
          lifecycle_stage: "idle",
          probes_completed: 0,
          probes_total: 0,
          elapsed_sec: 0,
          activity_label: "Preparing...",
          active_category: null,
          categories: [],
          preliminary_findings: 0,
          activity_log: [],
        },
      };

    case SCAN_ACTIONS.UPDATE_PROGRESS:
      return { ...state, progress: action.payload };

    case SCAN_ACTIONS.SCAN_PROGRESS_EVENT: {
      const evt = action.payload;
      const prevExec = state.scan_execution;
      if (!prevExec) return state;

      return {
        ...state,
        scan_execution: {
          ...prevExec,
          lifecycle_stage: evt.stage,
          probes_completed: evt.probes_completed,
          probes_total: evt.probes_total,
          elapsed_sec: evt.elapsed_sec,
          activity_label: evt.activity_label,
          active_category: evt.active_category,
          categories: evt.categories,
          preliminary_findings: evt.preliminary_findings,
        },
        // Also update legacy progress for compatibility
        progress: {
          current_probe: evt.probes_completed,
          total_probes: evt.probes_total,
          elapsed_sec: evt.elapsed_sec,
          current_step: evt.activity_label,
        },
      };
    }

    case SCAN_ACTIONS.SCAN_ACTIVITY_EVENT: {
      const prevExec = state.scan_execution;
      if (!prevExec) return state;

      // Cap log entries for performance
      const newLog = prevExec.activity_log.length >= MAX_LOG_ENTRIES
        ? [...prevExec.activity_log.slice(-MAX_LOG_ENTRIES + 1), action.payload]
        : [...prevExec.activity_log, action.payload];

      return {
        ...state,
        scan_execution: {
          ...prevExec,
          activity_log: newLog,
        },
      };
    }

    case SCAN_ACTIONS.SCAN_COMPLETE:
      return {
        ...state,
        phase: "complete",
        progress: null,
        scan_active: false,
        scan_execution: state.scan_execution
          ? {
              ...state.scan_execution,
              lifecycle_stage: "completed",
              activity_label: "Scan complete",
            }
          : null,
      };

    case SCAN_ACTIONS.SCAN_FAILED:
      return {
        ...state,
        phase: "failed",
        error: action.payload,
        error_details: (action as any).details ?? null,
        progress: null,
        scan_active: false,
        scan_execution: state.scan_execution
          ? {
              ...state.scan_execution,
              lifecycle_stage: "failed",
              activity_label: "Scan failed",
            }
          : null,
      };

    case SCAN_ACTIONS.SCAN_CANCELLED:
      return {
        ...state,
        phase: "cancelled",
        progress: null,
        scan_active: false,
        scan_execution: state.scan_execution
          ? {
              ...state.scan_execution,
              lifecycle_stage: "cancelled",
              activity_label: "Scan cancelled",
            }
          : null,
      };

    case SCAN_ACTIONS.RESET_SCAN:
      return {
        ...state,
        phase: state.consent_given ? "consented" : "idle",
        target: null,
        mode: null,
        scan_depth: "standard",
        scan_strategy: "manual",
        categories: [],
        progress: null,
        error: null,
        error_details: null,
        manifest_file: null,
        scan_execution: null,
        scan_active: false,
      };

    case SCAN_ACTIONS.SET_ERROR:
      return { ...state, error: action.payload };

    case SCAN_ACTIONS.CLEAR_ERROR:
      return { ...state, error: null, error_details: null };

    case SCAN_ACTIONS.SET_MANIFEST_FILE:
      return { ...state, manifest_file: action.payload };

    case SCAN_ACTIONS.SET_SCAN_STRATEGY:
      return { ...state, scan_strategy: action.payload };

    default:
      return state;
  }
}

// ─────────────────────────────────────────────
//  Context
// ─────────────────────────────────────────────

interface ScanContextValue {
  state: ScanState;
  dispatch: Dispatch<ScanAction>;
}

const ScanContext = createContext<ScanContextValue | null>(null);

// ─────────────────────────────────────────────
//  Provider
// ─────────────────────────────────────────────

interface ScanProviderProps {
  children: ReactNode;
}

export function ScanProvider({ children }: ScanProviderProps) {
  const [state, dispatch] = useReducer(scanReducer, undefined, createInitialState);

  return (
    <ScanContext.Provider value={{ state, dispatch }}>
      {children}
    </ScanContext.Provider>
  );
}

// ─────────────────────────────────────────────
//  Hook
// ─────────────────────────────────────────────

export function useScanContext(): ScanContextValue {
  const context = useContext(ScanContext);
  if (context === null) {
    throw new Error("useScanContext must be used within a ScanProvider");
  }
  return context;
}
