/**
 * Sentryɸ -- Recommendations / Actions (Screen 7)
 * pages/ActionsPage.tsx
 *
 * A focused remediation-planning workspace built from report.recommendations[].
 *
 * Data contract (read-only from ReportContext):
 *   Recommendation = { category: string, severity: SeverityLevel, actions: string[] }
 *
 * Key rules:
 *   - Reads report.recommendations directly — no duplication of backend logic.
 *   - severity IS the priority (backend already sorts HIGH → MEDIUM → LOW).
 *   - Category is the only finding relationship; labels it as such.
 *   - No fabricated rationale, no invented priorities, no fake action steps.
 *   - Review state is session-only (rec_reviewed in ReportContext).
 *     Marking reviewed ≠ fix applied or verified.
 *   - Evidence and actions rendered as safe text (React default, no dangerouslySetInnerHTML).
 *   - Actions route is a hub branch: returns to results, no advance to export.
 *
 * Layout regions:
 *   A. PageHeader — "Recommendations", target, back to results
 *   B. Summary bar — total recs, high count, reviewed count, remaining
 *   C. Filter bar — severity filter + reviewed filter + sort + reset
 *   D. Recommendation list — cards with expand/collapse detail panel
 *   E. Empty state — zero recs or zero filtered recs
 *
 * Simulation provenance: shown when scan_id starts with "sim-".
 *
 * UI_ARCHITECTURE.md refs:
 *   Section 2 (actions is hub branch → returns to results)
 *   Section 3 (ReportContext state)
 *   Section 9 (report.recommendations → action list)
 */

import React, { useState, useCallback, useMemo } from "react";
import { useReportContext } from "../store/ReportContext";
import { REPORT_ACTIONS } from "../store/actions";
import { PageHeader } from "../components/layout/PageHeader";
import { AlertBanner } from "../components/feedback/AlertBanner";
import type { Recommendation, SeverityLevel } from "../services/reportTypes";
import {
  SEVERITY_LABELS,
  categoryLabel,
  severityWeight,
} from "../services/reportTypes";

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface ActionsPageProps {
  onBack:    () => void; // returns to Screen 6 (results)
  onExport?: () => void; // optional path to Screen 8 (not required by hub rules)
}

// ─────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────

type SeverityFilter  = SeverityLevel | "all";
type ReviewedFilter  = "all" | "reviewed" | "unreviewed";
type RecSort         = "severity" | "category" | "reviewed";

// ─────────────────────────────────────────────
//  Severity badge (shared with ResultsPage pattern)
// ─────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: string }) {
  const norm = (severity ?? "").toLowerCase() as SeverityLevel;
  return (
    <span
      className={`results-badge results-badge--${norm}`}
      aria-label={`Priority: ${SEVERITY_LABELS[norm] ?? severity}`}
    >
      {SEVERITY_LABELS[norm] ?? severity}
    </span>
  );
}

// ─────────────────────────────────────────────
//  Summary bar
// ─────────────────────────────────────────────

function SummaryBar({
  recs,
  reviewed,
}: {
  recs:     Recommendation[];
  reviewed: Record<string, boolean>;
}) {
  const total    = recs.length;
  const highCount   = recs.filter((r) => r.severity === "high").length;
  const reviewedCount = recs.filter((r) => reviewed[r.category]).length;
  const remaining   = total - reviewedCount;

  return (
    <div className="actions-summary" id="actions-summary" aria-label="Recommendation summary">
      <div className="actions-summary__stat">
        <span className="actions-summary__value" id="actions-total">{total}</span>
        <span className="actions-summary__label">Total</span>
      </div>
      <div className="actions-summary__divider" />
      <div className="actions-summary__stat actions-summary__stat--high">
        <span className="actions-summary__value" id="actions-high">{highCount}</span>
        <span className="actions-summary__label">High priority</span>
      </div>
      <div className="actions-summary__divider" />
      <div className="actions-summary__stat actions-summary__stat--done">
        <span className="actions-summary__value" id="actions-reviewed">{reviewedCount}</span>
        <span className="actions-summary__label">Reviewed</span>
      </div>
      <div className="actions-summary__divider" />
      <div className="actions-summary__stat">
        <span className="actions-summary__value" id="actions-remaining">{remaining}</span>
        <span className="actions-summary__label">Remaining</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Filter / sort bar
// ─────────────────────────────────────────────

interface FilterBarProps {
  severityFilter: SeverityFilter;
  reviewedFilter: ReviewedFilter;
  sort:           RecSort;
  hasActiveFilter: boolean;
  onSeverity:     (v: SeverityFilter)  => void;
  onReviewed:     (v: ReviewedFilter)  => void;
  onSort:         (v: RecSort)         => void;
  onReset:        () => void;
}

function FilterBar({
  severityFilter,
  reviewedFilter,
  sort,
  hasActiveFilter,
  onSeverity,
  onReviewed,
  onSort,
  onReset,
}: FilterBarProps) {
  return (
    <div className="actions-filter-bar" id="actions-filter-bar">
      <div className="actions-filter-bar__filters">
        {/* Severity / priority filter */}
        <select
          className="results-filter-select"
          value={severityFilter}
          onChange={(e) => onSeverity(e.target.value as SeverityFilter)}
          aria-label="Filter by priority"
          id="actions-filter-severity"
        >
          <option value="all">All priorities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        {/* Review status filter */}
        <select
          className="results-filter-select"
          value={reviewedFilter}
          onChange={(e) => onReviewed(e.target.value as ReviewedFilter)}
          aria-label="Filter by review status"
          id="actions-filter-reviewed"
        >
          <option value="all">All statuses</option>
          <option value="unreviewed">Not reviewed</option>
          <option value="reviewed">Reviewed</option>
        </select>

        {hasActiveFilter && (
          <button
            type="button"
            className="button button--ghost"
            onClick={onReset}
            id="actions-filter-reset"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Sort */}
      <div className="actions-filter-bar__sort">
        <span className="results-findings-table__sort-label">Sort:</span>
        {(["severity", "category", "reviewed"] as RecSort[]).map((s) => (
          <button
            key={s}
            type="button"
            className={`results-sort-btn${sort === s ? " results-sort-btn--active" : ""}`}
            onClick={() => onSort(s)}
            id={`actions-sort-${s}`}
          >
            {s === "severity" ? "Priority" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Single recommendation card
// ─────────────────────────────────────────────

interface RecCardProps {
  rec:        Recommendation;
  index:      number;
  reviewed:   boolean;
  expanded:   boolean;
  onToggle:   () => void;
  onReview:   () => void;
  /**
   * Related findings from the same category (by category association only —
   * no stable probe_id link exists between recommendations and findings).
   */
  relatedFindings: { severity: string; probe_id: string; confidence: number }[];
}

function RecCard({ rec, index, reviewed, expanded, onToggle, onReview, relatedFindings }: RecCardProps) {
  const sev = rec.severity as SeverityLevel;

  return (
    <article
      className={`rec-card${reviewed ? " rec-card--reviewed" : ""}${expanded ? " rec-card--expanded" : ""}`}
      id={`rec-card-${index}`}
      aria-label={`Recommendation ${index + 1}: ${categoryLabel(rec.category)}`}
    >
      {/* ── Card header (always visible) ── */}
      <div className="rec-card__header">
        <button
          type="button"
          className="rec-card__toggle"
          onClick={onToggle}
          aria-expanded={expanded}
          aria-controls={`rec-card-detail-${index}`}
          id={`rec-card-toggle-${index}`}
        >
          <span className="rec-card__index" aria-hidden="true">{index + 1}</span>
          <span className="rec-card__category">{categoryLabel(rec.category)}</span>
          <SeverityBadge severity={sev} />
          <span className="rec-card__action-count">
            {rec.actions.length} action{rec.actions.length !== 1 ? "s" : ""}
          </span>
          {reviewed && (
            <span className="rec-card__reviewed-badge" aria-label="Marked as reviewed">
              ✓ Reviewed
            </span>
          )}
          <span className="rec-card__chevron" aria-hidden="true">
            {expanded ? "▲" : "▼"}
          </span>
        </button>

        {/* Review toggle — separate from expand so it doesn't conflict */}
        <button
          type="button"
          className={`rec-card__review-btn${reviewed ? " rec-card__review-btn--done" : ""}`}
          onClick={onReview}
          aria-pressed={reviewed}
          title={reviewed ? "Mark as not reviewed" : "Mark as reviewed"}
          id={`rec-card-review-${index}`}
        >
          {reviewed ? "✓ Reviewed" : "Mark reviewed"}
        </button>
      </div>

      {/* ── Expanded detail panel ── */}
      {expanded && (
        <div
          className="rec-card__detail"
          id={`rec-card-detail-${index}`}
          role="region"
          aria-label={`Detail for ${categoryLabel(rec.category)}`}
        >
          {/* Category association notice */}
          <div className="rec-card__assoc-note">
            <span className="rec-card__assoc-label">Category scope</span>
            <span className="rec-card__assoc-value">{categoryLabel(rec.category)}</span>
            <span className="rec-card__assoc-desc">
              This recommendation addresses all findings in the{" "}
              <strong>{categoryLabel(rec.category)}</strong> category.
            </span>
          </div>

          {/* Related findings (by category only) */}
          {relatedFindings.length > 0 && (
            <div className="rec-card__related">
              <div className="rec-card__related-label">
                Related findings ({relatedFindings.length})
              </div>
              <ul className="rec-card__related-list">
                {relatedFindings.map((f, i) => (
                  <li key={i} className="rec-card__related-item">
                    <span className={`rec-card__related-sev rec-card__related-sev--${f.severity}`}>
                      {SEVERITY_LABELS[f.severity as SeverityLevel] ?? f.severity}
                    </span>
                    <span className="rec-card__related-probe">
                      {f.probe_id || "—"}
                    </span>
                    <span className="rec-card__related-conf">
                      {Math.round(f.confidence * 100)}% confidence
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Remediation actions */}
          <div className="rec-card__actions-section">
            <div className="rec-card__actions-label">
              Remediation actions
            </div>
            {rec.actions.length === 0 ? (
              <p className="rec-card__no-actions">
                No specific actions available for this recommendation.
              </p>
            ) : (
              <ol className="rec-card__actions-list">
                {rec.actions.map((action, i) => (
                  <li key={i} className="rec-card__action-item">
                    <span className="rec-card__action-num">{i + 1}</span>
                    <span className="rec-card__action-text">{action}</span>
                  </li>
                ))}
              </ol>
            )}
          </div>

          {/* Review status clarification */}
          <div className="rec-card__review-note">
            <span className="rec-card__review-note-icon" aria-hidden="true">ℹ</span>
            <span className="rec-card__review-note-text">
              Marking as reviewed indicates you have read this recommendation.
              It does not confirm that the fix has been applied or verified.
            </span>
          </div>
        </div>
      )}
    </article>
  );
}

// ─────────────────────────────────────────────
//  Empty states
// ─────────────────────────────────────────────

function EmptyNoReport({ onBack }: { onBack: () => void }) {
  return (
    <div className="actions-empty" id="actions-no-report">
      <div className="actions-empty__icon">⚠</div>
      <div className="actions-empty__title">No assessment report available</div>
      <div className="actions-empty__desc">
        Return to the Results screen to load a report before viewing recommendations.
      </div>
      <button
        type="button"
        className="button button--primary"
        onClick={onBack}
        id="actions-back-no-report"
      >
        ← Back to Results
      </button>
    </div>
  );
}

function EmptyNoRecs() {
  return (
    <div className="actions-empty" id="actions-no-recs">
      <div className="actions-empty__icon">—</div>
      <div className="actions-empty__title">No recommendations available</div>
      <div className="actions-empty__desc">
        No recommendations are available for this assessment. This does not
        indicate that the target is secure — check the Results screen for
        the full finding breakdown.
      </div>
    </div>
  );
}

function EmptyFiltered({ onReset }: { onReset: () => void }) {
  return (
    <div className="actions-empty actions-empty--filtered" id="actions-no-filtered">
      <div className="actions-empty__title">No recommendations match the current filters</div>
      <button
        type="button"
        className="button button--ghost"
        onClick={onReset}
        id="actions-filtered-reset"
      >
        Clear filters
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Main page component
// ─────────────────────────────────────────────

export function ActionsPage({ onBack, onExport }: ActionsPageProps) {
  const { state: reportState, dispatch } = useReportContext();

  // ── Filter / sort state (local — no dispatch needed) ──
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [reviewedFilter, setReviewedFilter] = useState<ReviewedFilter>("all");
  const [sort, setSort] = useState<RecSort>("severity");
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const report    = reportState.report;
  const reviewed  = reportState.rec_reviewed;

  // ── Guard: no report ──
  if (!report) {
    return (
      <div className="actions-page" id="actions-page">
        <PageHeader
          title="Recommendations"
          onBack={onBack}
        />
        <EmptyNoReport onBack={onBack} />
      </div>
    );
  }

  const isSimulated  = report.meta.scan_id.startsWith("sim-");
  const allRecs      = report.recommendations; // sorted HIGH→MED→LOW by backend

  // ── Filter ──
  const filtered = useMemo(() => {
    let result = allRecs;

    if (severityFilter !== "all") {
      result = result.filter((r) => r.severity === severityFilter);
    }
    if (reviewedFilter === "reviewed") {
      result = result.filter((r) => reviewed[r.category]);
    } else if (reviewedFilter === "unreviewed") {
      result = result.filter((r) => !reviewed[r.category]);
    }

    // Sort
    return [...result].sort((a, b) => {
      if (sort === "severity") {
        const diff = severityWeight(a.severity) - severityWeight(b.severity);
        if (diff !== 0) return diff;
        return a.category.localeCompare(b.category);
      }
      if (sort === "category") {
        return a.category.localeCompare(b.category);
      }
      if (sort === "reviewed") {
        // Unreviewed first
        const ar = reviewed[a.category] ? 1 : 0;
        const br = reviewed[b.category] ? 1 : 0;
        if (ar !== br) return ar - br;
        return severityWeight(a.severity) - severityWeight(b.severity);
      }
      return 0;
    });
  }, [allRecs, severityFilter, reviewedFilter, sort, reviewed]);

  const hasActiveFilter = severityFilter !== "all" || reviewedFilter !== "all";

  const handleResetFilters = useCallback(() => {
    setSeverityFilter("all");
    setReviewedFilter("all");
  }, []);

  // ── Toggle expand ──
  const handleToggleExpand = useCallback((idx: number) => {
    setExpandedIndex((prev) => (prev === idx ? null : idx));
  }, []);

  // ── Toggle review (explicit user action only) ──
  const handleToggleReview = useCallback((category: string) => {
    dispatch({ type: REPORT_ACTIONS.TOGGLE_REC_REVIEW, payload: category });
  }, [dispatch]);

  // ── Clear all reviews ──
  const handleClearReviews = useCallback(() => {
    dispatch({ type: REPORT_ACTIONS.CLEAR_REC_REVIEWS });
  }, [dispatch]);

  // ── Related findings by category (category association only) ──
  const findingsByCategory = useMemo(() => {
    const map: Record<string, { severity: string; probe_id: string; confidence: number }[]> = {};
    for (const finding of report.findings) {
      if (!map[finding.category]) map[finding.category] = [];
      map[finding.category].push({
        severity:   finding.severity,
        probe_id:   finding.probe_id,
        confidence: finding.confidence,
      });
    }
    return map;
  }, [report.findings]);

  const reviewedCount = allRecs.filter((r) => reviewed[r.category]).length;

  return (
    <div className="actions-page" id="actions-page">

      {/* ── A. Page Header ── */}
      <PageHeader
        title="Recommendations"
        subtitle={report.meta.target}
        onBack={onBack}
      />

      {/* Simulation provenance notice */}
      {isSimulated && (
        <AlertBanner
          type="info"
          message="Simulation mode: recommendations below are generated for demonstration. Connect the backend for real scan results."
        />
      )}

      {/* ── B. Summary bar ── */}
      {allRecs.length > 0 && (
        <section className="actions-page__section actions-page__section--flush" id="actions-summary-section">
          <SummaryBar recs={allRecs} reviewed={reviewed} />
          {reviewedCount > 0 && (
            <button
              type="button"
              className="button button--ghost actions-page__clear-reviews"
              onClick={handleClearReviews}
              id="actions-clear-reviews"
            >
              Reset review marks
            </button>
          )}
        </section>
      )}

      {/* ── No recommendations at all ── */}
      {allRecs.length === 0 && <EmptyNoRecs />}

      {/* ── C. Filter bar + D. Recommendation list ── */}
      {allRecs.length > 0 && (
        <section className="actions-page__section" id="actions-list-section">
          <FilterBar
            severityFilter={severityFilter}
            reviewedFilter={reviewedFilter}
            sort={sort}
            hasActiveFilter={hasActiveFilter}
            onSeverity={setSeverityFilter}
            onReviewed={setReviewedFilter}
            onSort={setSort}
            onReset={handleResetFilters}
          />

          {/* Result count */}
          <div className="actions-filter-count" aria-live="polite">
            {filtered.length} recommendation{filtered.length !== 1 ? "s" : ""}
            {hasActiveFilter ? " (filtered)" : ""}
          </div>

          {/* ── Empty filtered state ── */}
          {filtered.length === 0 ? (
            <EmptyFiltered onReset={handleResetFilters} />
          ) : (
            <div className="actions-list" id="actions-list" role="list">
              {filtered.map((rec, i) => {
                const relatedFindings = findingsByCategory[rec.category] ?? [];
                return (
                  <RecCard
                    key={rec.category}
                    rec={rec}
                    index={i}
                    reviewed={reviewed[rec.category] ?? false}
                    expanded={expandedIndex === i}
                    onToggle={() => handleToggleExpand(i)}
                    onReview={() => handleToggleReview(rec.category)}
                    relatedFindings={relatedFindings}
                  />
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* ── Action bar ── */}
      <div className="actions-page__actions" id="actions-page-actions">
        <button
          type="button"
          className="button button--secondary"
          onClick={onBack}
          id="actions-back-btn"
        >
          ← Back to Results
        </button>
        {onExport && (
          <button
            type="button"
            className="button button--primary"
            onClick={onExport}
            id="actions-export-btn"
          >
            Export Report
          </button>
        )}
      </div>
    </div>
  );
}
