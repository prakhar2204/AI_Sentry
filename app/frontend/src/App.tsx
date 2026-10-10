/**
 * Sentryɸ -- App Root
 * App.tsx
 *
 * Root component that:
 *   1. Wraps the app in state providers (ScanProvider)
 *   2. Renders the app shell (header + step nav + content)
 *   3. Manages screen routing via useNavigation
 *   4. Tracks completed steps for step navigation
 *   5. Protects navigation during active scan (Phase 6d)
 *
 * Screen routing is handled in-memory (no URL-based router).
 * The app is a single-window Electron application.
 */

import React, { useState, useCallback } from "react";
import { ScanProvider, useScanContext } from "./store/ScanContext";
import { useNavigation, type ScreenId } from "./hooks/useNavigation";
import { AgreementPage } from "./pages/AgreementPage";
import { InputPage } from "./pages/InputPage";
import { ConfigPage } from "./pages/ConfigPage";
import { EstimatePage } from "./pages/EstimatePage";
import { ScanPage } from "./pages/ScanPage";
import { StepNav, WIZARD_STEPS } from "./components/layout/StepNav";
import { ThemeToggle } from "./components/layout/ThemeToggle";

// ─────────────────────────────────────────────
//  Placeholder pages (to be implemented)
// ─────────────────────────────────────────────

function PlaceholderPage({ name }: { name: string }) {
  return (
    <div className="placeholder-page">
      <h1>{name}</h1>
      <p>This screen will be implemented in a future phase.</p>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Screens that show the step nav
// ─────────────────────────────────────────────

const STEP_NAV_SCREENS = new Set([
  "input", "config", "confirm", "scan", "results",
  "actions", "export",
]);

// ─────────────────────────────────────────────
//  Screen Router
// ─────────────────────────────────────────────

function ScreenRouter() {
  const { currentScreen, navigateTo } = useNavigation();
  const { state } = useScanContext();
  const [completedScreens, setCompletedScreens] = useState<string[]>([]);

  // Track completed screens when navigating forward
  const handleNavigate = useCallback(
    (target: ScreenId) => {
      setCompletedScreens((prev) => {
        if (!prev.includes(currentScreen)) {
          return [...prev, currentScreen];
        }
        return prev;
      });
      navigateTo(target);
    },
    [currentScreen, navigateTo]
  );

  // Navigation protection: block StepNav clicks during active scan
  const handleStepNavClick = useCallback(
    (screenId: string) => {
      // Block all navigation while scan is active
      if (state.scan_active) return;
      navigateTo(screenId as ScreenId);
    },
    [state.scan_active, navigateTo]
  );

  const showStepNav = STEP_NAV_SCREENS.has(currentScreen);

  const renderScreen = (): React.ReactNode => {
    switch (currentScreen) {
      case "agree":
        return (
          <AgreementPage
            onAccept={() => handleNavigate("input")}
          />
        );

      case "input":
        return (
          <InputPage
            onContinue={() => handleNavigate("config")}
            onBack={() => navigateTo("agree")}
          />
        );

      case "config":
        return (
          <ConfigPage
            onContinue={() => handleNavigate("confirm")}
            onBack={() => navigateTo("input")}
          />
        );

      case "confirm":
        return (
          <EstimatePage
            onContinue={() => handleNavigate("scan")}
            onBack={() => navigateTo("config")}
          />
        );

      case "scan":
        return (
          <ScanPage
            onComplete={() => handleNavigate("results")}
            onCancel={() => navigateTo("config")}
          />
        );

      case "results":
        return <PlaceholderPage name="Results Dashboard" />;

      case "actions":
        return <PlaceholderPage name="Recommendations" />;

      case "export":
        return <PlaceholderPage name="Export Report" />;

      case "deploy-config":
        return <PlaceholderPage name="Deploy Configuration" />;

      case "deploy-compare":
        return <PlaceholderPage name="Cloud Comparison" />;

      case "deploy-execute":
        return <PlaceholderPage name="Deploy Execution" />;

      default:
        return <PlaceholderPage name="Unknown Screen" />;
    }
  };

  return (
    <>
      {/* ── Step Navigation (hidden on agreement gate) ── */}
      {showStepNav && (
        <StepNav
          steps={WIZARD_STEPS}
          activeScreenId={currentScreen}
          completedScreenIds={completedScreens}
          onNavigate={handleStepNavClick}
        />
      )}

      {/* ── Page Content ── */}
      <main className="app-shell__main">
        <div className="page-container" key={currentScreen}>
          {renderScreen()}
        </div>
      </main>
    </>
  );
}

// ─────────────────────────────────────────────
//  App Root
// ─────────────────────────────────────────────

export default function App() {
  return (
    <ScanProvider>
      <div className="app-shell">
        {/* ── Header ── */}
        <header className="app-shell__header">
          <div className="app-shell__brand">
            <div className="app-shell__brand-icon">S</div>
            Sentryɸ
          </div>
          <div className="app-shell__controls">
            <ThemeToggle />
          </div>
        </header>

        {/* ── Content ── */}
        <ScreenRouter />
      </div>
    </ScanProvider>
  );
}
