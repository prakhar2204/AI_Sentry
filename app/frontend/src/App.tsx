/**
 * AI-SENTRY -- App Root
 * App.tsx
 *
 * Root component that:
 *   1. Wraps the app in state providers (ScanProvider)
 *   2. Manages screen routing via useNavigation
 *   3. Renders the current screen
 *
 * Screen routing is handled in-memory (no URL-based router).
 * The app is a single-window Electron application.
 */

import React from "react";
import { ScanProvider, useScanContext } from "./store/ScanContext";
import { useNavigation, type ScreenId } from "./hooks/useNavigation";
import { AgreementPage } from "./pages/AgreementPage";
import { InputPage } from "./pages/InputPage";
import { ConfigPage } from "./pages/ConfigPage";

// ─────────────────────────────────────────────
//  Placeholder pages (to be implemented in later phases)
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
//  Screen Router
// ─────────────────────────────────────────────

function ScreenRouter() {
  const { currentScreen, navigateTo, goBack } = useNavigation();

  const renderScreen = (): React.ReactNode => {
    switch (currentScreen) {
      case "agree":
        return (
          <AgreementPage
            onAccept={() => navigateTo("input")}
          />
        );

      case "input":
        return (
          <InputPage
            onContinue={() => navigateTo("config")}
            onBack={() => navigateTo("agree")}
          />
        );

      case "config":
        return (
          <ConfigPage
            onContinue={() => navigateTo("confirm")}
            onBack={() => navigateTo("input")}
          />
        );

      case "confirm":
        return <PlaceholderPage name="Confirm (Step 4)" />;

      case "scan":
        return <PlaceholderPage name="Scan Progress (Step 5)" />;

      case "results":
        return <PlaceholderPage name="Results Dashboard (Step 6)" />;

      case "actions":
        return <PlaceholderPage name="Recommendations (Step 7)" />;

      case "export":
        return <PlaceholderPage name="Export Report (Step 8)" />;

      case "deploy-config":
        return <PlaceholderPage name="Deploy Config (Step 9)" />;

      case "deploy-compare":
        return <PlaceholderPage name="Cloud Compare (Step 10)" />;

      case "deploy-execute":
        return <PlaceholderPage name="Deploy Execute (Step 11)" />;

      default:
        return <PlaceholderPage name="Unknown Screen" />;
    }
  };

  return <>{renderScreen()}</>;
}

// ─────────────────────────────────────────────
//  App Root
// ─────────────────────────────────────────────

export default function App() {
  return (
    <ScanProvider>
      <div className="app">
        <ScreenRouter />
      </div>
    </ScanProvider>
  );
}
