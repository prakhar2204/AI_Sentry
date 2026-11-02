/**
 * Sentryɸ — Provider Selection Screen (W3.1)
 * components/deploy/ProviderSelectScreen.tsx
 *
 * Shown after scan results. Displays:
 *  1. AI-recommended provider card (from W1.3 recommendation engine)
 *  2. Four provider cards (AWS / Azure / GCP / Private) with estimated costs
 *  3. Full cost comparison table across all providers
 *  4. Security feature comparison grid
 */

import React, { useState } from "react";
import type { DeploymentRecommendation } from "../../services/deployTypes";
import { PROVIDER_COMPARISON_FEATURES } from "../../services/deployTypes";
import type { DeployProvider } from "../../services/deployIpcTypes";
import { PROVIDER_INFO } from "../../services/deployIpcTypes";

// ─────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────

const RISK_COLORS: Record<string, string> = {
  low:      "#10b981",
  medium:   "#f59e0b",
  high:     "#ef4444",
  critical: "#dc2626",
};

function RiskBadge({ level }: { level: string }) {
  return (
    <span
      className="risk-badge"
      style={{ background: `${RISK_COLORS[level] ?? "#94a3b8"}22`, color: RISK_COLORS[level] ?? "#94a3b8" }}
    >
      {level.toUpperCase()}
    </span>
  );
}

// ─────────────────────────────────────────────
//  Recommendation Card (W1.3 output)
// ─────────────────────────────────────────────

function RecommendationCard({ rec }: { rec: DeploymentRecommendation }) {
  const [expanded, setExpanded] = useState(false);
  const pInfo = PROVIDER_INFO[rec.recommended_provider as DeployProvider];

  return (
    <div className="deploy-rec-card">
      <div className="deploy-rec-card__header">
        <div className="deploy-rec-card__title-row">
          <span className="deploy-rec-card__ai-badge">🤖 AI Recommended</span>
          <RiskBadge level={rec.risk_level} />
        </div>
        <div className="deploy-rec-card__provider">
          <span className="deploy-rec-card__provider-icon">
            {pInfo?.icon ?? "🖥️"}
          </span>
          <div>
            <div className="deploy-rec-card__provider-name">
              {pInfo?.name ?? rec.recommended_provider.toUpperCase()}
            </div>
            <div className="deploy-rec-card__provider-mode">
              {rec.recommended_mode.replace(/_/g, " ")} · {rec.recommended_region}
            </div>
          </div>
        </div>
      </div>

      <p className="deploy-rec-card__rationale">{rec.rationale}</p>

      <div className="deploy-rec-card__cost">
        <span>Est. monthly cost</span>
        <span className="deploy-rec-card__cost-range">
          ${rec.estimated_cost.low_usd} – ${rec.estimated_cost.high_usd}
        </span>
      </div>

      {rec.security_warnings.length > 0 && (
        <button
          className="deploy-rec-card__toggle"
          onClick={() => setExpanded((e) => !e)}
        >
          {expanded ? "▲ Hide" : "▼ Show"} {rec.security_warnings.length} security notice(s)
        </button>
      )}

      {expanded && (
        <ul className="deploy-rec-card__warnings">
          {rec.security_warnings.map((w, i) => (
            <li key={i}>⚠️ {w}</li>
          ))}
        </ul>
      )}

      {rec.compliance_notes.length > 0 && (
        <div className="deploy-rec-card__compliance">
          {rec.compliance_notes.map((n, i) => (
            <span key={i} className="deploy-rec-card__compliance-tag">{n}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Provider Card
// ─────────────────────────────────────────────

interface ProviderCardProps {
  provider:    DeployProvider;
  costLow?:    number;
  costHigh?:   number;
  isRecommended?: boolean;
  onSelect:    (p: DeployProvider) => void;
}

function ProviderCard({ provider, costLow, costHigh, isRecommended, onSelect }: ProviderCardProps) {
  const info = PROVIDER_INFO[provider];

  return (
    <div
      className={[
        "deploy-ps-card",
        isRecommended ? "deploy-ps-card--recommended" : "",
      ].join(" ").trim()}
      role="button"
      tabIndex={0}
      id={`provider-card-${provider}`}
      onClick={() => onSelect(provider)}
      onKeyDown={(e) => e.key === "Enter" && onSelect(provider)}
    >
      {isRecommended && (
        <div className="deploy-ps-card__rec-banner">✓ Recommended</div>
      )}
      <div className="deploy-ps-card__icon">{info.icon}</div>
      <div className="deploy-ps-card__name">{info.name}</div>
      <div className="deploy-ps-card__desc">{info.description}</div>

      {costLow !== undefined && costHigh !== undefined && (
        <div className="deploy-ps-card__cost">
          <span className="deploy-ps-card__cost-label">Est. monthly</span>
          <span className="deploy-ps-card__cost-value">
            ${costLow}–${costHigh}
          </span>
        </div>
      )}

      {provider === "private" && (
        <div className="deploy-ps-card__cost">
          <span className="deploy-ps-card__cost-label">Infrastructure cost</span>
          <span className="deploy-ps-card__cost-value">Your own</span>
        </div>
      )}

      <div className="deploy-ps-card__cta">
        {provider === "private" ? "Export Config →" : `Sign in to ${info.name.split(" ")[0]} →`}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Cost Comparison Table
// ─────────────────────────────────────────────

interface CostRow {
  label:    string;
  aws:      string;
  azure:    string;
  gcp:      string;
}

function CostComparisonTable({ rows }: { rows: CostRow[] }) {
  return (
    <div className="deploy-compare-table">
      <div className="deploy-compare-table__header">
        <div className="deploy-compare-table__header-cell" />
        <div className="deploy-compare-table__header-cell">
          <span>🟠</span> AWS
        </div>
        <div className="deploy-compare-table__header-cell">
          <span>🔵</span> Azure
        </div>
        <div className="deploy-compare-table__header-cell">
          <span>🔴</span> GCP
        </div>
      </div>
      {rows.map((row, i) => (
        <div key={i} className="deploy-compare-table__row">
          <div className="deploy-compare-table__label">{row.label}</div>
          <div className="deploy-compare-table__cell">{row.aws}</div>
          <div className="deploy-compare-table__cell">{row.azure}</div>
          <div className="deploy-compare-table__cell">{row.gcp}</div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Feature Comparison Grid
// ─────────────────────────────────────────────

function FeatureCell({ value }: { value: boolean | string }) {
  if (value === true)  return <span className="deploy-feature__yes">✓</span>;
  if (value === false) return <span className="deploy-feature__no">✗</span>;
  return <span className="deploy-feature__partial">{value}</span>;
}

function FeatureComparisonGrid() {
  return (
    <div className="deploy-feature-grid">
      <div className="deploy-feature-grid__header">
        <div />
        <div>AWS</div>
        <div>Azure</div>
        <div>GCP</div>
      </div>
      {PROVIDER_COMPARISON_FEATURES.map((f, i) => (
        <div key={i} className="deploy-feature-grid__row">
          <div className="deploy-feature-grid__name">{f.name}</div>
          <FeatureCell value={f.aws}   />
          <FeatureCell value={f.azure} />
          <FeatureCell value={f.gcp}   />
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Main component
// ─────────────────────────────────────────────

interface ProviderSelectScreenProps {
  recommendation?: DeploymentRecommendation | null;
  onSelectProvider: (provider: DeployProvider) => void;
}

// Default cost estimates when no recommendation available
const DEFAULT_COSTS: Record<DeployProvider, [number, number]> = {
  aws:     [45,  280],
  azure:   [55,  310],
  gcp:     [40,  260],
  private: [0,   0  ],
};

const DEFAULT_COST_ROWS: CostRow[] = [
  { label: "Compute (p50)",      aws: "$0.13/hr",  azure: "$0.19/hr", gcp: "$0.11/hr"  },
  { label: "Storage (100 GB)",   aws: "$2.30/mo",  azure: "$1.92/mo", gcp: "$2.00/mo"  },
  { label: "API calls (1M req)", aws: "$0.35",     azure: "$0.40",    gcp: "$0.30"     },
  { label: "Egress (10 GB)",     aws: "$0.90",     azure: "$0.87",    gcp: "$0.85"     },
  { label: "Min monthly total",  aws: "~$45",      azure: "~$55",     gcp: "~$40"      },
  { label: "Free tier",          aws: "12 months", azure: "$200 trial",gcp: "$300 trial"},
];

export function ProviderSelectScreen({ recommendation, onSelectProvider }: ProviderSelectScreenProps) {
  const [activeTab, setActiveTab] = useState<"providers" | "cost" | "features">("providers");
  const providers: DeployProvider[] = ["aws", "azure", "gcp", "private"];
  const recProvider = recommendation?.recommended_provider as DeployProvider | undefined;

  return (
    <div className="deploy-ps">
      {/* Header */}
      <div className="deploy-ps__header">
        <h1 className="deploy-ps__title">Deploy Your AI Model</h1>
        <p className="deploy-ps__subtitle">
          Choose where to deploy. Sentryɸ will guide you through secure
          sign-in and apply your scan-based security recommendations automatically.
        </p>
      </div>

      {/* Recommendation card */}
      {recommendation && (
        <RecommendationCard rec={recommendation} />
      )}

      {/* Tab nav */}
      <div className="deploy-ps__tabs" role="tablist">
        {(["providers", "cost", "features"] as const).map((tab) => (
          <button
            key={tab}
            id={`deploy-tab-${tab}`}
            className={`deploy-ps__tab ${activeTab === tab ? "deploy-ps__tab--active" : ""}`}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
          >
            {tab === "providers" ? "☁️ Select Provider"
            : tab === "cost"    ? "💰 Cost Comparison"
            :                     "🔒 Feature Comparison"}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      {activeTab === "providers" && (
        <div className="deploy-ps__provider-grid" role="tabpanel">
          {providers.map((p) => (
            <ProviderCard
              key={p}
              provider={p}
              costLow={p !== "private" ? DEFAULT_COSTS[p][0] : undefined}
              costHigh={p !== "private" ? DEFAULT_COSTS[p][1] : undefined}
              isRecommended={recProvider === p}
              onSelect={onSelectProvider}
            />
          ))}
        </div>
      )}

      {activeTab === "cost" && (
        <div role="tabpanel">
          <p className="deploy-ps__tab-note">
            Estimated costs based on a typical LLM inference deployment (8 vCPU, 32 GB RAM).
            Actual costs depend on your usage patterns and configuration.
          </p>
          <CostComparisonTable rows={DEFAULT_COST_ROWS} />
        </div>
      )}

      {activeTab === "features" && (
        <div role="tabpanel">
          <p className="deploy-ps__tab-note">
            Security and compliance features available on each provider for AI model hosting.
          </p>
          <FeatureComparisonGrid />
        </div>
      )}
    </div>
  );
}
