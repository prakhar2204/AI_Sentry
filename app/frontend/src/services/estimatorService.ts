import { buildScanConfig } from "./scanService";

export interface EstimateResult {
  model_profile?: { name: string; format: string; weights_gib: number; required_ram_gib: number; recommended_vram_gib: number };
  capacity?: { allowed: boolean; reason: string; available_ram_gib: number; required_ram_gib: number };
  total_probes: number;
  estimated_time_sec: number | null;
  estimated_time_display: string;
  estimated_cost_usd: number | null;
  per_category: Record<string, number>;
  shared_categories: Record<string, string[]>;
  mode: string;
  engine: string;
  is_heavy: boolean;
  note: string;
}

export interface EstimateConfig {
  local_model_path?: string;
  target?: string;
  categories: string[];
  scan_depth: "quick" | "standard" | "deep";
  mode: "api" | "local";
  engine?: "auto" | "garak" | "pyrit" | "mock";
}

/** Desktop estimates come from the same probe tables as the selected engine. */
export async function getEstimate(config: EstimateConfig): Promise<EstimateResult> {
  if (window.electronAPI) {
    return await window.electronAPI.runBackendCommand({
      command: "scan:estimate", ...config,
    }) as EstimateResult;
  }
  // Browser-only preview follows the simulator's configuration, never claims a
  // real engine was selected or estimates charges for a simulated scan.
  const preview = buildScanConfig("browser-preview", config.mode, config.scan_depth, config.categories);
  return {
    total_probes: preview.total_probes,
    per_category: preview.per_category_probes,
    shared_categories: {},
    mode: config.mode,
    engine: "Browser simulation",
    estimated_time_sec: null,
    estimated_time_display: "Simulation only",
    estimated_cost_usd: 0,
    is_heavy: false,
    note: "Browser preview uses simulated results. Open the desktop app to scan a model.",
  };
}
