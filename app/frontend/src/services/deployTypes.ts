/**
 * Sentryɸ — Deploy Configuration Types (W3.5 Unified)
 * services/deployTypes.ts
 *
 * Comprehensive typed deployment configuration model for Sentryɸ.
 * Supports:
 *   - Legacy single-cloud (AWS) configuration (Screens 9-11)
 *   - W3 multi-cloud (AWS, Azure, GCP, Private) deployment wizard
 *   - Live pricing estimates, recommendations, and OAuth state
 *
 * Architecture decisions:
 *   D-017: Credentials live in OS keychain only (never in this config object)
 *   D-022: Multi-cloud automated provisioning (AWS, Azure, GCP, Private export)
 *   D-023: Plan → User review → Provision → Verify
 */

// ─────────────────────────────────────────────
//  Provider and deployment mode enumerations
// ─────────────────────────────────────────────

export type CloudProvider = "aws" | "azure" | "gcp";
export type ProviderType = CloudProvider | "private" | null;

/**
 * Deployment modes for AWS (legacy enum alias)
 */
export type AwsDeploymentMode = "bedrock" | "sagemaker" | "lambda";

/**
 * Full multi-cloud deployment modes
 */
export type DeployMode =
  | "bedrock"
  | "sagemaker"
  | "lambda"
  | "ai_services"
  | "container"
  | "app_service"
  | "vertex_ai"
  | "cloud_run"
  | "cloud_functions"
  | "docker_compose"
  | "kubernetes"
  | "bare_metal";

/** Endpoint access scope */
export type EndpointScope = "private" | "public";

// ─────────────────────────────────────────────
//  Regions
// ─────────────────────────────────────────────

export interface AwsRegion {
  id: string;
  value: string;
  label: string;
  bedrockAvailable: boolean;
}

export const AWS_REGIONS: AwsRegion[] = [
  { id: "us-east-1",      value: "us-east-1",      label: "US East (N. Virginia)",   bedrockAvailable: true },
  { id: "us-west-2",      value: "us-west-2",      label: "US West (Oregon)",         bedrockAvailable: true },
  { id: "eu-west-1",      value: "eu-west-1",      label: "Europe (Ireland)",          bedrockAvailable: true },
  { id: "eu-central-1",   value: "eu-central-1",   label: "Europe (Frankfurt)",        bedrockAvailable: false },
  { id: "ap-southeast-1", value: "ap-southeast-1", label: "Asia Pacific (Singapore)",  bedrockAvailable: false },
  { id: "ap-northeast-1", value: "ap-northeast-1", label: "Asia Pacific (Tokyo)",      bedrockAvailable: false },
];

export interface CloudRegion {
  id: string;
  value: string;
  label: string;
}

export const AZURE_REGIONS: CloudRegion[] = [
  { id: "eastus",          value: "eastus",          label: "East US"           },
  { id: "westus2",         value: "westus2",         label: "West US 2"         },
  { id: "westeurope",      value: "westeurope",      label: "West Europe"       },
  { id: "northeurope",     value: "northeurope",     label: "North Europe"      },
  { id: "southeastasia",   value: "southeastasia",   label: "Southeast Asia"    },
  { id: "australiaeast",   value: "australiaeast",   label: "Australia East"    },
];

export const GCP_REGIONS: CloudRegion[] = [
  { id: "us-central1",     value: "us-central1",     label: "Iowa (us-central1)"       },
  { id: "us-east1",        value: "us-east1",        label: "South Carolina (us-east1)"},
  { id: "europe-west1",    value: "europe-west1",    label: "Belgium (europe-west1)"   },
  { id: "europe-west4",    value: "europe-west4",    label: "Netherlands (europe-west4)"},
  { id: "asia-southeast1", value: "asia-southeast1", label: "Singapore (asia-southeast1)"},
  { id: "asia-east1",      value: "asia-east1",      label: "Taiwan (asia-east1)"      },
];

// ─────────────────────────────────────────────
//  Deployment modes metadata
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

export const DEPLOY_MODES: Record<CloudProvider, { value: DeployMode; label: string; description: string }[]> = {
  aws: [
    { value: "bedrock",   label: "Amazon Bedrock",    description: "Managed foundation model service — no infrastructure" },
    { value: "sagemaker", label: "SageMaker Endpoint",description: "Full control over compute — bring your own model"    },
    { value: "lambda",    label: "Lambda + API GW",   description: "Serverless, pay-per-request — small/infrequent loads"  },
  ],
  azure: [
    { value: "ai_services",  label: "Azure AI Services",   description: "Managed model endpoint — lowest ops overhead"      },
    { value: "container",    label: "Container Instances",  description: "Docker-based, flexible — full model control"       },
    { value: "app_service",  label: "App Service",          description: "Web app hosting with HTTPS + scaling"             },
  ],
  gcp: [
    { value: "vertex_ai",       label: "Vertex AI Endpoint",  description: "Google's managed ML platform — integrated MLOps" },
    { value: "cloud_run",       label: "Cloud Run",           description: "Containerized serverless — auto-scales to zero"  },
    { value: "cloud_functions", label: "Cloud Functions",     description: "Event-driven, serverless — lightweight inference" },
  ],
};

// ─────────────────────────────────────────────
//  Instance / compute types
// ─────────────────────────────────────────────

export interface AwsInstanceType {
  id:      string;
  value:   string;
  label:   string;
  gpu:     boolean;
  notes:   string;
  vcpu:    number;
  ram_gb:  number;
}

export const SAGEMAKER_INSTANCE_TYPES: AwsInstanceType[] = [
  { id: "ml.m5.xlarge",   value: "ml.m5.xlarge",   label: "ml.m5.xlarge (4 vCPU, 16 GB)",     gpu: false, notes: "CPU — lightweight adapters", vcpu: 4,  ram_gb: 16 },
  { id: "ml.m5.2xlarge",  value: "ml.m5.2xlarge",  label: "ml.m5.2xlarge (8 vCPU, 32 GB)",    gpu: false, notes: "CPU — standard",             vcpu: 8,  ram_gb: 32 },
  { id: "ml.g4dn.xlarge", value: "ml.g4dn.xlarge", label: "ml.g4dn.xlarge (1x T4, 16 GB)",    gpu: true,  notes: "GPU — small models",          vcpu: 4,  ram_gb: 16 },
  { id: "ml.g4dn.2xlarge",value: "ml.g4dn.2xlarge",label: "ml.g4dn.2xlarge (1x T4, 32 GB)",   gpu: true,  notes: "GPU — recommended",           vcpu: 8,  ram_gb: 32 },
  { id: "ml.g5.xlarge",   value: "ml.g5.xlarge",   label: "ml.g5.xlarge (1x A10G, 24 GB)",    gpu: true,  notes: "GPU — larger models",         vcpu: 4,  ram_gb: 24 },
  { id: "ml.g5.2xlarge",  value: "ml.g5.2xlarge",  label: "ml.g5.2xlarge (1x A10G, 24 GB)",   gpu: true,  notes: "GPU — production",            vcpu: 8,  ram_gb: 24 },
  { id: "ml.g5.4xlarge",  value: "ml.g5.4xlarge",  label: "ml.g5.4xlarge (1x A10G, 64 GB)",   gpu: true,  notes: "GPU — high compute",          vcpu: 16, ram_gb: 64 },
  { id: "ml.g5.12xlarge", value: "ml.g5.12xlarge", label: "ml.g5.12xlarge (4x A10G, 192 GB)", gpu: true,  notes: "GPU — distributed",          vcpu: 48, ram_gb: 192 },
];

export const SAGEMAKER_INSTANCES = SAGEMAKER_INSTANCE_TYPES;

export const VERTEX_AI_ACCELERATORS: { value: string; label: string }[] = [
  { value: "NVIDIA_TESLA_T4",  label: "NVIDIA T4 (16 GB VRAM)"   },
  { value: "NVIDIA_A100_80GB", label: "NVIDIA A100 (80 GB VRAM)" },
  { value: "NVIDIA_L4",        label: "NVIDIA L4 (24 GB VRAM)"   },
];

// ─────────────────────────────────────────────
//  OAuth State
// ─────────────────────────────────────────────

export type CredentialStatus = "idle" | "pending" | "valid" | "invalid" | "expired";

export interface OAuthState {
  status:    CredentialStatus;
  accountId: string;
  email:     string;
  provider:  CloudProvider | null;
  scopes:    string[];
  expiresAt: string | null;
}

export const INITIAL_OAUTH_STATE: OAuthState = {
  status:    "idle",
  accountId: "",
  email:     "",
  provider:  null,
  scopes:    [],
  expiresAt: null,
};

// ─────────────────────────────────────────────
//  Cost Estimate
// ─────────────────────────────────────────────

export interface CostLineItem {
  name:       string;
  unit:       string;
  quantity:   number;
  unit_price: number;
  monthly:    number;
}

export interface CostEstimate {
  provider:      CloudProvider;
  region:        string;
  mode:          DeployMode;
  monthly_min:   number;
  monthly_max:   number;
  monthly_mid:   number;
  one_time:      number;
  breakdown:     CostLineItem[];
  currency:      string;
  as_of_date:    string;
  disclaimer:    string;
}

// ─────────────────────────────────────────────
//  Deployment Recommendation (from W1.3 backend)
// ─────────────────────────────────────────────

export interface DeploymentRecommendation {
  recommended_provider: CloudProvider | "private";
  recommended_mode:     DeployMode | "docker_compose";
  recommended_region:   string;
  rationale:            string;
  risk_level:           "low" | "medium" | "high" | "critical";
  security_warnings:    string[];
  estimated_cost:       { low_usd: number; high_usd: number };
  compliance_notes:     string[];
}

// ─────────────────────────────────────────────
//  Provider Feature Comparison
// ─────────────────────────────────────────────

export interface ProviderFeature {
  name:            string;
  aws:             boolean | string;
  azure:           boolean | string;
  gcp:             boolean | string;
}

export const PROVIDER_COMPARISON_FEATURES: ProviderFeature[] = [
  { name: "Private endpoint",          aws: true,     azure: true,    gcp: true    },
  { name: "Content safety filter",     aws: true,     azure: true,    gcp: "beta"  },
  { name: "SOC 2 Type II",             aws: true,     azure: true,    gcp: true    },
  { name: "HIPAA",                     aws: true,     azure: true,    gcp: true    },
  { name: "Auto-scaling",              aws: true,     azure: true,    gcp: true    },
  { name: "Serverless option",         aws: true,     azure: false,   gcp: true    },
  { name: "Model monitoring",          aws: true,     azure: true,    gcp: true    },
  { name: "Budget alerts",             aws: true,     azure: true,    gcp: true    },
  { name: "VPC/private networking",    aws: true,     azure: true,    gcp: true    },
  { name: "Custom domain / TLS",       aws: true,     azure: true,    gcp: true    },
  { name: "Free tier",                 aws: "limited",azure: "trial", gcp: "trial" },
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
  valid:            boolean;
  /** List of blocking issues preventing proceed */
  blockingIssues:   string[];
  errors:           string[];
  warnings:         string[];
}

// ─────────────────────────────────────────────
//  Core deployment configuration model
// ─────────────────────────────────────────────

export interface DeployConfig {
  provider:       ProviderType;
  mode:           DeployMode | null;
  region:         string | null;

  // Model / workload
  modelId:        string;
  modelLabel:     string;

  // Compute
  instanceType:   string | null;
  replicas:       number;

  // Network / access
  endpointScope:  EndpointScope;
  requireAuth:    boolean;
  enableLogging:  boolean;
  enableGuardrails: boolean;

  // Budget
  budgetMonthlyUsd: number | null;
  budgetAlertUsd?:  number | null;

  // Provider-specific configs
  resourceGroup?: string | null;
  projectId?:     string | null;
  domain?:        string | null;

  // Provenance
  sourceScanId:   string | null;
  isSimulated:    boolean;

  // Plan status
  lastModifiedAt: string;
  deployed:       boolean;
}

export function emptyDeployConfig(): DeployConfig {
  return {
    provider:         null,
    mode:             null,
    region:           null,
    modelId:          "",
    modelLabel:       "",
    instanceType:     null,
    replicas:         1,
    endpointScope:    "private",
    requireAuth:      true,
    enableLogging:    true,
    enableGuardrails: false,
    budgetMonthlyUsd: null,
    budgetAlertUsd:   null,
    resourceGroup:    null,
    projectId:        null,
    domain:           null,
    sourceScanId:     null,
    isSimulated:      false,
    lastModifiedAt:   new Date().toISOString(),
    deployed:         false,
  };
}

// ─────────────────────────────────────────────
//  Validation functions
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
  const warnings: string[] = [];

  // Provider
  let providerV: FieldValidation;
  if (!cfg.provider) {
    providerV = fieldIncomplete("Select a cloud provider");
    issues.push("Cloud provider is required");
  } else if (cfg.provider === "azure" || cfg.provider === "gcp" || cfg.provider === "private") {
    providerV = fieldOk();
  } else {
    providerV = fieldOk();
  }

  // Deployment mode
  let modeV: FieldValidation;
  if (!cfg.mode) {
    modeV = fieldIncomplete("Select a deployment mode");
    issues.push("Deployment mode is required");
  } else {
    modeV = fieldOk();
  }

  // Region
  let regionV: FieldValidation;
  if (!cfg.region && cfg.provider !== "private") {
    regionV = fieldIncomplete("Select a region");
    issues.push("Region is required");
  } else if (cfg.provider === "aws") {
    const regionDef = AWS_REGIONS.find((r) => r.id === cfg.region || r.value === cfg.region);
    if (!regionDef) {
      regionV = fieldErr(`Unrecognised region: ${cfg.region}`);
      issues.push("Region is not valid");
    } else if (cfg.mode === "bedrock" && !regionDef.bedrockAvailable) {
      regionV = fieldUnverified(`Amazon Bedrock may not be available in ${regionDef.label}. Verify availability before provisioning.`);
      warnings.push(`Amazon Bedrock may not be available in ${regionDef.label}`);
    } else {
      regionV = fieldOk();
    }
  } else {
    regionV = fieldOk();
  }

  // Model ID
  let modelIdV: FieldValidation;
  if (!cfg.modelId || cfg.modelId.trim() === "") {
    modelIdV = fieldIncomplete("Enter a model identifier");
    issues.push("Model identifier is required");
  } else if (cfg.modelId.trim().length < 2) {
    modelIdV = fieldErr("Model identifier is too short");
    issues.push("Model identifier is invalid");
  } else {
    modelIdV = fieldOk();
  }

  // Instance type
  let instanceTypeV: FieldValidation;
  if (cfg.provider === "aws" && cfg.mode === "sagemaker") {
    if (!cfg.instanceType) {
      instanceTypeV = fieldIncomplete("Select an instance type");
      issues.push("Instance type is required for SageMaker");
    } else {
      const known = SAGEMAKER_INSTANCE_TYPES.find((t) => t.id === cfg.instanceType || t.value === cfg.instanceType);
      instanceTypeV = known ? fieldOk() : fieldUnverified("Custom instance type — verify availability");
    }
  } else {
    instanceTypeV = { status: "valid", message: null };
  }

  // Replicas
  let replicasV: FieldValidation;
  if ((cfg.replicas ?? 1) < 1) {
    replicasV = fieldErr("Minimum 1 replica required");
    issues.push("Replica count must be at least 1");
  } else if (cfg.replicas > 10) {
    replicasV = fieldUnverified("High replica count — verify quota availability in your account");
    warnings.push("High replica count");
  } else {
    replicasV = fieldOk();
  }

  // Endpoint scope
  let endpointScopeV: FieldValidation;
  if (cfg.endpointScope === "public") {
    endpointScopeV = fieldUnverified(
      "Public endpoint exposes the model to the internet. Ensure authentication is enabled and access is properly scoped."
    );
    warnings.push("Public endpoint exposes your model to the internet — ensure auth is in place");
    if (!cfg.requireAuth) {
      endpointScopeV = fieldErr("Public endpoint without authentication is a security risk. Enable authentication or switch to private.");
      issues.push("Public endpoint requires authentication to be enabled");
    }
  } else {
    endpointScopeV = fieldOk();
  }

  // Budget
  let budgetV: FieldValidation;
  const budget = cfg.budgetMonthlyUsd ?? cfg.budgetAlertUsd;
  if (budget !== null && budget !== undefined) {
    if (budget <= 0) {
      budgetV = fieldErr("Budget must be greater than $0");
      issues.push("Budget amount is invalid");
    } else if (budget > 100_000) {
      budgetV = fieldUnverified("Budget exceeds $100,000/month — verify this is intentional");
      warnings.push("Budget exceeds $100,000/month");
    } else {
      budgetV = fieldOk();
    }
  } else {
    budgetV = fieldOk();
  }

  // Provider specific validations
  if (cfg.provider === "gcp" && !cfg.projectId) {
    warnings.push("GCP Project ID is recommended");
  }
  if (cfg.provider === "azure" && !cfg.resourceGroup) {
    warnings.push("Resource group not set — a new one will be created automatically");
  }

  const canProceed = issues.length === 0;

  return {
    provider:         providerV,
    mode:             modeV,
    region:           regionV,
    modelId:          modelIdV,
    instanceType:     instanceTypeV,
    replicas:         replicasV,
    endpointScope:    endpointScopeV,
    budgetMonthlyUsd: budgetV,
    canProceed,
    valid:            canProceed,
    blockingIssues:   issues,
    errors:           issues,
    warnings,
  };
}
