/**
 * Sentryɸ -- Deploy Configuration Types
 * services/deployTypes.ts
 *
 * Typed deployment configuration model for Screen 9 (Deploy Configuration).
 *
 * Architecture decisions applied:
 *   D-022: AWS only for provisioning; Azure/GCP = config docs only
 *   D-023: Plan → User review → Provision → Verify (Screen 9 is the Plan step)
 *   D-017: Credentials live in OS keychain only (never in this config object)
 *
 * IMPORTANT: This is a PLAN object only. No deployment has occurred
 * when this type is populated. Deployment execution is Screen 11.
 *
 * Fields deliberately excluded:
 *   - Cloud credentials (access key, secret key, service account) — OS keychain only
 *   - Live resource IDs — not provisioned yet
 *   - Real pricing data — not available without cloud API call
 */

// ─────────────────────────────────────────────
//  Provider and deployment mode enumerations
// ─────────────────────────────────────────────

/**
 * Supported cloud providers.
 * AWS: provisioning supported (D-022)
 * azure, gcp: configuration documentation only — no automated provisioning in v1
 */
export type CloudProvider = "aws" | "azure" | "gcp";

/**
 * Deployment modes for AWS (the only provider with automated provisioning).
 *
 * bedrock:    Amazon Bedrock managed model endpoint (no inference server needed)
 * sagemaker:  SageMaker real-time inference endpoint (bring your own model)
 * lambda:     API Gateway + Lambda (serverless, lightweight, smaller models)
 */
export type AwsDeploymentMode = "bedrock" | "sagemaker" | "lambda";

/** Endpoint access scope */
export type EndpointScope = "private" | "public";

// ─────────────────────────────────────────────
//  AWS regions (static list — no live API call)
// ─────────────────────────────────────────────

export interface AwsRegion {
  id:    string;
  label: string;
  /** Whether Bedrock is documented as available. Static, may be out-of-date. */
  bedrockAvailable: boolean;
}

export const AWS_REGIONS: AwsRegion[] = [
  { id: "us-east-1",      label: "US East (N. Virginia)",  bedrockAvailable: true },
  { id: "us-west-2",      label: "US West (Oregon)",        bedrockAvailable: true },
  { id: "eu-west-1",      label: "Europe (Ireland)",         bedrockAvailable: true },
  { id: "eu-central-1",   label: "Europe (Frankfurt)",       bedrockAvailable: false },
  { id: "ap-southeast-1", label: "Asia Pacific (Singapore)", bedrockAvailable: false },
  { id: "ap-northeast-1", label: "Asia Pacific (Tokyo)",     bedrockAvailable: false },
];

// ─────────────────────────────────────────────
//  AWS deployment modes — metadata
// ─────────────────────────────────────────────

export interface DeploymentModeInfo {
  id:          AwsDeploymentMode;
  label:       string;
  description: string;
  supportsGpu: boolean;
}

export const AWS_DEPLOYMENT_MODES: DeploymentModeInfo[] = [
  {
    id:          "bedrock",
    label:       "Amazon Bedrock",
    description: "Fully managed foundation model service. No inference infrastructure to manage.",
    supportsGpu: false,
  },
  {
    id:          "sagemaker",
    label:       "Amazon SageMaker",
    description: "Managed ML inference endpoint. Supports custom model artifacts and GPU instances.",
    supportsGpu: true,
  },
  {
    id:          "lambda",
    label:       "API Gateway + Lambda",
    description: "Serverless function endpoint. Best for lightweight or adapter-style deployments.",
    supportsGpu: false,
  },
];

// ─────────────────────────────────────────────
//  AWS instance types (for SageMaker only)
// ─────────────────────────────────────────────

export interface AwsInstanceType {
  id:     string;
  label:  string;
  gpu:    boolean;
  notes:  string;
}

export const SAGEMAKER_INSTANCE_TYPES: AwsInstanceType[] = [
  { id: "ml.m5.xlarge",   label: "ml.m5.xlarge (4 vCPU, 16 GB)",    gpu: false, notes: "CPU — lightweight adapters" },
  { id: "ml.m5.2xlarge",  label: "ml.m5.2xlarge (8 vCPU, 32 GB)",   gpu: false, notes: "CPU — standard" },
  { id: "ml.g4dn.xlarge", label: "ml.g4dn.xlarge (1x T4, 16 GB)",   gpu: true,  notes: "GPU — small models" },
  { id: "ml.g4dn.2xlarge",label: "ml.g4dn.2xlarge (1x T4, 32 GB)",  gpu: true,  notes: "GPU — recommended" },
  { id: "ml.g5.xlarge",   label: "ml.g5.xlarge (1x A10G, 24 GB)",   gpu: true,  notes: "GPU — larger models" },
  { id: "ml.g5.2xlarge",  label: "ml.g5.2xlarge (1x A10G, 24 GB)",  gpu: true,  notes: "GPU — production" },
];

// ─────────────────────────────────────────────
//  Validation
// ─────────────────────────────────────────────

export type ValidationStatus = "valid" | "invalid" | "unverified" | "incomplete";

export interface FieldValidation {
  status:  ValidationStatus;
  message: string | null;
}

export interface DeployConfigValidation {
  provider:         FieldValidation;
  mode:             FieldValidation;
  region:           FieldValidation;
  modelId:          FieldValidation;
  instanceType:     FieldValidation;
  replicas:         FieldValidation;
  endpointScope:    FieldValidation;
  budgetMonthlyUsd: FieldValidation;
  /** Overall: all required fields valid and no blocking errors */
  canProceed:       boolean;
  /** List of blocking issues preventing proceed */
  blockingIssues:   string[];
}

// ─────────────────────────────────────────────
//  Core deployment configuration model
// ─────────────────────────────────────────────

/**
 * DeployConfig — the deployment plan assembled on Screen 9.
 *
 * This is a PLAN only. No resources are created until the user
 * explicitly approves and executes (Screen 11).
 *
 * Credentials are NEVER stored here — they live in the OS keychain (D-017).
 */
export interface DeployConfig {
  // Provider selection
  provider:       CloudProvider | null;

  // AWS-specific
  mode:           AwsDeploymentMode | null;
  region:         string | null;

  // Model / workload
  /** Model identifier — e.g. "anthropic.claude-3-sonnet-20240229-v1:0" for Bedrock */
  modelId:        string;
  /** Friendly name for display only */
  modelLabel:     string;

  // SageMaker compute (only if mode === "sagemaker")
  instanceType:   string | null;
  replicas:       number;

  // Network / access
  endpointScope:  EndpointScope;
  /** Require API key authentication on the endpoint */
  requireAuth:    boolean;
  /** Enable CloudWatch logging */
  enableLogging:  boolean;
  /** Enable Bedrock Guardrails (Bedrock mode only) */
  enableGuardrails: boolean;

  // Budget constraint (informational — not a hard cloud-side limit)
  budgetMonthlyUsd: number | null;

  // Provenance
  /** scan_id of the assessment this plan is based on — may be null if report unavailable */
  sourceScanId:   string | null;
  /** True if the source assessment was simulated */
  isSimulated:    boolean;

  // Plan status
  /** ISO timestamp when config was last modified */
  lastModifiedAt: string;
  /** Deployment has NOT been executed — this is always false in Screen 9 */
  deployed:       false;
}

/**
 * Empty/default configuration — safe starting state.
 * All booleans default to the safer option.
 */
export function emptyDeployConfig(): DeployConfig {
  return {
    provider:         null,
    mode:             null,
    region:           null,
    modelId:          "",
    modelLabel:       "",
    instanceType:     null,
    replicas:         1,
    endpointScope:    "private",  // Safe default — never silently public
    requireAuth:      true,       // Require auth by default
    enableLogging:    true,       // Logging on by default
    enableGuardrails: false,      // Off until user enables
    budgetMonthlyUsd: null,
    sourceScanId:     null,
    isSimulated:      false,
    lastModifiedAt:   new Date().toISOString(),
    deployed:         false,
  };
}

// ─────────────────────────────────────────────
//  Validation functions (pure — no side effects)
// ─────────────────────────────────────────────

function fieldOk(message: string | null = null): FieldValidation {
  return { status: "valid", message };
}
function fieldErr(message: string): FieldValidation {
  return { status: "invalid", message };
}
function fieldUnverified(message: string): FieldValidation {
  return { status: "unverified", message };
}
function fieldIncomplete(message: string): FieldValidation {
  return { status: "incomplete", message };
}

export function validateDeployConfig(cfg: DeployConfig): DeployConfigValidation {
  const issues: string[] = [];

  // Provider
  let providerV: FieldValidation;
  if (!cfg.provider) {
    providerV = fieldIncomplete("Select a cloud provider");
    issues.push("Cloud provider is required");
  } else if (cfg.provider === "azure" || cfg.provider === "gcp") {
    providerV = fieldUnverified(`${cfg.provider.toUpperCase()} automated provisioning is not supported in v1. Configuration planning is available.`);
    // Not blocking — user can still build a config plan
  } else {
    providerV = fieldOk();
  }

  // Deployment mode
  let modeV: FieldValidation;
  if (cfg.provider !== "aws") {
    // Only AWS has mode selection
    modeV = { status: "unverified", message: null };
  } else if (!cfg.mode) {
    modeV = fieldIncomplete("Select a deployment mode");
    issues.push("Deployment mode is required");
  } else {
    modeV = fieldOk();
  }

  // Region
  let regionV: FieldValidation;
  if (!cfg.region) {
    regionV = fieldIncomplete("Select a region");
    issues.push("Region is required");
  } else if (cfg.provider === "aws") {
    const regionDef = AWS_REGIONS.find((r) => r.id === cfg.region);
    if (!regionDef) {
      regionV = fieldErr(`Unrecognised region: ${cfg.region}`);
      issues.push("Region is not valid");
    } else if (cfg.mode === "bedrock" && !regionDef.bedrockAvailable) {
      regionV = fieldUnverified(`Amazon Bedrock may not be available in ${regionDef.label}. Verify availability before provisioning.`);
      // Warn but not blocking
    } else {
      regionV = fieldOk();
    }
  } else {
    regionV = fieldUnverified("Region availability not verified for this provider");
  }

  // Model ID
  let modelIdV: FieldValidation;
  if (!cfg.modelId || cfg.modelId.trim() === "") {
    modelIdV = fieldIncomplete("Enter a model identifier");
    issues.push("Model identifier is required");
  } else if (cfg.modelId.trim().length < 3) {
    modelIdV = fieldErr("Model identifier is too short");
    issues.push("Model identifier is invalid");
  } else if (cfg.provider === "aws" && cfg.mode === "bedrock") {
    // Bedrock model IDs have a known format
    modelIdV = fieldUnverified("Model ID format unverified — confirm this is a valid Bedrock model ARN or ID");
  } else {
    modelIdV = fieldOk();
  }

  // Instance type (SageMaker only)
  let instanceTypeV: FieldValidation;
  if (cfg.provider === "aws" && cfg.mode === "sagemaker") {
    if (!cfg.instanceType) {
      instanceTypeV = fieldIncomplete("Select an instance type");
      issues.push("Instance type is required for SageMaker");
    } else {
      const known = SAGEMAKER_INSTANCE_TYPES.find((t) => t.id === cfg.instanceType);
      instanceTypeV = known ? fieldOk() : fieldUnverified("Custom instance type — verify availability");
    }
  } else {
    instanceTypeV = { status: "valid", message: null };
  }

  // Replicas
  let replicasV: FieldValidation;
  if (cfg.replicas < 1) {
    replicasV = fieldErr("Minimum 1 replica required");
    issues.push("Replica count must be at least 1");
  } else if (cfg.replicas > 10) {
    replicasV = fieldUnverified("High replica count — verify quota availability in your AWS account");
  } else {
    replicasV = fieldOk();
  }

  // Endpoint scope
  let endpointScopeV: FieldValidation;
  if (cfg.endpointScope === "public") {
    endpointScopeV = fieldUnverified(
      "Public endpoint exposes the model to the internet. Ensure authentication is enabled and access is properly scoped."
    );
    if (!cfg.requireAuth) {
      endpointScopeV = fieldErr("Public endpoint without authentication is a security risk. Enable authentication or switch to private.");
      issues.push("Public endpoint requires authentication to be enabled");
    }
  } else {
    endpointScopeV = fieldOk();
  }

  // Budget
  let budgetV: FieldValidation;
  if (cfg.budgetMonthlyUsd !== null) {
    if (cfg.budgetMonthlyUsd <= 0) {
      budgetV = fieldErr("Budget must be greater than $0");
      issues.push("Budget amount is invalid");
    } else if (cfg.budgetMonthlyUsd > 100_000) {
      budgetV = fieldUnverified("Budget exceeds $100,000/month — verify this is intentional");
    } else {
      budgetV = fieldUnverified(
        "Budget is informational only — it does not enforce a hard AWS spending limit. Enable AWS Budgets separately."
      );
    }
  } else {
    budgetV = fieldOk();
  }

  return {
    provider:         providerV,
    mode:             modeV,
    region:           regionV,
    modelId:          modelIdV,
    instanceType:     instanceTypeV,
    replicas:         replicasV,
    endpointScope:    endpointScopeV,
    budgetMonthlyUsd: budgetV,
    canProceed:       issues.length === 0,
    blockingIssues:   issues,
  };
}
