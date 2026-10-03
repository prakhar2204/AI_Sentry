/**
 * AI-SENTRY -- Scan Service (Simulator)
 * services/scanService.ts
 *
 * Deterministic scan simulation that emits events matching the
 * ScanProgressEvent contract defined in scanTypes.ts.
 *
 * Implementation note (background tab throttling):
 *   Browsers clamp setTimeout to ≥1000ms when the page is in a background
 *   tab. This service uses a chunked tick approach: each "tick" processes
 *   a batch of virtual work and then schedules the next tick. The batch
 *   size is calibrated so each tick takes <16ms of real computation, while
 *   the inter-tick gap is 100ms (fast enough to see progress in foreground;
 *   degrades gracefully in background tabs to ~1 tick/sec).
 *
 * Architecture:
 *   React → scanService.startScan(config, handlers) → events → React
 *
 * When real backend integration is ready:
 *   React → window.api.startScan(config) → IPC → Python → events → React
 *
 * The public API (startScan, buildScanConfig) does NOT change.
 */

import {
  type ScanExecutionConfig,
  type ScanEventHandlers,
  type ScanController,
  type ScanProgressEvent,
  type ScanActivityEntry,
  type CategoryState,
  type ScanLifecycleStage,
  type LogSeverity,
  CATEGORY_LABELS,
  STAGE_LABELS,
} from "./scanTypes";

// ─────────────────────────────────────────────
//  Constants
// ─────────────────────────────────────────────

const BASE_PROBES: Record<string, number> = {
  prompt_injection: 45,
  jailbreak: 50,
  data_leak: 55,
  harmful_output: 45,
};

const DEPTH_MULTIPLIERS: Record<string, number> = {
  quick: 0.5,
  standard: 1.0,
  deep: 2.0,
};

/**
 * Deterministic simulated finding labels per category.
 * Prefixed [sim] to distinguish from real findings.
 */
const SIMULATED_FINDING_LABELS: Record<string, string[]> = {
  prompt_injection: [
    "Potential instruction override pattern identified",
    "Context manipulation vector identified",
    "Role-play injection pattern bypassed constraint",
  ],
  jailbreak: [
    "Content filter bypass pattern detected",
    "Multi-turn escalation vector detected",
  ],
  data_leak: [
    "Response data boundary violation risk",
    "Configuration detail exposure risk",
    "Potential training data fragment exposure",
  ],
  harmful_output: [
    "Output constraint bypass under obfuscation",
    "Bias amplification in adversarial context",
  ],
};

/**
 * Probe tick configuration.
 *
 * PROBES_PER_TICK: How many virtual probes to "run" per scheduler tick.
 *   Higher = faster simulation, fewer renders.
 * TICK_INTERVAL_MS: Target ms between ticks.
 *   100ms gives ~10 renders/sec in foreground.
 *   Degrades to ~1/sec in background — acceptable.
 * FINDING_EVERY_N_PROBES: Emit a finding warn every N probes per category.
 */
const PROBES_PER_TICK = 3;
const TICK_INTERVAL_MS = 100;
const FINDING_EVERY_N_PROBES = 12;

// ─────────────────────────────────────────────
//  Singleton guard
// ─────────────────────────────────────────────

let activeScanId = 0;

// ─────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────

function ts(): string {
  return new Date().toLocaleTimeString("en-GB", { hour12: false });
}

function computePerCategoryProbes(
  categories: string[],
  depth: string
): Record<string, number> {
  const mult = DEPTH_MULTIPLIERS[depth] ?? 1.0;
  const result: Record<string, number> = {};
  for (const cat of categories) {
    result[cat] = Math.round((BASE_PROBES[cat] ?? 0) * mult);
  }
  return result;
}

// ─────────────────────────────────────────────
//  Public API
// ─────────────────────────────────────────────

export function startScan(
  config: ScanExecutionConfig,
  handlers: ScanEventHandlers
): ScanController {
  activeScanId++;
  const thisScanId = activeScanId;

  const controller: ScanController = {
    cancelled: false,
    cancel() {
      (this as { cancelled: boolean }).cancelled = true;
    },
  };

  // Kick off simulation on next tick so mount is settled
  setTimeout(() => {
    if (controller.cancelled || thisScanId !== activeScanId) return;
    runSimulation(config, handlers, controller, thisScanId);
  }, 50);

  return controller;
}

// ─────────────────────────────────────────────
//  Simulation State Machine
// ─────────────────────────────────────────────

/**
 * Internal simulation state. Held in closure, not React state.
 * React state receives only typed events via handlers.
 */
interface SimState {
  // Configuration
  scanId: number;
  config: ScanExecutionConfig;
  handlers: ScanEventHandlers;
  controller: ScanController;

  // Timing
  startTime: number;
  tickHandle: ReturnType<typeof setTimeout> | null;

  // Stage machine
  stage: ScanLifecycleStage;
  stageProgress: number;        // ticks completed in current stage

  // Overall probe tracking
  probesCompleted: number;
  probesTotal: number;

  // Category tracking
  catStates: CategoryState[];
  catIdx: number;               // which category we're currently in

  // Findings
  findings: number;
}

function runSimulation(
  config: ScanExecutionConfig,
  handlers: ScanEventHandlers,
  controller: ScanController,
  scanId: number
): void {
  const perCat =
    Object.keys(config.per_category_probes).length > 0
      ? config.per_category_probes
      : computePerCategoryProbes(config.categories, config.scan_depth);

  const totalProbes = Object.values(perCat).reduce((a, b) => a + b, 0);

  const catStates: CategoryState[] = config.categories.map((id) => ({
    id,
    label: CATEGORY_LABELS[id] ?? id,
    status: "queued" as const,
    probes_total: perCat[id] ?? 0,
    probes_completed: 0,
  }));

  const sim: SimState = {
    scanId,
    config,
    handlers,
    controller,
    startTime: Date.now(),
    tickHandle: null,
    stage: "preparing",
    stageProgress: 0,
    probesCompleted: 0,
    probesTotal: totalProbes,
    catStates,
    catIdx: 0,
    findings: 0,
  };

  // Emit initial activity log (synchronous — before any awaits)
  emit(sim, "info", "Preparing scan configuration");
  emit(sim, "info", `Target: ${config.target}`);
  emit(sim, "info", `Mode: ${config.mode === "api" ? "API Endpoint" : "Local Model"}`);
  emit(sim, "info", `Depth: ${config.scan_depth}`);
  emit(sim, "info", `Categories: ${config.categories.length} selected`);
  emit(sim, "info", `Total probes: ${totalProbes}`);

  // Emit initial progress
  emitProgress(sim);

  // Schedule first tick
  scheduleTick(sim);
}

// ─────────────────────────────────────────────
//  Tick scheduler
// ─────────────────────────────────────────────

function scheduleTick(sim: SimState): void {
  sim.tickHandle = setTimeout(() => tick(sim), TICK_INTERVAL_MS);
}

/**
 * Main simulation tick.
 * Each call advances the state machine by one step.
 * Schedules itself unless simulation is complete/cancelled.
 */
function tick(sim: SimState): void {
  if (sim.controller.cancelled || sim.scanId !== activeScanId) return;

  const elapsed = Math.round((Date.now() - sim.startTime) / 1000);

  switch (sim.stage) {
    // ── Preparing: 4 ticks (≈400ms) ──
    case "preparing": {
      sim.stageProgress++;
      if (sim.stageProgress >= 4) {
        advanceTo(sim, "validating_target");
        emit(sim, "info", "Validating target endpoint");
        emitProgress(sim);
      } else {
        emitProgress(sim);
      }
      break;
    }

    // ── Validating target: 5 ticks ──
    case "validating_target": {
      sim.stageProgress++;
      if (sim.stageProgress >= 5) {
        emit(sim, "info", "Target validation completed");
        advanceTo(sim, "initializing_scan");
        emit(sim, "info", "Initializing analysis modules");
        emitProgress(sim);
      } else {
        emitProgress(sim);
      }
      break;
    }

    // ── Initializing scan: 6 ticks ──
    case "initializing_scan": {
      sim.stageProgress++;
      if (sim.stageProgress >= 6) {
        emit(sim, "info", "Analysis modules initialized");
        advanceTo(sim, "scanning");
        // Initialize first category
        if (sim.catStates.length > 0) {
          sim.catStates[0].status = "active";
          emit(sim, "info", `Evaluating ${sim.catStates[0].label.toLowerCase()}`);
        }
        emitProgress(sim);
      } else {
        emitProgress(sim);
      }
      break;
    }

    // ── Scanning: per-category probe batches ──
    case "scanning": {
      const cat = sim.catStates[sim.catIdx];
      if (!cat) {
        // All categories done
        advanceTo(sim, "analyzing");
        emit(sim, "info", "All probes completed. Starting analysis...");
        emitProgress(sim);
        break;
      }

      // Run a batch of probes
      const remaining = cat.probes_total - cat.probes_completed;
      const batch = Math.min(PROBES_PER_TICK, remaining);

      for (let i = 0; i < batch; i++) {
        cat.probes_completed++;
        sim.probesCompleted++;

        // Emit finding at interval
        if (
          cat.probes_completed > 0 &&
          cat.probes_completed % FINDING_EVERY_N_PROBES === 0
        ) {
          const labels = SIMULATED_FINDING_LABELS[cat.id] ?? [];
          if (labels.length > 0) {
            const idx = Math.floor(cat.probes_completed / FINDING_EVERY_N_PROBES - 1) % labels.length;
            sim.findings++;
            emit(sim, "warn", `Potential finding: ${labels[idx]}`);
          }
        }
      }

      // Category complete?
      if (cat.probes_completed >= cat.probes_total) {
        cat.status = "complete";
        emit(sim, "info", `${cat.label} evaluation completed (${cat.probes_total} probes)`);
        sim.catIdx++;

        // Start next category
        if (sim.catIdx < sim.catStates.length) {
          sim.catStates[sim.catIdx].status = "active";
          emit(sim, "info", `Evaluating ${sim.catStates[sim.catIdx].label.toLowerCase()}`);
        }
      }

      emitProgress(sim);
      break;
    }

    // ── Analyzing: 4 ticks ──
    case "analyzing": {
      sim.stageProgress++;
      if (sim.stageProgress >= 4) {
        emit(sim, "info", "Analysis complete");
        advanceTo(sim, "scoring");
        emit(sim, "info", "Computing risk scores");
        emitProgress(sim);
      } else {
        emitProgress(sim);
      }
      break;
    }

    // ── Scoring: 3 ticks ──
    case "scoring": {
      sim.stageProgress++;
      if (sim.stageProgress >= 3) {
        emit(sim, "info", "Risk scoring complete");
        advanceTo(sim, "generating_recommendations");
        emit(sim, "info", "Generating security recommendations");
        emitProgress(sim);
      } else {
        emitProgress(sim);
      }
      break;
    }

    // ── Recommendations: 3 ticks ──
    case "generating_recommendations": {
      sim.stageProgress++;
      if (sim.stageProgress >= 3) {
        advanceTo(sim, "generating_report");
        emit(sim, "info", "Compiling security report");
        emitProgress(sim);
      } else {
        emitProgress(sim);
      }
      break;
    }

    // ── Report: 4 ticks ──
    case "generating_report": {
      sim.stageProgress++;
      if (sim.stageProgress >= 4) {
        advanceTo(sim, "completed");
        emit(sim, "info", "Scan complete — report ready");
        emitProgress(sim);
        // Signal completion — do NOT schedule next tick
        sim.handlers.onComplete();
        return;
      } else {
        emitProgress(sim);
      }
      break;
    }

    default:
      return;
  }

  scheduleTick(sim);
}

// ─────────────────────────────────────────────
//  State machine helpers
// ─────────────────────────────────────────────

function advanceTo(sim: SimState, stage: ScanLifecycleStage): void {
  sim.stage = stage;
  sim.stageProgress = 0;
}

function emit(sim: SimState, severity: LogSeverity, message: string): void {
  if (sim.controller.cancelled || sim.scanId !== activeScanId) return;
  const entry: ScanActivityEntry = {
    timestamp: ts(),
    severity,
    message,
  };
  sim.handlers.onActivity(entry);
}

function emitProgress(sim: SimState): void {
  if (sim.controller.cancelled || sim.scanId !== activeScanId) return;

  const elapsed = Math.round((Date.now() - sim.startTime) / 1000);
  const activeCat = sim.catStates[sim.catIdx]?.id ?? null;
  const label = computeLabel(sim);

  const event: ScanProgressEvent = {
    stage: sim.stage,
    timestamp: ts(),
    probes_completed: sim.probesCompleted,
    probes_total: sim.probesTotal,
    active_category: activeCat,
    activity_label: label,
    categories: sim.catStates.map((c) => ({ ...c })),
    preliminary_findings: sim.findings,
    elapsed_sec: elapsed,
  };

  sim.handlers.onProgress(event);
}

function computeLabel(sim: SimState): string {
  if (sim.stage === "scanning") {
    const cat = sim.catStates[sim.catIdx];
    if (cat) return `Testing ${cat.label.toLowerCase()}`;
    return STAGE_LABELS.scanning;
  }
  return STAGE_LABELS[sim.stage] ?? sim.stage;
}

// ─────────────────────────────────────────────
//  Config builder (public)
// ─────────────────────────────────────────────

export function buildScanConfig(
  target: string,
  mode: "api" | "local",
  depth: "quick" | "standard" | "deep",
  categories: string[]
): ScanExecutionConfig {
  const perCat = computePerCategoryProbes(categories, depth);
  const total = Object.values(perCat).reduce((a, b) => a + b, 0);
  return {
    target,
    mode,
    scan_depth: depth,
    categories,
    total_probes: total,
    per_category_probes: perCat,
  };
}
