/**
 * Sentryɸ — Provider Config Panel (W3.3)
 * components/deploy/ProviderConfigPanel.tsx
 *
 * Provider-specific deployment settings shown after OAuth sign-in.
 * Shows region, mode, instance type, endpoint scope, and budget alert.
 * Real-time cost estimate updates as settings change.
 */

import React, { useState, useEffect, useCallback } from "react";
import type { DeployProvider } from "../../services/deployIpcTypes";
import {
  AWS_REGIONS,
  AZURE_REGIONS,
  GCP_REGIONS,
  SAGEMAKER_INSTANCES,
  VERTEX_AI_ACCELERATORS,
  DEPLOY_MODES,
  type DeployMode,
  type CloudProvider,
  type CostEstimate,
} from "../../services/deployTypes";

// ─────────────────────────────────────────────
//  Cost calculator (client-side estimate)
// ─────────────────────────────────────────────

function estimateCost(
  provider: CloudProvider,
  mode: DeployMode,
  region: string
): Pick<CostEstimate, "monthly_min" | "monthly_max" | "monthly_mid"> {
  // Rough per-region cost multipliers
  const regionMul: Record<string, number> = {
    "us-east-1":       1.00, "eastus":       1.00, "us-central1":    1.00,
    "us-west-2":       1.00, "westus2":      0.98, "us-east1":       0.98,
    "eu-west-1":       1.10, "westeurope":   1.10, "europe-west1":   1.08,
    "eu-central-1":    1.12, "northeurope":  1.09, "europe-west4":   1.10,
    "ap-southeast-1":  1.08, "southeastasia":1.08, "asia-southeast1":1.06,
    "ap-northeast-1":  1.12, "australiaeast":1.15, "asia-east1":     1.09,
  };
  const mul = regionMul[region] ?? 1.10;

  const BASE: Record<string, [number, number]> = {
    bedrock:         [30,  120],
    sagemaker:       [60,  350],
    lambda:          [15,   80],
    ai_services:     [40,  180],
    container:       [55,  280],
    app_service:     [35,  160],
    vertex_ai:       [45,  240],
    cloud_run:       [20,  120],
    cloud_functions: [10,   60],
  };
  const [lo, hi] = BASE[mode] ?? [50, 200];
  const min = Math.round(lo * mul);
  const max = Math.round(hi * mul);
  return { monthly_min: min, monthly_max: max, monthly_mid: Math.round((min + max) / 2) };
}

// ─────────────────────────────────────────────
//  Cost display
// ─────────────────────────────────────────────

function CostEstimateDisplay({
  min, mid, max,
}: { min: number; mid: number; max: number }) {
  return (
    <div className="deploy-cfg__cost-card">
      <div className="deploy-cfg__cost-label">Real-time Cost Estimate</div>
      <div className="deploy-cfg__cost-range-row">
        <span className="deploy-cfg__cost-range-lo">${min}</span>
        <div className="deploy-cfg__cost-bar">
          <div
            className="deploy-cfg__cost-bar-fill"
            style={{ width: `${Math.min(100, (mid / (max || 1)) * 100)}%` }}
          />
        </div>
        <span className="deploy-cfg__cost-range-hi">${max}</span>
      </div>
      <div className="deploy-cfg__cost-mid">≈ ${mid} / month</div>
      <div className="deploy-cfg__cost-note">
        Estimate only. Actual costs depend on usage.
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Field components
// ─────────────────────────────────────────────

function SelectField({
  id, label, value, onChange, options,
}: {
  id:       string;
  label:    string;
  value:    string;
  onChange: (v: string) => void;
  options:  { value: string; label: string }[];
}) {
  return (
    <div className="deploy-cfg__field">
      <label className="deploy-cfg__label" htmlFor={id}>{label}</label>
      <select
        id={id}
        className="deploy-cfg__select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function TextInput({
  id, label, value, onChange, placeholder,
}: {
  id:          string;
  label:       string;
  value:       string;
  onChange:    (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="deploy-cfg__field">
      <label className="deploy-cfg__label" htmlFor={id}>{label}</label>
      <input
        id={id}
        className="deploy-cfg__input"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Main panel
// ─────────────────────────────────────────────

interface ProviderConfigPanelProps {
  provider:    DeployProvider;
  accountName: string;
  onSubmit:    (cfg: Record<string, string>) => void;
  onBack:      () => void;
}

export function ProviderConfigPanel({
  provider, accountName, onSubmit, onBack,
}: ProviderConfigPanelProps) {
  const regions =
    provider === "aws"   ? AWS_REGIONS :
    provider === "azure" ? AZURE_REGIONS :
    provider === "gcp"   ? GCP_REGIONS :
    [{ value: "self-hosted", label: "Self-Hosted" }];

  const modes =
    provider === "private"
      ? [
          { value: "docker_compose", label: "Docker Compose",  description: "Single-host container stack" },
          { value: "kubernetes",     label: "Kubernetes",      description: "Multi-node orchestration"    },
          { value: "bare_metal",     label: "Bare Metal",      description: "Direct system installation"  },
        ]
      : DEPLOY_MODES[provider as CloudProvider] ?? [];

  const [region, setRegion]       = useState(regions[0]?.value ?? "");
  const [mode,   setMode]         = useState(modes[0]?.value   ?? "");
  const [scope,  setScope]        = useState("private");
  const [instance, setInstance]   = useState(SAGEMAKER_INSTANCES[0]?.value ?? "");
  const [accel,    setAccel]      = useState(VERTEX_AI_ACCELERATORS[0]?.value ?? "");
  const [budget,   setBudget]     = useState("");
  const [projId,   setProjId]     = useState("");
  const [rg,       setRg]         = useState("");
  const [domain,   setDomain]     = useState("");

  const [cost, setCost] = useState(() =>
    provider !== "private"
      ? estimateCost(provider as CloudProvider, mode as DeployMode, region)
      : { monthly_min: 0, monthly_max: 0, monthly_mid: 0 }
  );

  // Recalculate cost whenever mode or region changes
  useEffect(() => {
    if (provider !== "private") {
      setCost(estimateCost(provider as CloudProvider, mode as DeployMode, region));
    }
  }, [provider, mode, region]);

  const handleSubmit = useCallback(() => {
    const cfg: Record<string, string> = {
      region,
      deployment_mode:  mode,
      endpoint_scope:   scope,
    };
    if (budget)   cfg.budget_alert_usd = budget;
    if (instance && provider === "aws" && mode === "sagemaker") cfg.instance_type = instance;
    if (accel    && provider === "gcp" && mode === "vertex_ai") cfg.accelerator   = accel;
    if (projId   && provider === "gcp")    cfg.gcp_project_id    = projId;
    if (rg       && provider === "azure")  cfg.azure_resource_group = rg;
    if (domain   && provider === "private") cfg.domain = domain;
    onSubmit(cfg);
  }, [region, mode, scope, budget, instance, accel, projId, rg, domain, provider, onSubmit]);

  const providerIcons: Record<DeployProvider, string> = {
    aws: "🟠", azure: "🔵", gcp: "🔴", private: "🖥️",
  };

  const selectedModeInfo = modes.find((m) => m.value === mode);

  return (
    <div className="deploy-cfg">
      {/* Account bar */}
      <div className="deploy-cfg__account-bar">
        <span className="deploy-cfg__account-icon">{providerIcons[provider]}</span>
        <span className="deploy-cfg__account-name">Signed in as {accountName}</span>
        <span className="deploy-cfg__account-check">✓</span>
      </div>

      <div className="deploy-cfg__layout">
        {/* Settings column */}
        <div className="deploy-cfg__settings">
          <h2 className="deploy-cfg__heading">Deployment Settings</h2>

          <SelectField
            id="cfg-region"
            label="Region"
            value={region}
            onChange={setRegion}
            options={regions}
          />

          <SelectField
            id="cfg-mode"
            label="Deployment Mode"
            value={mode}
            onChange={setMode}
            options={modes}
          />

          {selectedModeInfo && (
            <p className="deploy-cfg__mode-desc">{selectedModeInfo.description}</p>
          )}

          {/* SageMaker instance picker */}
          {provider === "aws" && mode === "sagemaker" && (
            <SelectField
              id="cfg-instance"
              label="Instance Type"
              value={instance}
              onChange={setInstance}
              options={SAGEMAKER_INSTANCES}
            />
          )}

          {/* Vertex AI accelerator picker */}
          {provider === "gcp" && mode === "vertex_ai" && (
            <SelectField
              id="cfg-accel"
              label="GPU Accelerator"
              value={accel}
              onChange={setAccel}
              options={VERTEX_AI_ACCELERATORS}
            />
          )}

          {/* Endpoint scope */}
          {provider !== "private" && (
            <SelectField
              id="cfg-scope"
              label="Endpoint Access"
              value={scope}
              onChange={setScope}
              options={[
                { value: "private", label: "Private (VPC/internal only)" },
                { value: "public",  label: "Public (internet-accessible)" },
              ]}
            />
          )}

          {scope === "public" && (
            <div className="deploy-cfg__warning">
              ⚠️ Public endpoints expose your model to the internet.
              Ensure authentication is configured before deploying.
            </div>
          )}

          {/* Azure resource group */}
          {provider === "azure" && (
            <TextInput
              id="cfg-rg"
              label="Resource Group (optional)"
              value={rg}
              onChange={setRg}
              placeholder="sentryphi-rg"
            />
          )}

          {/* GCP project ID */}
          {provider === "gcp" && (
            <TextInput
              id="cfg-proj"
              label="GCP Project ID"
              value={projId}
              onChange={setProjId}
              placeholder="my-project-id"
            />
          )}

          {/* Private: domain */}
          {provider === "private" && (
            <TextInput
              id="cfg-domain"
              label="Domain / Hostname"
              value={domain}
              onChange={setDomain}
              placeholder="api.yourcompany.com"
            />
          )}

          {/* Budget alert */}
          {provider !== "private" && (
            <div className="deploy-cfg__field">
              <label className="deploy-cfg__label" htmlFor="cfg-budget">
                Monthly Budget Alert (USD, optional)
              </label>
              <div className="deploy-cfg__input-prefix">
                <span className="deploy-cfg__prefix">$</span>
                <input
                  id="cfg-budget"
                  className="deploy-cfg__input deploy-cfg__input--prefixed"
                  type="number"
                  min="0"
                  step="10"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  placeholder="500"
                />
              </div>
            </div>
          )}
        </div>

        {/* Cost sidebar */}
        {provider !== "private" && (
          <div className="deploy-cfg__sidebar">
            <CostEstimateDisplay
              min={cost.monthly_min}
              mid={cost.monthly_mid}
              max={cost.monthly_max}
            />
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="deploy-cfg__actions">
        <button
          id="cfg-back"
          className="deploy-flow__btn deploy-flow__btn--ghost"
          onClick={onBack}
        >
          ← Back
        </button>
        <button
          id="cfg-generate-plan"
          className="deploy-flow__btn deploy-flow__btn--primary"
          onClick={handleSubmit}
        >
          Generate Deployment Plan →
        </button>
      </div>
    </div>
  );
}
