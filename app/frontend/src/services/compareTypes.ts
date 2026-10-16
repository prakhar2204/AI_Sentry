/**
 * Sentryɸ -- Cloud Comparison Types
 * services/compareTypes.ts
 *
 * Types for the Cloud Compare screen (Screen 10).
 *
 * IMPORTANT: This is a planning tool only.
 *   - No cloud API calls are made
 *   - No credentials are requested or stored
 *   - No resources are provisioned
 *   - All pricing is STATIC ILLUSTRATIVE data with explicit disclaimers
 *
 * Pricing data rationale:
 *   No live cloud pricing API exists in this project.
 *   The backend estimator.py (core/estimator.py) estimates scan costs only
 *   (GPT-3.5 probe pricing) — it is NOT a cloud deployment cost engine.
 *
 *   Rather than fabricate exact current prices, this module uses:
 *     - Static illustrative ranges with explicit ILLUSTRATIVE labels
 *     - Source URLs pointing to public pricing pages (not fetched at runtime)
 *     - Clear exclusion lists (data transfer, storage, support, etc.)
 *     - Explicit "pricing unavailable" states for unsupported combinations
 *
 *   Per Phase 6i master prompt §5.1:
 *   "Do not invent exact current prices or claim that stale sample values
 *    are live pricing."
 */

import type { DeployConfig, AwsDeploymentMode } from "./deployTypes";

// ─────────────────────────────────────────────
//  Provider capability status
// ─────────────────────────────────────────────

/**
 * Whether a provider can actually be provisioned by this application.
 * Derives from D-022: AWS only for provisioning; Azure/GCP = plan only.
 */
export type ProvisioningCapability =
  | "supported"    // AWS: automated provisioning available in v1
  | "plan-only"    // Azure/GCP: configuration plan, no automation in v1
  | "unsupported"; // Not supported at all

/** Compatibility of the user's configuration with a deployment option */
export type CompatibilityStatus =
  | "compatible"   // All required fields present and valid for this option
  | "incompatible" // A field is definitively unsupported (e.g. GPU required but mode has no GPU)
  | "unverified"   // Compatible in principle but cannot verify (e.g. region availability)
  | "incomplete";  // Required config fields are missing

// ─────────────────────────────────────────────
//  Pricing data model
// ─────────────────────────────────────────────

/**
 * Static illustrative pricing entry.
 *
 * ALL values in this module are ILLUSTRATIVE ESTIMATES published for
 * educational planning purposes only. They are NOT live prices, NOT
 * provider quotes, and may be significantly out of date.
 *
 * Source URLs are provided so users can verify current pricing themselves.
 */
export interface IllustrativePriceEntry {
  /** Human-readable label for this price component */
  component:      string;
  /** Unit description */
  unit:           string;
  /**
   * Low end of illustrative range (USD).
   * null = pricing unavailable for this combination.
   */
  pricePerUnitLow:  number | null;
  /**
   * High end of illustrative range (USD).
   * null = pricing unavailable for this combination.
   */
  pricePerUnitHigh: number | null;
  currency:       "USD";
  /** Reference URL (not fetched — user should verify) */
  sourceUrl:      string;
  /** Month/year the values were recorded. Not guaranteed current. */
  dataAsOf:       string;
  /** What this price does NOT include */
  exclusions:     string[];
  notes:          string;
}

/**
 * Monthly cost estimate derived from illustrative pricing + stated assumptions.
 * Explicitly labelled as illustrative — never presented as a provider quote.
 */
export interface IllustrativeMonthlyCost {
  /** Always "illustrative" — never "quote", "actual", or "guaranteed" */
  type:           "illustrative";
  /** Lower bound of monthly range (USD) */
  monthlyLow:     number | null;
  /** Upper bound of monthly range (USD) */
  monthlyHigh:    number | null;
  currency:       "USD";
  /** The assumptions that produced this estimate */
  assumptions:    CostAssumption[];
  /** Components included in this estimate */
  includedComponents: string[];
  /** Significant costs NOT included */
  excludedComponents: string[];
  /** Whether this is a complete TCO estimate or a partial one */
  isPartial:      boolean;
  /** Brief label for the partial reason, if isPartial=true */
  partialReason:  string | null;
}

/** A single stated assumption used in cost calculation */
export interface CostAssumption {
  label: string;
  value: string;
}

// ─────────────────────────────────────────────
//  Per-option comparison entry
// ─────────────────────────────────────────────

/**
 * A single cloud deployment option shown in the comparison table.
 * Derived from the user's DeployConfig — never from live cloud data.
 */
export interface CompareOption {
  /** Unique key for React rendering */
  id:             string;

  /** Display label */
  label:          string;

  /** Provider identifier */
  provider:       DeployConfig["provider"];

  /** AWS deployment mode, if applicable */
  mode:           AwsDeploymentMode | null;

  /** Whether this application can provision this option */
  provisioningCap: ProvisioningCapability;

  /** Whether the user's current config is compatible with this option */
  compatibility:  CompatibilityStatus;

  /** Human-readable compatibility explanation */
  compatibilityNote: string | null;

  /** Region shown for this option */
  region:         string | null;

  /** Key capabilities of this option */
  capabilities:   string[];

  /** Limitations or caveats specific to this option */
  limitations:    string[];

  /** Illustrative cost estimate — null if pricing unavailable */
  cost:           IllustrativeMonthlyCost | null;

  /** Why cost is unavailable (if cost is null) */
  costUnavailableReason: string | null;

  /** Whether this is the currently selected configuration from Screen 9 */
  isSelectedConfig: boolean;

  /** Warnings specific to this option */
  warnings:       string[];
}

// ─────────────────────────────────────────────
//  Overall comparison result
// ─────────────────────────────────────────────

export interface ComparisonResult {
  /** The config this comparison was derived from — for stale-detection */
  derivedFromConfigAt: string; // lastModifiedAt of the source DeployConfig

  /** All options generated */
  options:            CompareOption[];

  /**
   * Recommended option ID, or null if no safe recommendation can be made.
   * A recommendation is withheld when:
   *   - The selected option is incompatible
   *   - Multiple options are equally matched and cost data is unavailable
   *   - The config is incomplete
   */
  recommendedId:      string | null;

  /** Why a recommendation was or was not made */
  recommendationRationale: string;

  /** True if the source config was from a simulated assessment */
  isSimulated:        boolean;

  /** Timestamp of comparison generation */
  generatedAt:        string;
}

// ─────────────────────────────────────────────
//  Static illustrative pricing tables
//  (NOT live prices — see docstring above)
// ─────────────────────────────────────────────

/**
 * Illustrative SageMaker instance hourly costs (USD).
 * Source: https://aws.amazon.com/sagemaker/pricing/
 * Values recorded: 2024 (us-east-1)
 * NOT guaranteed current. Check AWS pricing page before decisions.
 */
const SAGEMAKER_ILLUSTRATIVE_HOURLY: Record<string, { low: number; high: number }> = {
  "ml.m5.xlarge":    { low: 0.23,  high: 0.25 },
  "ml.m5.2xlarge":   { low: 0.46,  high: 0.50 },
  "ml.g4dn.xlarge":  { low: 0.74,  high: 0.80 },
  "ml.g4dn.2xlarge": { low: 1.48,  high: 1.60 },
  "ml.g5.xlarge":    { low: 1.41,  high: 1.55 },
  "ml.g5.2xlarge":   { low: 2.02,  high: 2.20 },
};

const SAGEMAKER_PRICING_URL = "https://aws.amazon.com/sagemaker/pricing/";
const BEDROCK_PRICING_URL   = "https://aws.amazon.com/bedrock/pricing/";
const LAMBDA_PRICING_URL    = "https://aws.amazon.com/lambda/pricing/";
const PRICING_DATA_AS_OF    = "2024-Q4 (illustrative)";

const COMMON_EXCLUSIONS = [
  "Data transfer / egress costs",
  "Storage (S3, EBS)",
  "CloudWatch logs and metrics",
  "AWS Support plan",
  "Network load balancer (if applicable)",
  "Taxes and fees",
];

/**
 * Build an illustrative monthly cost for SageMaker.
 * Uses stated assumptions: 24h/day, 30 days, single replica.
 */
function sagemakerMonthlyCost(
  instanceType: string | null,
  replicas: number
): IllustrativeMonthlyCost | null {
  if (!instanceType) return null;
  const prices = SAGEMAKER_ILLUSTRATIVE_HOURLY[instanceType];
  if (!prices) return null; // Unknown instance type

  const hoursPerMonth = 24 * 30; // Assumption: always-on
  const low  = parseFloat((prices.low  * hoursPerMonth * replicas).toFixed(2));
  const high = parseFloat((prices.high * hoursPerMonth * replicas).toFixed(2));

  return {
    type:    "illustrative",
    monthlyLow:  low,
    monthlyHigh: high,
    currency: "USD",
    assumptions: [
      { label: "Usage",     value: "24 hours/day × 30 days (always-on)" },
      { label: "Replicas",  value: `${replicas}` },
      { label: "Instance",  value: instanceType },
      { label: "Region",    value: "us-east-1 rates (may vary by region)" },
    ],
    includedComponents: ["Instance compute"],
    excludedComponents: COMMON_EXCLUSIONS,
    isPartial:    true,
    partialReason: "Excludes data transfer, storage, and CloudWatch costs",
  };
}

/**
 * Illustrative Lambda + API Gateway monthly cost.
 * Lambda pricing is consumption-based — requires request/duration assumptions.
 * Range: free tier to moderate traffic scenario.
 */
function lambdaMonthlyCost(): IllustrativeMonthlyCost {
  return {
    type:    "illustrative",
    monthlyLow:  0,      // Free tier may cover light use
    monthlyHigh: 25,     // ~1M requests/month, 512MB, 2s avg duration
    currency: "USD",
    assumptions: [
      { label: "Requests",   value: "0 – 1M requests/month" },
      { label: "Memory",     value: "512 MB" },
      { label: "Duration",   value: "≈ 2 seconds average" },
      { label: "API Gateway",value: "REST API, regional" },
    ],
    includedComponents: ["Lambda compute", "API Gateway requests"],
    excludedComponents: [
      ...COMMON_EXCLUSIONS,
      "Concurrent execution limits / reserved concurrency",
    ],
    isPartial:    true,
    partialReason: "Cost is highly variable — depends on actual request volume and duration",
  };
}

/**
 * Illustrative Bedrock cost.
 * Bedrock is per-token — cannot estimate without knowing request volume and model.
 */
function bedrockMonthlyCost(): IllustrativeMonthlyCost {
  return {
    type:    "illustrative",
    monthlyLow:  null,
    monthlyHigh: null,
    currency: "USD",
    assumptions: [
      { label: "Pricing model", value: "Per-token (on-demand)" },
    ],
    includedComponents: [],
    excludedComponents: [
      "Token consumption (unknown without request volume and model selection)",
      ...COMMON_EXCLUSIONS,
    ],
    isPartial:    true,
    partialReason: "Token-based pricing cannot be estimated without request volume and model",
  };
}

// ─────────────────────────────────────────────
//  Comparison builder (pure function)
// ─────────────────────────────────────────────

/**
 * Derive a ComparisonResult from the current DeployConfig.
 * Pure function — no side effects, no API calls.
 *
 * Called on Screen 10 mount and whenever config changes.
 * If config.lastModifiedAt has changed, callers should rebuild.
 */
export function buildComparison(config: DeployConfig): ComparisonResult {
  const options: CompareOption[] = [];
  const now = new Date().toISOString();
  const isSimulated = config.sourceScanId?.startsWith("sim-") ?? config.isSimulated;

  // ── Option 1: AWS Bedrock (if provider=aws, mode=bedrock or mode=null) ──
  if (config.provider === "aws" || config.provider === null) {
    const selected = config.provider === "aws" && config.mode === "bedrock";
    const bedrockRegion = config.region;
    const compatibility = _bedrockCompatibility(config);

    options.push({
      id:              "aws-bedrock",
      label:           "AWS — Amazon Bedrock",
      provider:        "aws",
      mode:            "bedrock",
      provisioningCap: "supported",
      compatibility,
      compatibilityNote: _bedrockCompatNote(config),
      region:          bedrockRegion,
      capabilities: [
        "Fully managed — no inference infrastructure to provision",
        "Built-in Bedrock Guardrails support",
        "Scales automatically with demand",
        "Supports Claude, Llama, Titan, and other foundation models",
      ],
      limitations: [
        "Available only in select AWS regions",
        "Limited to models available in Bedrock catalog",
        "Custom model weights cannot be deployed directly",
        "Per-token pricing — costs scale with traffic",
      ],
      cost:                selected ? bedrockMonthlyCost() : null,
      costUnavailableReason: selected ? null : "Select AWS + Bedrock mode on Screen 9 to see cost estimate",
      isSelectedConfig:    selected,
      warnings:            _bedrockWarnings(config),
    });
  }

  // ── Option 2: AWS SageMaker (if provider=aws, mode=sagemaker or mode=null) ──
  if (config.provider === "aws" || config.provider === null) {
    const selected = config.provider === "aws" && config.mode === "sagemaker";
    const compatibility = _sagemakerCompatibility(config);

    options.push({
      id:              "aws-sagemaker",
      label:           "AWS — SageMaker",
      provider:        "aws",
      mode:            "sagemaker",
      provisioningCap: "supported",
      compatibility,
      compatibilityNote: _sagemakerCompatNote(config),
      region:          config.region,
      capabilities: [
        "Deploy custom model artifacts (GGUF, HuggingFace, etc.)",
        "GPU instance support (T4, A10G)",
        "Auto-scaling with warm pools",
        "Supports multi-model endpoints",
      ],
      limitations: [
        "Requires model artifact preparation and container image",
        "Instance charges apply 24/7 unless auto-scaling configured",
        "Higher operational complexity than Bedrock",
        "Quota limits apply per AWS account",
      ],
      cost: selected
        ? sagemakerMonthlyCost(config.instanceType, config.replicas)
        : null,
      costUnavailableReason: selected ? null : "Select AWS + SageMaker mode on Screen 9 to see cost estimate",
      isSelectedConfig: selected,
      warnings: _sagemakerWarnings(config),
    });
  }

  // ── Option 3: AWS Lambda (if provider=aws, mode=lambda or mode=null) ──
  if (config.provider === "aws" || config.provider === null) {
    const selected = config.provider === "aws" && config.mode === "lambda";
    const compatibility = _lambdaCompatibility(config);

    options.push({
      id:              "aws-lambda",
      label:           "AWS — API Gateway + Lambda",
      provider:        "aws",
      mode:            "lambda",
      provisioningCap: "supported",
      compatibility,
      compatibilityNote: _lambdaCompatNote(config),
      region:          config.region,
      capabilities: [
        "Consumption-based pricing — pay per request",
        "Zero idle cost when not in use",
        "Simple API Gateway integration",
        "Fast deployment cycles",
      ],
      limitations: [
        "15-minute maximum execution timeout",
        "No GPU support",
        "512 MB – 10 GB memory limit",
        "Cold start latency for infrequent traffic",
        "Best suited for lightweight or adapter-style model calls",
      ],
      cost:             selected ? lambdaMonthlyCost() : null,
      costUnavailableReason: selected ? null : "Select AWS + Lambda mode on Screen 9 to see cost estimate",
      isSelectedConfig: selected,
      warnings:         _lambdaWarnings(config),
    });
  }

  // ── Option 4: Azure (plan only) ──
  if (config.provider === "azure" || config.provider === null) {
    const selected = config.provider === "azure";
    options.push({
      id:              "azure",
      label:           "Microsoft Azure — Azure OpenAI / ML",
      provider:        "azure",
      mode:            null,
      provisioningCap: "plan-only",
      compatibility:   selected ? "unverified" : "unverified",
      compatibilityNote: "Automated provisioning for Azure is not available in this version. Export this plan for manual deployment.",
      region:          selected ? config.region : null,
      capabilities: [
        "Azure OpenAI Service — managed GPT-4/o models",
        "Azure Machine Learning managed endpoints",
        "Microsoft content safety filters built-in",
        "Enterprise compliance (SOC 2, ISO 27001, HIPAA)",
      ],
      limitations: [
        "Automated provisioning NOT available in Sentryɸ v1",
        "Manual Azure CLI / portal deployment required",
        "Azure subscription with appropriate quotas required",
        "Region availability varies by service tier",
      ],
      cost:             null,
      costUnavailableReason: "Azure pricing is not available in this version. See: https://azure.microsoft.com/pricing/",
      isSelectedConfig: selected,
      warnings: [
        "Sentryɸ v1 cannot provision Azure resources. Use this plan as a reference for manual deployment.",
      ],
    });
  }

  // ── Option 5: GCP (plan only) ──
  if (config.provider === "gcp" || config.provider === null) {
    const selected = config.provider === "gcp";
    options.push({
      id:              "gcp",
      label:           "Google Cloud — Vertex AI",
      provider:        "gcp",
      mode:            null,
      provisioningCap: "plan-only",
      compatibility:   "unverified",
      compatibilityNote: "Automated provisioning for GCP is not available in this version. Export this plan for manual deployment.",
      region:          selected ? config.region : null,
      capabilities: [
        "Vertex AI managed model endpoints",
        "Model Garden — Gemini, Llama, Mistral",
        "PaLM 2 / Gemini API access",
        "Google Cloud Armor security controls",
      ],
      limitations: [
        "Automated provisioning NOT available in Sentryɸ v1",
        "Manual gcloud CLI / console deployment required",
        "GCP project with Vertex AI enabled required",
        "Regional availability varies",
      ],
      cost:             null,
      costUnavailableReason: "GCP pricing is not available in this version. See: https://cloud.google.com/vertex-ai/pricing",
      isSelectedConfig: selected,
      warnings: [
        "Sentryɸ v1 cannot provision GCP resources. Use this plan as a reference for manual deployment.",
      ],
    });
  }

  // ── Recommendation logic ──
  const { recommendedId, rationale } = _computeRecommendation(options, config);

  return {
    derivedFromConfigAt:     config.lastModifiedAt,
    options,
    recommendedId,
    recommendationRationale: rationale,
    isSimulated,
    generatedAt: now,
  };
}

// ─────────────────────────────────────────────
//  Compatibility helpers (pure)
// ─────────────────────────────────────────────

function _bedrockCompatibility(cfg: DeployConfig): CompatibilityStatus {
  if (cfg.provider !== "aws") return "unverified";
  if (cfg.mode && cfg.mode !== "bedrock") return "incompatible";
  if (!cfg.modelId || cfg.modelId.trim() === "") return "incomplete";
  if (!cfg.region) return "incomplete";
  return "unverified"; // Region availability unverified at runtime
}

function _bedrockCompatNote(cfg: DeployConfig): string | null {
  if (cfg.provider !== "aws") return null;
  if (cfg.mode && cfg.mode !== "bedrock") return "Your configuration uses a different AWS mode.";
  if (!cfg.modelId) return "Model identifier is required.";
  if (!cfg.region) return "Region is required.";
  return "Region Bedrock availability is not verified at runtime — check AWS documentation.";
}

function _bedrockWarnings(cfg: DeployConfig): string[] {
  const warnings: string[] = [];
  if (cfg.enableGuardrails && cfg.provider === "aws" && cfg.mode === "bedrock") {
    warnings.push("Bedrock Guardrails will require additional configuration in the AWS console after provisioning.");
  }
  if (cfg.endpointScope === "public" && !cfg.requireAuth) {
    warnings.push("Public endpoint without authentication is a security risk.");
  }
  return warnings;
}

function _sagemakerCompatibility(cfg: DeployConfig): CompatibilityStatus {
  if (cfg.provider !== "aws") return "unverified";
  if (cfg.mode && cfg.mode !== "sagemaker") return "incompatible";
  if (!cfg.modelId) return "incomplete";
  if (!cfg.region) return "incomplete";
  if (!cfg.instanceType) return "incomplete";
  return "compatible";
}

function _sagemakerCompatNote(cfg: DeployConfig): string | null {
  if (cfg.provider !== "aws") return null;
  if (cfg.mode && cfg.mode !== "sagemaker") return "Your configuration uses a different AWS mode.";
  if (!cfg.instanceType) return "Instance type is required for SageMaker.";
  if (!cfg.modelId) return "Model identifier is required.";
  if (!cfg.region) return "Region is required.";
  return null;
}

function _sagemakerWarnings(cfg: DeployConfig): string[] {
  const warnings: string[] = [];
  if (cfg.replicas > 3) {
    warnings.push(`${cfg.replicas} replicas requested — verify quota in your AWS account before provisioning.`);
  }
  if (cfg.endpointScope === "public" && !cfg.requireAuth) {
    warnings.push("Public endpoint without authentication is a security risk.");
  }
  return warnings;
}

function _lambdaCompatibility(cfg: DeployConfig): CompatibilityStatus {
  if (cfg.provider !== "aws") return "unverified";
  if (cfg.mode && cfg.mode !== "lambda") return "incompatible";
  if (!cfg.modelId) return "incomplete";
  if (!cfg.region) return "incomplete";
  return "compatible";
}

function _lambdaCompatNote(cfg: DeployConfig): string | null {
  if (cfg.provider !== "aws") return null;
  if (cfg.mode && cfg.mode !== "lambda") return "Your configuration uses a different AWS mode.";
  if (!cfg.modelId) return "Model identifier is required.";
  if (!cfg.region) return "Region is required.";
  return "Lambda is best suited for lightweight adapter-style LLM integrations.";
}

function _lambdaWarnings(cfg: DeployConfig): string[] {
  const warnings: string[] = [];
  warnings.push("Lambda has a 15-minute timeout limit — ensure your model responds within this window.");
  if (cfg.endpointScope === "public" && !cfg.requireAuth) {
    warnings.push("Public endpoint without authentication is a security risk.");
  }
  return warnings;
}

// ─────────────────────────────────────────────
//  Recommendation logic (pure)
// ─────────────────────────────────────────────

function _computeRecommendation(
  options: CompareOption[],
  cfg: DeployConfig
): { recommendedId: string | null; rationale: string } {

  // 1. If config is incomplete or no provider selected, withhold recommendation
  if (!cfg.provider || !cfg.modelId || !cfg.region) {
    return {
      recommendedId: null,
      rationale: "A recommendation cannot be made: provider, model ID, and region are all required.",
    };
  }

  // 2. If a specific option is already selected and compatible, recommend it
  const selected = options.find((o) => o.isSelectedConfig);
  if (selected) {
    if (selected.compatibility === "compatible") {
      return {
        recommendedId: selected.id,
        rationale: `Your selected configuration (${selected.label}) is compatible. No reason to switch.`,
      };
    }
    if (selected.compatibility === "unverified") {
      return {
        recommendedId: selected.id,
        rationale: `Your selected configuration (${selected.label}) has unverified region availability. Review warnings before proceeding.`,
      };
    }
    if (selected.compatibility === "incomplete") {
      return {
        recommendedId: null,
        rationale: `Cannot recommend: your selected configuration (${selected.label}) is missing required fields.`,
      };
    }
    if (selected.compatibility === "incompatible") {
      return {
        recommendedId: null,
        rationale: `Cannot recommend: your selected configuration (${selected.label}) is incompatible. Return to Screen 9 to fix the configuration.`,
      };
    }
  }

  // 3. Provider is set but no mode selected — suggest Bedrock for managed simplicity
  if (cfg.provider === "aws" && !cfg.mode) {
    return {
      recommendedId: "aws-bedrock",
      rationale: "Amazon Bedrock is suggested as a starting point — it requires the least infrastructure management. Select a mode on Screen 9 and return to refine this comparison.",
    };
  }

  // 4. Azure/GCP: plan-only providers — cannot meaningfully recommend
  if (cfg.provider === "azure" || cfg.provider === "gcp") {
    return {
      recommendedId: null,
      rationale: `${cfg.provider.toUpperCase()} provisioning is not automated in Sentryɸ v1. Export the configuration plan for manual deployment. No automated deployment recommendation can be made.`,
    };
  }

  return {
    recommendedId: null,
    rationale: "Insufficient configuration to generate a recommendation. Complete provider, mode, model ID, and region on Screen 9.",
  };
}

// ─────────────────────────────────────────────
//  Stale-detection helper
// ─────────────────────────────────────────────

/**
 * Returns true if the comparison result is derived from an older config
 * (i.e., the user changed config after the comparison was built).
 */
export function isComparisonStale(
  result: ComparisonResult,
  currentConfig: DeployConfig
): boolean {
  return result.derivedFromConfigAt !== currentConfig.lastModifiedAt;
}

// ─────────────────────────────────────────────
//  Pricing source metadata (for display)
// ─────────────────────────────────────────────

export const PRICING_SOURCE_METADATA = {
  sagemaker: {
    label:     "AWS SageMaker Pricing",
    url:       SAGEMAKER_PRICING_URL,
    asOf:      PRICING_DATA_AS_OF,
    note:      "Illustrative on-demand rates for us-east-1. Regional pricing varies. Not a provider quote.",
  },
  bedrock: {
    label:     "AWS Bedrock Pricing",
    url:       BEDROCK_PRICING_URL,
    asOf:      PRICING_DATA_AS_OF,
    note:      "Token-based pricing cannot be estimated without request volume and model ID.",
  },
  lambda: {
    label:     "AWS Lambda + API Gateway Pricing",
    url:       LAMBDA_PRICING_URL,
    asOf:      PRICING_DATA_AS_OF,
    note:      "Consumption-based pricing — actual cost depends on request volume and execution duration.",
  },
} as const;
