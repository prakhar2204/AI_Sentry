/**
 * AI-SENTRY -- Theme Toggle
 * components/layout/ThemeToggle.tsx
 *
 * Dark/light mode toggle button.
 * Persists choice to localStorage.
 */

import React, { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "ai-sentry-theme";

export function ThemeToggle() {
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved !== "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute(
      "data-theme",
      isDark ? "dark" : "light"
    );
    localStorage.setItem(STORAGE_KEY, isDark ? "dark" : "light");
  }, [isDark]);

  const toggle = useCallback(() => {
    setIsDark((prev) => !prev);
  }, []);

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Light mode" : "Dark mode"}
      id="theme-toggle"
    >
      {isDark ? "☀" : "☾"}
    </button>
  );
}
