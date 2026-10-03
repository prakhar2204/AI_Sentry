/**
 * AI-SENTRY -- Step Navigation
 * components/layout/StepNav.tsx
 *
 * Horizontal step indicator displayed at the top of the app.
 * Shows wizard progress: completed → active → upcoming steps.
 *
 * Rules:
 *   - Active step is highlighted
 *   - Completed steps show checkmark and are clickable
 *   - Future steps are dimmed and non-interactive
 *   - Agreement screen has no step nav (it's a gate)
 */

import React from "react";

// ─────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────

export interface StepDef {
  id: string;
  label: string;
  screenId: string;
}

interface StepNavProps {
  steps: StepDef[];
  activeScreenId: string;
  completedScreenIds: string[];
  onNavigate: (screenId: string) => void;
}

// ─────────────────────────────────────────────
//  Step definitions (shared constant)
// ─────────────────────────────────────────────

export const WIZARD_STEPS: StepDef[] = [
  { id: "1", label: "Input",    screenId: "input" },
  { id: "2", label: "Config",   screenId: "config" },
  { id: "3", label: "Estimate", screenId: "confirm" },
  { id: "4", label: "Scan",     screenId: "scan" },
  { id: "5", label: "Results",  screenId: "results" },
];

// ─────────────────────────────────────────────
//  Component
// ─────────────────────────────────────────────

export function StepNav({
  steps,
  activeScreenId,
  completedScreenIds,
  onNavigate,
}: StepNavProps) {
  return (
    <nav className="step-nav" aria-label="Scan wizard progress">
      {steps.map((step, idx) => {
        const isActive = step.screenId === activeScreenId;
        const isComplete = completedScreenIds.includes(step.screenId);
        const isClickable = isComplete && !isActive;

        const className = [
          "step-nav__item",
          isActive && "step-nav__item--active",
          isComplete && !isActive && "step-nav__item--complete",
          isClickable && "step-nav__item--clickable",
        ]
          .filter(Boolean)
          .join(" ");

        return (
          <React.Fragment key={step.id}>
            {idx > 0 && (
              <div
                className={`step-nav__connector${
                  isComplete || isActive ? " step-nav__connector--complete" : ""
                }`}
              />
            )}
            <button
              type="button"
              className={className}
              onClick={isClickable ? () => onNavigate(step.screenId) : undefined}
              disabled={!isClickable && !isActive}
              aria-current={isActive ? "step" : undefined}
              id={`step-nav-${step.screenId}`}
            >
              <span className="step-nav__number">
                {isComplete && !isActive ? "✓" : step.id}
              </span>
              {step.label}
            </button>
          </React.Fragment>
        );
      })}
    </nav>
  );
}
