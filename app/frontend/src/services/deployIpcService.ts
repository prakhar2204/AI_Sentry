/**
 * Sentryɸ — Deploy IPC Service (W2)
 * services/deployIpcService.ts
 *
 * Frontend bridge for all deploy:* commands sent to the Python backend
 * via a dedicated Electron request/response channel.
 *
 * A persistent Python worker handles commands sequentially, retaining deployment
 * state in memory and returning the typed result after each command completes.
 *
 * Command flow:
 *   1. User selects provider → cloudAuthService launches the official CLI
 *   2. The CLI opens the system browser and owns the authentication session
 *   3. Electron verifies identity and returns only public account metadata
 *   4. Frontend calls generatePlan() → shows plan to user
 *   5. User reviews + confirms → dryRun() → deploy()
 *   6. Results shown in DeployResultPage
 */

import type {
  DeployProvider,
  CloudDeployConfig,
  DeployPlanResult,
  DryRunResult,
  DeployExecuteResult,
  CredentialValidationResult,
  DeployStatusResult,
  DeployRollbackResult,
} from "./deployIpcTypes";

// ─────────────────────────────────────────────
//  Electron API bridge
// ─────────────────────────────────────────────

function getApi(): NonNullable<typeof window.electronAPI> {
  if (!window.electronAPI) {
    throw new Error("Electron API unavailable — not running in Electron");
  }
  return window.electronAPI;
}

// ─────────────────────────────────────────────
//  Deploy IPC helpers
// ─────────────────────────────────────────────

/**
 * Send a deploy:* command to the Python backend and wait for a typed response.
 * The Python process emits one JSON line for the result event, then exits.
 */
async function invokeDeployCommand<T>(
  command: string,
  provider: DeployProvider,
  credentials: Record<string, string>,
  payload: Record<string, unknown> = {}
): Promise<T> {
  const api = getApi();
  const ipcPayload = {
    command,
    provider,
    credentials,
    payload,
  };

  // Await the command result; a process-start acknowledgement is not a result.
  return await api.runBackendCommand(ipcPayload) as T;
}

// ─────────────────────────────────────────────
//  Public API
// ─────────────────────────────────────────────


/**
 * Step 1b — Validate credentials already in hand (access key, token, etc.)
 * without going through the browser flow.
 */
export async function validateCredentials(
  provider: DeployProvider,
  credentials: Record<string, string>
): Promise<CredentialValidationResult> {
  return invokeDeployCommand<CredentialValidationResult>(
    "deploy:validate_credentials",
    provider,
    credentials,
  );
}

/**
 * Step 2 — Generate a deployment plan.
 * Returns the full plan (resources, estimated cost, security notes).
 */
export async function generateDeployPlan(
  provider:    DeployProvider,
  config:      CloudDeployConfig,
  credentials: Record<string, string>,
  scanReport:  Record<string, unknown>
): Promise<DeployPlanResult> {
  return invokeDeployCommand<DeployPlanResult>(
    "deploy:generate_plan",
    provider,
    credentials,
    { config, scan_report: scanReport }
  );
}

/**
 * Step 3 — Dry run: validate the plan without creating any resources.
 */
export async function dryRunDeployment(
  provider:    DeployProvider,
  plan:        Record<string, unknown>,
  credentials: Record<string, string>
): Promise<DryRunResult> {
  return invokeDeployCommand<DryRunResult>(
    "deploy:dry_run",
    provider,
    credentials,
    { plan }
  );
}

/**
 * Step 4 — Execute the deployment. Requires confirmed=true.
 * NEVER call this without showing the plan to the user first.
 */
export async function executeDeployment(
  provider:    DeployProvider,
  plan:        Record<string, unknown>,
  credentials: Record<string, string>,
  confirmed:   boolean = false
): Promise<DeployExecuteResult> {
  if (!confirmed) {
    throw new Error("User must confirm the deployment plan before executing");
  }
  return invokeDeployCommand<DeployExecuteResult>(
    "deploy:execute",
    provider,
    credentials,
    { plan, confirmed: true }
  );
}

/**
 * Poll the status of a running deployment.
 */
export async function getDeploymentStatus(
  provider:      DeployProvider,
  deploymentId:  string,
  credentials:   Record<string, string>
): Promise<DeployStatusResult> {
  return invokeDeployCommand<DeployStatusResult>(
    "deploy:status",
    provider,
    credentials,
    { deployment_id: deploymentId }
  );
}

/**
 * Rollback / tear down a deployment by ID.
 */
export async function rollbackDeployment(
  provider:     DeployProvider,
  deploymentId: string,
  credentials:  Record<string, string>
): Promise<DeployRollbackResult> {
  return invokeDeployCommand<DeployRollbackResult>(
    "deploy:rollback",
    provider,
    credentials,
    { deployment_id: deploymentId }
  );
}
