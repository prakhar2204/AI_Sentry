/**
 * AI-SENTRY -- Configuration Page (Screen 3)
 * pages/ConfigPage.tsx
 *
 * Controls how the scan will run. User selects:
 *   1. Scan strategy (manifest / manual / full)
 *   2. Probe categories (if manual)
 *   3. Scan depth (quick / standard / deep)
 *
 * Shows read-only summary of target + mode from Screen 2.
 *
 * Follows UI_ARCHITECTURE.md:
 *   - Section 2: Screen 3 definition (exit: manifest assembled)
 *   - Section 3: ScanContext fields (scan_strategy, categories, scan_depth)
 *   - Section 7: UX rules (disable don't hide, one primary action)
 *   - Section 8: Edge cases (mode switch clears state)
 *
 * Validation:
 *   - Manifest mode: manifest_file must exist in ScanContext
 *   - Manual mode: at least 1 category selected
 *   - Full scan: always valid
 *   - Depth: always has a default (standard)
 */

import React, { useState, useCallback, useMemo } from "react";
import {
  useScanContext,
  type ScanDepth,
  type ScanStrategy,
} from "../store/ScanContext";
import { SCAN_ACTIONS } from "../store/actions";
import { PageHeader } from "../components/layout/PageHeader";
import { RadioGroup } from "../components/forms/RadioGroup";
import { CheckboxGroup } from "../components/forms/CheckboxGroup";
import { AlertBanner } from "../components/feedback/AlertBanner";

// ─────────────────────────────────────────────
//  Constants
// ─────────────────────────────────────────────

const ALL_CATEGORIES = [
  { value: "prompt_injection", label: "Prompt Injection" },
  { value: "data_leak", label: "Data Leak" },
  { value: "jailbreak", label: "Jailbreak" },
  { value: "harmful_output", label: "Harmful Output" },
];

const ALL_CATEGORY_VALUES = ALL_CATEGORIES.map((c) => c.value);

const DEPTH_OPTIONS = [
  { value: "quick", label: "Quick (5-15 min)" },
  { value: "standard", label: "Standard (30-90 min)" },
  { value: "deep", label: "Deep (2-6 hrs)" },
];

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface ConfigPageProps {
  onContinue: () => void;
  onBack: () => void;
}

// ─────────────────────────────────────────────
//  Component
// ─────────────────────────────────────────────

export function ConfigPage({ onContinue, onBack }: ConfigPageProps) {
  const { state, dispatch } = useScanContext();

  // ── Determine if manifest strategy is available ──
  const hasManifest = state.manifest_file !== null;

  // ── Local state ──
  const [strategy, setStrategy] = useState<ScanStrategy>(
    state.scan_strategy === "manifest" && !hasManifest
      ? "manual"
      : state.scan_strategy
  );
  const [categories, setCategories] = useState<string[]>(
    state.categories.length > 0 ? state.categories : []
  );
  const [depth, setDepth] = useState<ScanDepth>(state.scan_depth);
  const [categoryError, setCategoryError] = useState<string | null>(null);

  // ── Strategy options ──
  const strategyOptions = useMemo(() => {
    const options = [
      {
        value: "manifest",
        label: hasManifest
          ? `Use uploaded manifest (${state.manifest_file})`
          : "Use uploaded manifest (no file provided)",
      },
      { value: "manual", label: "Select scan categories manually" },
      { value: "full", label: "Full scan (all checks)" },
    ];
    return options;
  }, [hasManifest, state.manifest_file]);

  // ── Strategy switch handler ──
  const handleStrategyChange = useCallback(
    (value: string) => {
      const newStrategy = value as ScanStrategy;

      // Block manifest selection if no manifest exists
      if (newStrategy === "manifest" && !hasManifest) return;

      setStrategy(newStrategy);
      setCategoryError(null);

      // Reset categories on switch
      if (newStrategy === "full") {
        setCategories(ALL_CATEGORY_VALUES);
      } else if (newStrategy === "manifest") {
        setCategories([]);
      } else {
        // manual — keep current selection or clear
        if (strategy !== "manual") {
          setCategories([]);
        }
      }
    },
    [hasManifest, strategy]
  );

  // ── Category toggle handler ──
  const handleCategoriesChange = useCallback((selected: string[]) => {
    setCategories(selected);
    setCategoryError(null);
  }, []);

  // ── Validation ──
  const validate = useCallback((): boolean => {
    if (strategy === "manifest") {
      if (!hasManifest) return false;
      return true;
    }
    if (strategy === "manual") {
      if (categories.length === 0) {
        setCategoryError("Select at least one category.");
        return false;
      }
      return true;
    }
    // full — always valid
    return true;
  }, [strategy, hasManifest, categories]);

  // ── Can continue (for button disable state) ──
  const canContinue = useMemo(() => {
    if (strategy === "manifest") return hasManifest;
    if (strategy === "manual") return categories.length > 0;
    return true; // full
  }, [strategy, hasManifest, categories]);

  // ── Submit handler ──
  const handleContinue = useCallback(() => {
    if (!validate()) return;

    // Determine final categories
    const finalCategories =
      strategy === "full" ? ALL_CATEGORY_VALUES : categories;

    // Update ScanContext
    dispatch({ type: SCAN_ACTIONS.SET_SCAN_STRATEGY, payload: strategy });
    dispatch({ type: SCAN_ACTIONS.SET_CATEGORIES, payload: finalCategories });
    dispatch({ type: SCAN_ACTIONS.SET_SCAN_DEPTH, payload: depth });
    dispatch({ type: SCAN_ACTIONS.START_CONFIRMING });

    onContinue();
  }, [validate, strategy, categories, depth, dispatch, onContinue]);

  // ── Mode display label ──
  const modeLabel = state.mode === "api" ? "API Endpoint" : "Local Model";

  return (
    <div className="config-page">
      <PageHeader
        title="Scan Configuration"
        subtitle="Choose how the scan will run."
        onBack={onBack}
      />

      <div className="config-page__content">

        {/* ── Target Summary (read-only) ── */}
        <section className="config-page__section">
          <h2 className="config-page__section-title">Target Summary</h2>
          <dl className="config-page__summary">
            <div className="config-page__summary-row">
              <dt className="config-page__summary-label">Target</dt>
              <dd className="config-page__summary-value">
                {state.target || "Not set"}
              </dd>
            </div>
            <div className="config-page__summary-row">
              <dt className="config-page__summary-label">Mode</dt>
              <dd className="config-page__summary-value">{modeLabel}</dd>
            </div>
          </dl>
        </section>

        {/* ── Scan Strategy ── */}
        <section className="config-page__section">
          <RadioGroup
            legend="Scan Strategy"
            options={strategyOptions}
            selected={strategy}
            onChange={handleStrategyChange}
            name="scan-strategy"
          />

          {/* Manifest not available hint */}
          {!hasManifest && strategy !== "manifest" && (
            <p className="config-page__hint">
              To use a manifest, upload one on the previous screen.
            </p>
          )}
        </section>

        {/* ── Category Selection (manual mode only) ── */}
        <section className="config-page__section">
          <CheckboxGroup
            legend="Probe Categories"
            options={ALL_CATEGORIES}
            selected={categories}
            onChange={handleCategoriesChange}
            disabled={strategy !== "manual"}
            error={categoryError || undefined}
          />
        </section>

        {/* ── Full Scan Warning ── */}
        {strategy === "full" && (
          <AlertBanner
            type="warning"
            message="This will scan all categories and may take longer."
          />
        )}

        {/* ── Scan Depth ── */}
        <section className="config-page__section">
          <RadioGroup
            legend="Scan Depth"
            options={DEPTH_OPTIONS}
            selected={depth}
            onChange={(val) => setDepth(val as ScanDepth)}
            name="scan-depth"
          />
        </section>

        {/* ── Primary Action ── */}
        <div className="config-page__actions">
          <button
            type="button"
            className="button button--primary"
            disabled={!canContinue}
            onClick={handleContinue}
            id="config-continue-button"
          >
            Continue
          </button>
        </div>

      </div>
    </div>
  );
}
