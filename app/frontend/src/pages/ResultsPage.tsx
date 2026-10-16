/**
 * Sentryɸ -- Results Dashboard (Screen 6)
 * pages/ResultsPage.tsx
 *
 * The risk dashboard shown immediately after scan completion.
 *
 * Layout regions:
 *   A. PageHeader   — title "Security Results", target, scan metadata
 *   B. Score Panel  — risk_score gauge + risk_level label + finding counts
 *   C. Severity Bar — HIGH / MEDIUM / LOW breakdown with counts
 *   D. Category Cards — per-category summary (max severity, count, confidence)
 *   E. Findings Table — filterable, sortable, expandable evidence rows
 *   F. Recommendations — per-category action cards (max 4)
 *   G. Engine Footer — engine name, probes, duration, scan ID
 *   H. Action Bar   — "View Actions" | "Export Report" primary buttons
 *
 * UX Rules (UI_ARCHITECTURE.md):
 *   - Progressive disclosure: summary first, evidence on expand
 *   - Severity always visible on every finding and category
 *   - Evidence is verbatim — no truncation, no rephrasing
 *   - Tables for findings > 5 items, cards for recommendations (max 4)
 *   - Numbers are precise (e.g. "92%" confidence, "47/100" score)
 *   - No vanity metrics — every number maps to a ScanReport field
 *   - Empty state handled for 0-finding scans
 *   - Missing data handled (null fields) without crashes
 *
 * State: All report data from ReportContext.
 *        This page does NOT own the report — it only reads it.
 */

import React, { useState, useCallback, useMemo } from "react";
import { useReportContext, selectFilteredFindings, pageFindings, buildSimulatedReport } from "../store/ReportContext";
import { REPORT_ACTIONS } from "../store/actions";
import { useScanContext } from "../store/ScanContext";
import { PageHeader } from "../components/layout/PageHeader";
import { AlertBanner } from "../components/feedback/AlertBanner";
import type {
  ScanFinding,
  SeverityLevel,
  FindingsSort,
  ScanReport,
} from "../services/reportTypes";
import {
  SEVERITY_LABELS,
  RISK_LEVEL_LABELS,
  categoryLabel,
  formatConfidence,
  formatDuration,
  formatTimestamp,
  severityWeight,
} from "../services/reportTypes";

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface ResultsPageProps {
  onViewActions: () => void;
  onExport:      () => void;
  onNewScan:     () => void;
}

// ─────────────────────────────────────────────
//  Severity badge
// ─────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: string }) {
  const norm = (severity ?? "").toLowerCase() as SeverityLevel;
  return (
    <span
      className={`results-badge results-badge--${norm}`}
      aria-label={`Severity: ${SEVERITY_LABELS[norm] ?? severity}`}
    >
      {SEVERITY_LABELS[norm] ?? severity}
    </span>
  );
}

// ─────────────────────────────────────────────
//  Score gauge
// ─────────────────────────────────────────────

function ScoreGauge({ score, level }: { score: number; level: string }) {
  const norm = score > 100 ? 100 : score < 0 ? 0 : score;
  // Color class based on level
  const levelClass =
    level === "CRITICAL" ? "critical" :
    level === "HIGH"     ? "high" :
    level === "MEDIUM"   ? "medium" :
    level === "LOW"      ? "low" : "none";

  // SVG arc gauge
  const radius  = 52;
  const cx      = 64;
  const cy      = 64;
  const circ    = 2 * Math.PI * radius;
  // Only draw 270° arc (from 135° to 405°)
  const arcFrac = (norm / 100) * 0.75;
  const dashArr = circ * arcFrac;
  const dashOff = 0;
  const totalArc = circ * 0.75;

  return (
    <div className="score-gauge" id="results-score-gauge" aria-label={`Risk score ${norm} out of 100`}>
      <svg viewBox="0 0 128 128" className="score-gauge__svg" aria-hidden="true">
        {/* Track arc */}
        <circle
          cx={cx} cy={cy} r={radius}
          fill="none"
          stroke="var(--bg-raised)"
          strokeWidth="10"
          strokeDasharray={`${totalArc} ${circ}`}
          strokeDashoffset={-circ * 0.125}
          strokeLinecap="round"
        />
        {/* Fill arc */}
        {norm > 0 && (
          <circle
            cx={cx} cy={cy} r={radius}
            fill="none"
            className={`score-gauge__fill score-gauge__fill--${levelClass}`}
            strokeWidth="10"
            strokeDasharray={`${dashArr} ${circ}`}
            strokeDashoffset={-circ * 0.125}
            strokeLinecap="round"
          />
        )}
      </svg>
      <div className="score-gauge__label">
        <span className={`score-gauge__score score-gauge__score--${levelClass}`}>
          {norm}
        </span>
        <span className="score-gauge__max">/100</span>
        <span className={`score-gauge__level score-gauge__level--${levelClass}`}>
          {RISK_LEVEL_LABELS[level as import("../services/reportTypes").RiskLevel] ?? level}
        </span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Severity bar
// ─────────────────────────────────────────────

function SeverityBar({ breakdown, total }: {
  breakdown: { high: number; medium: number; low: number };
  total: number;
}) {
  const { high, medium, low } = breakdown;
  const pct = (n: number) => total > 0 ? `${Math.round((n / total) * 100)}%` : "0%";

  return (
    <div className="results-sev-bar" id="results-severity-breakdown" aria-label="Severity breakdown">
      <div className="results-sev-bar__track">
        {high > 0 && (
          <div
            className="results-sev-bar__segment results-sev-bar__segment--high"
            style={{ width: pct(high) }}
            title={`${high} high`}
          />
        )}
        {medium > 0 && (
          <div
            className="results-sev-bar__segment results-sev-bar__segment--medium"
            style={{ width: pct(medium) }}
            title={`${medium} medium`}
          />
        )}
        {low > 0 && (
          <div
            className="results-sev-bar__segment results-sev-bar__segment--low"
            style={{ width: pct(low) }}
            title={`${low} low`}
          />
        )}
        {total === 0 && (
          <div className="results-sev-bar__segment results-sev-bar__segment--none" style={{ width: "100%" }} />
        )}
      </div>
      <div className="results-sev-bar__legend">
        <span className="results-sev-bar__legend-item">
          <span className="results-sev-bar__dot results-sev-bar__dot--high" />
          <span className="results-sev-bar__legend-count">{high}</span>
          <span className="results-sev-bar__legend-label">High</span>
        </span>
        <span className="results-sev-bar__legend-item">
          <span className="results-sev-bar__dot results-sev-bar__dot--medium" />
          <span className="results-sev-bar__legend-count">{medium}</span>
          <span className="results-sev-bar__legend-label">Medium</span>
        </span>
        <span className="results-sev-bar__legend-item">
          <span className="results-sev-bar__dot results-sev-bar__dot--low" />
          <span className="results-sev-bar__legend-count">{low}</span>
          <span className="results-sev-bar__legend-label">Low</span>
        </span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Category card
// ─────────────────────────────────────────────

function CategoryCard({ id, data, onClick, selected }: {
  id: string;
  data: { count: number; max_severity: string | null; avg_confidence: number; raw_score: number };
  onClick: () => void;
  selected: boolean;
}) {
  const sev = (data.max_severity ?? "low") as SeverityLevel;
  return (
    <button
      type="button"
      className={`results-cat-card${selected ? " results-cat-card--selected" : ""}`}
      onClick={onClick}
      id={`results-cat-${id}`}
      aria-pressed={selected}
    >
      <div className="results-cat-card__header">
        <span className="results-cat-card__name">{categoryLabel(id)}</span>
        {data.count > 0 && <SeverityBadge severity={sev} />}
      </div>
      <div className="results-cat-card__stats">
        <div className="results-cat-card__stat">
          <span className="results-cat-card__stat-value">{data.count}</span>
          <span className="results-cat-card__stat-label">findings</span>
        </div>
        {data.count > 0 && (
          <div className="results-cat-card__stat">
            <span className="results-cat-card__stat-value">
              {formatConfidence(data.avg_confidence)}
            </span>
            <span className="results-cat-card__stat-label">avg. confidence</span>
          </div>
        )}
      </div>
      {data.count === 0 && (
        <div className="results-cat-card__no-findings">No findings</div>
      )}
    </button>
  );
}

// ─────────────────────────────────────────────
//  Single finding row
// ─────────────────────────────────────────────

function FindingRow({ finding, index, expanded, onToggle }: {
  finding: ScanFinding;
  index:   number;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      className={`results-finding${expanded ? " results-finding--expanded" : ""}`}
      id={`results-finding-${index}`}
    >
      {/* Summary row (always visible) */}
      <button
        type="button"
        className="results-finding__summary"
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={`results-finding-evidence-${index}`}
      >
        <span className="results-finding__num">{index + 1}</span>
        <span className="results-finding__sev"><SeverityBadge severity={finding.severity} /></span>
        <span className="results-finding__cat">{categoryLabel(finding.category)}</span>
        <span className="results-finding__conf">{formatConfidence(finding.confidence)}</span>
        <span className="results-finding__expand" aria-hidden="true">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {/* Evidence panel (visible when expanded) */}
      {expanded && (
        <div
          className="results-finding__evidence-panel"
          id={`results-finding-evidence-${index}`}
          role="region"
          aria-label={`Evidence for finding ${index + 1}`}
        >
          <div className="results-finding__evidence-meta">
            <span className="results-finding__meta-label">Source</span>
            <span className="results-finding__meta-value">{finding.source || "—"}</span>
            {finding.probe_id && (
              <>
                <span className="results-finding__meta-label">Probe ID</span>
                <span className="results-finding__meta-value results-finding__meta-value--mono">{finding.probe_id}</span>
              </>
            )}
          </div>
          <div className="results-finding__evidence-label">Evidence</div>
          <pre
            className="results-finding__evidence"
            aria-label="Evidence text"
          >
            {/* Verbatim evidence — no truncation, no rephrasing (UI_ARCHITECTURE.md rule 12) */}
            {finding.evidence || "No evidence text available."}
          </pre>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Findings table
// ─────────────────────────────────────────────

function FindingsTable({
  report,
  selectedCategory,
  selectedSeverity,
  sort,
  page,
  expandedFinding,
  onCategoryFilter,
  onSeverityFilter,
  onSort,
  onPage,
  onExpand,
}: {
  report:           ScanReport;
  selectedCategory: string | null;
  selectedSeverity: string | null;
  sort:             FindingsSort;
  page:             number;
  expandedFinding:  number | null;
  onCategoryFilter: (cat: string | null) => void;
  onSeverityFilter: (sev: string | null) => void;
  onSort:           (s: FindingsSort) => void;
  onPage:           (p: number) => void;
  onExpand:         (idx: number | null) => void;
}) {
  const filtered = useMemo(
    () => selectFilteredFindings(report.findings, selectedCategory, selectedSeverity, sort),
    [report.findings, selectedCategory, selectedSeverity, sort]
  );

  const { items, totalPages } = useMemo(
    () => pageFindings(filtered, page),
    [filtered, page]
  );

  // Unique categories and severities for filters
  const uniqueCategories = useMemo(
    () => [...new Set(report.findings.map((f) => f.category))].sort(),
    [report.findings]
  );

  const handleToggle = useCallback((idx: number) => {
    // idx is position within the current page's items
    onExpand(expandedFinding === idx ? null : idx);
  }, [expandedFinding, onExpand]);

  if (report.findings.length === 0) {
    return (
      <div className="results-empty" id="results-no-findings">
        <div className="results-empty__icon">✓</div>
        <div className="results-empty__title">No vulnerabilities detected</div>
        <div className="results-empty__desc">
          The target passed all probes in the selected categories.
        </div>
      </div>
    );
  }

  return (
    <div className="results-findings-table" id="results-findings-table">
      {/* Filters + sort */}
      <div className="results-findings-table__controls">
        <div className="results-findings-table__filters">
          {/* Category filter */}
          <select
            className="results-filter-select"
            value={selectedCategory ?? ""}
            onChange={(e) => onCategoryFilter(e.target.value || null)}
            aria-label="Filter by category"
            id="results-filter-category"
          >
            <option value="">All categories</option>
            {uniqueCategories.map((cat) => (
              <option key={cat} value={cat}>{categoryLabel(cat)}</option>
            ))}
          </select>

          {/* Severity filter */}
          <select
            className="results-filter-select"
            value={selectedSeverity ?? ""}
            onChange={(e) => onSeverityFilter(e.target.value || null)}
            aria-label="Filter by severity"
            id="results-filter-severity"
          >
            <option value="">All severities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {/* Active filter indicator */}
          {(selectedCategory || selectedSeverity) && (
            <button
              type="button"
              className="button button--ghost"
              onClick={() => { onCategoryFilter(null); onSeverityFilter(null); }}
              id="results-clear-filters"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Sort */}
        <div className="results-findings-table__sort">
          <span className="results-findings-table__sort-label">Sort:</span>
          {(["severity", "category", "confidence"] as FindingsSort[]).map((s) => (
            <button
              key={s}
              type="button"
              className={`results-sort-btn${sort === s ? " results-sort-btn--active" : ""}`}
              onClick={() => onSort(s)}
              id={`results-sort-${s}`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Count */}
      <div className="results-findings-table__count" aria-live="polite">
        {filtered.length} finding{filtered.length !== 1 ? "s" : ""}
        {(selectedCategory || selectedSeverity) ? " (filtered)" : ""}
      </div>

      {/* Column headers */}
      <div className="results-findings-table__header" aria-hidden="true">
        <span className="results-findings-table__col-num">#</span>
        <span className="results-findings-table__col-sev">Severity</span>
        <span className="results-findings-table__col-cat">Category</span>
        <span className="results-findings-table__col-conf">Confidence</span>
        <span className="results-findings-table__col-expand" />
      </div>

      {/* Rows */}
      <div className="results-findings-table__rows">
        {filtered.length === 0 ? (
          <div className="results-empty--filtered">
            No findings match the current filters.
          </div>
        ) : (
          items.map((finding, i) => {
            const globalIdx = (page - 1) * 20 + i;
            return (
              <FindingRow
                key={`${finding.category}-${finding.probe_id}-${globalIdx}`}
                finding={finding}
                index={globalIdx}
                expanded={expandedFinding === globalIdx}
                onToggle={() => handleToggle(globalIdx)}
              />
            );
          })
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="results-findings-table__pagination">
          <button
            type="button"
            className="button button--secondary"
            disabled={page <= 1}
            onClick={() => onPage(page - 1)}
            id="results-page-prev"
          >
            ← Previous
          </button>
          <span className="results-findings-table__page-info">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            className="button button--secondary"
            disabled={page >= totalPages}
            onClick={() => onPage(page + 1)}
            id="results-page-next"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Recommendation card
// ─────────────────────────────────────────────

function RecommendationCard({ rec, index }: {
  rec: { category: string; severity: string; actions: string[] };
  index: number;
}) {
  return (
    <div
      className="results-rec-card"
      id={`results-rec-${index}`}
    >
      <div className="results-rec-card__header">
        <span className="results-rec-card__category">{categoryLabel(rec.category)}</span>
        <SeverityBadge severity={rec.severity} />
      </div>
      <ol className="results-rec-card__actions">
        {rec.actions.map((action, i) => (
          <li key={i} className="results-rec-card__action">
            {action}
          </li>
        ))}
      </ol>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Engine footer
// ─────────────────────────────────────────────

function EngineFooter({ report }: { report: ScanReport }) {
  const { engine, meta } = report;
  return (
    <div className="results-engine-footer" id="results-engine-footer">
      <div className="results-engine-footer__row">
        <span className="results-engine-footer__label">Engine</span>
        <span className="results-engine-footer__value">{engine.name || "—"}</span>
      </div>
      <div className="results-engine-footer__row">
        <span className="results-engine-footer__label">Probes run</span>
        <span className="results-engine-footer__value">{engine.total_probes}</span>
      </div>
      {engine.duration_sec > 0 && (
        <div className="results-engine-footer__row">
          <span className="results-engine-footer__label">Duration</span>
          <span className="results-engine-footer__value">{formatDuration(engine.duration_sec)}</span>
        </div>
      )}
      <div className="results-engine-footer__row">
        <span className="results-engine-footer__label">Scan depth</span>
        <span className="results-engine-footer__value results-engine-footer__value--caps">
          {meta.scan_depth}
        </span>
      </div>
      <div className="results-engine-footer__row">
        <span className="results-engine-footer__label">Generated</span>
        <span className="results-engine-footer__value">{formatTimestamp(meta.report_generated_at)}</span>
      </div>
      <div className="results-engine-footer__row">
        <span className="results-engine-footer__label">Scan ID</span>
        <span className="results-engine-footer__value results-engine-footer__value--mono">
          {meta.scan_id}
        </span>
      </div>
      {engine.error && (
        <div className="results-engine-footer__error">
          Engine error: {engine.error}
        </div>
      )}
      {meta.output_dir && !meta.output_dir.includes("[simulation") && (
        <div className="results-engine-footer__row">
          <span className="results-engine-footer__label">Output dir</span>
          <span className="results-engine-footer__value results-engine-footer__value--mono">
            {meta.output_dir}
          </span>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Main page component
// ─────────────────────────────────────────────

export function ResultsPage({ onViewActions, onExport, onNewScan }: ResultsPageProps) {
  const { state: reportState, dispatch } = useReportContext();
  const { state: scanState } = useScanContext();

  // ── If no report yet, build a simulated one ──
  // This happens when we navigate from ScanPage in simulator mode.
  const report: ScanReport | null = useMemo(() => {
    if (reportState.report) return reportState.report;

    // Build from scan config — scan just completed
    if (scanState.phase === "complete" || scanState.target) {
      const simulated = buildSimulatedReport(
        scanState.target || "https://api.example.com",
        scanState.mode || "api",
        scanState.scan_depth || "standard",
        scanState.categories.length > 0
          ? scanState.categories
          : ["prompt_injection", "jailbreak", "data_leak", "harmful_output"]
      );
      // Store it in context for downstream screens
      dispatch({ type: REPORT_ACTIONS.SET_REPORT, payload: simulated });
      return simulated;
    }

    return null;
  }, [reportState.report, scanState.phase, scanState.target, scanState.mode, scanState.scan_depth, scanState.categories, dispatch]);

  // ── Filter/sort/page dispatch helpers ──
  const setCategory = useCallback((cat: string | null) => {
    dispatch({ type: REPORT_ACTIONS.SET_CATEGORY_FILTER, payload: cat });
  }, [dispatch]);

  const setSeverity = useCallback((sev: string | null) => {
    dispatch({ type: REPORT_ACTIONS.SET_SEVERITY_FILTER, payload: sev });
  }, [dispatch]);

  const setSort = useCallback((s: FindingsSort) => {
    dispatch({ type: REPORT_ACTIONS.SET_FINDINGS_SORT, payload: s });
  }, [dispatch]);

  const setPage = useCallback((p: number) => {
    dispatch({ type: REPORT_ACTIONS.SET_FINDINGS_PAGE, payload: p });
  }, [dispatch]);

  const setExpanded = useCallback((idx: number | null) => {
    dispatch({ type: "SET_EXPANDED_FINDING", payload: idx });
  }, [dispatch]);

  // ── Category card filter toggle ──
  const handleCategoryCardClick = useCallback((catId: string) => {
    setCategory(reportState.selected_category === catId ? null : catId);
  }, [reportState.selected_category, setCategory]);

  // ── Guard: no report available ──
  if (!report) {
    return (
      <div className="results-page" id="results-page">
        <PageHeader title="Security Results" />
        <AlertBanner type="error" message="No scan report available. Please run a scan first." />
        <div className="results-page__actions">
          <button
            type="button"
            className="button button--primary"
            onClick={onNewScan}
            id="results-new-scan"
          >
            Start New Scan
          </button>
        </div>
      </div>
    );
  }

  const { summary, breakdown, categories, findings, recommendations } = report;
  const hasFindings = summary.total_findings > 0;
  const categoryIds = Object.keys(categories);

  // Simulated report provenance label
  const isSimulated = report.meta.scan_id.startsWith("sim-");

  return (
    <div className="results-page" id="results-page">
      {/* ── A. Page Header ── */}
      <PageHeader
        title="Security Results"
        subtitle={report.meta.target}
      />

      {/* Simulation provenance notice — not shown to end users with real backend */}
      {isSimulated && (
        <AlertBanner
          type="info"
          message="Simulation mode: findings below are generated for demonstration. Connect the backend for real scan results."
        />
      )}

      {/* ── B. Score Panel ── */}
      <section className="results-page__section results-score-panel" id="results-score-section">
        <div className="results-score-panel__gauge">
          <ScoreGauge score={summary.risk_score} level={summary.risk_level} />
        </div>

        <div className="results-score-panel__stats">
          <div className="results-stat">
            <span className="results-stat__value" id="results-total-findings">
              {summary.total_findings}
            </span>
            <span className="results-stat__label">Total findings</span>
          </div>
          <div className="results-stat results-stat--high">
            <span className="results-stat__value" id="results-high-count">
              {breakdown.high}
            </span>
            <span className="results-stat__label">High</span>
          </div>
          <div className="results-stat results-stat--medium">
            <span className="results-stat__value" id="results-medium-count">
              {breakdown.medium}
            </span>
            <span className="results-stat__label">Medium</span>
          </div>
          <div className="results-stat results-stat--low">
            <span className="results-stat__value" id="results-low-count">
              {breakdown.low}
            </span>
            <span className="results-stat__label">Low</span>
          </div>
        </div>
      </section>

      {/* ── C. Severity Bar ── */}
      {hasFindings && (
        <section className="results-page__section" id="results-severity-section">
          <h2 className="results-page__section-title">Severity Distribution</h2>
          <SeverityBar breakdown={breakdown} total={summary.total_findings} />
        </section>
      )}

      {/* ── D. Category Cards ── */}
      {categoryIds.length > 0 && (
        <section className="results-page__section" id="results-categories-section">
          <h2 className="results-page__section-title">Category Summary</h2>
          <div className="results-cat-grid">
            {categoryIds.map((id) => (
              <CategoryCard
                key={id}
                id={id}
                data={categories[id]}
                selected={reportState.selected_category === id}
                onClick={() => handleCategoryCardClick(id)}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── E. Findings Table ── */}
      <section className="results-page__section" id="results-findings-section">
        <h2 className="results-page__section-title">
          {hasFindings ? "Findings" : "Findings — None Detected"}
        </h2>
        <FindingsTable
          report={report}
          selectedCategory={reportState.selected_category}
          selectedSeverity={reportState.selected_severity}
          sort={reportState.findings_sort}
          page={reportState.findings_page}
          expandedFinding={reportState.expanded_finding}
          onCategoryFilter={setCategory}
          onSeverityFilter={setSeverity}
          onSort={setSort}
          onPage={setPage}
          onExpand={setExpanded}
        />
      </section>

      {/* ── F. Recommendations ── */}
      {recommendations.length > 0 && (
        <section className="results-page__section" id="results-recommendations-section">
          <h2 className="results-page__section-title">Recommendations</h2>
          <div className="results-rec-grid">
            {recommendations.slice(0, 4).map((rec, i) => (
              <RecommendationCard key={rec.category} rec={rec} index={i} />
            ))}
          </div>
          {recommendations.length > 4 && (
            <button
              type="button"
              className="button button--ghost results-page__more-recs"
              onClick={onViewActions}
              id="results-view-all-recs"
            >
              View all {recommendations.length} recommendations →
            </button>
          )}
        </section>
      )}

      {!hasFindings && (
        <section className="results-page__section" id="results-no-recommendations">
          <h2 className="results-page__section-title">Recommendations</h2>
          <p className="results-page__no-recs">
            No recommendations — target passed all probes.
          </p>
        </section>
      )}

      {/* ── G. Engine Footer ── */}
      <section className="results-page__section results-page__section--faint" id="results-engine-section">
        <h2 className="results-page__section-title results-page__section-title--sm">
          Scan Details
        </h2>
        <EngineFooter report={report} />
      </section>

      {/* ── H. Action Bar ── */}
      <div className="results-page__actions" id="results-actions">
        <button
          type="button"
          className="button button--primary"
          onClick={onViewActions}
          id="results-view-actions"
        >
          View Recommendations
        </button>
        <button
          type="button"
          className="button button--secondary"
          onClick={onExport}
          id="results-export"
        >
          Export Report
        </button>
        <button
          type="button"
          className="button button--ghost"
          onClick={onNewScan}
          id="results-new-scan-btn"
        >
          New Scan
        </button>
      </div>
    </div>
  );
}
