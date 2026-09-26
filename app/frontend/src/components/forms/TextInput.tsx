/**
 * AI-SENTRY -- TextInput Component
 * components/forms/TextInput.tsx
 *
 * Single-line text input with label, validation state,
 * and helper/error text.
 *
 * Props follow UI_ARCHITECTURE.md Section 6.
 */

import React from "react";

interface TextInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  id: string;
  placeholder?: string;
  error?: string;
  disabled?: boolean;
  type?: "text" | "url";
}

export function TextInput({
  label,
  value,
  onChange,
  id,
  placeholder,
  error,
  disabled = false,
  type = "text",
}: TextInputProps) {
  return (
    <div className={`text-input ${error ? "text-input--error" : ""}`}>
      <label className="text-input__label" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        type={type}
        className="text-input__field"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
      />
      {error && (
        <p className="text-input__error" id={`${id}-error`} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
