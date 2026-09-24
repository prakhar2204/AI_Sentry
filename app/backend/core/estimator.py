"""
AI-SENTRY -- Pre-Scan Estimation Engine
core/estimator.py

Deterministic calculation of probe counts, time estimates, and cost
projections for a given ScanManifest.

No randomness, no network calls, no external APIs -- pure arithmetic
derived from the manifest's depth, mode, and selected categories.

Reference data:
    - Probe counts are calibrated from TRD §2.3 probe taxonomy and
      engine adapter specifications (Garak baseline counts)
    - Time-per-probe assumes sequential execution per engine
    - Cost-per-probe assumes OpenAI gpt-3.5-turbo pricing
      ($0.0005/1K input tokens, ~800 tokens avg per probe)

Phase 3a deliverable.
Reference: docs/TRD.md Section 2.1 (Manifest System), Section 2.3 (Probes)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.manifest import ScanManifest, ScanDepth, ScanMode, ProbeCategory


# ─────────────────────────────────────────────
#  Constants -- probe counts per category
# ─────────────────────────────────────────────

# Base probes per category at "standard" depth.
# Quick = base * QUICK_MULTIPLIER, Deep = base * DEEP_MULTIPLIER.
BASE_PROBES_PER_CATEGORY: dict[str, int] = {
    "prompt_injection": 45,
    "jailbreak":        50,
    "data_leak":        55,
    "harmful_output":   45,
}

# ─────────────────────────────────────────────
#  Constants -- depth multipliers
# ─────────────────────────────────────────────

DEPTH_MULTIPLIERS: dict[str, float] = {
    "quick":    0.5,
    "standard": 1.0,
    "deep":     2.0,
}

# ─────────────────────────────────────────────
#  Constants -- time per probe (seconds)
# ─────────────────────────────────────────────

TIME_PER_PROBE: dict[str, float] = {
    "api":   1.5,   # remote API: network latency + rate limiting
    "local": 0.8,   # local llama.cpp: no network, faster inference
}

# ─────────────────────────────────────────────
#  Constants -- cost per probe (USD)
# ─────────────────────────────────────────────

COST_PER_PROBE: dict[str, float] = {
    "api":   0.0005,  # ~800 tokens avg, gpt-3.5-turbo pricing
    "local": 0.0,     # local inference has no per-call cost
}


# ─────────────────────────────────────────────
#  Result type
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class ScanEstimate:
    """
    Immutable result of the estimation engine.

    All fields are deterministic given the same manifest input.

    Attributes:
        total_probes       -- Number of adversarial probes to send
        estimated_time_sec -- Total estimated wall time in seconds
        estimated_time_min -- Same value converted to minutes (rounded to 1 dp)
        estimated_cost_usd -- Projected API cost (0.00 for local mode)
        per_category       -- Breakdown: {category_name: probe_count}
        depth_multiplier   -- The multiplier applied (0.5 / 1.0 / 2.0)
        mode               -- "api" or "local" (echoed for display)
    """
    total_probes:       int
    estimated_time_sec: int
    estimated_time_min: float
    estimated_cost_usd: float
    per_category:       dict[str, int]
    depth_multiplier:   float
    mode:               str

    def to_dict(self) -> dict:
        """Return a plain dict suitable for JSON serialization."""
        return {
            "total_probes":       self.total_probes,
            "estimated_time_sec": self.estimated_time_sec,
            "estimated_time_min": self.estimated_time_min,
            "estimated_cost_usd": self.estimated_cost_usd,
            "per_category":       dict(self.per_category),
            "depth_multiplier":   self.depth_multiplier,
            "mode":               self.mode,
        }


# ─────────────────────────────────────────────
#  Core calculation
# ─────────────────────────────────────────────

def calculate_probes_per_category(
    categories: list[ProbeCategory],
    depth: ScanDepth,
) -> dict[str, int]:
    """
    Calculate the number of probes for each selected category,
    scaled by depth multiplier.

    Parameters:
        categories -- List of ProbeCategory enum values
        depth      -- ScanDepth enum value

    Returns:
        Dict mapping category name (str) to probe count (int).
        Unknown categories are safely returned as 0 probes.
    """
    multiplier = DEPTH_MULTIPLIERS.get(depth.value, 1.0)
    result: dict[str, int] = {}

    for cat in categories:
        base = BASE_PROBES_PER_CATEGORY.get(cat.value, 0)
        result[cat.value] = max(1, int(base * multiplier))

    return result


def calculate_total_probes(per_category: dict[str, int]) -> int:
    """Sum all per-category probe counts."""
    return sum(per_category.values())


def calculate_time(total_probes: int, mode: ScanMode) -> tuple[int, float]:
    """
    Estimate total scan time.

    Returns:
        (seconds: int, minutes: float rounded to 1 decimal)
    """
    rate = TIME_PER_PROBE.get(mode.value, 1.5)
    seconds = int(total_probes * rate)
    minutes = round(seconds / 60, 1)
    return seconds, minutes


def calculate_cost(total_probes: int, mode: ScanMode) -> float:
    """
    Estimate total API cost in USD.

    Returns 0.0 for local mode.
    """
    rate = COST_PER_PROBE.get(mode.value, 0.0)
    return round(total_probes * rate, 4)


# ─────────────────────────────────────────────
#  Orchestrator
# ─────────────────────────────────────────────

def estimate_scan(manifest: ScanManifest) -> ScanEstimate:
    """
    Produce a full ScanEstimate from a validated ScanManifest.

    This is the single entry point used by the CLI pipeline.
    It delegates to the individual calculation functions and
    assembles the result.

    Parameters:
        manifest -- A validated ScanManifest (after Phase 2c)

    Returns:
        ScanEstimate with all fields populated.
    """
    per_category = calculate_probes_per_category(
        categories=manifest.categories,
        depth=manifest.scan_depth,
    )

    total = calculate_total_probes(per_category)
    time_sec, time_min = calculate_time(total, manifest.mode)
    cost = calculate_cost(total, manifest.mode)
    multiplier = DEPTH_MULTIPLIERS.get(manifest.scan_depth.value, 1.0)

    return ScanEstimate(
        total_probes=total,
        estimated_time_sec=time_sec,
        estimated_time_min=time_min,
        estimated_cost_usd=cost,
        per_category=per_category,
        depth_multiplier=multiplier,
        mode=manifest.mode.value,
    )


# ─────────────────────────────────────────────
#  Display
# ─────────────────────────────────────────────

_DIVIDER = "-" * 60


def format_estimation(estimate: ScanEstimate) -> str:
    """
    Return a human-readable estimation block for CLI output.

    Output format:
        ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
          SCAN ESTIMATE
        ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
          Total probes   : 95
          Est. time      : ~1.2 min  (71 sec)
          Est. cost      : $0.0475   (api mode)
          Depth factor   : x0.5     (quick)

          Per category:
            prompt_injection : 22
            jailbreak        : 25
        ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
    """
    lines = [
        "",
        _DIVIDER,
        "  SCAN ESTIMATE",
        _DIVIDER,
        f"  Total probes   : {estimate.total_probes}",
    ]

    # Time
    if estimate.estimated_time_min >= 60:
        hrs = round(estimate.estimated_time_min / 60, 1)
        lines.append(
            f"  Est. time      : ~{hrs} hrs  ({estimate.estimated_time_sec} sec)"
        )
    else:
        lines.append(
            f"  Est. time      : ~{estimate.estimated_time_min} min  "
            f"({estimate.estimated_time_sec} sec)"
        )

    # Cost
    if estimate.estimated_cost_usd > 0:
        lines.append(
            f"  Est. cost      : ${estimate.estimated_cost_usd:.4f}  "
            f"({estimate.mode} mode)"
        )
    else:
        lines.append(
            f"  Est. cost      : $0.00  ({estimate.mode} mode -- no API cost)"
        )

    lines.append(
        f"  Depth factor   : x{estimate.depth_multiplier}  "
        f"({estimate.mode})"
    )

    # Per-category breakdown
    lines.append("")
    lines.append("  Per category:")
    max_name_len = max(len(name) for name in estimate.per_category)
    for name, count in estimate.per_category.items():
        padded = name.ljust(max_name_len)
        lines.append(f"    {padded} : {count}")

    lines.append(_DIVIDER)
    return "\n".join(lines)


def display_estimation(estimate: ScanEstimate) -> None:
    """Print the formatted estimation to stdout."""
    print(format_estimation(estimate))
