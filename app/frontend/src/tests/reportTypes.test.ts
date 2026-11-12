/**
 * Sentryφ — reportTypes Utility Tests (W5)
 * src/tests/reportTypes.test.ts
 *
 * Tests all pure utility functions from services/reportTypes.ts:
 *   severityWeight, categoryLabel, formatConfidence,
 *   formatDuration, formatTimestamp
 */

import { describe, it, expect } from "vitest";
import {
  severityWeight,
  categoryLabel,
  formatConfidence,
  formatDuration,
  formatTimestamp,
  SEVERITY_LABELS,
  RISK_LEVEL_LABELS,
} from "../services/reportTypes";

// ─── severityWeight ───────────────────────────────────────────────────────────

describe("severityWeight", () => {
  it("returns 0 for high", () => {
    expect(severityWeight("high")).toBe(0);
  });

  it("returns 1 for medium", () => {
    expect(severityWeight("medium")).toBe(1);
  });

  it("returns 2 for low", () => {
    expect(severityWeight("low")).toBe(2);
  });

  it("returns 99 for unknown severity", () => {
    expect(severityWeight("unknown")).toBe(99);
    expect(severityWeight("")).toBe(99);
  });

  it("sorts high before medium before low", () => {
    const levels = ["low", "high", "medium"];
    const sorted = [...levels].sort((a, b) => severityWeight(a) - severityWeight(b));
    expect(sorted).toEqual(["high", "medium", "low"]);
  });
});

// ─── categoryLabel ────────────────────────────────────────────────────────────

describe("categoryLabel", () => {
  it("maps prompt_injection to display label", () => {
    expect(categoryLabel("prompt_injection")).toBe("Prompt Injection");
  });

  it("maps jailbreak to display label", () => {
    expect(categoryLabel("jailbreak")).toBe("Jailbreak Resistance");
  });

  it("maps data_leak to display label", () => {
    expect(categoryLabel("data_leak")).toBe("Data Leakage");
  });

  it("maps harmful_output to display label", () => {
    expect(categoryLabel("harmful_output")).toBe("Harmful Output");
  });

  it("falls back to raw id for unknown categories", () => {
    expect(categoryLabel("custom_category")).toBe("custom_category");
    expect(categoryLabel("")).toBe("");
  });
});

// ─── formatConfidence ─────────────────────────────────────────────────────────

describe("formatConfidence", () => {
  it("formats 0.92 as 92%", () => {
    expect(formatConfidence(0.92)).toBe("92%");
  });

  it("formats 1.0 as 100%", () => {
    expect(formatConfidence(1.0)).toBe("100%");
  });

  it("formats 0.0 as 0%", () => {
    expect(formatConfidence(0.0)).toBe("0%");
  });

  it("rounds 0.555 to 56%", () => {
    expect(formatConfidence(0.555)).toBe("56%");
  });

  it("formats 0.333 as 33%", () => {
    expect(formatConfidence(0.333)).toBe("33%");
  });
});

// ─── formatDuration ───────────────────────────────────────────────────────────

describe("formatDuration", () => {
  it("formats 45 seconds as '45s'", () => {
    expect(formatDuration(45)).toBe("45s");
  });

  it("formats 60 seconds as '1m 0s'", () => {
    expect(formatDuration(60)).toBe("1m 0s");
  });

  it("formats 150 seconds as '2m 30s'", () => {
    expect(formatDuration(150)).toBe("2m 30s");
  });

  it("formats 0 seconds as '0s'", () => {
    expect(formatDuration(0)).toBe("0s");
  });

  it("formats 3661 seconds as '61m 1s'", () => {
    expect(formatDuration(3661)).toBe("61m 1s");
  });

  it("rounds fractional seconds", () => {
    expect(formatDuration(45.6)).toBe("46s");
    expect(formatDuration(45.4)).toBe("45s");
  });
});

// ─── formatTimestamp ──────────────────────────────────────────────────────────

describe("formatTimestamp", () => {
  it("returns a non-empty string for valid ISO timestamp", () => {
    const result = formatTimestamp("2024-06-15T10:30:00Z");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("falls back gracefully for invalid ISO (returns a string)", () => {
    const result = formatTimestamp("not-a-date");
    // jsdom toLocaleString of invalid Date returns 'Invalid Date'
    // The actual implementation may return the raw input or 'Invalid Date'
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("contains the year for a known date", () => {
    const result = formatTimestamp("2024-06-15T10:30:00Z");
    expect(result).toContain("2024");
  });
});

// ─── SEVERITY_LABELS / RISK_LEVEL_LABELS ─────────────────────────────────────

describe("SEVERITY_LABELS", () => {
  it("contains human-readable label for all severity levels", () => {
    expect(SEVERITY_LABELS.high).toBe("High");
    expect(SEVERITY_LABELS.medium).toBe("Medium");
    expect(SEVERITY_LABELS.low).toBe("Low");
  });
});

describe("RISK_LEVEL_LABELS", () => {
  it("contains all risk levels", () => {
    expect(RISK_LEVEL_LABELS.CRITICAL).toBe("Critical");
    expect(RISK_LEVEL_LABELS.HIGH).toBe("High");
    expect(RISK_LEVEL_LABELS.MEDIUM).toBe("Medium");
    expect(RISK_LEVEL_LABELS.LOW).toBe("Low");
    expect(RISK_LEVEL_LABELS.NONE).toBe("None");
  });
});
