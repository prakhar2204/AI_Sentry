/**
 * Sentryɸ — Deploy IPC Type Contracts (W2)
 * services/deployIpcTypes.ts
 *
 * Shared TypeScript types for all deploy operations.
 * These mirror the Python backend dataclasses in core/deploy/base.py.
 */

// ─────────────────────────────────────────────
//  Provider types
// ─────────────────────────────────────────────

export type DeployProvider = "aws" | "azure" | "gcp" | "private";

export type CredentialStatus =
  | "valid"
  | "invalid"
  | "expired"
  | "missing"
  | "unknown";

export type DeployStatus =
  | "pending"
  | "running"
  | "complete"
  | "failed"
  | "rolled_back";

export type PrivateStack = "docker_compose" | "kubernetes" | "bare_metal";

// ─────────────────────────────────────────────
//  Cloud deploy config (from UI settings)
// ─────────────────────────────────────────────

export interface AwsDeployConfig {
  region:            string;
  deployment_mode:   "bedrock" | "sagemaker" | "lambda";
  endpoint_scope:    "public" | "private";
  instance_type?:    string;   // SageMaker only
  model_id?:         string;   // Bedrock only
  budget_alert_usd?: number;
}

export interface AzureDeployConfig {
  region:                 string;
  deployment_mode:        "ai_services" | "container" | "app_service";
  endpoint_scope:         "public" | "private";
  container_image?:       string;
  enable_content_safety?: boolean;
}

export interface GcpDeployConfig {
  region:                  string;
  deployment_mode:         "vertex_ai" | "cloud_run" | "cloud_functions";
  endpoint_scope:          "public" | "private";
  container_image?:        string;
  enable_cloud_armor?:     boolean;
  enable_model_monitoring?: boolean;
}

export interface PrivateDeployConfig {
  stack:               PrivateStack;
  domain:              string;
  model_image?:        string;
  model_name?:         string;
  enable_rate_limiting?: boolean;
  rate_limit_rps?:     number;
  output_dir?:         string;
  // Kubernetes specific
  k8s_namespace?: string;
  replicas?:      number;
  min_replicas?:  number;
  max_replicas?:  number;
}

export type CloudDeployConfig =
  | AwsDeployConfig
  | AzureDeployConfig
  | GcpDeployConfig
  | PrivateDeployConfig;

// ─────────────────────────────────────────────
//  Deploy Resource
// ─────────────────────────────────────────────

export interface DeployResource {
  resource_type: string;
  resource_id:   string;
  region:        string;
  arn_or_id:     string;
  status:        string;
}

// ─────────────────────────────────────────────
//  Cost estimate
// ─────────────────────────────────────────────

export interface CostEstimate {
  low_usd:   number;
  high_usd:  number;
  currency?: string;
  basis?:    string;
  source?:   string;
  note?:     string;
  breakdown?: Record<string, string | number>;
}

// ─────────────────────────────────────────────
//  Operation results
// ─────────────────────────────────────────────

export interface CredentialValidationResult {
  status:  CredentialStatus;
  account: string;
  message: string;
}

export interface AuthCompleteResult {
  status:  CredentialStatus;
  account: string;
  message: string;
}

export interface DeployPlanResult {
  deployment_id:  string;
  provider:       string;
  region:         string;
  resources:      DeployResource[];
  estimated_cost: CostEstimate;
  security_notes: string[];
  raw_config?:    CloudDeployConfig;
}

export interface DryRunResult {
  success:  boolean;
  errors:   string[];
  warnings: string[];
  message:  string;
}

export interface DeployExecuteResult {
  status:        DeployStatus;
  deployment_id: string;
  endpoint_url:  string;
  resources:     DeployResource[];
  errors:        string[];
  message:       string;
}

export interface DeployStatusResult {
  status:        DeployStatus;
  deployment_id: string;
  endpoint_url?: string;
  resources:     DeployResource[];
  errors:        string[];
  message:       string;
}

export interface DeployRollbackResult {
  success:  boolean;
  deleted:  string[];
  errors:   string[];
  message:  string;
}

// ─────────────────────────────────────────────
//  Provider display metadata
// ─────────────────────────────────────────────

export interface ProviderInfo {
  id:          DeployProvider;
  name:        string;
  description: string;
  icon:        string;   // emoji or icon class
  authType:    "oauth" | "apikey" | "none";
  docUrl:      string;
}

export const PROVIDER_INFO: Record<DeployProvider, ProviderInfo> = {
  aws: {
    id:          "aws",
    name:        "Amazon Web Services",
    description: "Bedrock, SageMaker, or Lambda + API Gateway",
    icon:        "🟠",
    authType:    "oauth",
    docUrl:      "https://aws.amazon.com/console/",
  },
  azure: {
    id:          "azure",
    name:        "Microsoft Azure",
    description: "Azure AI Services, Container Instances, or App Service",
    icon:        "🔵",
    authType:    "oauth",
    docUrl:      "https://portal.azure.com/",
  },
  gcp: {
    id:          "gcp",
    name:        "Google Cloud Platform",
    description: "Vertex AI, Cloud Run, or Cloud Functions",
    icon:        "🔴",
    authType:    "oauth",
    docUrl:      "https://console.cloud.google.com/",
  },
  private: {
    id:          "private",
    name:        "Private / Self-Hosted",
    description: "Docker Compose, Kubernetes, or bare-metal deployment",
    icon:        "🖥️",
    authType:    "none",
    docUrl:      "https://docs.docker.com/",
  },
};

// ─────────────────────────────────────────────
//  Deployment flow state machine
// ─────────────────────────────────────────────

export type DeployFlowStep =
  | "provider_select"   // User picks AWS/Azure/GCP/Private
  | "auth"              // OAuth sign-in
  | "config"            // Provider-specific settings
  | "plan_review"       // Show plan + cost estimate
  | "dry_run"           // Dry run validation
  | "confirm"           // User confirms before live deploy
  | "deploying"         // Live deploy in progress
  | "complete"          // Deploy complete
  | "error";            // Error state

export interface DeployFlowState {
  step:          DeployFlowStep;
  provider:      DeployProvider | null;
  credentials:   Record<string, string>;
  config:        Partial<CloudDeployConfig>;
  plan:          DeployPlanResult | null;
  dryRunResult:  DryRunResult | null;
  deployResult:  DeployExecuteResult | null;
  error:         string | null;
  isLoading:     boolean;
}

export const INITIAL_DEPLOY_STATE: DeployFlowState = {
  step:         "provider_select",
  provider:     null,
  credentials:  {},
  config:       {},
  plan:         null,
  dryRunResult: null,
  deployResult: null,
  error:        null,
  isLoading:    false,
};

// ─────────────────────────────────────────────
//  buildDryRunPlan — pure helper (required by Phase 6j tests)
// ─────────────────────────────────────────────

/**
 * Build a lightweight dry-run summary plan from a full DeployPlanResult.
 * Pure function — no side effects, no network calls.
 */
export function buildDryRunPlan(plan: DeployPlanResult): {
  deployment_id: string;
  provider:      string;
  region:        string;
  resource_count: number;
  estimated_monthly_min: number;
  estimated_monthly_max: number;
  security_notes: string[];
} {
  return {
    deployment_id:          plan.deployment_id,
    provider:               plan.provider,
    region:                 plan.region,
    resource_count:         plan.resources.length,
    estimated_monthly_min:  plan.estimated_cost?.low_usd  ?? 0,
    estimated_monthly_max:  plan.estimated_cost?.high_usd ?? 0,
    security_notes:         plan.security_notes,
  };
}
