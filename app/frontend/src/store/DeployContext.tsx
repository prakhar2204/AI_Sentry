/**
 * Sentryɸ -- Deploy Context
 * store/DeployContext.tsx
 *
 * State management for the deployment configuration workflow (Screens 9-11).
 *
 * Architecture:
 *   - useReducer + React Context (no external state library, per UI_ARCHITECTURE §3)
 *   - Mirrors the DeployState schema from UI_ARCHITECTURE.md §3
 *   - Config is SEPARATE from ReportContext — scan report is never mutated
 *   - Credentials are NEVER stored here (D-017: OS keychain only)
 *   - Session-only: no localStorage or file persistence
 *
 * State transitions (Screen 9 covers: idle → configuring):
 *   idle         — no provider selected yet
 *   configuring  — user is filling in deploy-config form (Screen 9)
 *   comparing    — handed off to Screen 10 (not yet implemented)
 *   executing    — deployment in progress (Screen 11, not yet implemented)
 *   complete     — deployment done (Screen 11)
 *   failed       — deployment failed (Screen 11)
 */

import React, {
  createContext,
  useContext,
  useReducer,
  ReactNode,
  Dispatch,
} from "react";

import { DEPLOY_ACTIONS } from "./actions";
import {
  DeployConfig,
  DeployConfigValidation,
  validateDeployConfig,
  emptyDeployConfig,
} from "../services/deployTypes";

// ─────────────────────────────────────────────
//  State shape
// ─────────────────────────────────────────────

export interface DeployState {
  /** Workflow phase */
  phase: "idle" | "configuring" | "comparing" | "executing" | "complete" | "failed";

  /** The deployment configuration being assembled on Screen 9 */
  config: DeployConfig;

  /** Live validation result — recomputed whenever config changes */
  validation: DeployConfigValidation;

  /** Deployment execution error (Screen 11 — not yet used) */
  deploy_error: string | null;
}

// ─────────────────────────────────────────────
//  Actions
// ─────────────────────────────────────────────

// Payload types for deploy actions
type SetProviderPayload = { provider: DeployConfig["provider"] };
type SetRegionPayload   = { region: string | null };
type SetConfigPayload   = Partial<Omit<DeployConfig, "provider" | "region" | "deployed">>;

export type DeployAction =
  | { type: typeof DEPLOY_ACTIONS.SET_PROVIDER; payload: SetProviderPayload }
  | { type: typeof DEPLOY_ACTIONS.SET_REGION;   payload: SetRegionPayload }
  | { type: typeof DEPLOY_ACTIONS.SET_CONFIG;   payload: SetConfigPayload }
  | { type: typeof DEPLOY_ACTIONS.START_DEPLOY }
  | { type: typeof DEPLOY_ACTIONS.DEPLOY_COMPLETE }
  | { type: typeof DEPLOY_ACTIONS.DEPLOY_FAILED; payload: string }
  | { type: typeof DEPLOY_ACTIONS.RESET_DEPLOY };

// ─────────────────────────────────────────────
//  Initial state
// ─────────────────────────────────────────────

const baseConfig = emptyDeployConfig();

const initialState: DeployState = {
  phase:        "idle",
  config:       baseConfig,
  validation:   validateDeployConfig(baseConfig),
  deploy_error: null,
};

// ─────────────────────────────────────────────
//  Reducer
// ─────────────────────────────────────────────

/**
 * Merge config patch and revalidate.
 * Validation always runs fresh — no stale "valid" state on changed fields.
 */
function applyConfigPatch(
  state: DeployState,
  patch: Partial<DeployConfig>
): DeployState {
  const newConfig: DeployConfig = {
    ...state.config,
    ...patch,
    lastModifiedAt: new Date().toISOString(),
    deployed: false,
  };
  return {
    ...state,
    phase:      "configuring",
    config:     newConfig,
    validation: validateDeployConfig(newConfig),
  };
}

function deployReducer(state: DeployState, action: DeployAction): DeployState {
  switch (action.type) {

    case DEPLOY_ACTIONS.SET_PROVIDER: {
      const { provider } = action.payload;
      // Provider change: reset mode/region/instanceType to avoid stale incompatible values
      const patch: Partial<DeployConfig> = {
        provider,
        mode:         null,
        region:       null,
        instanceType: null,
      };
      return applyConfigPatch(state, patch);
    }

    case DEPLOY_ACTIONS.SET_REGION:
      return applyConfigPatch(state, { region: action.payload.region });

    case DEPLOY_ACTIONS.SET_CONFIG:
      return applyConfigPatch(state, action.payload);

    case DEPLOY_ACTIONS.START_DEPLOY:
      return { ...state, phase: "executing", deploy_error: null };

    case DEPLOY_ACTIONS.DEPLOY_COMPLETE:
      return { ...state, phase: "complete" };

    case DEPLOY_ACTIONS.DEPLOY_FAILED:
      return { ...state, phase: "failed", deploy_error: action.payload };

    case DEPLOY_ACTIONS.RESET_DEPLOY: {
      const fresh = emptyDeployConfig();
      return {
        phase:        "idle",
        config:       fresh,
        validation:   validateDeployConfig(fresh),
        deploy_error: null,
      };
    }

    default:
      return state;
  }
}

// ─────────────────────────────────────────────
//  Context
// ─────────────────────────────────────────────

interface DeployContextValue {
  state:    DeployState;
  dispatch: Dispatch<DeployAction>;
}

const DeployContext = createContext<DeployContextValue | null>(null);

// ─────────────────────────────────────────────
//  Provider
// ─────────────────────────────────────────────

export function DeployProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(deployReducer, initialState);
  return (
    <DeployContext.Provider value={{ state, dispatch }}>
      {children}
    </DeployContext.Provider>
  );
}

// ─────────────────────────────────────────────
//  Hook
// ─────────────────────────────────────────────

export function useDeployContext(): DeployContextValue {
  const context = useContext(DeployContext);
  if (context === null) {
    throw new Error("useDeployContext must be used within a DeployProvider");
  }
  return context;
}
