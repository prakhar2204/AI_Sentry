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
  generateDeployPlan,
  dryRunDeployment,
  executeDeployment,
  getDeploymentStatus,
  rollbackDeployment,
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
import { CloudLoginPanel } from "../components/deploy/CloudLoginPanel";
import { cloudAuth } from "../services/cloudAuthService";

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
    (reportState.report as unknown as { deploy_recommendation?: unknown })
      ?.deploy_recommendation as Parameters<typeof ProviderSelectScreen>[0]["recommendation"] ?? null;

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

function AuthStep({ onEdit }: { onEdit?: () => void }) {
  const { state, dispatch } = useDeployFlow();
  const { state: reports } = useReportContext();
  const provider = state.provider!;
  async function afterLogin(credentials: Record<string, string>) {
    dispatch({ type: 'SET_CREDENTIALS', credentials });
    if ('deployment_mode' in state.config && state.config.deployment_mode === 'managed_model') {
      dispatch({ type: 'SET_LOADING', loading: true });
      try {
        const plan = await generateDeployPlan(provider, state.config as CloudDeployConfig, credentials, reports.report as unknown as Record<string, unknown>);
        dispatch({ type: 'SET_PLAN', plan });
      } catch (error) { dispatch({ type: 'SET_ERROR', error: String(error) }); }
    } else dispatch({ type: 'SET_STEP', step: 'config' });
  }
  if (provider === "private") return <div className="deploy-flow__panel">
    <h2>Private deployment</h2>
    <p>Build and start the scanned model using local Docker. The endpoint will bind to this computer only.</p>
    <button className="deploy-flow__btn deploy-flow__btn--primary"
      onClick={() => afterLogin({})}>Prepare deployment</button>
  </div>;
  return <CloudLoginPanel provider={provider}
    initialRegion={"region" in state.config ? state.config.region : undefined}
    onBack={onEdit || (() => dispatch({ type: "SET_STEP", step: "provider_select" }))}
    onConfirmed={identity => {
      void afterLogin({
        auth_mode: "cli", profile: identity.profile || "", account_id: identity.account,
        identity: identity.identity, region: identity.region,
      });
    }} />;
}

// ── Config step ───────────────────────────────────────────────────────────────

function ConfigStep() {
  const { state, dispatch } = useDeployFlow();
  const provider = state.provider!;
  const { state: reportState } = useReportContext();
  const [recoveryId, setRecoveryId] = React.useState("");
  const [recoveryError, setRecoveryError] = React.useState("");
  const [recovering, setRecovering] = React.useState(false);
  async function recover() {
    setRecovering(true); setRecoveryError("");
    try {
      const result = await getDeploymentStatus(provider, recoveryId.trim(), state.credentials);
      dispatch({ type: "SET_DEPLOY_RESULT", result: { ...result, endpoint_url: result.endpoint_url || "" } });
    } catch (error) { setRecoveryError(String(error)); }
    finally { setRecovering(false); }
  }

  const accountName =
    (state.credentials as Record<string, string>).email ??
    (state.credentials as Record<string, string>).account_id ??
    "Your Account";

  const handleSubmit = useCallback(
    async (cfg: Record<string, string>) => {
      const credentials = { ...state.credentials, ...(cfg.gcp_project_id ? { gcp_project_id: cfg.gcp_project_id } : {}) };
      dispatch({ type: "SET_CREDENTIALS", credentials });
      dispatch({ type: "SET_CONFIG", config: cfg as unknown as CloudDeployConfig });
      dispatch({ type: "SET_LOADING", loading: true });
      try {
        const scanReport = (reportState.report as unknown as Record<string, unknown>) ?? {};
        const plan = await generateDeployPlan(
          provider,
          cfg as unknown as CloudDeployConfig,
          credentials,
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
    <>
    {provider === "aws" && <div className="deploy-flow__panel">
      <label htmlFor="recover-deployment-id">Resume an existing deployment (optional)</label>
      <input id="recover-deployment-id" className="deploy-auth__input" placeholder="sp-..."
        value={recoveryId} onChange={event => setRecoveryId(event.target.value)} />
      <button className="deploy-flow__btn" disabled={!recoveryId.trim() || recovering} onClick={recover}>Check deployment</button>
      {recoveryError && <p role="alert">{recoveryError}</p>}
    </div>}
    <ProviderConfigPanel
      provider={provider}
      accountName={accountName}
      initialRegion={state.credentials.region}
      initialConfig={state.config as Record<string, string>}
      onSubmit={handleSubmit}
      onBack={() => dispatch({ type: "SET_STEP", step: "auth" })}
    />
    </>
  );
}

// ── Plan review step ──────────────────────────────────────────────────────────

function PlanReviewStep({ onEdit }: { onEdit?: () => void }) {
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
          {cost?.low_usd != null && cost?.high_usd != null
            ? `$${cost.low_usd} – $${cost.high_usd} / mo` : "Not estimated"}
        </span>
        {cost?.note && <p>{cost.note}</p>}
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
          onClick={onEdit || (() => dispatch({ type: "SET_STEP", step: "config" }))}
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
      if (state.provider !== "private") {
        await cloudAuth(state.provider!).select_scope({
          provider: state.provider!, account: state.credentials.account_id,
          identity: state.credentials.identity, region: state.plan!.region,
        });
      }
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
      {state.provider !== "private" && <dl>
        <dt>Identity</dt><dd><code>{state.credentials.identity}</code></dd>
        <dt>Account</dt><dd>{state.credentials.account_id}</dd>
        <dt>Region</dt><dd>{state.plan?.region}</dd>
      </dl>}

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
  const { state, dispatch } = useDeployFlow();
  React.useEffect(() => {
    const id = state.deployResult?.deployment_id;
    if (!id || !state.provider) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const result = await getDeploymentStatus(state.provider!, id, state.credentials);
        if (!cancelled) dispatch({ type: "SET_DEPLOY_RESULT", result: { ...result, endpoint_url: result.endpoint_url || "" } });
      } catch (error) {
        if (!cancelled) dispatch({ type: "SET_ERROR", error: String(error) });
      }
    }, 5000);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [state.deployResult, state.provider, state.credentials, dispatch]);
  return (
    <div className="deploy-flow__panel deploy-flow__panel--centered">
      <div className="deploy-deploying__spinner" />
      <h2 className="deploy-flow__panel-title">Deploying…</h2>
      <p className="deploy-flow__panel-desc">
        Provisioning your model endpoint. This may take a few minutes.
        {state.deployResult?.message}
      </p>
      {state.deployResult && <code>Deployment ID: {state.deployResult.deployment_id}</code>}
    </div>
  );
}

// ── Complete step ─────────────────────────────────────────────────────────────

function CompleteStep({ onEdit }: { onEdit?: () => void }) {
  const { state, dispatch } = useDeployFlow();
  const result = state.deployResult!;

  return (
    <div className="deploy-flow__panel deploy-flow__panel--centered">
      <div className="deploy-complete__icon">✓</div>
      <h2 className="deploy-flow__panel-title deploy-flow__panel-title--success">
        {result.status === "rolled_back" ? "Deployment Removed" : "Deployment Complete!"}
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
      {result.status !== "rolled_back" && <DeploymentRecovery />}
      <button
        id="deploy-complete-reset"
        className="deploy-flow__btn deploy-flow__btn--ghost"
        onClick={() => { dispatch({ type: "RESET" }); onEdit?.(); }}
      >
        Start New Deployment
      </button>
    </div>
  );
}

// ── Error step ────────────────────────────────────────────────────────────────

function ErrorStep({ onEdit }: { onEdit?: () => void }) {
  const { state, dispatch } = useDeployFlow();
  return (
    <div className="deploy-flow__panel deploy-flow__panel--centered">
      <div className="deploy-error__icon">✗</div>
      <h2 className="deploy-flow__panel-title deploy-flow__panel-title--error">
        Deployment Failed
      </h2>
      <p className="deploy-error__message">{state.error}</p>
      {state.deployResult && <DeploymentRecovery />}
      <div className="deploy-flow__actions">
        <button
          id="deploy-error-retry"
          className="deploy-flow__btn deploy-flow__btn--primary"
          onClick={onEdit || (() => dispatch({ type: "SET_STEP", step: "config" }))}
        >
          ← Back to Settings
        </button>
        <button
          id="deploy-error-reset"
          className="deploy-flow__btn deploy-flow__btn--ghost"
          onClick={() => { dispatch({ type: "RESET" }); onEdit?.(); }}
        >
          Start Over
        </button>
      </div>
    </div>
  );
}

function DeploymentRecovery() {
  const { state, dispatch } = useDeployFlow();
  const [remove, setRemove] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  async function refresh(deleting = false) {
    if (!state.deployResult || !state.provider) return;
    setBusy(true);
    try {
      if (deleting) {
        const result = await rollbackDeployment(state.provider, state.deployResult.deployment_id, state.credentials);
        if (!result.success) throw new Error(result.errors.join("; "));
      }
      const result = await getDeploymentStatus(state.provider, state.deployResult.deployment_id, state.credentials);
      dispatch({ type: "SET_DEPLOY_RESULT", result: { ...result, endpoint_url: result.endpoint_url || "" } });
    } catch (error) { dispatch({ type: "SET_ERROR", error: String(error) }); }
    finally { setBusy(false); }
  }
  return <div>
    <p>Deployment ID: <code>{state.deployResult?.deployment_id}</code></p>
    <button className="deploy-flow__btn" disabled={busy} onClick={() => refresh()}>Refresh deployment status</button>
    <label><input type="checkbox" checked={remove} disabled={busy}
      onChange={e => setRemove(e.target.checked)} /> Remove resources created by this deployment</label>
    <button className="deploy-flow__btn deploy-flow__btn--danger" disabled={!remove || busy}
      onClick={() => refresh(true)}>Confirm removal</button>
  </div>;
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DeployFlowPage({ onEdit }: { onEdit?: () => void }) {
  const { state } = useDeployFlow();

  const renderStep = () => {
    switch (state.step) {
      case "provider_select": return <ProviderSelectStep />;
      case "auth":            return <AuthStep onEdit={onEdit} />;
      case "config":          return <ConfigStep />;
      case "plan_review":     return <PlanReviewStep onEdit={onEdit} />;
      case "dry_run":         // falls through to confirm (dry_run sets step=confirm)
      case "confirm":         return <ConfirmStep />;
      case "deploying":       return <DeployingStep />;
      case "complete":        return <CompleteStep onEdit={onEdit} />;
      case "error":           return <ErrorStep onEdit={onEdit} />;
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
