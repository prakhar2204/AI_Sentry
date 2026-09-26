/**
 * AI-SENTRY -- Action Type Constants
 * store/actions.ts
 *
 * Single source of truth for all reducer action types.
 * Grouped by domain context.
 */

// ─────────────────────────────────────────────
//  ScanContext actions
// ─────────────────────────────────────────────

export const SCAN_ACTIONS = {
  /** User accepted consent terms. Sets consent_given = true, phase = "consented" */
  ACCEPT_CONSENT: "ACCEPT_CONSENT",

  /** Set scan target URL or file path */
  SET_TARGET: "SET_TARGET",

  /** Set scan mode (api | local) */
  SET_MODE: "SET_MODE",

  /** Set scan depth (quick | standard | deep) */
  SET_SCAN_DEPTH: "SET_SCAN_DEPTH",

  /** Set selected probe categories */
  SET_CATEGORIES: "SET_CATEGORIES",

  /** Transition phase to "configuring" */
  START_CONFIGURING: "START_CONFIGURING",

  /** Transition phase to "confirming" */
  START_CONFIRMING: "START_CONFIRMING",

  /** Transition phase to "scanning" */
  START_SCAN: "START_SCAN",

  /** Update progress during scan */
  UPDATE_PROGRESS: "UPDATE_PROGRESS",

  /** Scan completed successfully */
  SCAN_COMPLETE: "SCAN_COMPLETE",

  /** Scan failed with error */
  SCAN_FAILED: "SCAN_FAILED",

  /** User aborted scan */
  SCAN_CANCELLED: "SCAN_CANCELLED",

  /** Reset to start a new scan (preserves consent) */
  RESET_SCAN: "RESET_SCAN",

  /** Set error message */
  SET_ERROR: "SET_ERROR",

  /** Clear error */
  CLEAR_ERROR: "CLEAR_ERROR",

  /** Set optional manifest file path */
  SET_MANIFEST_FILE: "SET_MANIFEST_FILE",

  /** Set scan strategy (manifest | manual | full) */
  SET_SCAN_STRATEGY: "SET_SCAN_STRATEGY",
} as const;

// ─────────────────────────────────────────────
//  ReportContext actions
// ─────────────────────────────────────────────

export const REPORT_ACTIONS = {
  /** Store the ScanReport from backend */
  SET_REPORT: "SET_REPORT",

  /** Clear current report */
  CLEAR_REPORT: "CLEAR_REPORT",

  /** Set category filter for findings view */
  SET_CATEGORY_FILTER: "SET_CATEGORY_FILTER",

  /** Set severity filter for findings view */
  SET_SEVERITY_FILTER: "SET_SEVERITY_FILTER",

  /** Set findings sort order */
  SET_FINDINGS_SORT: "SET_FINDINGS_SORT",

  /** Set findings pagination page */
  SET_FINDINGS_PAGE: "SET_FINDINGS_PAGE",

  /** Start export operation */
  EXPORT_START: "EXPORT_START",

  /** Export succeeded */
  EXPORT_SUCCESS: "EXPORT_SUCCESS",

  /** Export failed */
  EXPORT_FAILED: "EXPORT_FAILED",

  /** Reset export status */
  EXPORT_RESET: "EXPORT_RESET",
} as const;

// ─────────────────────────────────────────────
//  DeployContext actions
// ─────────────────────────────────────────────

export const DEPLOY_ACTIONS = {
  /** Set deployment provider */
  SET_PROVIDER: "SET_PROVIDER",

  /** Set deployment region */
  SET_REGION: "SET_REGION",

  /** Set provider-specific config */
  SET_CONFIG: "SET_CONFIG",

  /** Start deployment execution */
  START_DEPLOY: "START_DEPLOY",

  /** Deployment completed */
  DEPLOY_COMPLETE: "DEPLOY_COMPLETE",

  /** Deployment failed */
  DEPLOY_FAILED: "DEPLOY_FAILED",

  /** Reset deployment state */
  RESET_DEPLOY: "RESET_DEPLOY",
} as const;
