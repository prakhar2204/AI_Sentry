/**
 * AI-SENTRY -- AlertBanner Component
 * components/feedback/AlertBanner.tsx
 *
 * Full-width banner for warnings, errors, and info messages.
 * Optionally dismissible.
 *
 * Props follow UI_ARCHITECTURE.md Section 6.
 */

import React from "react";

interface AlertBannerProps {
  type: "warning" | "error" | "info";
  message: string;
  onDismiss?: () => void;
}

export function AlertBanner({ type, message, onDismiss }: AlertBannerProps) {
  return (
    <div
      className={`alert-banner alert-banner--${type}`}
      role={type === "error" ? "alert" : "status"}
    >
      <p className="alert-banner__message">{message}</p>
      {onDismiss && (
        <button
          type="button"
          className="alert-banner__dismiss"
          onClick={onDismiss}
          aria-label="Dismiss"
        >
          &times;
        </button>
      )}
    </div>
  );
}
