/**
 * AI-SENTRY -- Scan Context
 * store/ScanContext.tsx
 *
 * Manages the scan lifecycle state: consent, configuration,
 * progress, and completion. Used by all screens in the
 * pre-scan wizard (Steps 1-5) and referenced by post-scan
 * screens for metadata.
 *
 * State shape follows UI_ARCHITECTURE.md Section 3 exactly.
 * Persistence: consent_given is stored in localStorage.
 */

import React, {
  createContext,
  useContext,
  useReducer,
  useEffect,
  type ReactNode,
  type Dispatch,
} from "react";
import { SCAN_ACTIONS } from "./actions";

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

export interface ScanProgress {
  current_probe: number;
  total_probes: number;
  elapsed_sec: number;
  current_step: string;
}

export interface ScanState {
  phase: ScanPhase;
  target: string | null;
  mode: ScanMode | null;
  scan_depth: ScanDepth;
  categories: string[];
  progress: ScanProgress | null;
  error: string | null;
  consent_given: boolean;
  manifest_file: string | null;
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
    // Corrupted localStorage or unavailable (e.g., incognito)
    return false;
  }
}

function saveConsentToStorage(value: boolean): void {
  try {
    localStorage.setItem(CONSENT_STORAGE_KEY, String(value));
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

function createInitialState(): ScanState {
  const consent = loadConsentFromStorage();
  return {
    phase: consent ? "consented" : "idle",
    target: null,
    mode: null,
    scan_depth: "standard",
    categories: [],
    progress: null,
    error: null,
    consent_given: consent,
    manifest_file: null,
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
  | { type: typeof SCAN_ACTIONS.SCAN_COMPLETE }
  | { type: typeof SCAN_ACTIONS.SCAN_FAILED; payload: string }
  | { type: typeof SCAN_ACTIONS.SCAN_CANCELLED }
  | { type: typeof SCAN_ACTIONS.RESET_SCAN }
  | { type: typeof SCAN_ACTIONS.SET_ERROR; payload: string }
  | { type: typeof SCAN_ACTIONS.CLEAR_ERROR }
  | { type: typeof SCAN_ACTIONS.SET_MANIFEST_FILE; payload: string | null };

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
      };

    case SCAN_ACTIONS.UPDATE_PROGRESS:
      return { ...state, progress: action.payload };

    case SCAN_ACTIONS.SCAN_COMPLETE:
      return { ...state, phase: "complete", progress: null };

    case SCAN_ACTIONS.SCAN_FAILED:
      return {
        ...state,
        phase: "failed",
        error: action.payload,
        progress: null,
      };

    case SCAN_ACTIONS.SCAN_CANCELLED:
      return {
        ...state,
        phase: "cancelled",
        progress: null,
      };

    case SCAN_ACTIONS.RESET_SCAN:
      return {
        ...state,
        phase: state.consent_given ? "consented" : "idle",
        target: null,
        mode: null,
        scan_depth: "standard",
        categories: [],
        progress: null,
        error: null,
        manifest_file: null,
      };

    case SCAN_ACTIONS.SET_ERROR:
      return { ...state, error: action.payload };

    case SCAN_ACTIONS.CLEAR_ERROR:
      return { ...state, error: null };

    case SCAN_ACTIONS.SET_MANIFEST_FILE:
      return { ...state, manifest_file: action.payload };

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
