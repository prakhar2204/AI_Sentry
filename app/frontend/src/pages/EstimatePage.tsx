/**
 * AI-SENTRY -- Estimate Page (Screen 4)
 * pages/EstimatePage.tsx
 *
 * Scan preview and decision gate. Shows the user what the scan
 * will cost in time, probes, and money before they commit.
 *
 * On load:
 *   - Reads categories, scan_depth, mode from ScanContext
 *   - Calls getEstimate() (simulated IPC)
 *   - Displays results
 *
 * Heavy scan:
 *   - If is_heavy, shows AlertBanner (warning)
 *   - User must still explicitly click "Start Scan"
 *
 * States:
 *   - loading: "Calculating estimate..." with buttons disabled
 *   - ready:   estimation displayed, buttons enabled
 *   - error:   error banner with retry button
 *
 * Follows UI_ARCHITECTURE.md:
 *   - Section 2: Screen 4 (exit: user confirms)
 *   - Section 7: UX rules (disable don't hide, numbers are precise)
 *   - Section 8: Heavy scan warning
 */

import React, { useState, useEffect, useCallback } from "react";
import { useScanContext } from "../store/ScanContext";
import { SCAN_ACTIONS } from "../store/actions";
import { PageHeader } from "../components/layout/PageHeader";
import { AlertBanner } from "../components/feedback/AlertBanner";
import {
  getEstimate,
  type EstimateResult,
} from "../services/estimatorService";

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface EstimatePageProps {
  onContinue: () => void;
  onBack: () => void;
}

// ─────────────────────────────────────────────
//  Component
// ─────────────────────────────────────────────

export function EstimatePage({ onContinue, onBack }: EstimatePageProps) {
  const { state, dispatch } = useScanContext();

  // ── Local state ──
  const [estimate, setEstimate] = useState<EstimateResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Fetch estimate on mount ──
  const fetchEstimate = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await getEstimate({
        categories: state.categories,
        scan_depth: state.scan_depth,
        mode: state.mode || "api",
      });
      setEstimate(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to calculate estimate. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }, [state.categories, state.scan_depth, state.mode]);

  useEffect(() => {
    fetchEstimate();
  }, [fetchEstimate]);

  // ── Continue handler ──
  const handleContinue = useCallback(() => {
    if (!estimate) return;
    dispatch({ type: SCAN_ACTIONS.START_SCAN });
    onContinue();
  }, [estimate, dispatch, onContinue]);

  // ── Format cost ──
  const formatCost = (usd: number): string => {
    if (usd === 0) return "Free (local)";
    return `$${usd.toFixed(4)}`;
  };

  return (
    <div className="estimate-page">
      <PageHeader
        title="Scan Estimate"
        subtitle="Review the estimated impact before starting."
        onBack={onBack}
      />

      <div className="estimate-page__content">

        {/* ── Loading State ── */}
        {loading && (
          <div className="estimate-page__loading">
            <p className="estimate-page__loading-text">
              Calculating estimate...
            </p>
          </div>
        )}

        {/* ── Error State ── */}
        {error && !loading && (
          <div className="estimate-page__error">
            <AlertBanner type="error" message={error} />
            <div className="estimate-page__error-actions">
              <button
                type="button"
                className="button button--secondary"
                onClick={fetchEstimate}
                id="estimate-retry-button"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* ── Estimate Display ── */}
        {estimate && !loading && !error && (
          <>
            {/* ── Heavy Scan Warning ── */}
            {estimate.is_heavy && (
              <AlertBanner
                type="warning"
                message="Heavy scan detected. This may take significant time and resources."
              />
            )}

            {/* ── Summary Table ── */}
            <section className="estimate-page__section">
              <h2 className="estimate-page__section-title">Scan Overview</h2>
              <dl className="estimate-page__stats">
                <div className="estimate-page__stat-row">
                  <dt className="estimate-page__stat-label">Total Probes</dt>
                  <dd className="estimate-page__stat-value" id="stat-probes">
                    {estimate.total_probes}
                  </dd>
                </div>
                <div className="estimate-page__stat-row">
                  <dt className="estimate-page__stat-label">Estimated Time</dt>
                  <dd className="estimate-page__stat-value" id="stat-time">
                    {estimate.estimated_time_display}
                  </dd>
                </div>
                <div className="estimate-page__stat-row">
                  <dt className="estimate-page__stat-label">Estimated Cost</dt>
                  <dd className="estimate-page__stat-value" id="stat-cost">
                    {formatCost(estimate.estimated_cost_usd)}
                  </dd>
                </div>
                <div className="estimate-page__stat-row">
                  <dt className="estimate-page__stat-label">Scan Depth</dt>
                  <dd className="estimate-page__stat-value" id="stat-depth">
                    {state.scan_depth} ({estimate.depth_multiplier}x)
                  </dd>
                </div>
                <div className="estimate-page__stat-row">
                  <dt className="estimate-page__stat-label">Mode</dt>
                  <dd className="estimate-page__stat-value" id="stat-mode">
                    {estimate.mode === "api" ? "API Endpoint" : "Local Model"}
                  </dd>
                </div>
              </dl>
            </section>

            {/* ── Per-Category Breakdown ── */}
            <section className="estimate-page__section">
              <h2 className="estimate-page__section-title">
                Category Breakdown
              </h2>
              <table className="estimate-page__table">
                <thead>
                  <tr>
                    <th className="estimate-page__th">Category</th>
                    <th className="estimate-page__th">Probes</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(estimate.per_category).map(
                    ([category, probes]) => (
                      <tr key={category} className="estimate-page__tr">
                        <td className="estimate-page__td">{category}</td>
                        <td className="estimate-page__td">{probes}</td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </section>
          </>
        )}

        {/* ── Actions ── */}
        <div className="estimate-page__actions">
          <button
            type="button"
            className="button button--secondary"
            onClick={onBack}
            disabled={loading}
            id="estimate-back-button"
          >
            Back
          </button>
          <button
            type="button"
            className="button button--primary"
            onClick={handleContinue}
            disabled={loading || !!error || !estimate}
            id="estimate-continue-button"
          >
            Start Scan
          </button>
        </div>

      </div>
    </div>
  );
}
