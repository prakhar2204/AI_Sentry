/**
 * AI-SENTRY -- Scan Progress Page (Screen 5)
 * pages/ScanPage.tsx
 *
 * Live scan execution display.
 *
 * Layout regions:
 *   A. Page Header — title, target, config summary
 *   B. Overall Progress — bar, percentage, probes, elapsed
 *   C. Current Activity — lifecycle stage description
 *   D. Category Progress — per-category status table
 *   E. Activity Feed — scrollable event log (capped)
 *   F. Preliminary Findings — count of detected findings
 *   G. Scan Controls — cancel with confirmation
 *
 * Lifecycle:
 *   Mount → auto-start scan via scanService
 *   Progress events → dispatch to ScanContext
 *   Complete → brief transition → navigate to results
 *   Cancel → confirmation → stop → navigate to config
 *   Fail → error display → retry/back options
 *
 * Rules (UI_ARCHITECTURE.md):
 *   - Forward-only during scan (no back button)
 *   - No external engine names in user-facing UI
 *   - Destructive actions require confirmation
 *   - Progress derives from actual event state
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useScanContext } from "../store/ScanContext";
import { SCAN_ACTIONS } from "../store/actions";
import { PageHeader } from "../components/layout/PageHeader";
import { AlertBanner } from "../components/feedback/AlertBanner";
import { startScan, buildScanConfig } from "../services/scanService";
import {
  type ScanController,
  type ScanLifecycleStage,
  type CategoryState,
  STAGE_LABELS,
  ACTIVE_STAGES,
  TERMINAL_STAGES,
} from "../services/scanTypes";

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface ScanPageProps {
  onComplete: () => void;
  onCancel: () => void;
}

// ─────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────

function formatElapsed(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function truncateTarget(target: string, max: number = 48): string {
  if (target.length <= max) return target;
  return target.substring(0, max - 3) + "…";
}

/** Category status badge label */
function statusLabel(status: CategoryState["status"]): string {
  switch (status) {
    case "queued": return "Queued";
    case "active": return "Active";
    case "complete": return "Complete";
    case "failed": return "Failed";
    case "skipped": return "Skipped";
    default: return status;
  }
}

// ─────────────────────────────────────────────
//  Component
// ─────────────────────────────────────────────

export function ScanPage({ onComplete, onCancel }: ScanPageProps) {
  const { state, dispatch } = useScanContext();
  const exec = state.scan_execution;

  // ── Local UI state ──
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);

  // ── Refs ──
  const controllerRef = useRef<ScanController | null>(null);
  const hasStartedRef = useRef(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const mountedRef = useRef(true);

  // ── Cleanup on unmount ──
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (controllerRef.current) {
        controllerRef.current.cancel();
      }
    };
  }, []);

  // ── Auto-scroll activity feed ──
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [exec?.activity_log.length]);

  // ── Start scan on mount ──
  useEffect(() => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;

    // Defensive fallback: if categories are empty (e.g. navigated here
    // programmatically without going through ConfigPage), use all categories.
    const FALLBACK_CATEGORIES = ["prompt_injection", "jailbreak", "data_leak", "harmful_output"];
    const effectiveCategories =
      state.categories && state.categories.length > 0
        ? state.categories
        : FALLBACK_CATEGORIES;

    const config = buildScanConfig(
      state.target || "https://api.example.com",
      (state.mode as "api" | "local") || "api",
      state.scan_depth || "standard",
      effectiveCategories
    );

    const controller = startScan(config, {
      onProgress(event) {
        if (!mountedRef.current) return;
        dispatch({
          type: SCAN_ACTIONS.SCAN_PROGRESS_EVENT,
          payload: event,
        });
      },
      onActivity(entry) {
        if (!mountedRef.current) return;
        dispatch({
          type: SCAN_ACTIONS.SCAN_ACTIVITY_EVENT,
          payload: entry,
        });
      },
      onComplete() {
        if (!mountedRef.current) return;
        setIsCompleting(true);
      },
      onError(error, details) {
        if (!mountedRef.current) return;
        dispatch({
          type: SCAN_ACTIONS.SCAN_FAILED,
          payload: error,
          details,
        } as any);
      },
    });

    controllerRef.current = controller;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Completion transition ──
  useEffect(() => {
    if (!isCompleting) return;

    const timer = setTimeout(() => {
      if (!mountedRef.current) return;
      dispatch({ type: SCAN_ACTIONS.SCAN_COMPLETE });
      onComplete();
    }, 1500);

    return () => clearTimeout(timer);
  }, [isCompleting, dispatch, onComplete]);

  // ── Cancel handler ──
  const handleCancelRequest = useCallback(() => {
    setShowCancelConfirm(true);
  }, []);

  const handleCancelConfirm = useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.cancel();
    }
    setShowCancelConfirm(false);
    dispatch({ type: SCAN_ACTIONS.SCAN_CANCELLED });
    onCancel();
  }, [dispatch, onCancel]);

  const handleCancelDismiss = useCallback(() => {
    setShowCancelConfirm(false);
  }, []);

  // ── Retry after failure ──
  const handleRetry = useCallback(() => {
    onCancel(); // Return to config to retry
  }, [onCancel]);

  // ── Derived values ──
  const probesCompleted = exec?.probes_completed ?? 0;
  const probesTotal = exec?.probes_total ?? 0;
  const progressPercent = probesTotal > 0
    ? Math.round((probesCompleted / probesTotal) * 100)
    : 0;
  const elapsedSec = exec?.elapsed_sec ?? 0;
  const lifecycleStage = exec?.lifecycle_stage ?? "idle";
  const activityLabel = exec?.activity_label ?? "Preparing...";
  const categories = exec?.categories ?? [];
  const findings = exec?.preliminary_findings ?? 0;
  const activityLog = exec?.activity_log ?? [];
  const isFailed = state.phase === "failed";
  const isCancelled = state.phase === "cancelled";
  const isTerminal = isFailed || isCancelled || isCompleting;

  return (
    <div className="scan-page" id="scan-page">
      {/* ── A. Page Header ── */}
      <PageHeader
        title="Security Scan"
        subtitle={truncateTarget(state.target || "")}
      />

      <div className="scan-page__content">
        {/* ── Error State ── */}
        {isFailed && (
          <div className="scan-page__error-block">
            <AlertBanner type="error" message={state.error || "Analysis failed."} />
            {state.error_details && (
              <details className="scan-page__error-details">
                <summary>Technical details</summary>
                <pre className="scan-page__error-pre">{state.error_details}</pre>
              </details>
            )}
            <div className="scan-page__error-actions">
              <button
                type="button"
                className="button button--secondary"
                onClick={handleRetry}
                id="scan-retry-button"
              >
                Return to Configuration
              </button>
            </div>
          </div>
        )}

        {/* ── Cancelled State ── */}
        {isCancelled && (
          <div className="scan-page__cancelled-block">
            <AlertBanner type="info" message="Scan cancelled." />
            <div className="scan-page__error-actions">
              <button
                type="button"
                className="button button--secondary"
                onClick={handleRetry}
                id="scan-restart-button"
              >
                Return to Configuration
              </button>
            </div>
          </div>
        )}

        {/* ── B. Overall Progress ── */}
        {!isFailed && !isCancelled && (
          <>
            <section className="scan-page__section" id="scan-progress-section">
              <div className="scan-page__progress-header">
                <span className="scan-page__status-text" id="scan-status">
                  {isCompleting ? "Scan complete" : activityLabel}
                </span>
                <span className="scan-page__progress-pct" id="scan-percent">
                  {isCompleting ? 100 : progressPercent}%
                </span>
              </div>
              <div className="scan-page__progress-track">
                <div
                  className={`scan-page__progress-fill${isCompleting ? " scan-page__progress-fill--complete" : ""}`}
                  style={{ width: `${isCompleting ? 100 : progressPercent}%` }}
                  role="progressbar"
                  aria-valuenow={isCompleting ? 100 : progressPercent}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Scan progress"
                  id="scan-progress-bar"
                />
              </div>
              <div className="scan-page__progress-meta">
                <span>{probesCompleted} / {probesTotal} probes</span>
                <span>Elapsed: {formatElapsed(elapsedSec)}</span>
              </div>
            </section>

            {/* ── C + F. Current Activity + Findings ── */}
            <div className="scan-page__status-row">
              <div className="scan-page__activity-block">
                <span className="scan-page__label">Current Stage</span>
                <span className="scan-page__value" id="scan-stage">
                  {isCompleting
                    ? STAGE_LABELS.completed
                    : STAGE_LABELS[lifecycleStage] || activityLabel}
                </span>
              </div>
              {findings > 0 && (
                <div className="scan-page__findings-block">
                  <span className="scan-page__label">Potential Findings</span>
                  <span className="scan-page__findings-count" id="scan-findings-count">
                    {findings}
                  </span>
                </div>
              )}
            </div>

            {/* ── D. Category Progress ── */}
            {categories.length > 0 && (
              <section className="scan-page__section" id="scan-categories-section">
                <h2 className="scan-page__section-title">Category Progress</h2>
                <div className="scan-page__cat-list">
                  {categories.map((cat) => (
                    <div
                      key={cat.id}
                      className={`scan-page__cat-row scan-page__cat-row--${cat.status}`}
                      id={`scan-cat-${cat.id}`}
                    >
                      <span className="scan-page__cat-label">{cat.label}</span>
                      <span className="scan-page__cat-probes">
                        {cat.probes_completed}/{cat.probes_total}
                      </span>
                      <span
                        className={`scan-page__cat-badge scan-page__cat-badge--${cat.status}`}
                        aria-label={`${cat.label}: ${statusLabel(cat.status)}`}
                      >
                        {statusLabel(cat.status)}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* ── E. Activity Feed ── */}
            {activityLog.length > 0 && (
              <section className="scan-page__section" id="scan-activity-section">
                <h2 className="scan-page__section-title">Scan Activity</h2>
                <div
                  className="scan-page__feed"
                  ref={feedRef}
                  id="scan-activity-feed"
                  aria-live="off"
                  role="log"
                >
                  {activityLog.map((entry, idx) => (
                    <div
                      key={idx}
                      className={`scan-page__feed-entry scan-page__feed-entry--${entry.severity}`}
                    >
                      <span className="scan-page__feed-time">{entry.timestamp}</span>
                      <span className="scan-page__feed-msg">{entry.message}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* ── G. Controls ── */}
            {!isTerminal && (
              <div className="scan-page__actions" id="scan-actions">
                <button
                  type="button"
                  className="button button--secondary"
                  onClick={handleCancelRequest}
                  id="scan-cancel-button"
                >
                  Cancel Scan
                </button>
              </div>
            )}

            {/* ── Completion message ── */}
            {isCompleting && (
              <div className="scan-page__actions">
                <span className="scan-page__complete-text">
                  Scan complete — preparing results…
                </span>
              </div>
            )}
          </>
        )}

        {/* ── Cancel Confirmation Dialog ── */}
        {showCancelConfirm && (
          <div
            className="scan-page__overlay"
            role="dialog"
            aria-modal="true"
            aria-label="Cancel scan confirmation"
            id="scan-cancel-dialog"
          >
            <div className="scan-page__dialog">
              <h3 className="scan-page__dialog-title">Cancel Scan?</h3>
              <p className="scan-page__dialog-text">
                This will stop the scan and discard current progress.
                Completed categories will not be retained.
              </p>
              <div className="scan-page__dialog-actions">
                <button
                  type="button"
                  className="button button--secondary"
                  onClick={handleCancelDismiss}
                  id="scan-cancel-dismiss"
                  autoFocus
                >
                  Continue Scanning
                </button>
                <button
                  type="button"
                  className="button button--primary scan-page__dialog-danger"
                  onClick={handleCancelConfirm}
                  id="scan-cancel-confirm"
                >
                  Cancel Scan
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
