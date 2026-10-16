/**
 * Sentryɸ -- Deploy Execution (Screen 11)
 * pages/DeployExecutePage.tsx
 *
 * Dry-run deployment planning and confirmation screen.
 *
 * INVARIANTS:
 *   - deployed remains false — this screen NEVER sets deployed=true
 *   - No cloud API calls, no credentials, no resource creation
 *   - Azure/GCP configs display "plan-only" state — no simulation
 *   - Plan is local and deterministic (buildDryRunPlan pure function)
 *   - All plan content is labelled DRY RUN / SIMULATION ONLY
 *   - Configuration changes invalidate the existing plan
 *
 * D-023: Plan → User review → Provision → Verify
 *   This screen covers "Plan" and "User review" only.
 *   "Provision" and "Verify" are future work requiring a real cloud adapter.
 *
 * Navigation:
 *   Back: → Screen 10 (Cloud Compare)
 *   onBackToConfig: → Screen 9 (Deploy Config) — shown when config invalid
 */

import React, { useState, useCallback, useMemo } from "react";
import { useDeployContext } from "../store/DeployContext";
import { useReportContext } from "../store/ReportContext";
import { PageHeader } from "../components/layout/PageHeader";
import { AlertBanner } from "../components/feedback/AlertBanner";
import {
  buildDryRunPlan,
  buildPreflightChecks,
  areAutomatedChecksPassed,
  areAllPreflightChecksDone,
  isDryRunPlanStale,
  type DryRunPlan,
  type PreflightCheck,
  type DryRunStage,
  type StageStatus,
} from "../services/dryRunTypes";

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface DeployExecutePageProps {
  onBack:         () => void; // → Screen 10
  onBackToConfig: () => void; // → Screen 9 (when config invalid)
}

// ─────────────────────────────────────────────
//  Sub-components
// ─────────────────────────────────────────────

const STAGE_STATUS_LABELS: Record<StageStatus, string> = {
  planned:   "Planned",
  simulated: "Simulated",
  skipped:   "Skipped",
  blocked:   "Blocked",
};
const STAGE_STATUS_CLASS: Record<StageStatus, string> = {
  planned:   "execute-stage--planned",
  simulated: "execute-stage--simulated",
  blocked:   "execute-stage--blocked",
  skipped:   "execute-stage--skipped",
};
const STAGE_STATUS_ICON: Record<StageStatus, string> = {
  planned:   "○",
  simulated: "✓",
  blocked:   "✗",
  skipped:   "—",
};

function StageCard({ stage, index }: { stage: DryRunStage; index: number }) {
  return (
    <div
      className={`execute-stage ${STAGE_STATUS_CLASS[stage.status]}`}
      id={`execute-stage-${stage.id}`}
    >
      <div className="execute-stage__header">
        <div className="execute-stage__num">{index + 1}</div>
        <div className="execute-stage__title">{stage.label}</div>
        <span
          className={`execute-stage__badge execute-stage__badge--${stage.status}`}
          aria-label={STAGE_STATUS_LABELS[stage.status]}
        >
          <span aria-hidden="true">{STAGE_STATUS_ICON[stage.status]}</span>
          {STAGE_STATUS_LABELS[stage.status]}
        </span>
      </div>
      <p className="execute-stage__desc">{stage.description}</p>
      <div className="execute-stage__note">
        <span className="execute-stage__note-label">Dry-run output: </span>
        {stage.dryRunNote}
      </div>
      {stage.blockReason && (
        <div className="execute-stage__block-reason" role="alert">
          ✗ {stage.blockReason}
        </div>
      )}
    </div>
  );
}

function PreflightRow({
  check,
  onAck,
}: {
  check: PreflightCheck;
  onAck: (id: string, acked: boolean) => void;
}) {
  const isUserAck = check.status === "user-ack";
  const rowClass = [
    "execute-preflight__row",
    `execute-preflight__row--${check.status}`,
    isUserAck && check.acknowledged ? "execute-preflight__row--acked" : "",
  ].filter(Boolean).join(" ");

  const icon = isUserAck
    ? check.acknowledged ? "☑" : "☐"
    : check.status === "pass" ? "✓"
    : check.status === "fail" ? "✗"
    : "⚠";

  return (
    <div className={rowClass} id={`execute-preflight-${check.id}`}>
      <div className="execute-preflight__icon" aria-hidden="true">{icon}</div>
      <div className="execute-preflight__body">
        <div className="execute-preflight__label">
          {isUserAck ? (
            <label className="execute-preflight__ack-label">
              <input
                type="checkbox"
                className="execute-preflight__checkbox"
                checked={check.acknowledged}
                onChange={(e) => onAck(check.id, e.target.checked)}
                aria-describedby={`execute-preflight-desc-${check.id}`}
              />
              {check.label}
            </label>
          ) : (
            check.label
          )}
        </div>
        <div
          className="execute-preflight__desc"
          id={`execute-preflight-desc-${check.id}`}
        >
          {check.description}
        </div>
        {check.reason && (
          <div className="execute-preflight__reason" role="alert">
            {check.reason}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Plan-only provider state
// ─────────────────────────────────────────────

function PlanOnlyState({
  provider,
  onBackToConfig,
  onBack,
}: {
  provider: string;
  onBackToConfig: () => void;
  onBack: () => void;
}) {
  const PROVIDER_LINKS: Record<string, string> = {
    azure: "https://azure.microsoft.com/products/machine-learning/",
    gcp:   "https://cloud.google.com/vertex-ai",
  };

  return (
    <div className="execute-plan-only" id="execute-plan-only" role="region" aria-label="Plan-only provider">
      <div className="execute-plan-only__icon">🗺</div>
      <div className="execute-plan-only__title">
        Deployment planning only — {provider.toUpperCase()}
      </div>
      <div className="execute-plan-only__body">
        <p>
          Sentryɸ v1 cannot automate {provider.toUpperCase()} deployment.
          This provider is <strong>plan-only</strong>: Sentryɸ helps you design
          your configuration, but you must provision resources manually using the
          provider's console or CLI.
        </p>
        <p>
          To proceed, export your configuration plan from Screen 8 and follow
          the provider's deployment documentation.
        </p>
        {PROVIDER_LINKS[provider] && (
          <p>
            <a
              href={PROVIDER_LINKS[provider]}
              target="_blank"
              rel="noopener noreferrer"
              className="execute-plan-only__link"
            >
              {provider.toUpperCase()} deployment documentation ↗
            </a>
          </p>
        )}
        <p className="execute-plan-only__note">
          To switch to an AWS configuration with automated provisioning support,
          return to Screen 9.
        </p>
      </div>
      <div className="execute-plan-only__actions">
        <button
          type="button"
          className="button button--secondary"
          onClick={onBack}
          id="execute-plan-only-back"
        >
          ← Back to Cloud Compare
        </button>
        <button
          type="button"
          className="button button--primary"
          onClick={onBackToConfig}
          id="execute-plan-only-config"
        >
          ← Change to AWS Configuration
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Config strip
// ─────────────────────────────────────────────

function ConfigSummaryStrip({ plan }: { plan: DryRunPlan }) {
  return (
    <section className="execute-config-strip" id="execute-config-strip">
      <div className="execute-config-strip__title">Configuration being planned</div>
      <div className="execute-config-strip__items">
        <div className="execute-config-strip__item">
          <span className="execute-config-strip__label">Provider</span>
          <span className="execute-config-strip__value">{plan.provider?.toUpperCase() ?? "—"}</span>
        </div>
        {plan.mode && (
          <div className="execute-config-strip__item">
            <span className="execute-config-strip__label">Mode</span>
            <span className="execute-config-strip__value">{plan.mode}</span>
          </div>
        )}
        <div className="execute-config-strip__item">
          <span className="execute-config-strip__label">Region</span>
          <span className="execute-config-strip__value">{plan.region ?? "—"}</span>
        </div>
        <div className="execute-config-strip__item">
          <span className="execute-config-strip__label">Model ID</span>
          <span className="execute-config-strip__value execute-config-strip__value--mono">
            {plan.modelId || "—"}
          </span>
        </div>
        {plan.configSnapshot.instanceType && (
          <div className="execute-config-strip__item">
            <span className="execute-config-strip__label">Instance</span>
            <span className="execute-config-strip__value">
              {plan.configSnapshot.instanceType} × {plan.configSnapshot.replicas}
            </span>
          </div>
        )}
        <div className="execute-config-strip__item">
          <span className="execute-config-strip__label">Endpoint</span>
          <span className="execute-config-strip__value">
            {plan.configSnapshot.endpointScope === "public" ? "⚠ Public" : "Private"}
          </span>
        </div>
        <div className="execute-config-strip__item">
          <span className="execute-config-strip__label">Auth</span>
          <span className="execute-config-strip__value">
            {plan.configSnapshot.requireAuth ? "Required" : "⚠ Disabled"}
          </span>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────
//  Main page
// ─────────────────────────────────────────────

type PageState = "review" | "generating" | "done";

export function DeployExecutePage({ onBack, onBackToConfig }: DeployExecutePageProps) {
  const { state: deployState }  = useDeployContext();
  const { state: reportState }  = useReportContext();

  const config = deployState.config;
  const report = reportState.report;
  const isSimulated = report?.meta.scan_id.startsWith("sim-") ?? false;

  // Track user acknowledgements for preflight user-ack checks
  const [acknowledgedIds, setAcknowledgedIds] = useState<Set<string>>(new Set());

  // Generated plan (null = not yet generated)
  const [plan, setPlan] = useState<DryRunPlan | null>(null);

  // Page state machine
  const [pageState, setPageState] = useState<PageState>("review");

  // Build live preflight checks (for the review phase, before plan generation)
  const liveChecks = useMemo(() => {
    return buildPreflightChecks(config).map((c) => ({
      ...c,
      acknowledged: acknowledgedIds.has(c.id),
    }));
  }, [config, acknowledgedIds]);

  const automatedPassed = areAutomatedChecksPassed(liveChecks);
  const allDone = areAllPreflightChecksDone(liveChecks);

  // Provider capability
  const isPlanOnlyProvider = config.provider === "azure" || config.provider === "gcp";
  const hasNoProvider = config.provider === null;

  // Stale plan detection
  const isPlanStale = plan !== null && isDryRunPlanStale(plan, config);

  const handleAck = useCallback((id: string, acked: boolean) => {
    setAcknowledgedIds((prev) => {
      const next = new Set(prev);
      if (acked) next.add(id); else next.delete(id);
      return next;
    });
    // If config was changed and plan exists, don't reset the plan here — stale detection handles it
  }, []);

  const handleGeneratePlan = useCallback(() => {
    if (pageState !== "review" && !isPlanStale) return;
    if (!allDone) return;

    setPageState("generating");

    // Use a short timeout to allow the UI to render "Generating…" state
    // This is NOT a fake progress indicator — it's just a React render flush
    setTimeout(() => {
      const generated = buildDryRunPlan(config, acknowledgedIds);
      setPlan(generated);
      setPageState("done");
    }, 120);
  }, [pageState, isPlanStale, allDone, config, acknowledgedIds]);

  const handleRegenerate = useCallback(() => {
    setPlan(null);
    setPageState("review");
    setAcknowledgedIds(new Set());
  }, []);

  // ── No provider selected ──
  if (hasNoProvider) {
    return (
      <div className="execute-page" id="execute-page">
        <PageHeader
          title="Deploy Execution"
          subtitle="Dry-run planning"
          onBack={onBack}
        />
        <div className="execute-no-config" role="alert" id="execute-no-config">
          <div className="execute-no-config__icon">⚙</div>
          <div className="execute-no-config__title">No deployment configuration</div>
          <p className="execute-no-config__desc">
            A cloud provider and deployment mode must be configured before generating a deployment plan.
            Return to Screen 9 to complete the configuration.
          </p>
          <div className="execute-no-config__actions">
            <button type="button" className="button button--secondary" onClick={onBack} id="execute-no-config-back">
              ← Back to Cloud Compare
            </button>
            <button type="button" className="button button--primary" onClick={onBackToConfig} id="execute-no-config-config">
              Configure Deployment →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Plan-only providers (Azure, GCP) ──
  if (isPlanOnlyProvider) {
    return (
      <div className="execute-page" id="execute-page">
        <PageHeader
          title="Deploy Execution"
          subtitle="Dry-run planning"
          onBack={onBack}
        />
        <PlanOnlyState
          provider={config.provider!}
          onBack={onBack}
          onBackToConfig={onBackToConfig}
        />
      </div>
    );
  }

  return (
    <div className="execute-page" id="execute-page">

      {/* Header */}
      <PageHeader
        title="Deploy Execution"
        subtitle={report ? `Based on assessment: ${report.meta.target}` : "No assessment loaded"}
        onBack={onBack}
      />

      {/* DRY RUN banner — always visible */}
      <div className="execute-dry-run-banner" id="execute-dry-run-banner" role="note">
        <div className="execute-dry-run-banner__badge">DRY RUN</div>
        <div className="execute-dry-run-banner__text">
          <strong>Simulation only — no cloud resources will be created.</strong>
          {" "}This screen generates a proposed deployment plan for review. No AWS APIs are called,
          no infrastructure is provisioned, and no costs are incurred.
        </div>
      </div>

      {/* Simulated assessment warning */}
      {isSimulated && (
        <AlertBanner
          type="info"
          message="This plan is based on a simulated assessment. Treat deployment recommendations as illustrative only. Run a real assessment before deploying to production."
        />
      )}

      {/* Stale plan warning */}
      {isPlanStale && (
        <AlertBanner
          type="error"
          message="Your configuration has changed since this plan was generated. Regenerate the plan to reflect the current configuration."
        />
      )}

      {/* deployed=false invariant display */}
      <div className="execute-invariant-note" id="execute-invariant-note" role="note">
        Deployment status: <strong>Not deployed</strong> — this workflow produces a plan only.
        The application never sets the deployment status to "deployed" during a dry run.
      </div>

      {/* ── Phase: REVIEW ── */}
      {(pageState === "review" || (pageState === "done" && isPlanStale)) && (
        <>
          {/* Config summary */}
          {/* Build a quick plan snapshot for display only */}
          <section className="execute-config-strip" id="execute-config-strip">
            <div className="execute-config-strip__title">Configuration being planned</div>
            <div className="execute-config-strip__items">
              <div className="execute-config-strip__item">
                <span className="execute-config-strip__label">Provider</span>
                <span className="execute-config-strip__value">{config.provider?.toUpperCase() ?? "—"}</span>
              </div>
              {config.mode && (
                <div className="execute-config-strip__item">
                  <span className="execute-config-strip__label">Mode</span>
                  <span className="execute-config-strip__value">{config.mode}</span>
                </div>
              )}
              <div className="execute-config-strip__item">
                <span className="execute-config-strip__label">Region</span>
                <span className="execute-config-strip__value">{config.region ?? "—"}</span>
              </div>
              <div className="execute-config-strip__item">
                <span className="execute-config-strip__label">Model ID</span>
                <span className="execute-config-strip__value execute-config-strip__value--mono">
                  {config.modelId || "—"}
                </span>
              </div>
              {config.instanceType && (
                <div className="execute-config-strip__item">
                  <span className="execute-config-strip__label">Instance</span>
                  <span className="execute-config-strip__value">
                    {config.instanceType} × {config.replicas}
                  </span>
                </div>
              )}
            </div>
          </section>

          {/* Preflight checklist */}
          <section className="execute-preflight" id="execute-preflight">
            <div className="execute-preflight__header">
              <h2 className="execute-preflight__title">Preflight Checks</h2>
              <p className="execute-preflight__subtitle">
                Complete all checks before generating the dry-run plan.
                Automated checks run against your configuration. User acknowledgements require your confirmation.
              </p>
            </div>
            <div className="execute-preflight__list" id="execute-preflight-list">
              {liveChecks.map((check) => (
                <PreflightRow key={check.id} check={check} onAck={handleAck} />
              ))}
            </div>

            {!automatedPassed && (
              <div className="execute-preflight__fail-banner" role="alert" id="execute-preflight-fail">
                <strong>Configuration issues detected.</strong>{" "}
                Resolve the failing checks by correcting your configuration.
                <button
                  type="button"
                  className="button button--secondary execute-preflight__fix-btn"
                  onClick={onBackToConfig}
                  id="execute-preflight-fix-btn"
                >
                  ← Fix Configuration (Screen 9)
                </button>
              </div>
            )}
          </section>

          {/* Generate plan button */}
          <div className="execute-generate-row" id="execute-generate-row">
            <div className="execute-generate-row__info">
              <strong>Generate Dry-Run Plan</strong>
              <p>
                Creates a local simulation of the deployment steps. No cloud resources will be created or modified.
                Explicit confirmation required before any real provisioning (not available in this version).
              </p>
            </div>
            <button
              type="button"
              className="button button--primary"
              onClick={handleGeneratePlan}
              disabled={!allDone}
              id="execute-generate-btn"
              aria-disabled={!allDone}
              title={!allDone ? "Complete all preflight checks first" : "Generate the dry-run deployment plan"}
            >
              Generate Dry-Run Plan
            </button>
          </div>
        </>
      )}

      {/* ── Phase: GENERATING ── */}
      {pageState === "generating" && (
        <div className="execute-generating" id="execute-generating" role="status" aria-live="polite">
          <div className="execute-generating__spinner" aria-hidden="true">⚙</div>
          <div className="execute-generating__label">Generating dry-run plan locally…</div>
          <div className="execute-generating__note">No cloud calls are being made.</div>
        </div>
      )}

      {/* ── Phase: DONE ── */}
      {pageState === "done" && plan && !isPlanStale && (
        <>
          {/* Config strip from plan snapshot */}
          <ConfigSummaryStrip plan={plan} />

          {/* Plan status */}
          <div
            className={`execute-plan-status ${plan.planStatus === "ready" ? "execute-plan-status--ready" : "execute-plan-status--blocked"}`}
            id="execute-plan-status"
            role="status"
          >
            <div className="execute-plan-status__icon">
              {plan.planStatus === "ready" ? "✓" : "✗"}
            </div>
            <div className="execute-plan-status__body">
              <div className="execute-plan-status__title">
                {plan.planStatus === "ready" ? "Plan generated" : "Plan blocked"}
              </div>
              <div className="execute-plan-status__message">{plan.summaryMessage}</div>
              {plan.blockReason && (
                <div className="execute-plan-status__block-reason" role="alert">
                  {plan.blockReason}
                </div>
              )}
              <div className="execute-plan-status__provenance">
                Plan ID: <code>{plan.planId}</code> · Source: {plan.provenance.source} · Type: {plan.provenance.planType}
              </div>
            </div>
          </div>

          {/* Execution stages */}
          {plan.planStatus === "ready" && (
            <section className="execute-stages" id="execute-stages">
              <div className="execute-stages__header">
                <h2 className="execute-stages__title">Proposed Deployment Stages</h2>
                <p className="execute-stages__subtitle">
                  The following stages represent what <em>would</em> happen in a real deployment.
                  All stages are <strong>simulated</strong> — no cloud operations are performed.
                </p>
              </div>
              <div className="execute-stages__list" id="execute-stages-list">
                {plan.stages.map((stage, i) => (
                  <StageCard key={stage.id} stage={stage} index={i} />
                ))}
              </div>
            </section>
          )}

          {/* Fix config button if blocked */}
          {plan.planStatus === "blocked" && (
            <div className="execute-blocked-actions" id="execute-blocked-actions">
              <button
                type="button"
                className="button button--primary"
                onClick={onBackToConfig}
                id="execute-blocked-fix-btn"
              >
                ← Fix Configuration (Screen 9)
              </button>
            </div>
          )}

          {/* Final disclaimer */}
          <section className="execute-disclaimer" id="execute-disclaimer" role="note">
            <div className="execute-disclaimer__title">⚠ Dry-Run Disclaimer</div>
            <p className="execute-disclaimer__body">
              This plan is a <strong>local simulation only</strong>. It does not represent a confirmed
              deployment, a cloud provider quote, or evidence that the described resources can be
              created with the current configuration. No AWS, Azure, or GCP APIs were called.
              No cloud resources were created, modified, or deleted. The deployment status of
              this application remains <strong>Not deployed</strong>.
            </p>
            <p className="execute-disclaimer__body">
              To initiate a real deployment, a production-grade deployment adapter is required.
              This feature is not available in Sentryɸ v1.
            </p>
          </section>

          {/* Regenerate */}
          <div className="execute-regen-row" id="execute-regen-row">
            <button
              type="button"
              className="button button--ghost"
              onClick={handleRegenerate}
              id="execute-regen-btn"
            >
              ↩ Start Over / Regenerate Plan
            </button>
          </div>
        </>
      )}

      {/* ── Actions ── */}
      <div className="execute-page__actions" id="execute-page-actions">
        <button
          type="button"
          className="button button--secondary"
          onClick={onBack}
          id="execute-back-btn"
        >
          ← Back to Cloud Compare
        </button>
        <button
          type="button"
          className="button button--ghost"
          onClick={onBackToConfig}
          id="execute-back-config-btn"
        >
          ← Back to Configuration
        </button>
      </div>
    </div>
  );
}
