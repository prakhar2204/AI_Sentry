/**
 * AI-SENTRY -- CheckboxGroup Component
 * components/forms/CheckboxGroup.tsx
 *
 * Multi-select checkbox group with label.
 * Used for probe category selection on Config screen.
 *
 * Props follow UI_ARCHITECTURE.md Section 6.
 */

import React, { useCallback } from "react";

interface CheckboxOption {
  value: string;
  label: string;
}

interface CheckboxGroupProps {
  legend: string;
  options: CheckboxOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  disabled?: boolean;
  error?: string;
}

export function CheckboxGroup({
  legend,
  options,
  selected,
  onChange,
  disabled = false,
  error,
}: CheckboxGroupProps) {
  const handleToggle = useCallback(
    (value: string) => {
      if (disabled) return;
      const next = selected.includes(value)
        ? selected.filter((v) => v !== value)
        : [...selected, value];
      onChange(next);
    },
    [selected, onChange, disabled]
  );

  return (
    <fieldset
      className={`checkbox-group ${error ? "checkbox-group--error" : ""}`}
      disabled={disabled}
    >
      <legend className="checkbox-group__legend">{legend}</legend>
      <div className="checkbox-group__options">
        {options.map((option) => (
          <label
            key={option.value}
            className={`checkbox-group__option ${
              selected.includes(option.value)
                ? "checkbox-group__option--selected"
                : ""
            }`}
          >
            <input
              type="checkbox"
              value={option.value}
              checked={selected.includes(option.value)}
              onChange={() => handleToggle(option.value)}
              className="checkbox-group__input"
              disabled={disabled}
            />
            <span className="checkbox-group__label">{option.label}</span>
          </label>
        ))}
      </div>
      {error && (
        <p className="checkbox-group__error" role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
