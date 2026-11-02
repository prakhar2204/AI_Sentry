/**
 * Sentryɸ — Deploy IPC Service (W2)
 * services/deployIpcService.ts
 *
 * Frontend bridge for all deploy:* commands sent to the Python backend
 * via the Electron IPC channel (same channel as scan commands).
 *
 * Each deploy operation spawns a new ipc_server process with a deploy:*
 * command and waits for the typed response event.
 *
 * Command flow:
 *   1. User selects provider → deployIpcService.getAuthUrl(provider)
 *   2. Python opens OAuth server, returns auth URL → Electron opens browser
 *   3. User signs in → callback → Python emits deploy_auth_complete
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
  AuthCompleteResult,
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

  // Use the existing startScan / IPC channel — deploy commands share the pipe
  const result = await api.startScan(ipcPayload as never);
  if (!result.started) {
    throw new Error(result.error ?? `Deploy command failed: ${command}`);
  }

  // Return the result carried in the IPC response
  return (result as unknown as { data: T }).data;
}

// ─────────────────────────────────────────────
//  Public API
// ─────────────────────────────────────────────

/**
 * Step 1 — Get the OAuth login URL for the given provider.
 * Also starts the local callback server on the Python side.
 * Returns the URL to open in the user's browser.
 */
export async function getAuthUrl(
  provider: DeployProvider
): Promise<string> {
  const PROVIDER_PORTS: Record<DeployProvider, number> = {
    aws:     9876,
    azure:   9877,
    gcp:     9878,
    private: 0,
  };
  const port = PROVIDER_PORTS[provider];
  const api  = getApi();

  // Special case: private has no OAuth
  if (provider === "private") return "";

  // Invoke auth URL command — this also starts the callback server
  const result = await api.startScan({
    command:  "deploy:auth_url",
    provider,
    credentials: {},
    payload: { redirect_port: port },
  } as never);

  return (result as unknown as { url?: string }).url ?? "";
}

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
