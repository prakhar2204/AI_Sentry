/**
 * Sentryɸ -- ScanReport Type Contract
 * services/reportTypes.ts
 *
 * TypeScript mirror of backend ScanReport.to_dict() schema.
 * This file is the SINGLE SOURCE OF TRUTH for the report data shape
 * consumed by the Results Dashboard (Screen 6) and all downstream screens.
 *
 * DO NOT reshape or re-derive data that already exists in the report.
 * Rules from UI_ARCHITECTURE.md Section 9:
 *   - report.findings[]    → findings table
 *   - report.summary       → score gauge
 *   - report.breakdown     → severity chart
 *   - report.categories    → category cards
 *   - report.recommendations → action list
 *   - report.engine        → footer metadata
 *
 * Source of truth: app/backend/core/report_generator.py :: ScanReport.to_dict()
 *                  app/backend/core/engine_interface.py :: ScanFinding.to_dict()
 *                  app/backend/core/recommender.py     :: Recommendation.to_dict()
 */

// ─────────────────────────────────────────────
//  Severity system
// ─────────────────────────────────────────────

export type SeverityLevel = "high" | "medium" | "low";
export type RiskLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";

// ─────────────────────────────────────────────
//  Report sub-sections
// ─────────────────────────────────────────────

export interface ReportMeta {
  target:               string;
  mode:                 string;
  scan_depth:           string;
  categories:           string[];
  scan_id:              string;
  timestamp:            string;
  report_generated_at:  string;
  output_dir:           string;
}

export interface ReportSummary {
  /** Risk score 0-100 */
  risk_score:     number;
  /** CRITICAL / HIGH / MEDIUM / LOW / NONE */
  risk_level:     RiskLevel;
  total_findings: number;
  raw_score:      number;
}

export interface ReportBreakdown {
  high:   number;
  medium: number;
  low:    number;
}

export interface CategoryBreakdown {
  count:          number;
  max_severity:   SeverityLevel | null;
  avg_confidence: number;
  raw_score:      number;
}

/** Finding from engine_interface.py :: ScanFinding.to_dict() */
export interface ScanFinding {
  category:   string;
  severity:   SeverityLevel;
  /** Confidence 0.0 – 1.0 */
  confidence: number;
  /** Verbatim evidence text — rendered exactly as returned */
  evidence:   string;
  source:     string;
  probe_id:   string;
}

/** Recommendation from recommender.py :: Recommendation.to_dict() */
export interface Recommendation {
  category: string;
  severity: SeverityLevel;
  actions:  string[];
}

export interface ReportEngine {
  name:         string;
  total_probes: number;
  duration_sec: number;
  error:        string | null;
}

// ─────────────────────────────────────────────
//  Top-level ScanReport
// ─────────────────────────────────────────────

/**
 * The full report object received from the backend (or built by the simulator).
 * Field names are exactly as returned by ScanReport.to_dict().
 */
export interface ScanReport {
  report_version:  string;
  meta:            ReportMeta;
  summary:         ReportSummary;
  breakdown:       ReportBreakdown;
  categories:      Record<string, CategoryBreakdown>;
  findings:        ScanFinding[];
  recommendations: Recommendation[];
  engine:          ReportEngine;
}

// ─────────────────────────────────────────────
//  Sort / filter types (UI state, not from backend)
// ─────────────────────────────────────────────

export type FindingsSort = "severity" | "category" | "confidence";
export type ExportStatus = "idle" | "exporting" | "success" | "failed";

// ─────────────────────────────────────────────
//  Helper utilities
// ─────────────────────────────────────────────

/** Severity ordering (HIGH = 0, LOW = 2) */
export const SEVERITY_ORDER: Record<SeverityLevel, number> = {
  high:   0,
  medium: 1,
  low:    2,
};

/**
 * Sort a severity level label to a numeric weight for display ordering.
 * Unknown severities sort to the end.
 */
export function severityWeight(severity: string): number {
  return SEVERITY_ORDER[severity as SeverityLevel] ?? 99;
}

/** Human-readable label for a severity level */
export const SEVERITY_LABELS: Record<SeverityLevel, string> = {
  high:   "High",
  medium: "Medium",
  low:    "Low",
};

/** Human-readable label for a risk level */
export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  CRITICAL: "Critical",
  HIGH:     "High",
  MEDIUM:   "Medium",
  LOW:      "Low",
  NONE:     "None",
};

/** Category ID → display label (matches CATEGORY_LABELS in scanTypes.ts) */
export const CATEGORY_DISPLAY_LABELS: Record<string, string> = {
  prompt_injection: "Prompt Injection",
  jailbreak:        "Jailbreak Resistance",
  data_leak:        "Data Leakage",
  harmful_output:   "Harmful Output",
};

export function categoryLabel(id: string): string {
  return CATEGORY_DISPLAY_LABELS[id] ?? id;
}

/** Format confidence 0.0-1.0 → "92%" */
export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

/** Format seconds → "2m 30s" or "45s" */
export function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

/** Format ISO timestamp → readable date */
export function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-GB", {
      day:    "2-digit",
      month:  "short",
      year:   "numeric",
      hour:   "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
