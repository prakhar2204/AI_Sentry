/**
 * Sentryɸ -- Dry-Run Plan Types
 * services/dryRunTypes.ts
 *
 * Typed model for the Screen 11 dry-run deployment plan.
 *
 * INVARIANTS (enforced in this file and in DeployExecutePage.tsx):
 *   - deployed remains false — a dry-run never changes actual deployment state
 *   - No cloud API calls are made — plan is generated locally from DeployConfig
 *   - No credentials are used or stored
 *   - No real resource IDs are generated
 *   - All plan content is explicitly marked DRY_RUN / SIMULATED
 *   - Azure and GCP cannot enter the execution simulation
 *
 * Follows D-023: Plan → User review → Provision → Verify
 *   This module covers the "Plan" and "User review" steps only.
 *   "Provision" and "Verify" are out of scope for v1.
 */

import type { DeployConfig, CloudProvider, AwsDeploymentMode } from "./deployTypes";
import { validateDeployConfig } from "./deployTypes";

// ─────────────────────────────────────────────
//  Plan stage model
// ─────────────────────────────────────────────

/** Execution status of a single plan stage */
export type StageStatus =
  | "planned"    // Will run when plan executes (dry-run only)
  | "simulated"  // Shown as a simulation step — no real action taken
  | "skipped"    // Not applicable for this config (e.g. GPU setup for Bedrock)
  | "blocked";   // Cannot proceed — validation issue

export interface DryRunStage {
  /** Short unique key */
  id:          string;
  /** Human-readable label */
  label:       string;
  /** What this stage would do in a real deployment */
  description: string;
  /** Dry-run note — what the simulation does instead */
  dryRunNote:  string;
  status:      StageStatus;
  /** If blocked, why it is blocked */
  blockReason: string | null;
}

// ─────────────────────────────────────────────
//  Preflight check model
// ─────────────────────────────────────────────

export type PreflightCheckStatus = "pass" | "fail" | "warn" | "user-ack";

export interface PreflightCheck {
  id:          string;
  label:       string;
  description: string;
  status:      PreflightCheckStatus;
  /** For user-ack items: has the user acknowledged? */
  acknowledged: boolean;
  /** Why this check failed/warned */
  reason:      string | null;
}

// ─────────────────────────────────────────────
//  Plan provenance (anti-fabrication)
// ─────────────────────────────────────────────

/**
 * Provenance record embedded in every DryRunPlan.
 * Makes clear that this is a local simulation, not a cloud response.
 */
export interface PlanProvenance {
  /** Always "local-simulation" — never "aws-response" or "cloud-api" */
  source:      "local-simulation";
  /** Always "dry-run" */
  planType:    "dry-run";
  /** Config snapshot reference (lastModifiedAt of source config) */
  configSnapshotAt: string;
  /** When the plan was generated (local Date.now()) */
  generatedAt: string;
}

// ─────────────────────────────────────────────
//  Full plan
// ─────────────────────────────────────────────

export interface DryRunPlan {
  /**
   * Plan identifier — locally generated, NOT a cloud resource ID.
   * Format: drp-<timestamp>-<random>
   * Prefix "drp-" distinguishes from real resource IDs.
   */
  planId:       string;

  provenance:   PlanProvenance;

  /** Provider from config */
  provider:     CloudProvider;

  /** Mode (AWS-only) */
  mode:         AwsDeploymentMode | null;

  /** Region from config */
  region:       string | null;

  /** Model/workload identifier */
  modelId:      string;

  /** Whether all preflight checks passed (automatically verified ones only) */
  preflightPassed: boolean;

  /** All preflight checks */
  preflightChecks: PreflightCheck[];

  /** Planned execution stages */
  stages:       DryRunStage[];

  /**
   * Final status after plan generation.
   * "ready"  = plan generated, user may review
   * "blocked" = plan cannot proceed due to validation failures
   */
  planStatus:   "ready" | "blocked";

  /** Why planStatus is "blocked", if applicable */
  blockReason:  string | null;

  /**
   * Explicit dry-run summary message.
   * MUST NOT use language implying real deployment success.
   * Correct: "Dry-run plan generated — no cloud resources created."
   */
  summaryMessage: string;

  /** The config snapshot this plan was derived from */
  configSnapshot: Readonly<DeployConfig>;
}

// ─────────────────────────────────────────────
//  Preflight check builders (pure functions)
// ─────────────────────────────────────────────

function _checkProviderSelected(cfg: DeployConfig): PreflightCheck {
  const pass = cfg.provider !== null;
  return {
    id:           "provider-selected",
    label:        "Cloud provider selected",
    description:  "A cloud provider must be selected before generating a deployment plan.",
    status:       pass ? "pass" : "fail",
    acknowledged: false,
    reason:       pass ? null : "No provider selected. Return to Screen 9.",
  };
}

function _checkProviderSupported(cfg: DeployConfig): PreflightCheck {
  const supported = cfg.provider === "aws";
  const planOnly  = cfg.provider === "azure" || cfg.provider === "gcp";
  let status: PreflightCheckStatus = "fail";
  let reason: string | null = null;

  if (supported) {
    status = "pass";
  } else if (planOnly) {
    status = "fail";
    reason = `${cfg.provider?.toUpperCase()} deployment is not automated in Sentryɸ v1. This provider is plan-only. Export the configuration plan and use the provider's console or CLI.`;
  } else {
    status = "fail";
    reason = "No provider selected.";
  }

  return {
    id:           "provider-supported",
    label:        "Provider supports automated provisioning",
    description:  "Only AWS supports automated provisioning in Sentryɸ v1. Azure and GCP are plan-only.",
    status,
    acknowledged: false,
    reason,
  };
}

function _checkModeSelected(cfg: DeployConfig): PreflightCheck {
  const pass = cfg.provider !== "aws" || cfg.mode !== null;
  return {
    id:           "mode-selected",
    label:        "Deployment mode selected",
    description:  "An AWS deployment mode (Bedrock, SageMaker, or Lambda) must be selected.",
    status:       pass ? "pass" : "fail",
    acknowledged: false,
    reason:       pass ? null : "No deployment mode selected. Return to Screen 9.",
  };
}

function _checkModelId(cfg: DeployConfig): PreflightCheck {
  const pass = cfg.modelId.trim().length > 0;
  return {
    id:           "model-id",
    label:        "Model / workload identifier set",
    description:  "A model or workload identifier is required to generate a deployment plan.",
    status:       pass ? "pass" : "fail",
    acknowledged: false,
    reason:       pass ? null : "Model identifier is empty. Return to Screen 9.",
  };
}

function _checkRegion(cfg: DeployConfig): PreflightCheck {
  const pass = cfg.region !== null && cfg.region.trim().length > 0;
  return {
    id:           "region",
    label:        "Deployment region set",
    description:  "A cloud region must be specified for the deployment.",
    status:       pass ? "pass" : "fail",
    acknowledged: false,
    reason:       pass ? null : "Region not selected. Return to Screen 9.",
  };
}

function _checkSageMakerInstance(cfg: DeployConfig): PreflightCheck | null {
  if (cfg.provider !== "aws" || cfg.mode !== "sagemaker") return null;
  const pass = cfg.instanceType !== null;
  return {
    id:           "sagemaker-instance",
    label:        "SageMaker instance type selected",
    description:  "SageMaker mode requires an instance type to define compute resources.",
    status:       pass ? "pass" : "fail",
    acknowledged: false,
    reason:       pass ? null : "No instance type selected for SageMaker. Return to Screen 9.",
  };
}

function _checkPublicEndpointAck(cfg: DeployConfig): PreflightCheck | null {
  if (cfg.endpointScope !== "public") return null;
  return {
    id:           "public-endpoint-ack",
    label:        "Public endpoint exposure acknowledged",
    description:  "Your configuration exposes the endpoint publicly. Confirm you have reviewed the security implications.",
    status:       "user-ack",
    acknowledged: false,
    reason:       null,
  };
}

function _checkNoAuthAck(cfg: DeployConfig): PreflightCheck | null {
  if (cfg.requireAuth) return null;
  return {
    id:           "no-auth-ack",
    label:        "No authentication mode acknowledged",
    description:  "Authentication is disabled. Anyone who can reach the endpoint can use it. Confirm this is intentional.",
    status:       "user-ack",
    acknowledged: false,
    reason:       null,
  };
}

function _checkDryRunOnly(): PreflightCheck {
  return {
    id:           "dry-run-only",
    label:        "This is a dry-run simulation",
    description:  "No cloud resources will be created. The plan below is a proposed sequence of steps for review only.",
    status:       "user-ack",
    acknowledged: false,
    reason:       null,
  };
}

/** Build all applicable preflight checks for a config */
export function buildPreflightChecks(cfg: DeployConfig): PreflightCheck[] {
  const checks: PreflightCheck[] = [
    _checkProviderSelected(cfg),
    _checkProviderSupported(cfg),
    _checkModeSelected(cfg),
    _checkModelId(cfg),
    _checkRegion(cfg),
  ];

  const sagemakerCheck = _checkSageMakerInstance(cfg);
  if (sagemakerCheck) checks.push(sagemakerCheck);

  const pubAck = _checkPublicEndpointAck(cfg);
  if (pubAck) checks.push(pubAck);

  const noAuthAck = _checkNoAuthAck(cfg);
  if (noAuthAck) checks.push(noAuthAck);

  // Always last — user must acknowledge dry-run nature
  checks.push(_checkDryRunOnly());

  return checks;
}

/** Returns true only when all non-user-ack checks pass AND all user-ack checks are acknowledged */
export function areAllPreflightChecksDone(checks: PreflightCheck[]): boolean {
  return checks.every((c) => {
    if (c.status === "pass") return true;
    if (c.status === "user-ack") return c.acknowledged;
    return false; // fail or warn → not ready
  });
}

/** Returns true only when all automated checks (non-user-ack) pass */
export function areAutomatedChecksPassed(checks: PreflightCheck[]): boolean {
  return checks
    .filter((c) => c.status !== "user-ack")
    .every((c) => c.status === "pass");
}

// ─────────────────────────────────────────────
//  Stage builders (pure functions)
// ─────────────────────────────────────────────

function _stageValidate(cfg: DeployConfig): DryRunStage {
  const validation = validateDeployConfig(cfg);
  const valid = validation.canProceed;
  return {
    id:          "validate-config",
    label:       "Validate configuration",
    description: "Verify all required fields are present and consistent.",
    dryRunNote:  valid
      ? "Configuration is valid — all required fields are set."
      : `Configuration has validation errors: ${validation.blockingIssues.join("; ")}`,
    status:      valid ? "simulated" : "blocked",
    blockReason: valid ? null : `Validation failed: ${validation.blockingIssues.join("; ")}`,
  };
}

function _stageResolveProvider(cfg: DeployConfig): DryRunStage {
  const provLabel: Record<string, string> = {
    aws:   "Amazon Web Services",
    azure: "Microsoft Azure",
    gcp:   "Google Cloud Platform",
  };
  return {
    id:          "resolve-provider",
    label:       "Resolve provider and mode",
    description: "Determine the deployment target based on provider and mode selection.",
    dryRunNote:  `Provider: ${provLabel[cfg.provider ?? ""] ?? cfg.provider} · Mode: ${cfg.mode ?? "N/A"} · Region: ${cfg.region ?? "N/A"}`,
    status:      "simulated",
    blockReason: null,
  };
}

function _stagePrepareSpec(cfg: DeployConfig): DryRunStage {
  let description = "";
  let dryRunNote  = "";

  if (cfg.mode === "bedrock") {
    description = "Prepare Bedrock model invocation specification.";
    dryRunNote  = `Would configure Bedrock model endpoint for: ${cfg.modelId}. Guardrails: ${cfg.enableGuardrails ? "enabled" : "disabled"}.`;
  } else if (cfg.mode === "sagemaker") {
    description = "Prepare SageMaker endpoint configuration and model artifact specification.";
    dryRunNote  = `Would create SageMaker endpoint with ${cfg.instanceType ?? "no instance type"} × ${cfg.replicas} replica(s) for model: ${cfg.modelId}.`;
  } else if (cfg.mode === "lambda") {
    description = "Prepare API Gateway and Lambda function specification.";
    dryRunNote  = `Would configure Lambda function with API Gateway for model: ${cfg.modelId}.`;
  } else {
    description = "Prepare workload deployment specification.";
    dryRunNote  = `Would prepare deployment spec for: ${cfg.modelId}.`;
  }

  return {
    id:          "prepare-spec",
    label:       "Prepare deployment specification",
    description,
    dryRunNote,
    status:      "simulated",
    blockReason: null,
  };
}

function _stageSecurityReview(cfg: DeployConfig): DryRunStage {
  const issues: string[] = [];
  if (cfg.endpointScope === "public" && !cfg.requireAuth) {
    issues.push("Public endpoint with no authentication — high risk");
  }
  if (cfg.endpointScope === "public") {
    issues.push("Public exposure: ensure IP allowlisting or API key auth is configured before real provisioning");
  }
  if (!cfg.enableLogging) {
    issues.push("Logging is disabled — consider enabling for audit trail");
  }

  return {
    id:          "security-review",
    label:       "Review security settings",
    description: "Audit endpoint scope, authentication, and logging configuration.",
    dryRunNote:  issues.length > 0
      ? `⚠ Security review notes: ${issues.join("; ")}`
      : "Security settings look reasonable for a private endpoint with authentication.",
    status:      "simulated",
    blockReason: null,
  };
}

function _stageResourcePlan(cfg: DeployConfig): DryRunStage {
  let dryRunNote = "";

  if (cfg.mode === "bedrock") {
    dryRunNote = `Bedrock is fully managed — no compute instances to provision. Model invocation is on-demand.`;
  } else if (cfg.mode === "sagemaker") {
    dryRunNote = `Would propose: ${cfg.instanceType ?? "instance TBD"} × ${cfg.replicas} replica(s). Approx. always-on cost: see Cloud Compare screen.`;
  } else if (cfg.mode === "lambda") {
    dryRunNote = "Lambda is consumption-based. No persistent instances. API Gateway would route requests.";
  } else {
    dryRunNote = "Resource plan depends on provider and mode selection.";
  }

  return {
    id:          "resource-plan",
    label:       "Propose resource plan",
    description: "Define the cloud resources that would be created in a real deployment.",
    dryRunNote,
    status:      "simulated",
    blockReason: null,
  };
}

function _stageDryRunSummary(valid: boolean): DryRunStage {
  return {
    id:          "dry-run-summary",
    label:       "Generate dry-run summary",
    description: "Produce the final plan report for user review.",
    dryRunNote:  valid
      ? "Dry-run plan generated — no cloud resources created. Review the plan above before initiating a real deployment."
      : "Plan generation blocked by validation errors — review and correct the configuration on Screen 9.",
    status:      valid ? "simulated" : "blocked",
    blockReason: null,
  };
}

/** Build the complete stage list for a config */
export function buildPlanStages(cfg: DeployConfig): DryRunStage[] {
  const validation = validateDeployConfig(cfg);
  const valid = validation.canProceed && cfg.provider === "aws";

  const stages: DryRunStage[] = [
    _stageValidate(cfg),
    _stageResolveProvider(cfg),
  ];

  if (valid) {
    stages.push(
      _stagePrepareSpec(cfg),
      _stageSecurityReview(cfg),
      _stageResourcePlan(cfg),
    );
  }

  stages.push(_stageDryRunSummary(valid));

  return stages;
}

// ─────────────────────────────────────────────
//  Plan ID generator (local only, not a cloud ID)
// ─────────────────────────────────────────────

function _generateLocalPlanId(): string {
  const ts  = Date.now().toString(36);
  const rnd = Math.random().toString(36).slice(2, 7);
  return `drp-${ts}-${rnd}`;
}

// ─────────────────────────────────────────────
//  Main plan builder (pure function)
// ─────────────────────────────────────────────

/**
 * Build a DryRunPlan from a DeployConfig.
 *
 * Pure function — no side effects, no API calls.
 * Called when the user clicks "Generate Dry-Run Plan" on Screen 11.
 *
 * The returned plan:
 *   - Has planId prefixed "drp-" (never a real cloud resource ID)
 *   - Has provenance.source = "local-simulation"
 *   - Has summaryMessage that never claims real deployment success
 *   - Has configSnapshot that captures the config at plan-generation time
 */
export function buildDryRunPlan(
  cfg: DeployConfig,
  acknowledgedCheckIds: Set<string>
): DryRunPlan {
  const now = new Date().toISOString();
  const validation = validateDeployConfig(cfg);

  // Build preflight checks, applying acknowledgement state
  const rawChecks = buildPreflightChecks(cfg);
  const checks = rawChecks.map((c) => ({
    ...c,
    acknowledged: acknowledgedCheckIds.has(c.id) ? true : c.acknowledged,
  }));

  const automatedPassed = areAutomatedChecksPassed(checks);
  const isBlocked = !automatedPassed || cfg.provider !== "aws";

  const stages = buildPlanStages(cfg);

  let blockReason: string | null = null;
  let summaryMessage: string;

  if (cfg.provider === "azure" || cfg.provider === "gcp") {
    blockReason = `${cfg.provider?.toUpperCase()} provisioning is not automated in Sentryɸ v1. This provider is plan-only. Export the configuration and use the provider's console or CLI.`;
    summaryMessage = `Plan-only: ${cfg.provider?.toUpperCase()} deployment cannot be simulated. No cloud resources created.`;
  } else if (!automatedPassed) {
    const failedChecks = checks
      .filter((c) => c.status === "fail")
      .map((c) => c.label)
      .join("; ");
    blockReason = `Preflight checks failed: ${failedChecks || "see checks above"}. Correct the configuration on Screen 9 before generating a plan.`;
    summaryMessage = "Dry-run plan blocked — configuration is incomplete or invalid. No cloud resources created.";
  } else {
    summaryMessage = "Dry-run plan generated — no cloud resources created. This is a simulation only.";
  }

  return {
    planId:          _generateLocalPlanId(),
    provenance: {
      source:          "local-simulation",
      planType:        "dry-run",
      configSnapshotAt: cfg.lastModifiedAt,
      generatedAt:     now,
    },
    provider:         cfg.provider!,
    mode:             cfg.mode,
    region:           cfg.region,
    modelId:          cfg.modelId,
    preflightPassed:  automatedPassed,
    preflightChecks:  checks,
    stages,
    planStatus:       isBlocked ? "blocked" : "ready",
    blockReason,
    summaryMessage,
    configSnapshot:   Object.freeze({ ...cfg }),
  };
}

// ─────────────────────────────────────────────
//  Stale detection
// ─────────────────────────────────────────────

/**
 * Returns true if the plan was generated from an older config.
 * Used to show "Configuration changed — regenerate plan" warning.
 */
export function isDryRunPlanStale(
  plan: DryRunPlan,
  currentConfig: DeployConfig
): boolean {
  return plan.provenance.configSnapshotAt !== currentConfig.lastModifiedAt;
}
