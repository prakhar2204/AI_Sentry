/**
 * AI-SENTRY -- useNavigation Hook
 * hooks/useNavigation.ts
 *
 * Manages step-based wizard navigation.
 * Enforces transition rules from UI_ARCHITECTURE.md Section 2:
 *
 *   - Forward-only during scan (Step 5)
 *   - Back allowed pre-scan (Steps 1-4)
 *   - Hub from results (Step 6 branches to 7, 8, 9)
 *   - Consent skip if already accepted
 *   - Cannot skip ahead
 */

import { useState, useCallback, useMemo } from "react";
import { useScanContext } from "../store/ScanContext";

// ─────────────────────────────────────────────
//  Screen identifiers (ordered)
// ─────────────────────────────────────────────

export type ScreenId =
  | "agree"
  | "input"
  | "config"
  | "confirm"
  | "scan"
  | "results"
  | "actions"
  | "export"
  | "deploy-config"
  | "deploy-compare"
  | "deploy-execute";

const LINEAR_SCREENS: ScreenId[] = [
  "agree",
  "input",
  "config",
  "confirm",
  "scan",
  "results",
];

// ─────────────────────────────────────────────
//  Hook
// ─────────────────────────────────────────────

export interface NavigationAPI {
  currentScreen: ScreenId;
  navigateTo: (screen: ScreenId) => void;
  goNext: () => void;
  goBack: () => void;
  canGoBack: boolean;
  canGoNext: boolean;
}

export function useNavigation(): NavigationAPI {
  const { state } = useScanContext();

  // Determine initial screen based on consent state
  const initialScreen: ScreenId = state.consent_given ? "input" : "agree";
  const [currentScreen, setCurrentScreen] = useState<ScreenId>(initialScreen);

  const currentIndex = LINEAR_SCREENS.indexOf(currentScreen);
  const isLinear = currentIndex !== -1;

  const canGoBack = useMemo(() => {
    // Cannot go back during scan
    if (currentScreen === "scan") return false;
    // Cannot go back from agree (first screen)
    if (currentScreen === "agree") return false;
    // Hub branches can return to results
    if (["actions", "export", "deploy-config", "deploy-compare", "deploy-execute"].includes(currentScreen)) {
      return true;
    }
    // Linear screens can go back if not first
    return isLinear && currentIndex > 0;
  }, [currentScreen, currentIndex, isLinear]);

  const canGoNext = useMemo(() => {
    // Cannot advance during scan (auto-advances on complete)
    if (currentScreen === "scan") return false;
    // Cannot advance from hub branches (they return to results)
    if (["actions", "export", "deploy-execute"].includes(currentScreen)) return false;
    return true;
  }, [currentScreen]);

  const navigateTo = useCallback((screen: ScreenId) => {
    // Bypass protection: cannot navigate to any screen without consent
    if (!state.consent_given && screen !== "agree") {
      return;
    }
    setCurrentScreen(screen);
  }, [state.consent_given]);

  const goNext = useCallback(() => {
    if (!canGoNext) return;

    if (isLinear && currentIndex < LINEAR_SCREENS.length - 1) {
      const nextScreen = LINEAR_SCREENS[currentIndex + 1];
      // Skip agree if already consented
      if (nextScreen === "agree" && state.consent_given) {
        setCurrentScreen(LINEAR_SCREENS[currentIndex + 2] || "input");
        return;
      }
      setCurrentScreen(nextScreen);
    }
  }, [canGoNext, isLinear, currentIndex, state.consent_given]);

  const goBack = useCallback(() => {
    if (!canGoBack) return;

    // Hub branches return to results
    if (["actions", "export", "deploy-config", "deploy-compare", "deploy-execute"].includes(currentScreen)) {
      setCurrentScreen("results");
      return;
    }

    if (isLinear && currentIndex > 0) {
      let prevIndex = currentIndex - 1;
      // Skip agree if already consented
      if (LINEAR_SCREENS[prevIndex] === "agree" && state.consent_given) {
        prevIndex = Math.max(0, prevIndex - 1);
      }
      setCurrentScreen(LINEAR_SCREENS[prevIndex]);
    }
  }, [canGoBack, currentScreen, isLinear, currentIndex, state.consent_given]);

  return {
    currentScreen,
    navigateTo,
    goNext,
    goBack,
    canGoBack,
    canGoNext,
  };
}
