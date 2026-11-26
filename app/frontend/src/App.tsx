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
import { DeployProvider, useDeployContext } from "./store/DeployContext";
import { DeployFlowProvider, useDeployFlow } from "./store/DeployFlowContext";
import DeployFlowPage from "./pages/DeployFlowPage";
import { StepNav, WIZARD_STEPS } from "./components/layout/StepNav";
import { UpdateSettings } from "./components/layout/UpdateSettings";
import { ThemeToggle } from "./components/layout/ThemeToggle";
import { Logo } from "./components/Logo";
import { isElectron } from "./utils/platform";
import { ModelCloudPage } from './pages/ModelCloudPage';
import type { CloudDeployConfig } from "./services/deployIpcTypes";

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
  "actions", "export", "deploy-config", "deploy-compare", "deploy-execute", "deploy-flow",
]);

// ─────────────────────────────────────────────
//  Screen Router
// ─────────────────────────────────────────────

function ScreenRouter() {
  const { currentScreen, navigateTo } = useNavigation();
  const { state } = useScanContext();
  const { state: plannedDeployment } = useDeployContext();
  const { dispatch: deployDispatch } = useDeployFlow();
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

  React.useEffect(() => {
    if (document.scrollingElement) document.scrollingElement.scrollTop = 0;
  }, [currentScreen]);

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
            onDeploy={() => handleNavigate('deploy-config')}
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
          <ModelCloudPage onBack={() => navigateTo('results')} onSelect={(provider, config) => {
            deployDispatch({ type: 'SET_PROVIDER', provider });
            deployDispatch({ type: 'SET_CONFIG', config });
            navigateTo('deploy-flow');
          }} />
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
            onLiveDeploy={() => {
              const cfg = plannedDeployment.config;
              if (cfg.provider) {
                deployDispatch({ type: "SET_PROVIDER", provider: cfg.provider });
                deployDispatch({ type: "SET_CONFIG", config: {
                  region: cfg.region || "", deployment_mode: cfg.mode || undefined,
                  endpoint_scope: cfg.endpointScope, instance_type: cfg.instanceType || undefined,
                  model_id: cfg.modelId,
                } as Partial<CloudDeployConfig> });
              }
              navigateTo("deploy-flow");
            }}
            onBack={() => navigateTo("deploy-compare")}
            onBackToConfig={() => navigateTo("deploy-config")}
          />
        );

      case "deploy-flow":
        return <DeployFlowPage onEdit={() => navigateTo('deploy-config')} />;

      default:
        return <PlaceholderPage name="Unknown Screen" />;
    }
  };

  return (
    <>
          <header className="app-shell__header">
            <div className="app-shell__brand">
              <div className="app-shell__brand-icon"><Logo size={22} animate={false} /></div>
              Sentryɸ
            </div>
            <div className="app-shell__controls">
            {!isElectron() && <small>Browser preview</small>}
            <UpdateSettings startup={currentScreen === "agree" || currentScreen === "input"} />
            <ThemeToggle />
          </div>
          </header>
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
      <main id="main-content" className="app-shell__main" aria-label="Main content">
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
        <DeployFlowProvider>
        {/* W4.5: Skip-to-main for keyboard / screen reader users */}
        <a href="#main-content" className="skip-to-main">Skip to main content</a>
        <div className="app-shell">
          <ScreenRouter />
        </div>
        </DeployFlowProvider>
        </DeployProvider>
      </ReportProvider>
    </ScanProvider>
  );
}
