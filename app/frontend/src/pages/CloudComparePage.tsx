/**
 * Sentryɸ -- Cloud Compare (Screen 10)
 * pages/CloudComparePage.tsx
 *
 * Compares cloud deployment options derived from the Screen 9 configuration.
 * This is a PLANNING tool only — no cloud resources are created or provisioned.
 *
 * Data flow:
 *   Reads:  DeployContext.config  (from Screen 9)
 *           ReportContext.report  (for provenance display)
 *   Writes: Nothing — comparison is derived and display-only
 *
 * Pricing:
 *   All prices are ILLUSTRATIVE ESTIMATES with explicit labels.
 *   No live cloud pricing APIs are called. See compareTypes.ts.
 *
 * Navigation:
 *   Back:  → Screen 9 (Deploy Configuration)
 *   Next:  → Screen 11 (Deploy Execute) — disabled placeholder only
 */

import React, { useMemo, useCallback } from "react";
import { useDeployContext } from "../store/DeployContext";
import { useReportContext } from "../store/ReportContext";
import { PageHeader } from "../components/layout/PageHeader";
import { AlertBanner } from "../components/feedback/AlertBanner";
import {
  buildComparison,
  isComparisonStale,
  PRICING_SOURCE_METADATA,
  type CompareOption,
  type ComparisonResult,
  type CompatibilityStatus,
  type ProvisioningCapability,
} from "../services/compareTypes";

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface CloudComparePageProps {
  onBack:    () => void;
  onProceed: () => void; // routes to deploy-execute (disabled — placeholder)
}

// ─────────────────────────────────────────────
//  Sub-components
// ─────────────────────────────────────────────

const COMPAT_LABELS: Record<CompatibilityStatus, string> = {
  compatible:   "Compatible",
  incompatible: "Incompatible",
  unverified:   "Unverified",
  incomplete:   "Incomplete config",
};
const COMPAT_CLASSES: Record<CompatibilityStatus, string> = {
  compatible:   "compare-badge--compatible",
  incompatible: "compare-badge--incompatible",
  unverified:   "compare-badge--unverified",
  incomplete:   "compare-badge--incomplete",
};
const COMPAT_ICONS: Record<CompatibilityStatus, string> = {
  compatible:   "✓",
  incompatible: "✗",
  unverified:   "⚠",
  incomplete:   "○",
};

const PROV_LABELS: Record<ProvisioningCapability, string> = {
  "supported":  "Automated provisioning",
  "plan-only":  "Plan only — manual deployment",
  "unsupported":"Not supported",
};
const PROV_CLASSES: Record<ProvisioningCapability, string> = {
  "supported":  "compare-prov--supported",
  "plan-only":  "compare-prov--plan-only",
  "unsupported":"compare-prov--unsupported",
};

function CompatBadge({ status }: { status: CompatibilityStatus }) {
  return (
    <span className={`compare-badge ${COMPAT_CLASSES[status]}`} aria-label={COMPAT_LABELS[status]}>
      <span className="compare-badge__icon" aria-hidden="true">{COMPAT_ICONS[status]}</span>
      {COMPAT_LABELS[status]}
    </span>
  );
}

function ProvCapBadge({ cap }: { cap: ProvisioningCapability }) {
  return (
    <span className={`compare-prov ${PROV_CLASSES[cap]}`}>
      {PROV_LABELS[cap]}
    </span>
  );
}

function CostDisplay({ option }: { option: CompareOption }) {
  const { cost, costUnavailableReason } = option;

  if (!cost) {
    return (
      <div className="compare-cost compare-cost--unavailable">
        <span className="compare-cost__label">Cost estimate</span>
        <span className="compare-cost__value compare-cost__value--na">Unavailable</span>
        {costUnavailableReason && (
          <span className="compare-cost__note">{costUnavailableReason}</span>
        )}
      </div>
    );
  }

  const hasRange = cost.monthlyLow !== null && cost.monthlyHigh !== null;
  const isZeroPossible = cost.monthlyLow === 0;

  return (
    <div className="compare-cost">
      <span className="compare-cost__label">Illustrative monthly cost</span>
      <div className="compare-cost__value">
        {hasRange ? (
          <>
            <span className="compare-cost__amount">
              {isZeroPossible
                ? `$0 – $${cost.monthlyHigh?.toLocaleString()}`
                : `$${cost.monthlyLow?.toLocaleString()} – $${cost.monthlyHigh?.toLocaleString()}`}
            </span>
            <span className="compare-cost__currency">USD/mo</span>
          </>
        ) : (
          <span className="compare-cost__amount compare-cost__amount--token">
            Token-based — estimate requires request volume
          </span>
        )}
      </div>
      {cost.isPartial && cost.partialReason && (
        <span className="compare-cost__partial">⚠ Partial: {cost.partialReason}</span>
      )}
      <div className="compare-cost__disclaimer">
        ILLUSTRATIVE ONLY — not a provider quote. Actual costs may differ significantly.
      </div>
      {cost.assumptions.length > 0 && (
        <details className="compare-cost__assumptions">
          <summary className="compare-cost__assumptions-toggle">Cost assumptions</summary>
          <ul className="compare-cost__assumptions-list">
            {cost.assumptions.map((a) => (
              <li key={a.label}><strong>{a.label}:</strong> {a.value}</li>
            ))}
          </ul>
          {cost.excludedComponents.length > 0 && (
            <div className="compare-cost__exclusions">
              <strong>Excludes:</strong> {cost.excludedComponents.join(" · ")}
            </div>
          )}
        </details>
      )}
    </div>
  );
}

function OptionCard({
  option,
  isRecommended,
}: {
  option: CompareOption;
  isRecommended: boolean;
}) {
  const cardClass = [
    "compare-option",
    option.isSelectedConfig ? "compare-option--selected" : "",
    isRecommended ? "compare-option--recommended" : "",
    option.compatibility === "incompatible" ? "compare-option--incompatible" : "",
    option.provisioningCap === "plan-only" ? "compare-option--plan-only" : "",
  ].filter(Boolean).join(" ");

  return (
    <div className={cardClass} id={`compare-option-${option.id}`} role="article">
      {/* Card header */}
      <div className="compare-option__header">
        <div className="compare-option__title-row">
          <h3 className="compare-option__title">
            {option.label}
            {option.isSelectedConfig && (
              <span className="compare-option__selected-tag">Your selection</span>
            )}
          </h3>
          {isRecommended && (
            <span className="compare-option__rec-badge" aria-label="Recommended">
              ★ Recommended
            </span>
          )}
        </div>
        <div className="compare-option__badges">
          <ProvCapBadge cap={option.provisioningCap} />
          <CompatBadge status={option.compatibility} />
        </div>
        {option.compatibilityNote && (
          <p className="compare-option__compat-note">{option.compatibilityNote}</p>
        )}
      </div>

      {/* Divider */}
      <div className="compare-option__divider" />

      {/* Cost */}
      <div className="compare-option__section">
        <CostDisplay option={option} />
      </div>

      {/* Capabilities */}
      <div className="compare-option__section">
        <div className="compare-option__section-title">Capabilities</div>
        <ul className="compare-option__list compare-option__list--caps">
          {option.capabilities.map((cap) => (
            <li key={cap}>{cap}</li>
          ))}
        </ul>
      </div>

      {/* Limitations */}
      <div className="compare-option__section">
        <div className="compare-option__section-title">Limitations</div>
        <ul className="compare-option__list compare-option__list--limits">
          {option.limitations.map((lim) => (
            <li key={lim}>{lim}</li>
          ))}
        </ul>
      </div>

      {/* Warnings */}
      {option.warnings.length > 0 && (
        <div className="compare-option__warnings" role="alert">
          {option.warnings.map((w) => (
            <div key={w} className="compare-option__warning-item">⚠ {w}</div>
          ))}
        </div>
      )}

      {/* Plan-only notice */}
      {option.provisioningCap === "plan-only" && (
        <div className="compare-option__plan-notice" role="note">
          This provider cannot be provisioned automatically by Sentryɸ v1.
          Export the deployment plan and use the provider's console or CLI.
        </div>
      )}
    </div>
  );
}

function RecommendationPanel({ result }: { result: ComparisonResult }) {
  return (
    <div
      className={`compare-recommendation ${result.recommendedId ? "compare-recommendation--active" : "compare-recommendation--withheld"}`}
      id="compare-recommendation"
      role="note"
    >
      <div className="compare-recommendation__title">
        {result.recommendedId ? "★ Recommendation" : "No recommendation"}
      </div>
      <div className="compare-recommendation__rationale">
        {result.recommendationRationale}
      </div>
      {result.recommendedId && (
        <div className="compare-recommendation__disclaimer">
          Recommendation is based on configuration compatibility only — not on live pricing or provider availability.
          Verify costs and quotas independently before provisioning.
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Main page
// ─────────────────────────────────────────────

export function CloudComparePage({ onBack, onProceed }: CloudComparePageProps) {
  const { state: deployState }  = useDeployContext();
  const { state: reportState }  = useReportContext();

  const { config } = deployState;
  const report     = reportState.report;
  const isSimulated = report ? report.meta.scan_id.startsWith("sim-") : false;

  // Build comparison — recomputed when config changes (pure function)
  const comparison = useMemo<ComparisonResult>(() => {
    return buildComparison(config);
  }, [config]);

  // Stale guard — if config changed after comparison was built (shouldn't happen with useMemo,
  // but guards against future refactors)
  const isStale = isComparisonStale(comparison, config);

  const selectedOption = comparison.options.find((o) => o.isSelectedConfig) ?? null;
  const hasSelection   = config.provider !== null;
  const configIncomplete = !config.provider || !config.modelId || !config.region;

  // Pricing source for display
  const pricingSource = useMemo(() => {
    if (config.provider !== "aws" || !config.mode) return null;
    return PRICING_SOURCE_METADATA[config.mode as keyof typeof PRICING_SOURCE_METADATA] ?? null;
  }, [config.provider, config.mode]);

  const handleBack = useCallback(() => onBack(), [onBack]);

  // Screen 11 is not yet implemented — the button is shown but disabled
  const canProceedToExecute = selectedOption?.compatibility === "compatible"
    && selectedOption?.provisioningCap === "supported"
    && !configIncomplete;

  return (
    <div className="compare-page" id="compare-page">

      {/* Header */}
      <PageHeader
        title="Cloud Compare"
        subtitle={
          report
            ? `Based on assessment: ${report.meta.target}`
            : "No assessment loaded"
        }
        onBack={handleBack}
      />

      {/* No-provision notice */}
      <AlertBanner
        type="info"
        message="This comparison does not deploy cloud resources. No infrastructure is provisioned until you review and confirm on the execution screen."
      />

      {/* Simulated assessment warning */}
      {isSimulated && (
        <AlertBanner
          type="info"
          message="This comparison is based on a simulated assessment. Treat deployment recommendations as illustrative only."
        />
      )}

      {/* Missing config warning */}
      {configIncomplete && (
        <div className="compare-incomplete-banner" role="alert" id="compare-incomplete-banner">
          <div className="compare-incomplete-banner__icon">⚠</div>
          <div className="compare-incomplete-banner__body">
            <strong>Incomplete configuration</strong>
            <p>
              Provider{!config.provider ? " (missing)" : ""},
              model ID{!config.modelId ? " (missing)" : ""},
              and region{!config.region ? " (missing)" : ""} are required for a complete comparison.
              Return to Screen 9 to complete your configuration.
            </p>
            <button
              type="button"
              className="button button--secondary compare-incomplete-banner__btn"
              onClick={handleBack}
              id="compare-back-to-config-btn"
            >
              ← Configure Deployment
            </button>
          </div>
        </div>
      )}

      {/* Stale comparison warning (defensive) */}
      {isStale && (
        <AlertBanner
          type="error"
          message="Comparison data may be out of date. Return to Screen 9 and re-enter to refresh."
        />
      )}

      {/* ── Config summary strip ── */}
      <section className="compare-config-strip" id="compare-config-strip">
        <div className="compare-config-strip__title">Configuration being compared</div>
        <div className="compare-config-strip__items">
          <div className="compare-config-strip__item">
            <span className="compare-config-strip__label">Provider</span>
            <span className="compare-config-strip__value">
              {config.provider?.toUpperCase() ?? "—"}
            </span>
          </div>
          {config.mode && (
            <div className="compare-config-strip__item">
              <span className="compare-config-strip__label">Mode</span>
              <span className="compare-config-strip__value">{config.mode}</span>
            </div>
          )}
          <div className="compare-config-strip__item">
            <span className="compare-config-strip__label">Region</span>
            <span className="compare-config-strip__value">{config.region ?? "—"}</span>
          </div>
          <div className="compare-config-strip__item">
            <span className="compare-config-strip__label">Model ID</span>
            <span className="compare-config-strip__value compare-config-strip__value--mono">
              {config.modelId || "—"}
            </span>
          </div>
          {config.instanceType && (
            <div className="compare-config-strip__item">
              <span className="compare-config-strip__label">Instance</span>
              <span className="compare-config-strip__value">
                {config.instanceType} × {config.replicas}
              </span>
            </div>
          )}
          <div className="compare-config-strip__item">
            <span className="compare-config-strip__label">Scope</span>
            <span className="compare-config-strip__value">
              {config.endpointScope === "public" ? "⚠ Public" : "Private"}
            </span>
          </div>
        </div>
      </section>

      {/* ── Recommendation panel ── */}
      <RecommendationPanel result={comparison} />

      {/* ── Comparison options ── */}
      <section className="compare-options-section" id="compare-options-section">
        <div className="compare-options-section__header">
          <h2 className="compare-options-section__title">
            {hasSelection ? "Available options" : "All cloud options"}
          </h2>
          <p className="compare-options-section__note">
            {hasSelection
              ? "Your selected configuration is highlighted. Other options shown for reference."
              : "Select a provider on Screen 9 to see a focused comparison."}
          </p>
        </div>

        <div className="compare-options-grid" id="compare-options-grid">
          {comparison.options.map((option) => (
            <OptionCard
              key={option.id}
              option={option}
              isRecommended={option.id === comparison.recommendedId}
            />
          ))}
        </div>
      </section>

      {/* ── Pricing disclaimer ── */}
      <section className="compare-pricing-disclaimer" id="compare-pricing-disclaimer" role="note">
        <div className="compare-pricing-disclaimer__title">⚠ Pricing Disclaimer</div>
        <div className="compare-pricing-disclaimer__body">
          <p>
            All cost estimates shown are <strong>illustrative only</strong>. They are based on
            static pricing data recorded at the dates shown and are provided for planning purposes
            only. They are <strong>not provider quotes</strong> and may differ significantly from
            actual charges.
          </p>
          <p>
            Actual costs depend on: request volume, model characteristics, data transfer,
            storage, region, reserved capacity, support plan, and other factors not captured here.
          </p>
          {pricingSource && (
            <p>
              Pricing reference: <a
                href={pricingSource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="compare-pricing-disclaimer__link"
              >
                {pricingSource.label}
              </a> — data as of {pricingSource.asOf}. {pricingSource.note}
            </p>
          )}
          <p>
            Verify current pricing on the provider's official pricing page before making
            procurement decisions.
          </p>
        </div>
      </section>

      {/* ── Actions ── */}
      <div className="compare-page__actions" id="compare-page-actions">
        <button
          type="button"
          className="button button--secondary"
          onClick={handleBack}
          id="compare-back-btn"
        >
          ← Back to Configuration
        </button>

        <div className="compare-page__actions-right">
          {/* Screen 11 is not yet implemented */}
          <button
            type="button"
            className="button button--primary"
            disabled
            id="compare-proceed-btn"
            title="Deploy Execution (Screen 11) is not yet implemented in this version"
            aria-disabled="true"
          >
            Proceed to Deploy Execution
            <span className="compare-page__coming-soon"> — Coming soon</span>
          </button>
        </div>
      </div>
    </div>
  );
}
