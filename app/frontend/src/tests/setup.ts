/**
 * Sentryφ — Vitest Test Setup (W5)
 * src/tests/setup.ts
 *
 * Global setup for all frontend tests:
 *   - jest-dom matchers (toBeInTheDocument, toHaveClass, etc.)
 *   - ResizeObserver stub (not in jsdom)
 *   - matchMedia stub (not in jsdom)
 *   - requestAnimationFrame stub (animation in RiskGauge)
 */

import "@testing-library/jest-dom";

// ── ResizeObserver (used by some layout components) ──
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserver;

// ── matchMedia (ThemeToggle reads prefers-color-scheme) ──
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// ── requestAnimationFrame (RiskGauge counter animation) ──
let rafCallbacks: FrameRequestCallback[] = [];
let rafHandle = 0;

global.requestAnimationFrame = (cb: FrameRequestCallback) => {
  rafCallbacks.push(cb);
  return ++rafHandle;
};
global.cancelAnimationFrame = (handle: number) => {
  rafCallbacks = rafCallbacks.filter((_, i) => i !== handle - 1);
};

// Flush all pending RAF callbacks (call in tests that need animation to complete)
export function flushRaf() {
  const cbs = [...rafCallbacks];
  rafCallbacks = [];
  cbs.forEach((cb) => cb(performance.now()));
}

// ── window.isElectron ── (App.tsx calls this)
(window as any).isElectron = () => false;
(window as any).electron = undefined;
