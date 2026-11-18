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
  initialRegion?: string;
  initialConfig?: Record<string, string>;
  onSubmit:    (cfg: Record<string, string>) => void;
  onBack:      () => void;
}

export function ProviderConfigPanel({
  provider, accountName, initialRegion, initialConfig = {}, onSubmit, onBack,
}: ProviderConfigPanelProps) {
  const defaultRegions =
    provider === "aws"   ? AWS_REGIONS :
    provider === "azure" ? AZURE_REGIONS :
    provider === "gcp"   ? GCP_REGIONS :
    [{ value: "self-hosted", label: "Self-Hosted" }];
  const regions = initialRegion && !defaultRegions.some(option => option.value === initialRegion)
    ? [...defaultRegions, { value: initialRegion, label: initialRegion }]
    : defaultRegions;

  const modes =
    provider === "private"
      ? [
          { value: "docker_compose", label: "Docker Compose",  description: "Single-host container stack" },
          { value: "kubernetes",     label: "Kubernetes",      description: "Multi-node orchestration"    },
          { value: "bare_metal",     label: "Bare Metal",      description: "Direct system installation"  },
        ]
      : DEPLOY_MODES[provider as CloudProvider] ?? [];

  const [region, setRegion]       = useState(initialRegion || regions[0]?.value || "");
  const [mode,   setMode]         = useState(initialConfig.deployment_mode || modes[0]?.value || "");
  const [scope,  setScope]        = useState(initialConfig.endpoint_scope || "private");
  const [instance, setInstance]   = useState(initialConfig.instance_type || SAGEMAKER_INSTANCES[0]?.value || "");
  const [accel,    setAccel]      = useState(VERTEX_AI_ACCELERATORS[0]?.value ?? "");
  const [budget,   setBudget]     = useState("");
  const [projId,   setProjId]     = useState("");
  const [rg,       setRg]         = useState("");
  const [domain,   setDomain]     = useState("");
  const [role, setRole] = useState(initialConfig.execution_role_arn || "");
  const [image, setImage] = useState(initialConfig.container_image || "");
  const [modelData, setModelData] = useState(initialConfig.model_data_url || "");
  const [modelId, setModelId] = useState(initialConfig.model_id || "");

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
    if (provider === "private") cfg.stack = mode;
    if (provider === "aws") {
      cfg.execution_role_arn = role;
      if (mode === "bedrock") cfg.model_id = modelId;
      else cfg.container_image = image;
      if (mode === "sagemaker") cfg.model_data_url = modelData;
    }
    onSubmit(cfg);
  }, [region, mode, scope, budget, instance, accel, projId, rg, domain, provider, onSubmit, role, image, modelData, modelId]);

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
          {provider === "aws" && <>
            <TextInput id="cfg-execution-role" label="Existing execution role ARN" value={role} onChange={setRole}
              placeholder="arn:aws:iam::123456789012:role/InferenceRole" />
            <p>The role must trust the selected service and grant model/artifact access. The signed-in identity needs permission to pass this role.</p>
            {mode === "bedrock"
              ? <TextInput id="cfg-model-id" label="Bedrock model / inference profile ID" value={modelId} onChange={setModelId} />
              : <TextInput id="cfg-image" label="Inference container image (ECR URI)" value={image} onChange={setImage} />}
            {mode === "sagemaker" && <TextInput id="cfg-model-data" label="Model artifact (S3 URL)" value={modelData} onChange={setModelData}
              placeholder="s3://your-bucket/model.tar.gz" />}
          </>}
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
              {provider === "aws" ? "AWS requests require IAM authentication (SigV4)." : "Ensure authentication is configured before deploying."}
            </div>
          )}
          {provider === "aws" && scope === "private" && <p role="status">
            AWS private networking is not implemented yet. To proceed, explicitly select the IAM-authenticated public endpoint, or choose Private / Self-Hosted.
          </p>}

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
          {provider !== "private" && provider !== "aws" && (
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
        {provider !== "private" && provider !== "aws" && (
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
