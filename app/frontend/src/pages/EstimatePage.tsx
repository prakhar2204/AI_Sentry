/**
 * AI-SENTRY -- Estimate Page (Screen 4)
 * pages/EstimatePage.tsx
 *
 * Scan preview and decision gate. Shows the user what the scan
 * will cost in time, probes, compute power, and GPU usage before they commit.
 *
 * Sections:
 *   A. Scan Overview (probes, time, cost, depth, mode, engine)
 *   B. Compute & GPU Resources (GPU name, VRAM total/free, utilization)
 *   C. Per-Category Breakdown
 *   D. Local Model Notice (if mode=local and target is a file path)
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
//  GPU Info type
// ─────────────────────────────────────────────

interface GpuInfo {
  available: boolean;
  name?: string;
  vram_total_mb?: number;
  vram_free_mb?: number;
  utilization_pct?: number;
  driver_version?: string;
  error?: string;
}

// ─────────────────────────────────────────────
//  VRAM overhead estimate per depth (probe runner overhead only)
// ─────────────────────────────────────────────

const VRAM_ESTIMATE_MB: Record<string, number> = {
  quick:    512,
  standard: 1024,
  deep:     2048,
};

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface EstimatePageProps {
  onContinue: () => void;
  onBack: () => void;
}

// ─────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────

function formatVram(mb: number): string {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${mb} MB`;
}

function vramSufficient(gpuInfo: GpuInfo, depth: string): boolean {
  if (!gpuInfo.available || gpuInfo.vram_free_mb == null) return true;
  return gpuInfo.vram_free_mb >= (VRAM_ESTIMATE_MB[depth] ?? 512);
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
  const [gpuInfo, setGpuInfo] = useState<GpuInfo | null>(null);
  const [gpuLoading, setGpuLoading] = useState(false);

  // ── Fetch compute estimate on mount ──
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

  // ── Fetch GPU info (Electron only) ──
  const fetchGpuInfo = useCallback(async () => {
    const api = (window as any).electronAPI;
    if (!api?.getGpuInfo) {
      setGpuInfo({ available: false, error: "GPU query not available in browser mode" });
      return;
    }
    setGpuLoading(true);
    try {
      const info: GpuInfo = await api.getGpuInfo();
      setGpuInfo(info);
    } catch {
      setGpuInfo({ available: false, error: "Failed to query GPU" });
    } finally {
      setGpuLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEstimate();
    fetchGpuInfo();
  }, [fetchEstimate, fetchGpuInfo]);

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

  // Is the target a local .gguf file (not a URL)?
  const isLocalGguf =
    state.mode === "local" &&
    state.target != null &&
    !state.target.startsWith("http");

  return (
    <div className="estimate-page">
      <PageHeader
        title="Scan Estimate"
        subtitle="Review the estimated compute impact before starting."
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

        {/* ── Local GGUF Notice ── */}
        {isLocalGguf && !loading && (
          <AlertBanner
            type="warning"
            message={
              `Local model file detected: "${state.target}". ` +
              `The scanner probes your model via its local inference server ` +
              `(default: http://localhost:11434). ` +
              `Ensure Ollama or llama.cpp server is running with this model loaded before starting.`
            }
          />
        )}

        {/* ── Estimate + GPU Display ── */}
        {estimate && !loading && !error && (
          <>
            {/* ── Heavy Scan Warning ── */}
            {estimate.is_heavy && (
              <AlertBanner
                type="warning"
                message="Heavy scan detected. This may take significant time and resources."
              />
            )}

            {/* ── A. Scan Overview ── */}
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
                <div className="estimate-page__stat-row">
                  <dt className="estimate-page__stat-label">Scan Engine</dt>
                  <dd className="estimate-page__stat-value" id="stat-engine">
                    {state.engine === "auto"
                      ? "Auto (selects best available)"
                      : state.engine ?? "auto"}
                  </dd>
                </div>
              </dl>
            </section>

            {/* ── B. Compute & GPU Resources ── */}
            <section className="estimate-page__section">
              <h2 className="estimate-page__section-title">Compute Resources</h2>

              {gpuLoading && (
                <p className="estimate-page__loading-text" style={{ fontSize: "0.85rem", marginBottom: "0.5rem" }}>
                  Detecting GPU...
                </p>
              )}

              {!gpuLoading && gpuInfo && (
                <dl className="estimate-page__stats">
                  {/* GPU availability */}
                  <div className="estimate-page__stat-row">
                    <dt className="estimate-page__stat-label">NVIDIA GPU</dt>
                    <dd
                      className="estimate-page__stat-value"
                      id="stat-gpu-name"
                      style={{
                        color: gpuInfo.available
                          ? "var(--color-success, #22c55e)"
                          : "var(--color-warn, #f59e0b)",
                      }}
                    >
                      {gpuInfo.available
                        ? gpuInfo.name ?? "Unknown"
                        : "Not detected — CPU only"}
                    </dd>
                  </div>

                  {/* Per-GPU stats when available */}
                  {gpuInfo.available && (
                    <>
                      <div className="estimate-page__stat-row">
                        <dt className="estimate-page__stat-label">VRAM Total</dt>
                        <dd className="estimate-page__stat-value" id="stat-vram-total">
                          {formatVram(gpuInfo.vram_total_mb ?? 0)}
                        </dd>
                      </div>

                      <div className="estimate-page__stat-row">
                        <dt className="estimate-page__stat-label">VRAM Free</dt>
                        <dd
                          className="estimate-page__stat-value"
                          id="stat-vram-free"
                          style={{
                            color: vramSufficient(gpuInfo, state.scan_depth)
                              ? undefined
                              : "var(--color-error, #ef4444)",
                          }}
                        >
                          {formatVram(gpuInfo.vram_free_mb ?? 0)}
                          {!vramSufficient(gpuInfo, state.scan_depth) &&
                            " ⚠ May be insufficient"}
                        </dd>
                      </div>

                      <div className="estimate-page__stat-row">
                        <dt className="estimate-page__stat-label">GPU Utilization</dt>
                        <dd className="estimate-page__stat-value" id="stat-gpu-util">
                          {gpuInfo.utilization_pct ?? 0}%
                          {(gpuInfo.utilization_pct ?? 0) > 80 && " ⚠ High load"}
                        </dd>
                      </div>

                      <div className="estimate-page__stat-row">
                        <dt className="estimate-page__stat-label">Driver</dt>
                        <dd className="estimate-page__stat-value" id="stat-gpu-driver">
                          {gpuInfo.driver_version ?? "unknown"}
                        </dd>
                      </div>
                    </>
                  )}

                  {/* Estimated probe-runner VRAM overhead */}
                  <div className="estimate-page__stat-row">
                    <dt className="estimate-page__stat-label">Est. VRAM Required</dt>
                    <dd className="estimate-page__stat-value" id="stat-vram-req">
                      {formatVram(VRAM_ESTIMATE_MB[state.scan_depth] ?? 512)}
                      <span
                        style={{ fontSize: "0.75em", opacity: 0.6, marginLeft: "6px" }}
                      >
                        (probe runner overhead)
                      </span>
                    </dd>
                  </div>

                  {/* CPU-only warning */}
                  {!gpuInfo.available && (
                    <div className="estimate-page__stat-row">
                      <dt className="estimate-page__stat-label">Acceleration</dt>
                      <dd
                        className="estimate-page__stat-value"
                        id="stat-acceleration"
                        style={{ color: "var(--color-warn, #f59e0b)" }}
                      >
                        CPU only — scanning will be slower
                      </dd>
                    </div>
                  )}
                </dl>
              )}

              {!gpuLoading && !gpuInfo && (
                <p style={{ fontSize: "0.85rem", opacity: 0.6 }}>
                  GPU information unavailable.
                </p>
              )}
            </section>

            {/* ── C. Per-Category Breakdown ── */}
            <section className="estimate-page__section">
              <h2 className="estimate-page__section-title">Category Breakdown</h2>
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
