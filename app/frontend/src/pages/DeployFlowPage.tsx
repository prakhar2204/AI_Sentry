/**
 * Sentryɸ — Deploy Flow Page (W3)
 * pages/DeployFlowPage.tsx
 *
 * Multi-step deployment wizard rendered after scan results.
 * W3: Now uses rich ProviderSelectScreen (cost comparison, feature grid, recommendation)
 *     and ProviderConfigPanel (live cost, provider-specific settings).
 *
 * All cloud API calls go through deployIpcService.ts → Python backend.
 * No fetch() or direct cloud SDK calls from this file.
 */

import React, { useCallback } from "react";
import { useDeployFlow } from "../store/DeployFlowContext";
import { useReportContext } from "../store/ReportContext";
import {
  getAuthUrl,
  generateDeployPlan,
  dryRunDeployment,
  executeDeployment,
} from "../services/deployIpcService";
import type {
  DeployProvider,
  DeployFlowStep,
  CloudDeployConfig,
} from "../services/deployIpcTypes";
import {
  PROVIDER_INFO,
} from "../services/deployIpcTypes";
import { ProviderSelectScreen } from "../components/deploy/ProviderSelectScreen";
import { ProviderConfigPanel } from "../components/deploy/ProviderConfigPanel";

// ── Sub-components ────────────────────────────────────────────────────────────

function StepIndicator({ step }: { step: DeployFlowStep }) {
  const steps: { id: DeployFlowStep; label: string }[] = [
    { id: "provider_select", label: "Provider" },
    { id: "auth",            label: "Sign In" },
    { id: "config",          label: "Settings" },
    { id: "plan_review",     label: "Plan" },
    { id: "dry_run",         label: "Validate" },
    { id: "confirm",         label: "Confirm" },
    { id: "deploying",       label: "Deploy" },
    { id: "complete",        label: "Done" },
  ];
  const activeIdx = steps.findIndex((s) => s.id === step);

  return (
    <div className="deploy-flow__steps">
      {steps.map((s, i) => (
        <React.Fragment key={s.id}>
          <div
            className={[
              "deploy-flow__step",
              i < activeIdx  ? "deploy-flow__step--done"   : "",
              i === activeIdx ? "deploy-flow__step--active" : "",
            ].join(" ").trim()}
          >
            <div className="deploy-flow__step-dot">
              {i < activeIdx ? "✓" : i + 1}
            </div>
            <span className="deploy-flow__step-label">{s.label}</span>
          </div>
          {i < steps.length - 1 && (
            <div className={`deploy-flow__step-line ${i < activeIdx ? "deploy-flow__step-line--done" : ""}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ── Provider selector ─────────────────────────────────────────────────────────

function ProviderSelectStep() {
  const { dispatch } = useDeployFlow();
  const { state: reportState } = useReportContext();

  // Extract recommendation from report if available
  const recommendation =
    (reportState.report as unknown as { deployment_recommendation?: unknown })
      ?.deployment_recommendation as Parameters<typeof ProviderSelectScreen>[0]["recommendation"] ?? null;

  return (
    <ProviderSelectScreen
      recommendation={recommendation}
      onSelectProvider={(provider) =>
        dispatch({ type: "SET_PROVIDER", provider })
      }
    />
  );
}

// ── Auth step ─────────────────────────────────────────────────────────────────

function AuthStep() {
  const { state, dispatch } = useDeployFlow();
  const provider = state.provider!;
  const info     = PROVIDER_INFO[provider];

  const handleOAuth = useCallback(async () => {
    if (info.authType === "none") {
      dispatch({ type: "SET_STEP", step: "config" });
      return;
    }
    dispatch({ type: "SET_LOADING", loading: true });
    try {
      const url = await getAuthUrl(provider);
      if (url && window.electronAPI) {
        // Open browser for OAuth
        await window.electronAPI?.openExternal?.(url);
        // The Python process will emit deploy_auth_complete which arrives
        // via the IPC event. For now, advance to config after 3s timeout.
        // In production this event is caught by Electron and dispatched here.
        dispatch({ type: "MERGE_CREDENTIALS", patch: { auth_started: "true" } });
        dispatch({ type: "SET_STEP", step: "config" });
      } else {
        dispatch({ type: "SET_STEP", step: "config" });
      }
    } catch (err: unknown) {
      dispatch({ type: "SET_ERROR", error: String(err) });
    }
  }, [provider, info.authType, dispatch]);

  const handleManualKey = useCallback(() => {
    dispatch({ type: "SET_STEP", step: "config" });
  }, [dispatch]);

  return (
    <div className="deploy-flow__panel">
      <h2 className="deploy-flow__panel-title">
        {info.icon} Sign in to {info.name}
      </h2>

      {info.authType === "none" ? (
        <>
          <p className="deploy-flow__panel-desc">
            Private deployment doesn't require cloud account sign-in.
            Sentryɸ will generate deployment artifacts you can use on your own infrastructure.
          </p>
          <button
            id="deploy-auth-continue"
            className="deploy-flow__btn deploy-flow__btn--primary"
            onClick={handleManualKey}
          >
            Continue to Settings →
          </button>
        </>
      ) : (
        <>
          <p className="deploy-flow__panel-desc">
            Sentryɸ will open {info.name}'s login page in your browser.
            After you sign in, you'll be redirected back here automatically.
          </p>
          <div className="deploy-auth__options">
            <button
              id="deploy-auth-browser"
              className="deploy-flow__btn deploy-flow__btn--primary"
              disabled={state.isLoading}
              onClick={handleOAuth}
            >
              {state.isLoading ? "Opening browser…" : `Sign in with ${info.name} →`}
            </button>
            <div className="deploy-auth__divider">
              <span>or enter credentials manually</span>
            </div>
            <ManualCredentialsForm provider={provider} onDone={handleManualKey} />
          </div>
        </>
      )}
    </div>
  );
}

function ManualCredentialsForm({
  provider,
  onDone,
}: {
  provider: DeployProvider;
  onDone: () => void;
}) {
  const { dispatch } = useDeployFlow();
  const [fields, setFields] = React.useState<Record<string, string>>({});

  const FIELD_MAP: Record<DeployProvider, { key: string; label: string; type: string }[]> = {
    aws: [
      { key: "aws_access_key_id",     label: "Access Key ID",     type: "text" },
      { key: "aws_secret_access_key", label: "Secret Access Key", type: "password" },
      { key: "aws_session_token",     label: "Session Token (optional)", type: "password" },
    ],
    azure: [
      { key: "azure_access_token",      label: "Access Token",     type: "password" },
      { key: "azure_subscription_id",   label: "Subscription ID",  type: "text" },
    ],
    gcp: [
      { key: "gcp_access_token", label: "Access Token",  type: "password" },
      { key: "gcp_project_id",   label: "Project ID",    type: "text" },
    ],
    private: [],
  };

  const fieldList = FIELD_MAP[provider] ?? [];

  const handleSave = () => {
    dispatch({ type: "SET_CREDENTIALS", credentials: fields });
    onDone();
  };

  return (
    <div className="deploy-auth__manual-form">
      {fieldList.map((f) => (
        <div key={f.key} className="deploy-auth__field">
          <label className="deploy-auth__label" htmlFor={`cred-${f.key}`}>
            {f.label}
          </label>
          <input
            id={`cred-${f.key}`}
            className="deploy-auth__input"
            type={f.type}
            placeholder={f.type === "password" ? "••••••••" : f.label}
            value={fields[f.key] ?? ""}
            onChange={(e) =>
              setFields((prev) => ({ ...prev, [f.key]: e.target.value }))
            }
          />
        </div>
      ))}
      {fieldList.length > 0 && (
        <button
          id="deploy-auth-manual-save"
          className="deploy-flow__btn deploy-flow__btn--secondary"
          onClick={handleSave}
        >
          Save & Continue →
        </button>
      )}
    </div>
  );
}

// ── Config step ───────────────────────────────────────────────────────────────

function ConfigStep() {
  const { state, dispatch } = useDeployFlow();
  const provider = state.provider!;
  const { state: reportState } = useReportContext();

  const accountName =
    (state.credentials as Record<string, string>).email ??
    (state.credentials as Record<string, string>).account_id ??
    "Your Account";

  const handleSubmit = useCallback(
    async (cfg: Record<string, string>) => {
      dispatch({ type: "SET_CONFIG", config: cfg as unknown as CloudDeployConfig });
      dispatch({ type: "SET_LOADING", loading: true });
      try {
        const scanReport = (reportState.report as unknown as Record<string, unknown>) ?? {};
        const plan = await generateDeployPlan(
          provider,
          cfg as unknown as CloudDeployConfig,
          state.credentials,
          scanReport
        );
        dispatch({ type: "SET_PLAN", plan });
      } catch (err: unknown) {
        dispatch({ type: "SET_ERROR", error: String(err) });
      }
    },
    [provider, state.credentials, reportState.report, dispatch]
  );

  return (
    <ProviderConfigPanel
      provider={provider}
      accountName={accountName}
      onSubmit={handleSubmit}
      onBack={() => dispatch({ type: "SET_STEP", step: "auth" })}
    />
  );
}

// ── Plan review step ──────────────────────────────────────────────────────────

function PlanReviewStep() {
  const { state, dispatch } = useDeployFlow();
  const plan = state.plan!;

  const handleDryRun = useCallback(async () => {
    dispatch({ type: "SET_LOADING", loading: true });
    try {
      const result = await dryRunDeployment(
        state.provider!,
        plan as unknown as Record<string, unknown>,
        state.credentials
      );
      dispatch({ type: "SET_DRY_RUN", result });
    } catch (err: unknown) {
      dispatch({ type: "SET_ERROR", error: String(err) });
    }
  }, [state.provider, state.credentials, plan, dispatch]);

  const cost = plan.estimated_cost;

  return (
    <div className="deploy-flow__panel">
      <h2 className="deploy-flow__panel-title">Deployment Plan</h2>
      <p className="deploy-flow__panel-desc">
        Review what Sentryɸ will create in your {PROVIDER_INFO[state.provider!].name} account.
        No resources are provisioned until you confirm.
      </p>

      {/* Cost estimate */}
      <div className="deploy-plan__cost">
        <span className="deploy-plan__cost-label">Estimated Monthly Cost</span>
        <span className="deploy-plan__cost-range">
          ${cost?.low_usd ?? 0} – ${cost?.high_usd ?? 0} / mo
        </span>
      </div>

      {/* Resources */}
      <div className="deploy-plan__resources">
        <h3 className="deploy-plan__section-title">
          Resources to Create ({plan.resources.length})
        </h3>
        <ul className="deploy-plan__resource-list">
          {plan.resources.map((r, i) => (
            <li key={i} className="deploy-plan__resource-item">
              <span className="deploy-plan__resource-type">{r.resource_type}</span>
              {r.region && r.region !== "global" && r.region !== "self-hosted" && (
                <span className="deploy-plan__resource-region">{r.region}</span>
              )}
            </li>
          ))}
        </ul>
      </div>

      {/* Security notes */}
      {plan.security_notes.length > 0 && (
        <div className="deploy-plan__security">
          <h3 className="deploy-plan__section-title">Security Controls</h3>
          <ul className="deploy-plan__security-list">
            {plan.security_notes.map((n, i) => (
              <li key={i} className="deploy-plan__security-item">
                <span className="deploy-plan__security-icon">🔒</span> {n}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="deploy-flow__actions">
        <button
          id="deploy-plan-back"
          className="deploy-flow__btn deploy-flow__btn--ghost"
          onClick={() => dispatch({ type: "SET_STEP", step: "config" })}
        >
          ← Back
        </button>
        <button
          id="deploy-plan-validate"
          className="deploy-flow__btn deploy-flow__btn--primary"
          disabled={state.isLoading}
          onClick={handleDryRun}
        >
          {state.isLoading ? "Validating…" : "Validate Plan →"}
        </button>
      </div>
    </div>
  );
}

// ── Confirm step ──────────────────────────────────────────────────────────────

function ConfirmStep() {
  const { state, dispatch } = useDeployFlow();
  const dryRun = state.dryRunResult!;
  const [confirmed, setConfirmed] = React.useState(false);

  const handleDeploy = useCallback(async () => {
    if (!confirmed) return;
    dispatch({ type: "SET_STEP",    step: "deploying" });
    dispatch({ type: "SET_LOADING", loading: true });
    try {
      const result = await executeDeployment(
        state.provider!,
        state.plan as unknown as Record<string, unknown>,
        state.credentials,
        true
      );
      dispatch({ type: "SET_DEPLOY_RESULT", result });
    } catch (err: unknown) {
      dispatch({ type: "SET_ERROR", error: String(err) });
    }
  }, [confirmed, state.provider, state.plan, state.credentials, dispatch]);

  return (
    <div className="deploy-flow__panel">
      <h2 className="deploy-flow__panel-title">Confirm Deployment</h2>

      {dryRun.warnings.length > 0 && (
        <div className="deploy-confirm__warnings">
          <strong>⚠️ Warnings ({dryRun.warnings.length})</strong>
          <ul>
            {dryRun.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      <div className="deploy-confirm__message">
        {dryRun.message}
      </div>

      <div className="deploy-confirm__checkbox">
        <input
          type="checkbox"
          id="deploy-confirm-checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
        />
        <label htmlFor="deploy-confirm-checkbox">
          I confirm I want to deploy to {PROVIDER_INFO[state.provider!].name}.
          I understand this will create real cloud resources and incur costs.
        </label>
      </div>

      <div className="deploy-flow__actions">
        <button
          id="deploy-confirm-back"
          className="deploy-flow__btn deploy-flow__btn--ghost"
          onClick={() => dispatch({ type: "SET_STEP", step: "plan_review" })}
        >
          ← Review Plan
        </button>
        <button
          id="deploy-confirm-execute"
          className="deploy-flow__btn deploy-flow__btn--danger"
          disabled={!confirmed || state.isLoading}
          onClick={handleDeploy}
        >
          🚀 Deploy Now
        </button>
      </div>
    </div>
  );
}

// ── Deploying step ────────────────────────────────────────────────────────────

function DeployingStep() {
  return (
    <div className="deploy-flow__panel deploy-flow__panel--centered">
      <div className="deploy-deploying__spinner" />
      <h2 className="deploy-flow__panel-title">Deploying…</h2>
      <p className="deploy-flow__panel-desc">
        Provisioning your model endpoint. This may take a few minutes.
        Do not close the application.
      </p>
    </div>
  );
}

// ── Complete step ─────────────────────────────────────────────────────────────

function CompleteStep() {
  const { state, dispatch } = useDeployFlow();
  const result = state.deployResult!;

  return (
    <div className="deploy-flow__panel deploy-flow__panel--centered">
      <div className="deploy-complete__icon">✓</div>
      <h2 className="deploy-flow__panel-title deploy-flow__panel-title--success">
        Deployment Complete!
      </h2>
      {result.endpoint_url && (
        <div className="deploy-complete__endpoint">
          <span className="deploy-complete__endpoint-label">Endpoint URL</span>
          <code className="deploy-complete__endpoint-url">{result.endpoint_url}</code>
        </div>
      )}
      <p className="deploy-flow__panel-desc">
        {result.message} · {result.resources.length} resource(s) created.
      </p>
      <button
        id="deploy-complete-reset"
        className="deploy-flow__btn deploy-flow__btn--ghost"
        onClick={() => dispatch({ type: "RESET" })}
      >
        Start New Deployment
      </button>
    </div>
  );
}

// ── Error step ────────────────────────────────────────────────────────────────

function ErrorStep() {
  const { state, dispatch } = useDeployFlow();
  return (
    <div className="deploy-flow__panel deploy-flow__panel--centered">
      <div className="deploy-error__icon">✗</div>
      <h2 className="deploy-flow__panel-title deploy-flow__panel-title--error">
        Deployment Failed
      </h2>
      <p className="deploy-error__message">{state.error}</p>
      <div className="deploy-flow__actions">
        <button
          id="deploy-error-retry"
          className="deploy-flow__btn deploy-flow__btn--primary"
          onClick={() => dispatch({ type: "SET_STEP", step: "config" })}
        >
          ← Back to Settings
        </button>
        <button
          id="deploy-error-reset"
          className="deploy-flow__btn deploy-flow__btn--ghost"
          onClick={() => dispatch({ type: "RESET" })}
        >
          Start Over
        </button>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DeployFlowPage() {
  const { state } = useDeployFlow();

  const renderStep = () => {
    switch (state.step) {
      case "provider_select": return <ProviderSelectStep />;
      case "auth":            return <AuthStep />;
      case "config":          return <ConfigStep />;
      case "plan_review":     return <PlanReviewStep />;
      case "dry_run":         // falls through to confirm (dry_run sets step=confirm)
      case "confirm":         return <ConfirmStep />;
      case "deploying":       return <DeployingStep />;
      case "complete":        return <CompleteStep />;
      case "error":           return <ErrorStep />;
      default:                return <ProviderSelectStep />;
    }
  };

  return (
    <div className="deploy-flow">
      <div className="deploy-flow__header">
        <h1 className="deploy-flow__title">
          Deploy Your AI Model
        </h1>
        <p className="deploy-flow__subtitle">
          Secure, guided deployment with settings recommended from your scan results.
        </p>
      </div>
      <StepIndicator step={state.step} />
      <div className="deploy-flow__content">
        {renderStep()}
      </div>
    </div>
  );
}
