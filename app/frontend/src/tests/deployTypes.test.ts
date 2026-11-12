/**
 * Sentryφ — deployTypes Utility Tests (W5)
 * src/tests/deployTypes.test.ts
 *
 * Tests for emptyDeployConfig() defaults and validateDeployConfig() logic.
 */

import { describe, it, expect } from "vitest";
import {
  emptyDeployConfig,
  validateDeployConfig,
  AWS_REGIONS,
  AZURE_REGIONS,
  GCP_REGIONS,
  SAGEMAKER_INSTANCE_TYPES,
} from "../services/deployTypes";

// ─── emptyDeployConfig ────────────────────────────────────────────────────────

describe("emptyDeployConfig", () => {
  it("returns object with provider null", () => {
    expect(emptyDeployConfig().provider).toBeNull();
  });

  it("sets default replicas to 1", () => {
    expect(emptyDeployConfig().replicas).toBe(1);
  });

  it("defaults endpointScope to private", () => {
    expect(emptyDeployConfig().endpointScope).toBe("private");
  });

  it("defaults requireAuth to true", () => {
    expect(emptyDeployConfig().requireAuth).toBe(true);
  });

  it("defaults enableLogging to true", () => {
    expect(emptyDeployConfig().enableLogging).toBe(true);
  });

  it("defaults enableGuardrails to false", () => {
    expect(emptyDeployConfig().enableGuardrails).toBe(false);
  });

  it("defaults deployed to false", () => {
    expect(emptyDeployConfig().deployed).toBe(false);
  });

  it("generates a valid ISO timestamp for lastModifiedAt", () => {
    const cfg = emptyDeployConfig();
    expect(() => new Date(cfg.lastModifiedAt)).not.toThrow();
    expect(new Date(cfg.lastModifiedAt).getTime()).not.toBeNaN();
  });
});

// ─── validateDeployConfig ─────────────────────────────────────────────────────

describe("validateDeployConfig — canProceed = false when provider missing", () => {
  it("blocks proceed when no provider is selected", () => {
    const cfg = emptyDeployConfig(); // provider = null
    const result = validateDeployConfig(cfg);
    expect(result.canProceed).toBe(false);
  });

  it("includes a blocking issue about provider", () => {
    const cfg = emptyDeployConfig();
    const result = validateDeployConfig(cfg);
    expect(result.blockingIssues.length).toBeGreaterThan(0);
  });
});

describe("validateDeployConfig — AWS provider", () => {
  it("allows proceed with valid AWS config", () => {
    const cfg = {
      ...emptyDeployConfig(),
      provider:     "aws" as const,
      mode:         "sagemaker" as const,
      region:       "us-east-1",
      modelId:      "gpt-neo-2.7B",
      replicas:     1,
      instanceType: "ml.m5.xlarge",
    };
    const result = validateDeployConfig(cfg);
    expect(result.canProceed).toBe(true);
  });

  it("blocks when modelId is too short (<2 chars)", () => {
    const cfg = {
      ...emptyDeployConfig(),
      provider: "aws" as const,
      mode:     "bedrock" as const,
      region:   "us-east-1",
      modelId:  "a",
    };
    const result = validateDeployConfig(cfg);
    expect(result.canProceed).toBe(false);
    expect(result.blockingIssues.some((i) => /model/i.test(i))).toBe(true);
  });

  it("blocks when replicas is 0", () => {
    const cfg = {
      ...emptyDeployConfig(),
      provider:  "aws" as const,
      mode:      "sagemaker" as const,
      region:    "us-east-1",
      modelId:   "some-model",
      replicas:  0,
    };
    const result = validateDeployConfig(cfg);
    expect(result.canProceed).toBe(false);
  });

  it("blocks when replicas is negative", () => {
    const cfg = {
      ...emptyDeployConfig(),
      provider: "aws" as const,
      mode:     "sagemaker" as const,
      region:   "us-east-1",
      modelId:  "some-model",
      replicas: -1,
    };
    const result = validateDeployConfig(cfg);
    expect(result.canProceed).toBe(false);
  });
});

describe("validateDeployConfig — public endpoint security", () => {
  it("adds warning for public endpoint with auth enabled", () => {
    const cfg = {
      ...emptyDeployConfig(),
      provider:      "aws" as const,
      mode:          "sagemaker" as const,
      region:        "us-east-1",
      modelId:       "my-model",
      replicas:      1,
      endpointScope: "public" as const,
      requireAuth:   true,
    };
    const result = validateDeployConfig(cfg);
    expect(result.warnings.length).toBeGreaterThan(0);
  });

  it("blocks for public endpoint without auth", () => {
    const cfg = {
      ...emptyDeployConfig(),
      provider:      "aws" as const,
      mode:          "sagemaker" as const,
      region:        "us-east-1",
      modelId:       "my-model",
      replicas:      1,
      endpointScope: "public" as const,
      requireAuth:   false,
    };
    const result = validateDeployConfig(cfg);
    expect(result.canProceed).toBe(false);
  });
});

describe("validateDeployConfig — budget validation", () => {
  it("blocks when budget is 0", () => {
    const cfg = {
      ...emptyDeployConfig(),
      provider:         "aws" as const,
      mode:             "bedrock" as const,
      region:           "us-east-1",
      modelId:          "my-model",
      budgetMonthlyUsd: 0,
    };
    const result = validateDeployConfig(cfg);
    expect(result.canProceed).toBe(false);
  });

  it("allows when budget is null", () => {
    const cfg = {
      ...emptyDeployConfig(),
      provider:         "aws" as const,
      mode:             "bedrock" as const,
      region:           "us-east-1",
      modelId:          "my-model",
      budgetMonthlyUsd: null,
    };
    const result = validateDeployConfig(cfg);
    // budget = null should not create a budget error
    const hasBudgetIssue = result.blockingIssues.some((i) => /budget/i.test(i));
    expect(hasBudgetIssue).toBe(false);
  });
});

// ─── Static data integrity ────────────────────────────────────────────────────

describe("AWS_REGIONS", () => {
  it("contains at least 5 regions", () => {
    expect(AWS_REGIONS.length).toBeGreaterThanOrEqual(5);
  });

  it("every region has an id and label", () => {
    for (const r of AWS_REGIONS) {
      expect(r.id).toBeTruthy();
      expect(r.label).toBeTruthy();
    }
  });

  it("includes us-east-1", () => {
    expect(AWS_REGIONS.some((r) => r.id === "us-east-1")).toBe(true);
  });
});

describe("AZURE_REGIONS", () => {
  it("contains at least 3 regions", () => {
    expect(AZURE_REGIONS.length).toBeGreaterThanOrEqual(3);
  });

  it("every region has an id and label", () => {
    for (const r of AZURE_REGIONS) {
      expect(r.id).toBeTruthy();
      expect(r.label).toBeTruthy();
    }
  });
});

describe("GCP_REGIONS", () => {
  it("contains at least 3 regions", () => {
    expect(GCP_REGIONS.length).toBeGreaterThanOrEqual(3);
  });
});

describe("SAGEMAKER_INSTANCE_TYPES", () => {
  it("contains at least 3 instance types", () => {
    expect(SAGEMAKER_INSTANCE_TYPES.length).toBeGreaterThanOrEqual(3);
  });

  it("each instance type has id, label, vcpu, ram_gb", () => {
    for (const inst of SAGEMAKER_INSTANCE_TYPES) {
      expect(inst.id).toBeTruthy();
      expect(inst.label).toBeTruthy();
      expect(typeof inst.vcpu).toBe("number");
      expect(typeof inst.ram_gb).toBe("number");
    }
  });
});
