/**
 * AI-SENTRY -- RadioGroup Component
 * components/forms/RadioGroup.tsx
 *
 * Single-select radio group with label.
 * Used for scan mode selection on Input screen
 * and scan depth selection on Config screen.
 *
 * Props follow UI_ARCHITECTURE.md Section 6.
 */

import React from "react";

interface RadioOption {
  value: string;
  label: string;
}

interface RadioGroupProps {
  legend: string;
  options: RadioOption[];
  selected: string;
  onChange: (value: string) => void;
  name: string;
  disabled?: boolean;
}

export function RadioGroup({
  legend,
  options,
  selected,
  onChange,
  name,
  disabled = false,
}: RadioGroupProps) {
  return (
    <fieldset className="radio-group" disabled={disabled}>
      <legend className="radio-group__legend">{legend}</legend>
      <div className="radio-group__options">
        {options.map((option) => (
          <label
            key={option.value}
            className={`radio-group__option ${
              selected === option.value ? "radio-group__option--selected" : ""
            }`}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={selected === option.value}
              onChange={() => onChange(option.value)}
              className="radio-group__input"
            />
            <span className="radio-group__label">{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
