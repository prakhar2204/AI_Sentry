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
import { ReportProvider } from "./store/ReportContext";
import { useNavigation, type ScreenId } from "./hooks/useNavigation";
import { AgreementPage } from "./pages/AgreementPage";
import { InputPage } from "./pages/InputPage";
import { ConfigPage } from "./pages/ConfigPage";
import { EstimatePage } from "./pages/EstimatePage";
import { ScanPage } from "./pages/ScanPage";
import { ResultsPage } from "./pages/ResultsPage";
import { ActionsPage } from "./pages/ActionsPage";
import { ExportPage } from "./pages/ExportPage";
import { DeployConfigPage } from "./pages/DeployConfigPage";
import { CloudComparePage } from "./pages/CloudComparePage";
import { DeployExecutePage } from "./pages/DeployExecutePage";
import { DeployProvider } from "./store/DeployContext";
import { StepNav, WIZARD_STEPS } from "./components/layout/StepNav";
import { ThemeToggle } from "./components/layout/ThemeToggle";
import { Logo } from "./components/Logo";
import { isElectron } from "./utils/platform";

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
  "actions", "export", "deploy-config", "deploy-compare", "deploy-execute",
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
        return (
          <ResultsPage
            onViewActions={() => handleNavigate("actions")}
            onExport={() => handleNavigate("export")}
            onNewScan={() => navigateTo("input")}
          />
        );

      case "actions":
        return (
          <ActionsPage
            onBack={() => navigateTo("results")}
            onExport={() => handleNavigate("export")}
          />
        );

      case "export":
        return (
          <ExportPage
            onBackToResults={() => navigateTo("results")}
            onBackToActions={() => navigateTo("actions")}
            onProceedToDeploy={() => handleNavigate("deploy-config")}
          />
        );

      case "deploy-config":
        return (
          <DeployConfigPage
            onBack={() => navigateTo("export")}
            onProceed={() => navigateTo("deploy-compare")}
          />
        );

      case "deploy-compare":
        return (
          <CloudComparePage
            onBack={() => navigateTo("deploy-config")}
            onProceed={() => navigateTo("deploy-execute")}
          />
        );

      case "deploy-execute":
        return (
          <DeployExecutePage
            onBack={() => navigateTo("deploy-compare")}
            onBackToConfig={() => navigateTo("deploy-config")}
          />
        );

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
      <ReportProvider>
        <DeployProvider>
        <div className="app-shell">
          {/* ── Header ── */}
          <header className="app-shell__header">
            <div className="app-shell__brand">
              <div className="app-shell__brand-icon"><Logo size={22} animate={false} /></div>
              Sentryɸ
            </div>
            <div className="app-shell__controls">
            {/* Mode indicator — Desktop (Electron) or Browser (simulated) */}
            <span
              className="mode-indicator"
              title={isElectron() ? "Running with Python backend" : "Running in browser simulation mode"}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                fontSize: "11px",
                fontWeight: 600,
                letterSpacing: "0.03em",
                padding: "3px 10px",
                borderRadius: "20px",
                background: isElectron()
                  ? "rgba(34,197,94,0.12)"
                  : "rgba(99,102,241,0.12)",
                color: isElectron() ? "var(--success, #22c55e)" : "var(--accent-primary, #6366f1)",
                border: isElectron()
                  ? "1px solid rgba(34,197,94,0.3)"
                  : "1px solid rgba(99,102,241,0.3)",
                cursor: "default",
                userSelect: "none",
                whiteSpace: "nowrap",
              }}
            >
              <span style={{ fontSize: "8px" }}>{isElectron() ? "🟢" : "🔵"}</span>
              {isElectron() ? "Desktop Mode" : "Browser Mode"}
            </span>
            <ThemeToggle />
          </div>
          </header>

          {/* ── Content ── */}
          <ScreenRouter />
        </div>
        </DeployProvider>
      </ReportProvider>
    </ScanProvider>
  );
}
