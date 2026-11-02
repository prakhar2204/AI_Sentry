/**
 * Sentryɸ — Deploy Flow Context (W2)
 * store/DeployFlowContext.tsx
 *
 * NEW in W2: Full multi-step deployment flow state machine.
 * (Separate from the existing DeployContext which manages Screen 9 config form)
 *
 * Flow steps:
 *   provider_select → auth → config → plan_review → dry_run → confirm → deploying → complete/error
 */

import React, {
  createContext,
  useContext,
  useReducer,
  type ReactNode,
} from "react";
import type {
  DeployFlowState,
  DeployFlowStep,
  DeployProvider,
  CloudDeployConfig,
  DeployPlanResult,
  DryRunResult,
  DeployExecuteResult,
} from "../services/deployIpcTypes";
import { INITIAL_DEPLOY_STATE } from "../services/deployIpcTypes";

// ─────────────────────────────────────────────
//  Actions
// ─────────────────────────────────────────────

export type DeployFlowAction =
  | { type: "SET_STEP";          step: DeployFlowStep }
  | { type: "SET_PROVIDER";      provider: DeployProvider }
  | { type: "SET_CREDENTIALS";   credentials: Record<string, string> }
  | { type: "MERGE_CREDENTIALS"; patch: Record<string, string> }
  | { type: "SET_CONFIG";        config: Partial<CloudDeployConfig> }
  | { type: "SET_PLAN";          plan: DeployPlanResult }
  | { type: "SET_DRY_RUN";       result: DryRunResult }
  | { type: "SET_DEPLOY_RESULT"; result: DeployExecuteResult }
  | { type: "SET_LOADING";       loading: boolean }
  | { type: "SET_ERROR";         error: string }
  | { type: "CLEAR_ERROR" }
  | { type: "RESET" };

// ─────────────────────────────────────────────
//  Reducer
// ─────────────────────────────────────────────

function deployFlowReducer(
  state: DeployFlowState,
  action: DeployFlowAction
): DeployFlowState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.step, error: null };

    case "SET_PROVIDER":
      return {
        ...state,
        provider:    action.provider,
        credentials: {},
        config:      {},
        plan:        null,
        dryRunResult: null,
        deployResult: null,
        error:       null,
        step:        "auth",
      };

    case "SET_CREDENTIALS":
      return { ...state, credentials: action.credentials };

    case "MERGE_CREDENTIALS":
      return {
        ...state,
        credentials: { ...state.credentials, ...action.patch },
      };

    case "SET_CONFIG":
      return { ...state, config: { ...state.config, ...action.config } };

    case "SET_PLAN":
      return { ...state, plan: action.plan, step: "plan_review", isLoading: false };

    case "SET_DRY_RUN":
      return {
        ...state,
        dryRunResult: action.result,
        isLoading:    false,
        step: action.result.success ? "confirm" : "error",
        error: action.result.success
          ? null
          : action.result.errors.join("; "),
      };

    case "SET_DEPLOY_RESULT":
      return {
        ...state,
        deployResult: action.result,
        isLoading:    false,
        step: action.result.status === "complete" ? "complete" : "error",
        error: action.result.errors.length > 0
          ? action.result.errors.join("; ")
          : null,
      };

    case "SET_LOADING":
      return { ...state, isLoading: action.loading, error: null };

    case "SET_ERROR":
      return { ...state, error: action.error, isLoading: false, step: "error" };

    case "CLEAR_ERROR":
      return { ...state, error: null };

    case "RESET":
      return { ...INITIAL_DEPLOY_STATE };

    default:
      return state;
  }
}

// ─────────────────────────────────────────────
//  Context
// ─────────────────────────────────────────────

interface DeployFlowContextValue {
  state:    DeployFlowState;
  dispatch: React.Dispatch<DeployFlowAction>;
}

const DeployFlowContext = createContext<DeployFlowContextValue | null>(null);

export function DeployFlowProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(deployFlowReducer, INITIAL_DEPLOY_STATE);
  return (
    <DeployFlowContext.Provider value={{ state, dispatch }}>
      {children}
    </DeployFlowContext.Provider>
  );
}

export function useDeployFlow(): DeployFlowContextValue {
  const ctx = useContext(DeployFlowContext);
  if (!ctx) {
    throw new Error("useDeployFlow must be used within <DeployFlowProvider>");
  }
  return ctx;
}
