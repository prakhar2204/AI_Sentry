/**
 * Sentryɸ -- Export Report (Screen 8)
 * pages/ExportPage.tsx
 *
 * A report preview and export workspace built from the existing ScanReport
 * in ReportContext. Offers three download formats:
 *
 *   1. JSON  — canonical structured output (report.to_dict() equivalent)
 *   2. TXT   — human-readable plain text (mirrors format_txt_report() from backend)
 *   3. HTML  — standalone readable document, safely escaped
 *
 * Export mechanism: browser Blob + <a download> — no IPC or native dialog.
 * No backend IPC bridge exists at this stage (see report_service.py note).
 * No PDF — not implemented safely, not offered.
 *
 * Security rules enforced:
 *   - All untrusted content (evidence, actions, target) is escaped via escapeHtml()
 *   - No dangerouslySetInnerHTML used anywhere
 *   - No report data transmitted to external services
 *   - Export state is shared with ReportContext (no duplication)
 *
 * Known limitations:
 *   - No native save dialog (browser-only stage)
 *   - No PDF (not safely implementable without a dependency)
 *   - TXT format mirrors backend output but is generated in the frontend
 *     (backend format_txt_report() is not invoked — no IPC bridge)
 *
 * Navigation:
 *   - Hub branch (like "actions"): returns to "results" or "actions"
 *   - Both onBack props are optional; at minimum "Back to Results" must work
 *
 * UI_ARCHITECTURE.md refs:
 *   Section 2 (export is hub branch, returns to results/actions)
 *   Section 3 (ReportContext, export_status)
 *   Section 9 (report schema fields)
 */

import React, { useState, useCallback } from "react";
import { useReportContext } from "../store/ReportContext";
import { REPORT_ACTIONS } from "../store/actions";
import { PageHeader } from "../components/layout/PageHeader";
import { AlertBanner } from "../components/feedback/AlertBanner";
import { isElectron } from "../utils/platform";
import type { ScanReport } from "../services/reportTypes";
import {
  categoryLabel,
  formatTimestamp,
  formatDuration,
  SEVERITY_LABELS,
  RISK_LEVEL_LABELS,
} from "../services/reportTypes";

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface ExportPageProps {
  onBackToResults:    () => void;
  onBackToActions?:   () => void;
  /** Part A fix: navigate to Screen 9 — Deploy Configuration */
  onProceedToDeploy:  () => void;
}

// ─────────────────────────────────────────────
//  Export format definitions
// ─────────────────────────────────────────────

type ExportFormat = "json" | "txt" | "html" | "pdf";

interface FormatDef {
  id:        ExportFormat;
  label:     string;
  ext:       string;
  mime:      string;
  purpose:   string;
  electronOnly?: boolean;  // true = requires Electron/Python
}

const FORMATS: FormatDef[] = [
  {
    id:      "json",
    label:   "JSON",
    ext:     "json",
    mime:    "application/json",
    purpose: "Structured machine-readable output. Preserves the complete report schema.",
  },
  {
    id:      "txt",
    label:   "Plain Text",
    ext:     "txt",
    mime:    "text/plain",
    purpose: "Human-readable report with all sections. Suitable for sharing as plain text.",
  },
  {
    id:      "html",
    label:   "HTML",
    ext:     "html",
    mime:    "text/html",
    purpose: "Standalone readable document. Viewable offline in any browser, no external assets.",
  },
  {
    id:      "pdf",
    label:   "PDF",
    ext:     "pdf",
    mime:    "application/pdf",
    purpose: "Professional PDF document. Requires Desktop Mode and WeasyPrint (falls back to HTML if unavailable).",
    electronOnly: true,
  },
];

// ─────────────────────────────────────────────
//  HTML escape — all untrusted content must pass through this
// ─────────────────────────────────────────────

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ─────────────────────────────────────────────
//  JSON serializer — matches backend ScanReport.to_dict()
// ─────────────────────────────────────────────

function serializeToJson(report: ScanReport): string {
  return JSON.stringify(report, null, 2);
}

// ─────────────────────────────────────────────
//  TXT formatter — mirrors backend format_txt_report()
// ─────────────────────────────────────────────

const DIVIDER     = "=".repeat(60);
const THIN_DIVIDER = "-".repeat(60);

const SEV_TAGS: Record<string, string> = {
  high:   "HIGH  ",
  medium: "MEDIUM",
  low:    "LOW   ",
};

function serializeToTxt(report: ScanReport): string {
  const lines: string[] = [];
  const isSimulated = report.meta.scan_id.startsWith("sim-");

  lines.push("");
  lines.push(DIVIDER);
  lines.push("  Sentryɸ -- SECURITY SCAN REPORT");
  if (isSimulated) lines.push("  *** SIMULATION MODE — NOT A REAL ASSESSMENT ***");
  lines.push(DIVIDER);
  lines.push("");

  // Meta
  lines.push(`  Target       : ${report.meta.target}`);
  lines.push(`  Mode         : ${report.meta.mode}`);
  lines.push(`  Scan Depth   : ${report.meta.scan_depth}`);
  lines.push(`  Categories   : ${report.meta.categories.join(", ")}`);
  lines.push(`  Scan ID      : ${report.meta.scan_id}`);
  lines.push(`  Scan Time    : ${report.meta.timestamp}`);
  lines.push(`  Report Time  : ${report.meta.report_generated_at}`);
  lines.push("");

  // Risk Summary
  lines.push(THIN_DIVIDER);
  lines.push("  RISK SUMMARY");
  lines.push(THIN_DIVIDER);
  lines.push("");

  const s = report.summary;
  const levelLabel = RISK_LEVEL_LABELS[s.risk_level] ?? s.risk_level;
  lines.push(`  Risk Score   : ${s.risk_score}/100  (${levelLabel})`);
  lines.push(`  Total Findings: ${s.total_findings}`);
  lines.push("");

  const b = report.breakdown;
  lines.push(`    HIGH       : ${b.high ?? 0}`);
  lines.push(`    MEDIUM     : ${b.medium ?? 0}`);
  lines.push(`    LOW        : ${b.low ?? 0}`);
  lines.push("");

  // Category Breakdown
  if (Object.keys(report.categories).length > 0) {
    lines.push(THIN_DIVIDER);
    lines.push("  CATEGORY BREAKDOWN");
    lines.push(THIN_DIVIDER);
    lines.push("");
    for (const [name, cat] of Object.entries(report.categories)) {
      lines.push(
        `    ${name.padEnd(20)}  findings: ${cat.count}  max: ${String(cat.max_severity ?? "none").padEnd(6)}  avg_conf: ${(cat.avg_confidence).toFixed(2)}`
      );
    }
    lines.push("");
  }

  // Findings
  lines.push(THIN_DIVIDER);
  lines.push("  FINDINGS");
  lines.push(THIN_DIVIDER);
  lines.push("");

  if (!report.findings || report.findings.length === 0) {
    lines.push("  No findings -- target passed all probes.");
    lines.push("");
  } else {
    report.findings.forEach((f, i) => {
      const tag = SEV_TAGS[f.severity] ?? "????? ";
      const confPct = Math.round(f.confidence * 100);
      lines.push(`  #${i + 1} [${tag}] ${f.category}  (confidence: ${confPct}%)`);
      lines.push(`     ${f.evidence}`);
      const sourceParts = [];
      if (f.probe_id) sourceParts.push(`Probe: ${f.probe_id}`);
      sourceParts.push(`Source: ${f.source}`);
      lines.push(`     ${sourceParts.join(" | ")}`);
      lines.push("");
    });
  }

  // Recommendations
  lines.push(THIN_DIVIDER);
  lines.push("  RECOMMENDATIONS");
  lines.push(THIN_DIVIDER);
  lines.push("");

  if (!report.recommendations || report.recommendations.length === 0) {
    lines.push("  No recommendations -- no vulnerabilities found.");
    lines.push("");
  } else {
    report.recommendations.forEach((rec) => {
      const tag = SEV_TAGS[rec.severity] ?? "????? ";
      lines.push(`  [${tag}] ${rec.category}`);
      rec.actions.forEach((action, j) => {
        lines.push(`    ${j + 1}. ${action}`);
      });
      lines.push("");
    });
  }

  // Engine Info
  lines.push(THIN_DIVIDER);
  lines.push("  ENGINE INFO");
  lines.push(THIN_DIVIDER);
  lines.push("");
  const eng = report.engine;
  lines.push(`  Engine       : ${eng.name}`);
  lines.push(`  Probes Run   : ${eng.total_probes}`);
  if (eng.duration_sec > 0) {
    lines.push(`  Duration     : ${formatDuration(eng.duration_sec)}`);
  }
  if (eng.error) {
    lines.push(`  Error        : ${eng.error}`);
  }
  lines.push("");

  lines.push(DIVIDER);
  lines.push("  Report generated by Sentryɸ");
  if (isSimulated) {
    lines.push("  SIMULATION MODE: These results are for demonstration only.");
    lines.push("  A real assessment must be run against the actual target.");
  }
  lines.push(DIVIDER);
  lines.push("");

  return lines.join("\n");
}

// ─────────────────────────────────────────────
//  HTML generator — fully escaped, standalone, no remote assets
// ─────────────────────────────────────────────

function serializeToHtml(report: ScanReport): string {
  const isSimulated = report.meta.scan_id.startsWith("sim-");
  const title = `Sentryɸ Security Report — ${escapeHtml(report.meta.target)}`;

  const sevColor: Record<string, string> = {
    high:   "#e05260",
    medium: "#e8a838",
    low:    "#4a9edb",
  };

  const riskColor: Record<string, string> = {
    CRITICAL: "#c0392b",
    HIGH:     "#e05260",
    MEDIUM:   "#e8a838",
    LOW:      "#4a9edb",
    NONE:     "#3dbc6a",
  };

  function sevBadge(sev: string): string {
    const color = sevColor[sev.toLowerCase()] ?? "#888";
    const label = SEVERITY_LABELS[sev as keyof typeof SEVERITY_LABELS] ?? sev;
    return `<span style="display:inline-block;padding:2px 8px;border-radius:4px;background:${color}22;color:${color};font-size:11px;font-weight:700;text-transform:uppercase;border:1px solid ${color}44;">${escapeHtml(label)}</span>`;
  }

  const rLabel = RISK_LEVEL_LABELS[report.summary.risk_level] ?? report.summary.risk_level;
  const rColor = riskColor[report.summary.risk_level] ?? "#888";

  // Findings rows
  const findingRows = (report.findings ?? []).map((f, i) => {
    const confPct = Math.round(f.confidence * 100);
    return `
      <tr>
        <td style="padding:10px 12px;color:#aaa;font-size:12px;white-space:nowrap;">#${i + 1}</td>
        <td style="padding:10px 12px;">${sevBadge(f.severity)}</td>
        <td style="padding:10px 12px;font-weight:600;">${escapeHtml(categoryLabel(f.category))}</td>
        <td style="padding:10px 12px;color:#aaa;">${confPct}%</td>
        <td style="padding:10px 12px;">
          <code style="font-family:monospace;font-size:12px;background:#1a1a2e;padding:6px 8px;border-radius:4px;display:block;white-space:pre-wrap;word-break:break-word;color:#c5c8d6;">${escapeHtml(f.evidence)}</code>
          <div style="margin-top:4px;font-size:11px;color:#666;">${escapeHtml(f.probe_id ? `Probe: ${f.probe_id} | Source: ${f.source}` : `Source: ${f.source}`)}</div>
        </td>
      </tr>`;
  }).join("");

  // Recommendation cards
  const recCards = (report.recommendations ?? []).map((rec) => {
    const actionItems = rec.actions.map((a, j) =>
      `<li style="margin:6px 0;color:#c5c8d6;">${j + 1}. ${escapeHtml(a)}</li>`
    ).join("");
    return `
      <div style="margin-bottom:16px;padding:16px;background:#1a1a2e;border:1px solid #2d2d4a;border-radius:8px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
          ${sevBadge(rec.severity)}
          <strong style="font-size:15px;">${escapeHtml(categoryLabel(rec.category))}</strong>
        </div>
        <ol style="margin:0;padding:0 0 0 0;list-style:none;">${actionItems}</ol>
      </div>`;
  }).join("");

  // Category rows
  const catRows = Object.entries(report.categories ?? {}).map(([name, cat]) => {
    const sev = cat.max_severity ?? "none";
    return `
      <tr>
        <td style="padding:8px 12px;font-weight:600;">${escapeHtml(categoryLabel(name))}</td>
        <td style="padding:8px 12px;">${cat.count}</td>
        <td style="padding:8px 12px;">${cat.max_severity ? sevBadge(cat.max_severity) : "—"}</td>
        <td style="padding:8px 12px;">${Math.round(cat.avg_confidence * 100)}%</td>
      </tr>`;
  }).join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${title}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, -apple-system, sans-serif; background: #0f0f1a; color: #c5c8d6; line-height: 1.6; }
  .page { max-width: 900px; margin: 0 auto; padding: 40px 24px; }
  h1 { font-size: 24px; font-weight: 700; color: #e8eaf2; margin-bottom: 4px; }
  h2 { font-size: 17px; font-weight: 700; color: #e8eaf2; margin: 32px 0 12px; padding-bottom: 8px; border-bottom: 1px solid #2d2d4a; }
  .meta-grid { display: grid; grid-template-columns: auto 1fr; gap: 4px 24px; }
  .meta-label { font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: .04em; white-space: nowrap; }
  .meta-value { font-size: 14px; color: #c5c8d6; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; margin: 8px 0; }
  th { text-align: left; padding: 8px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #666; border-bottom: 1px solid #2d2d4a; }
  td { border-bottom: 1px solid #1e1e35; vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  .sim-banner { background: #2a1a00; border: 1px solid #e8a838; border-radius: 8px; padding: 12px 16px; margin-bottom: 24px; color: #e8a838; font-size: 14px; }
  .score-row { display: flex; align-items: center; gap: 16px; margin: 16px 0; }
  .score-num { font-size: 48px; font-weight: 700; line-height: 1; color: ${rColor}; }
  .score-level { font-size: 18px; font-weight: 600; color: ${rColor}; }
  .breakdown-row { display: flex; gap: 24px; margin: 12px 0; }
  .breakdown-item { text-align: center; }
  .breakdown-val { font-size: 28px; font-weight: 700; }
  .breakdown-lbl { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #666; }
  .footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid #2d2d4a; font-size: 12px; color: #444; }
  .empty-note { color: #666; font-style: italic; padding: 16px 0; }
  @media print {
    body { background: #fff; color: #000; }
    .page { padding: 20px; }
    h2 { color: #000; border-color: #ccc; }
    table td, table th { border-color: #ccc; }
  }
</style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <h1>Sentryɸ Security Assessment Report</h1>
  <div style="margin-bottom:24px;margin-top:8px;font-size:13px;color:#666;">Scan ID: ${escapeHtml(report.meta.scan_id)}</div>

  <!-- Simulation disclaimer -->
  ${isSimulated ? `<div class="sim-banner">⚠ <strong>Simulation Mode:</strong> This report was generated using simulated data for demonstration purposes. It does not represent a real security assessment of the stated target. Run a real scan against the actual target for authoritative results.</div>` : ""}

  <!-- Report metadata -->
  <div class="meta-grid">
    <span class="meta-label">Target</span><span class="meta-value">${escapeHtml(report.meta.target)}</span>
    <span class="meta-label">Mode</span><span class="meta-value">${escapeHtml(report.meta.mode)}</span>
    <span class="meta-label">Scan depth</span><span class="meta-value">${escapeHtml(report.meta.scan_depth)}</span>
    <span class="meta-label">Categories</span><span class="meta-value">${report.meta.categories.map((c) => escapeHtml(categoryLabel(c))).join(", ")}</span>
    <span class="meta-label">Scan time</span><span class="meta-value">${escapeHtml(formatTimestamp(report.meta.timestamp))}</span>
    <span class="meta-label">Report generated</span><span class="meta-value">${escapeHtml(formatTimestamp(report.meta.report_generated_at))}</span>
  </div>

  <!-- Executive Summary -->
  <h2>Executive Summary</h2>
  <div class="score-row">
    <div class="score-num">${report.summary.risk_score}</div>
    <div>
      <div class="score-level">${escapeHtml(rLabel)} Risk</div>
      <div style="font-size:12px;color:#666;margin-top:4px;">Score out of 100</div>
    </div>
  </div>
  <div class="breakdown-row">
    <div class="breakdown-item"><div class="breakdown-val" style="color:#e05260;">${report.breakdown.high ?? 0}</div><div class="breakdown-lbl">High</div></div>
    <div class="breakdown-item"><div class="breakdown-val" style="color:#e8a838;">${report.breakdown.medium ?? 0}</div><div class="breakdown-lbl">Medium</div></div>
    <div class="breakdown-item"><div class="breakdown-val" style="color:#4a9edb;">${report.breakdown.low ?? 0}</div><div class="breakdown-lbl">Low</div></div>
    <div class="breakdown-item"><div class="breakdown-val" style="color:#c5c8d6;">${report.summary.total_findings}</div><div class="breakdown-lbl">Total</div></div>
  </div>
  <p style="font-size:13px;color:#888;margin-top:8px;">
    ${report.summary.total_findings === 0
      ? "No findings were detected in this assessment. This does not confirm that the target is free of vulnerabilities — coverage is limited to the configured probe categories and depth."
      : `This assessment detected ${report.summary.total_findings} finding${report.summary.total_findings !== 1 ? "s" : ""} across ${Object.keys(report.categories).length} categor${Object.keys(report.categories).length !== 1 ? "ies" : "y"}. Review all findings and apply the recommended remediations before deployment.`
    }
  </p>

  <!-- Category Breakdown -->
  ${Object.keys(report.categories).length > 0 ? `
  <h2>Category Breakdown</h2>
  <table>
    <thead><tr><th>Category</th><th>Findings</th><th>Max Severity</th><th>Avg Confidence</th></tr></thead>
    <tbody>${catRows}</tbody>
  </table>` : ""}

  <!-- Findings -->
  <h2>Findings</h2>
  ${!report.findings || report.findings.length === 0
    ? `<p class="empty-note">No findings detected.</p>`
    : `<table>
    <thead><tr><th>#</th><th>Severity</th><th>Category</th><th>Confidence</th><th>Evidence</th></tr></thead>
    <tbody>${findingRows}</tbody>
  </table>`}

  <!-- Recommendations -->
  <h2>Recommendations</h2>
  ${!report.recommendations || report.recommendations.length === 0
    ? `<p class="empty-note">No recommendations available.</p>`
    : recCards}

  <!-- Engine Info -->
  <h2>Assessment Details</h2>
  <div class="meta-grid">
    <span class="meta-label">Engine</span><span class="meta-value">${escapeHtml(report.engine.name)}</span>
    <span class="meta-label">Probes run</span><span class="meta-value">${report.engine.total_probes}</span>
    ${report.engine.duration_sec > 0 ? `<span class="meta-label">Duration</span><span class="meta-value">${escapeHtml(formatDuration(report.engine.duration_sec))}</span>` : ""}
    ${report.engine.error ? `<span class="meta-label">Error</span><span class="meta-value" style="color:#e05260;">${escapeHtml(report.engine.error)}</span>` : ""}
  </div>

  <!-- Footer -->
  <div class="footer">
    <div>Report generated by Sentryɸ &bull; Version ${escapeHtml(report.report_version ?? "1.0.0")}</div>
    ${isSimulated ? `<div style="margin-top:4px;color:#e8a838;">Simulation mode — not a real security assessment</div>` : ""}
  </div>

</div>
</body>
</html>`;
}

// ─────────────────────────────────────────────
//  Browser download helper
// ─────────────────────────────────────────────

function triggerDownload(content: string, filename: string, mime: string): void {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url  = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href     = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  // Revoke after short delay to allow download to start
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function buildFilename(report: ScanReport, ext: string): string {
  const scanId  = report.meta.scan_id.slice(0, 12).replace(/[^a-z0-9-]/gi, "-");
  const date    = new Date().toISOString().slice(0, 10);
  return `sentryphi-report-${date}-${scanId}.${ext}`;
}

// ─────────────────────────────────────────────
//  Preview sections
// ─────────────────────────────────────────────

function PreviewMetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="export-meta__row">
      <span className="export-meta__label">{label}</span>
      <span className="export-meta__value">{value}</span>
    </div>
  );
}

function PreviewSummary({ report }: { report: ScanReport }) {
  const rLabel = RISK_LEVEL_LABELS[report.summary.risk_level] ?? report.summary.risk_level;
  return (
    <div className="export-summary">
      <div className={`export-summary__score export-summary__score--${report.summary.risk_level.toLowerCase()}`}>
        {report.summary.risk_score}<span className="export-summary__score-max">/100</span>
      </div>
      <div className="export-summary__level">{rLabel} Risk</div>
      <div className="export-summary__stats">
        <div className="export-summary__stat export-summary__stat--high">
          <span className="export-summary__num">{report.breakdown.high ?? 0}</span>
          <span className="export-summary__lbl">High</span>
        </div>
        <div className="export-summary__stat export-summary__stat--medium">
          <span className="export-summary__num">{report.breakdown.medium ?? 0}</span>
          <span className="export-summary__lbl">Medium</span>
        </div>
        <div className="export-summary__stat export-summary__stat--low">
          <span className="export-summary__num">{report.breakdown.low ?? 0}</span>
          <span className="export-summary__lbl">Low</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Format card
// ─────────────────────────────────────────────

interface FormatCardProps {
  fmt:          FormatDef;
  isExporting:  boolean;
  lastExported: boolean;
  onExport:     () => void;
}

function FormatCard({ fmt, isExporting, lastExported, onExport }: FormatCardProps) {
  const inBrowserMode = !isElectron();
  const unavailable   = fmt.electronOnly && inBrowserMode;

  return (
    <div
      className={`export-fmt-card${lastExported ? " export-fmt-card--done" : ""}${unavailable ? " export-fmt-card--unavailable" : ""}`}
      id={`export-fmt-${fmt.id}`}
    >
      <div className="export-fmt-card__top">
        <div className="export-fmt-card__badge">{fmt.label}</div>
        <div className="export-fmt-card__ext">.{fmt.ext}</div>
        {unavailable && (
          <span style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "auto" }}>
            Desktop Only
          </span>
        )}
      </div>
      <p className="export-fmt-card__desc">{fmt.purpose}</p>
      <button
        type="button"
        className={`button button--primary export-fmt-card__btn${isExporting ? " button--loading" : ""}${unavailable ? " button--disabled" : ""}`}
        onClick={unavailable ? undefined : onExport}
        disabled={isExporting || unavailable}
        id={`export-btn-${fmt.id}`}
        aria-label={`Download report as ${fmt.label}`}
        title={unavailable ? "PDF export requires Desktop Mode (Electron + Python)" : undefined}
      >
        {isExporting
          ? "Exporting…"
          : lastExported
          ? "✓ Saved"
          : unavailable
          ? `${fmt.label} — Desktop Mode only`
          : isElectron()
          ? `↓ Save ${fmt.label}`
          : `↓ Download ${fmt.label}`
        }
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Empty guard
// ─────────────────────────────────────────────

function EmptyNoReport({ onBack }: { onBack: () => void }) {
  return (
    <div className="export-page" id="export-page">
      <PageHeader title="Export Report" onBack={onBack} />
      <div className="actions-empty" id="export-no-report">
        <div className="actions-empty__icon">⚠</div>
        <div className="actions-empty__title">No assessment report available</div>
        <div className="actions-empty__desc">
          Return to the Results screen to load a report before exporting.
        </div>
        <button
          type="button"
          className="button button--primary"
          onClick={onBack}
          id="export-back-no-report"
        >
          ← Back to Results
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Main page component
// ─────────────────────────────────────────────

export function ExportPage({ onBackToResults, onBackToActions, onProceedToDeploy }: ExportPageProps) {
  const { state: reportState, dispatch } = useReportContext();
  const report = reportState.report;
  const inElectron = isElectron();

  // Per-format in-progress tracker
  const [exportingFmt, setExportingFmt] = useState<ExportFormat | null>(null);
  // Track which formats have been successfully exported this session
  const [downloadedFmts, setDownloadedFmts] = useState<Set<ExportFormat>>(new Set());
  // Last saved file path (Electron mode)
  const [lastSavedPath, setLastSavedPath]   = useState<string | null>(null);
  // Fallback notice (e.g. WeasyPrint not available)
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);

  // Guard: no report
  if (!report) {
    return <EmptyNoReport onBack={onBackToResults} />;
  }

  const isSimulated = report.meta.scan_id.startsWith("sim-");

  const handleExport = useCallback(async (fmt: ExportFormat) => {
    if (exportingFmt !== null) return;
    setExportingFmt(fmt);
    setLastSavedPath(null);
    setFallbackNotice(null);
    dispatch({ type: REPORT_ACTIONS.EXPORT_START });

    try {
      const fmtDef = FORMATS.find((f) => f.id === fmt)!;

      if (inElectron && window.electronAPI) {
        // ── Desktop Mode: Python export + native save dialog ──────────────
        const result = await window.electronAPI.exportReport(report, fmt);
        if (result.saved && result.filePath) {
          dispatch({ type: REPORT_ACTIONS.EXPORT_SUCCESS, payload: result.filePath });
          setDownloadedFmts((prev) => new Set(prev).add(fmt));
          setLastSavedPath(result.filePath);
          if (result.fallback) setFallbackNotice(result.fallback);
        } else if (!result.saved && !result.filePath) {
          // User cancelled dialog — silent
          dispatch({ type: REPORT_ACTIONS.EXPORT_RESET });
        } else {
          dispatch({ type: REPORT_ACTIONS.EXPORT_FAILED, payload: result.error ?? "Export failed" });
        }
      } else {
        // ── Browser Mode: Blob download ───────────────────────────────────
        let content: string;
        if (fmt === "json") {
          content = serializeToJson(report);
        } else if (fmt === "txt") {
          content = serializeToTxt(report);
        } else if (fmt === "html") {
          content = serializeToHtml(report);
        } else {
          // PDF not available in browser
          dispatch({ type: REPORT_ACTIONS.EXPORT_FAILED, payload: "PDF export requires Desktop Mode" });
          setExportingFmt(null);
          return;
        }
        const filename = buildFilename(report, fmtDef.ext);
        triggerDownload(content, filename, fmtDef.mime);
        dispatch({ type: REPORT_ACTIONS.EXPORT_SUCCESS, payload: filename });
        setDownloadedFmts((prev) => new Set(prev).add(fmt));
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown export error";
      dispatch({ type: REPORT_ACTIONS.EXPORT_FAILED, payload: msg });
    } finally {
      setExportingFmt(null);
    }
  }, [report, exportingFmt, dispatch, inElectron]);

  const handleOpenFile = useCallback(async () => {
    if (!lastSavedPath || !window.electronAPI) return;
    await window.electronAPI.openFilePath(lastSavedPath);
  }, [lastSavedPath]);

  const handleOpenFolder = useCallback(async () => {
    if (!lastSavedPath || !window.electronAPI) return;
    await window.electronAPI.openFileFolder(lastSavedPath);
  }, [lastSavedPath]);

  const handleDismissError = useCallback(() => {
    dispatch({ type: REPORT_ACTIONS.EXPORT_RESET });
  }, [dispatch]);

  const handleDismissFallback = useCallback(() => {
    setFallbackNotice(null);
  }, []);

  return (
    <div className="export-page" id="export-page">

      {/* ── Header ── */}
      <PageHeader
        title="Export Report"
        subtitle={report.meta.target}
        onBack={onBackToResults}
      />

      {/* Simulation warning */}
      {isSimulated && (
        <AlertBanner
          type="info"
          message="Simulation mode: this report was generated with simulated data. Exported files will include a visible disclaimer."
        />
      )}

      {/* Export error banner */}
      {reportState.export_status === "failed" && reportState.export_error && (
        <AlertBanner
          type="error"
          message={`Export failed: ${reportState.export_error}`}
          onDismiss={handleDismissError}
        />
      )}

      {/* Fallback notice (e.g. PDF → HTML because WeasyPrint not installed) */}
      {fallbackNotice && (
        <AlertBanner
          type="info"
          message={fallbackNotice}
          onDismiss={handleDismissFallback}
        />
      )}

      {/* Export success banner — Desktop mode shows file path + open buttons */}
      {reportState.export_status === "success" && lastSavedPath && inElectron && (
        <div
          id="export-success-banner"
          style={{
            background: "rgba(34,197,94,0.08)",
            border: "1px solid rgba(34,197,94,0.25)",
            borderRadius: "10px",
            padding: "14px 18px",
            marginBottom: "16px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            flexWrap: "wrap",
          }}
        >
          <span style={{ color: "#22c55e", fontSize: "18px" }}>✓</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 700, color: "#22c55e", fontSize: "13px" }}>
              Report saved successfully
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "var(--text-muted)",
                marginTop: "2px",
                wordBreak: "break-all",
                fontFamily: "monospace",
              }}
            >
              {lastSavedPath}
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
            <button
              type="button"
              className="button button--secondary"
              style={{ fontSize: "12px", padding: "6px 14px" }}
              onClick={handleOpenFile}
              id="export-open-file-btn"
            >
              Open File
            </button>
            <button
              type="button"
              className="button button--secondary"
              style={{ fontSize: "12px", padding: "6px 14px" }}
              onClick={handleOpenFolder}
              id="export-show-folder-btn"
            >
              Show in Folder
            </button>
          </div>
        </div>
      )}

      {/* ── Report Preview ── */}
      <section className="export-page__section" id="export-preview">
        <div className="export-page__section-title">Report Preview</div>

        {/* Meta */}
        <div className="export-meta" id="export-meta">
          <PreviewMetaRow label="Scan ID"    value={report.meta.scan_id} />
          <PreviewMetaRow label="Target"     value={report.meta.target} />
          <PreviewMetaRow label="Mode"       value={report.meta.mode} />
          <PreviewMetaRow label="Scan depth" value={report.meta.scan_depth} />
          <PreviewMetaRow
            label="Categories"
            value={report.meta.categories.map((c) => categoryLabel(c)).join(", ")}
          />
          <PreviewMetaRow label="Scan time"  value={formatTimestamp(report.meta.timestamp)} />
          <PreviewMetaRow label="Generated"  value={formatTimestamp(report.meta.report_generated_at)} />
          {isSimulated && (
            <PreviewMetaRow label="Status" value="⚠ Simulation — not a real assessment" />
          )}
        </div>

        {/* Score summary */}
        <PreviewSummary report={report} />

        {/* Finding count */}
        <div className="export-preview__finding-count">
          <span className="export-preview__count-num">{report.findings.length}</span>
          <span className="export-preview__count-lbl">
            finding{report.findings.length !== 1 ? "s" : ""} across{" "}
            {Object.keys(report.categories).length} categor{Object.keys(report.categories).length !== 1 ? "ies" : "y"}
          </span>
        </div>

        {/* Findings preview (first 3) */}
        {report.findings.length > 0 && (
          <div className="export-preview__findings" id="export-preview-findings">
            <div className="export-preview__findings-label">
              Findings preview (first {Math.min(3, report.findings.length)} of {report.findings.length})
            </div>
            {report.findings.slice(0, 3).map((f, i) => (
              <div key={i} className="export-preview__finding-row">
                <span className={`results-badge results-badge--${f.severity}`}>
                  {SEVERITY_LABELS[f.severity] ?? f.severity}
                </span>
                <span className="export-preview__finding-cat">{categoryLabel(f.category)}</span>
                <span className="export-preview__finding-conf">{Math.round(f.confidence * 100)}%</span>
              </div>
            ))}
            {report.findings.length > 3 && (
              <div className="export-preview__findings-more">
                +{report.findings.length - 3} more (see exported file for full list)
              </div>
            )}
          </div>
        )}

        {/* Zero findings */}
        {report.findings.length === 0 && (
          <div className="export-preview__no-findings">
            No findings detected. The exported report will note coverage limitations.
          </div>
        )}
      </section>

      {/* ── Export Formats ── */}
      <section className="export-page__section" id="export-formats">
        <div className="export-page__section-title">Download Format</div>
        <div className="export-page__section-note">
          All formats are downloaded to your browser's default download location.
          No data is transmitted to external services.
        </div>
        <div className="export-fmt-grid" id="export-fmt-grid">
          {FORMATS.map((fmt) => (
            <FormatCard
              key={fmt.id}
              fmt={fmt}
              isExporting={exportingFmt === fmt.id}
              lastExported={downloadedFmts.has(fmt.id)}
              onExport={() => handleExport(fmt.id)}
            />
          ))}
        </div>
      </section>

      {/* ── Actions ── */}
      <div className="export-page__actions" id="export-page-actions">
        <div className="export-page__actions-left">
          <button
            type="button"
            className="button button--secondary"
            onClick={onBackToResults}
            id="export-back-results"
          >
            ← Back to Results
          </button>
          {onBackToActions && (
            <button
              type="button"
              className="button button--ghost"
              onClick={onBackToActions}
              id="export-back-actions"
            >
              ← Recommendations
            </button>
          )}
        </div>

        {/* ── Part A: Screen 8 → Screen 9 navigation ── */}
        <button
          type="button"
          className="button button--primary"
          onClick={onProceedToDeploy}
          id="export-proceed-deploy"
        >
          Continue to Deployment Planning →
        </button>
      </div>
    </div>
  );
}
