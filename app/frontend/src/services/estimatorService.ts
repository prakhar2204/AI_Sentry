/**
 * AI-SENTRY -- Estimator Service
 * services/estimatorService.ts
 *
 * Simulates the IPC call to the Python backend estimator.
 * Mirrors the exact calculation from core/estimator.py:
 *
 *   BASE_PROBES: prompt_injection=45, jailbreak=50, data_leak=55, harmful_output=45
 *   DEPTH_MULTIPLIERS: quick=0.5, standard=1.0, deep=2.0
 *   TIME_PER_PROBE: api=1.5s, local=0.8s
 *   COST_PER_PROBE: api=$0.0005, local=$0.0
 *   HEAVY: probes > 300 OR time > 300s
 *
 * When the Electron IPC bridge is built (Phase 8), this function
 * will be replaced with a real window.api.getEstimate() call.
 */

// ─────────────────────────────────────────────
//  Constants (match backend exactly)
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

const TIME_PER_PROBE: Record<string, number> = {
  api: 1.5,
  local: 0.8,
};

const COST_PER_PROBE: Record<string, number> = {
  api: 0.0005,
  local: 0.0,
};

const MAX_SAFE_PROBES = 300;
const MAX_SAFE_TIME_SEC = 300;

// ─────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────

export interface EstimateResult {
  total_probes: number;
  estimated_time_sec: number;
  estimated_time_display: string;
  estimated_cost_usd: number;
  per_category: Record<string, number>;
  depth_multiplier: number;
  mode: string;
  is_heavy: boolean;
  probes_exceeded: boolean;
  time_exceeded: boolean;
}

export interface EstimateConfig {
  categories: string[];
  scan_depth: string;
  mode: string;
}

// ─────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────

function formatTime(totalSeconds: number): string {
  if (totalSeconds < 60) {
    return `${totalSeconds} sec`;
  }
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (seconds === 0) {
    return `${minutes} min`;
  }
  return `${minutes} min ${seconds} sec`;
}

// ─────────────────────────────────────────────
//  Service
// ─────────────────────────────────────────────

/**
 * Calculate scan estimate.
 *
 * Deterministic -- same inputs always produce same outputs.
 * Mirrors core/estimator.py exactly.
 *
 * Returns a Promise to match the future IPC call signature.
 */
export async function getEstimate(
  config: EstimateConfig
): Promise<EstimateResult> {
  const multiplier = DEPTH_MULTIPLIERS[config.scan_depth] ?? 1.0;
  const timePerProbe = TIME_PER_PROBE[config.mode] ?? 1.5;
  const costPerProbe = COST_PER_PROBE[config.mode] ?? 0.0;

  // Calculate per-category probes
  const perCategory: Record<string, number> = {};
  let totalProbes = 0;

  for (const cat of config.categories) {
    const base = BASE_PROBES[cat] ?? 0;
    const probes = Math.round(base * multiplier);
    perCategory[cat] = probes;
    totalProbes += probes;
  }

  // Calculate time and cost
  const timeSec = Math.round(totalProbes * timePerProbe);
  const costUsd = Math.round(totalProbes * costPerProbe * 10000) / 10000;

  // Safety check
  const probesExceeded = totalProbes > MAX_SAFE_PROBES;
  const timeExceeded = timeSec > MAX_SAFE_TIME_SEC;
  const isHeavy = probesExceeded || timeExceeded;

  return {
    total_probes: totalProbes,
    estimated_time_sec: timeSec,
    estimated_time_display: formatTime(timeSec),
    estimated_cost_usd: costUsd,
    per_category: perCategory,
    depth_multiplier: multiplier,
    mode: config.mode,
    is_heavy: isHeavy,
    probes_exceeded: probesExceeded,
    time_exceeded: timeExceeded,
  };
}
