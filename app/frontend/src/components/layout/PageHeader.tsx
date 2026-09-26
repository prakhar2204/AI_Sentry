/**
 * AI-SENTRY -- PageHeader Component
 * components/layout/PageHeader.tsx
 *
 * Consistent page header with title, optional subtitle,
 * and optional back button. Used at the top of every page.
 *
 * Props follow UI_ARCHITECTURE.md Section 6.
 */

import React from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  onBack?: () => void;
}

export function PageHeader({ title, subtitle, onBack }: PageHeaderProps) {
  return (
    <header className="page-header">
      {onBack && (
        <button
          type="button"
          className="page-header__back"
          onClick={onBack}
          aria-label="Go back"
        >
          &larr; Back
        </button>
      )}
      <h1 className="page-header__title">{title}</h1>
      {subtitle && (
        <p className="page-header__subtitle">{subtitle}</p>
      )}
    </header>
  );
}
