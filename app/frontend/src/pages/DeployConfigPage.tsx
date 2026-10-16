/**
 * Sentryɸ -- Deploy Configuration (Screen 9)
 * pages/DeployConfigPage.tsx
 *
 * Lets the user configure a proposed cloud deployment plan based on
 * their assessment results. Does NOT provision any cloud resources.
 *
 * Navigation:
 *   Entry: from Screen 8 (Export) via hub branch from Screen 6 (Results)
 *   Back:  → Screen 8 (Export)
 *   Next:  → Screen 10 (Cloud Compare) — only when config is valid
 *
 * Architecture:
 *   - Reads report provenance from ReportContext
 *   - Writes deploy config to DeployContext (separate — report is never mutated)
 *   - No credentials collected, stored, or displayed
 *   - No cloud API calls made
 *   - Deployed = false for the entire lifecycle of this screen
 *
 * Provider support (D-022):
 *   AWS   — full configuration + provisioning automation (Screens 10-11)
 *   Azure — configuration plan only (no automated provisioning in v1)
 *   GCP   — configuration plan only (no automated provisioning in v1)
 */

import React, { useCallback, useId } from "react";
import { useReportContext } from "../store/ReportContext";
import { useDeployContext } from "../store/DeployContext";
import { DEPLOY_ACTIONS } from "../store/actions";
import { PageHeader } from "../components/layout/PageHeader";
import { AlertBanner } from "../components/feedback/AlertBanner";
import {
  DeployConfig,
  AWS_REGIONS,
  AWS_DEPLOYMENT_MODES,
  SAGEMAKER_INSTANCE_TYPES,
  CloudProvider,
  AwsDeploymentMode,
  FieldValidation,
  ValidationStatus,
} from "../services/deployTypes";

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface DeployConfigPageProps {
  onBack:    () => void;
  onProceed: () => void;
}

// ─────────────────────────────────────────────
//  Sub-components — validation indicator
// ─────────────────────────────────────────────

const STATUS_ICONS: Record<ValidationStatus, string> = {
  valid:      "✓",
  invalid:    "✗",
  unverified: "⚠",
  incomplete: "○",
};
const STATUS_CLASSES: Record<ValidationStatus, string> = {
  valid:      "deploy-field--valid",
  invalid:    "deploy-field--invalid",
  unverified: "deploy-field--unverified",
  incomplete: "deploy-field--incomplete",
};

function FieldHint({ v }: { v: FieldValidation }) {
  if (!v.message) return null;
  return (
    <div className={`deploy-field__hint deploy-field__hint--${v.status}`} role="alert">
      <span className="deploy-field__hint-icon" aria-hidden="true">
        {STATUS_ICONS[v.status]}
      </span>
      {v.message}
    </div>
  );
}

function ValidationBadge({ v }: { v: FieldValidation }) {
  if (v.status === "valid") return null;
  return (
    <span
      className={`deploy-validation-badge deploy-validation-badge--${v.status}`}
      title={v.message ?? v.status}
      aria-label={`${v.status}: ${v.message ?? ""}`}
    >
      {STATUS_ICONS[v.status]}
    </span>
  );
}

// ─────────────────────────────────────────────
//  Provider selector
// ─────────────────────────────────────────────

interface ProviderCardProps {
  id:        CloudProvider;
  label:     string;
  badge?:    string;
  disabled?: boolean;
  selected:  boolean;
  onClick:   () => void;
}

function ProviderCard({ id, label, badge, disabled, selected, onClick }: ProviderCardProps) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      aria-disabled={disabled}
      onClick={disabled ? undefined : onClick}
      className={[
        "deploy-provider-card",
        selected  ? "deploy-provider-card--selected"  : "",
        disabled  ? "deploy-provider-card--disabled"  : "",
      ].filter(Boolean).join(" ")}
      id={`deploy-provider-${id}`}
    >
      <span className="deploy-provider-card__name">{label}</span>
      {badge && (
        <span className={`deploy-provider-card__badge deploy-provider-card__badge--${badge.toLowerCase().replace(/\s+/g, "-")}`}>
          {badge}
        </span>
      )}
    </button>
  );
}

// ─────────────────────────────────────────────
//  Section wrapper
// ─────────────────────────────────────────────

function Section({
  title, children, note,
}: {
  title: string;
  children: React.ReactNode;
  note?: string;
}) {
  return (
    <section className="deploy-section">
      <div className="deploy-section__header">
        <h2 className="deploy-section__title">{title}</h2>
        {note && <p className="deploy-section__note">{note}</p>}
      </div>
      <div className="deploy-section__body">{children}</div>
    </section>
  );
}

// ─────────────────────────────────────────────
//  Form row
// ─────────────────────────────────────────────

function FormRow({
  label, htmlFor, required, validation, children,
}: {
  label:      string;
  htmlFor:    string;
  required?:  boolean;
  validation?: FieldValidation;
  children:   React.ReactNode;
}) {
  return (
    <div className={`deploy-form-row ${validation ? STATUS_CLASSES[validation.status] : ""}`}>
      <label className="deploy-form-row__label" htmlFor={htmlFor}>
        {label}
        {required && <span className="deploy-form-row__required" aria-hidden="true"> *</span>}
        {validation && <ValidationBadge v={validation} />}
      </label>
      <div className="deploy-form-row__input">{children}</div>
      {validation && <FieldHint v={validation} />}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Main page
// ─────────────────────────────────────────────

export function DeployConfigPage({ onBack, onProceed }: DeployConfigPageProps) {
  const { state: reportState }             = useReportContext();
  const { state: deployState, dispatch }   = useDeployContext();
  const { config, validation }             = deployState;

  const idPrefix = useId();
  const id = (name: string) => `${idPrefix}-${name}`;

  const report    = reportState.report;
  const isSimulated = report ? report.meta.scan_id.startsWith("sim-") : false;

  // Dispatch helpers
  const setProvider = useCallback((provider: CloudProvider | null) => {
    dispatch({ type: DEPLOY_ACTIONS.SET_PROVIDER, payload: { provider } });
  }, [dispatch]);

  const setRegion = useCallback((region: string | null) => {
    dispatch({ type: DEPLOY_ACTIONS.SET_REGION, payload: { region } });
  }, [dispatch]);

  const patchConfig = useCallback((patch: Partial<DeployConfig>) => {
    dispatch({ type: DEPLOY_ACTIONS.SET_CONFIG, payload: patch });
  }, [dispatch]);

  const isAws = config.provider === "aws";

  // ── Render ──
  return (
    <div className="deploy-config-page" id="deploy-config-page">

      {/* Header */}
      <PageHeader
        title="Deploy Configuration"
        subtitle={report ? `Assessment: ${report.meta.target}` : "No assessment loaded"}
        onBack={onBack}
      />

      {/* No-provision notice */}
      <AlertBanner
        type="info"
        message="Configuring a deployment plan does not create cloud resources. No infrastructure will be provisioned until you review and confirm on the execution screen."
      />

      {/* Simulation warning */}
      {isSimulated && (
        <AlertBanner
          type="info"
          message="This assessment was generated in simulation mode. Any deployment plan based on it should be treated as illustrative only — not as a validated security clearance for production."
        />
      )}

      {/* No report */}
      {!report && (
        <AlertBanner
          type="error"
          message="No assessment report is loaded. Return to Results to load a scan report before configuring a deployment."
        />
      )}

      {/* ── A. Provider selection ── */}
      <Section
        title="A. Cloud Provider"
        note="AWS is supported for automated provisioning. Azure and GCP offer configuration planning only in this version."
      >
        <div
          className="deploy-provider-grid"
          role="radiogroup"
          aria-label="Cloud provider"
          id={id("provider-group")}
        >
          <ProviderCard
            id="aws"
            label="Amazon Web Services"
            badge="Full support"
            selected={config.provider === "aws"}
            onClick={() => setProvider("aws")}
          />
          <ProviderCard
            id="azure"
            label="Microsoft Azure"
            badge="Plan only"
            selected={config.provider === "azure"}
            onClick={() => setProvider("azure")}
          />
          <ProviderCard
            id="gcp"
            label="Google Cloud"
            badge="Plan only"
            selected={config.provider === "gcp"}
            onClick={() => setProvider("gcp")}
          />
        </div>
        <FieldHint v={validation.provider} />

        {(config.provider === "azure" || config.provider === "gcp") && (
          <div className="deploy-info-box" role="note">
            <strong>{config.provider === "azure" ? "Azure" : "Google Cloud"} — Configuration Plan Mode</strong>
            <p>
              Automated provisioning for {config.provider === "azure" ? "Azure" : "GCP"} is not available in this version.
              You can still configure and export a deployment plan for manual execution.
              Automated provisioning is planned for a future release.
            </p>
          </div>
        )}
      </Section>

      {/* ── B. Deployment mode (AWS only) ── */}
      {isAws && (
        <Section
          title="B. Deployment Mode"
          note="Select how the model will be served on AWS."
        >
          <div
            className="deploy-mode-grid"
            role="radiogroup"
            aria-label="AWS deployment mode"
            id={id("mode-group")}
          >
            {AWS_DEPLOYMENT_MODES.map((m) => (
              <button
                key={m.id}
                type="button"
                role="radio"
                aria-checked={config.mode === m.id}
                className={`deploy-mode-card${config.mode === m.id ? " deploy-mode-card--selected" : ""}`}
                onClick={() => patchConfig({ mode: m.id as AwsDeploymentMode })}
                id={`deploy-mode-${m.id}`}
              >
                <div className="deploy-mode-card__label">{m.label}</div>
                <div className="deploy-mode-card__desc">{m.description}</div>
                {m.supportsGpu && (
                  <span className="deploy-mode-card__gpu-tag">GPU supported</span>
                )}
              </button>
            ))}
          </div>
          <FieldHint v={validation.mode} />
        </Section>
      )}

      {/* ── C. Model / workload ── */}
      {config.provider && (
        <Section
          title="C. Model / Workload"
          note="Enter the model identifier for your deployment. This is not automatically derived from the scanned target."
        >
          <FormRow
            label="Model Identifier"
            htmlFor={id("model-id")}
            required
            validation={validation.modelId}
          >
            <input
              id={id("model-id")}
              type="text"
              className="deploy-input"
              placeholder={
                config.provider === "aws" && config.mode === "bedrock"
                  ? "e.g. anthropic.claude-3-sonnet-20240229-v1:0"
                  : config.provider === "aws" && config.mode === "sagemaker"
                  ? "e.g. huggingface-llm-mistral-7b-instruct"
                  : "e.g. gpt-4o-mini"
              }
              value={config.modelId}
              onChange={(e) => patchConfig({ modelId: e.target.value })}
              autoComplete="off"
              spellCheck={false}
            />
          </FormRow>
          <FormRow
            label="Model Label (display name)"
            htmlFor={id("model-label")}
          >
            <input
              id={id("model-label")}
              type="text"
              className="deploy-input"
              placeholder="e.g. Claude 3 Sonnet"
              value={config.modelLabel}
              onChange={(e) => patchConfig({ modelLabel: e.target.value })}
            />
          </FormRow>

          {/* Scanned target notice */}
          {report && (
            <div className="deploy-info-box deploy-info-box--neutral" role="note">
              <strong>Scanned target:</strong> {report.meta.target}
              <p style={{ marginTop: 4 }}>
                The model to deploy may differ from the scanned target. Ensure the above
                identifier matches the model you intend to deploy.
              </p>
            </div>
          )}
        </Section>
      )}

      {/* ── D. Region ── */}
      {config.provider && (
        <Section title="D. Region">
          {isAws ? (
            <FormRow
              label="AWS Region"
              htmlFor={id("region")}
              required
              validation={validation.region}
            >
              <select
                id={id("region")}
                className="deploy-select"
                value={config.region ?? ""}
                onChange={(e) => setRegion(e.target.value || null)}
              >
                <option value="">— Select region —</option>
                {AWS_REGIONS.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label} ({r.id}){!r.bedrockAvailable && config.mode === "bedrock" ? " ⚠" : ""}
                  </option>
                ))}
              </select>
            </FormRow>
          ) : (
            <FormRow
              label="Region"
              htmlFor={id("region-text")}
              validation={validation.region}
            >
              <input
                id={id("region-text")}
                type="text"
                className="deploy-input"
                placeholder="e.g. eastus / us-central1"
                value={config.region ?? ""}
                onChange={(e) => setRegion(e.target.value || null)}
              />
            </FormRow>
          )}
          <div className="deploy-region-note">
            Region availability is not verified in real time. Confirm service availability in your cloud console before provisioning.
          </div>
        </Section>
      )}

      {/* ── D2. Compute (SageMaker only) ── */}
      {isAws && config.mode === "sagemaker" && (
        <Section
          title="D2. Compute Configuration"
          note="SageMaker instance configuration. Quota availability is not verified here."
        >
          <FormRow
            label="Instance Type"
            htmlFor={id("instance-type")}
            required
            validation={validation.instanceType}
          >
            <select
              id={id("instance-type")}
              className="deploy-select"
              value={config.instanceType ?? ""}
              onChange={(e) => patchConfig({ instanceType: e.target.value || null })}
            >
              <option value="">— Select instance type —</option>
              {SAGEMAKER_INSTANCE_TYPES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label} — {t.notes}
                </option>
              ))}
            </select>
          </FormRow>
          <FormRow
            label="Initial Replicas"
            htmlFor={id("replicas")}
            validation={validation.replicas}
          >
            <input
              id={id("replicas")}
              type="number"
              className="deploy-input deploy-input--short"
              min={1}
              max={10}
              value={config.replicas}
              onChange={(e) => patchConfig({ replicas: Math.max(1, parseInt(e.target.value, 10) || 1) })}
            />
          </FormRow>
        </Section>
      )}

      {/* ── E. Network and access ── */}
      {config.provider && (
        <Section
          title="E. Network and Access"
          note="Security defaults are set to the safer option. Public access requires explicit selection."
        >
          {/* Endpoint scope */}
          <FormRow
            label="Endpoint Scope"
            htmlFor={id("scope")}
            required
            validation={validation.endpointScope}
          >
            <div className="deploy-radio-group" role="radiogroup" aria-label="Endpoint scope">
              <label className="deploy-radio-label">
                <input
                  type="radio"
                  name={id("scope")}
                  value="private"
                  checked={config.endpointScope === "private"}
                  onChange={() => patchConfig({ endpointScope: "private" })}
                  id={id("scope-private")}
                />
                Private (recommended)
              </label>
              <label className="deploy-radio-label">
                <input
                  type="radio"
                  name={id("scope")}
                  value="public"
                  checked={config.endpointScope === "public"}
                  onChange={() => patchConfig({ endpointScope: "public" })}
                  id={id("scope-public")}
                />
                Public — exposed to internet
              </label>
            </div>
          </FormRow>

          {config.endpointScope === "public" && (
            <div className="deploy-warning-box" role="alert">
              ⚠ <strong>Public endpoint:</strong> This endpoint will be reachable from the internet.
              Ensure authentication is enabled and the model does not expose sensitive data.
              This setting does not configure firewall rules — you must configure network access in your cloud console.
            </div>
          )}

          {/* Auth */}
          <div className="deploy-toggle-row">
            <label className="deploy-toggle-label" htmlFor={id("require-auth")}>
              <input
                id={id("require-auth")}
                type="checkbox"
                className="deploy-checkbox"
                checked={config.requireAuth}
                onChange={(e) => patchConfig({ requireAuth: e.target.checked })}
              />
              Require API key authentication
            </label>
            <span className="deploy-toggle-note">Recommended</span>
          </div>

          {/* Logging */}
          <div className="deploy-toggle-row">
            <label className="deploy-toggle-label" htmlFor={id("enable-logging")}>
              <input
                id={id("enable-logging")}
                type="checkbox"
                className="deploy-checkbox"
                checked={config.enableLogging}
                onChange={(e) => patchConfig({ enableLogging: e.target.checked })}
              />
              Enable CloudWatch logging
              {config.provider !== "aws" && " (equivalent for selected provider)"}
            </label>
          </div>

          {/* Bedrock Guardrails */}
          {isAws && config.mode === "bedrock" && (
            <div className="deploy-toggle-row">
              <label className="deploy-toggle-label" htmlFor={id("guardrails")}>
                <input
                  id={id("guardrails")}
                  type="checkbox"
                  className="deploy-checkbox"
                  checked={config.enableGuardrails}
                  onChange={(e) => patchConfig({ enableGuardrails: e.target.checked })}
                />
                Enable Amazon Bedrock Guardrails
              </label>
              <span className="deploy-toggle-note">
                Helps mitigate prompt injection and harmful output risks
              </span>
            </div>
          )}

          <div className="deploy-security-note" role="note">
            These settings configure the deployment plan. They do not enforce cloud policy until you provision.
            Enabling checkboxes here does not guarantee that the corresponding cloud service is active.
          </div>
        </Section>
      )}

      {/* ── F. Budget ── */}
      {config.provider && (
        <Section
          title="F. Budget Constraint (Optional)"
          note="Informational only — does not create a cloud billing alert. Set up AWS Budgets separately."
        >
          <FormRow
            label="Monthly budget limit (USD)"
            htmlFor={id("budget")}
            validation={validation.budgetMonthlyUsd}
          >
            <div className="deploy-input-group">
              <span className="deploy-input-group__prefix">$</span>
              <input
                id={id("budget")}
                type="number"
                className="deploy-input deploy-input--short"
                min={0}
                placeholder="e.g. 500"
                value={config.budgetMonthlyUsd ?? ""}
                onChange={(e) => {
                  const v = e.target.value;
                  patchConfig({ budgetMonthlyUsd: v === "" ? null : parseFloat(v) });
                }}
              />
              <span className="deploy-input-group__suffix">/month</span>
            </div>
          </FormRow>
          <div className="deploy-budget-note">
            This figure is recorded in the plan only. It does not configure an AWS Budget alert or enforce
            a hard spending cap. A planned budget is different from an enforced provider-side spending limit.
          </div>
        </Section>
      )}

      {/* ── Configuration summary ── */}
      {config.provider && (
        <section className="deploy-summary" id="deploy-config-summary">
          <div className="deploy-summary__title">Configuration Summary</div>
          <div className="deploy-summary__grid">
            <span className="deploy-summary__label">Provider</span>
            <span className="deploy-summary__value">
              {config.provider?.toUpperCase() ?? "—"}
              {(config.provider === "azure" || config.provider === "gcp") && (
                <span className="deploy-summary__tag deploy-summary__tag--plan"> Plan only</span>
              )}
            </span>
            {isAws && (
              <>
                <span className="deploy-summary__label">Mode</span>
                <span className="deploy-summary__value">{config.mode ?? "—"}</span>
              </>
            )}
            <span className="deploy-summary__label">Region</span>
            <span className="deploy-summary__value">{config.region ?? "—"}</span>
            <span className="deploy-summary__label">Model ID</span>
            <span className="deploy-summary__value deploy-summary__value--mono">
              {config.modelId || "—"}
            </span>
            {isAws && config.mode === "sagemaker" && (
              <>
                <span className="deploy-summary__label">Instance</span>
                <span className="deploy-summary__value">{config.instanceType ?? "—"} × {config.replicas}</span>
              </>
            )}
            <span className="deploy-summary__label">Endpoint</span>
            <span className="deploy-summary__value">
              {config.endpointScope === "public" ? "⚠ Public" : "Private"}
              {config.requireAuth ? " · Auth required" : " · No auth ⚠"}
            </span>
            <span className="deploy-summary__label">Logging</span>
            <span className="deploy-summary__value">{config.enableLogging ? "Enabled" : "Disabled"}</span>
            {isAws && config.mode === "bedrock" && (
              <>
                <span className="deploy-summary__label">Guardrails</span>
                <span className="deploy-summary__value">{config.enableGuardrails ? "Enabled" : "Not configured"}</span>
              </>
            )}
            {config.budgetMonthlyUsd !== null && (
              <>
                <span className="deploy-summary__label">Budget</span>
                <span className="deploy-summary__value">${config.budgetMonthlyUsd}/mo (plan only)</span>
              </>
            )}
            <span className="deploy-summary__label">Deployed</span>
            <span className="deploy-summary__value deploy-summary__value--no-deploy">
              No — plan only
            </span>
            {isSimulated && (
              <>
                <span className="deploy-summary__label">Provenance</span>
                <span className="deploy-summary__value deploy-summary__value--sim">⚠ Based on simulated assessment</span>
              </>
            )}
          </div>

          {/* Blocking issues */}
          {!validation.canProceed && validation.blockingIssues.length > 0 && (
            <div className="deploy-blocking-issues" role="alert" id="deploy-blocking-issues">
              <div className="deploy-blocking-issues__title">Issues preventing progression:</div>
              <ul className="deploy-blocking-issues__list">
                {validation.blockingIssues.map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {/* ── Actions ── */}
      <div className="actions-page__actions" id="deploy-config-actions">
        <button
          type="button"
          className="button button--secondary"
          onClick={onBack}
          id="deploy-back-btn"
        >
          ← Back to Export
        </button>
        <button
          type="button"
          className="button button--primary"
          onClick={onProceed}
          disabled={!validation.canProceed}
          id="deploy-proceed-btn"
          aria-disabled={!validation.canProceed}
          title={
            validation.canProceed
              ? "Proceed to cloud comparison"
              : `Cannot proceed: ${validation.blockingIssues.join("; ")}`
          }
        >
          Proceed to Cloud Compare →
        </button>
      </div>
    </div>
  );
}
