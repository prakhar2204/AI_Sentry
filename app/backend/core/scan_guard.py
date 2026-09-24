"""
AI-SENTRY -- Scan Safety Guard
core/scan_guard.py

Detects scans that exceed safety thresholds and requires explicit
user acknowledgement before proceeding.

This is a UX safety layer, NOT a hard block. Heavy scans are never
auto-cancelled -- the user always decides. The guard simply ensures
they are aware of the cost/time implications.

Thresholds:
    MAX_SAFE_PROBES   = 300    (any scan with more probes is "heavy")
    MAX_SAFE_TIME_SEC = 300    (any scan estimated >5 min is "heavy")

Either threshold being exceeded triggers the warning.

Position in pipeline:
    CLI
    -> 1. Consent gate            (Phase 1a)
    -> 2. Manifest load + merge   (Phase 2b)
    -> 3. Manifest validation     (Phase 2c)
    -> 4. Estimate + Display      (Phase 3a)
    -> 5. SAFETY GUARD            (Phase 3b)  <- this module
         - light scan  -> normal confirm (Phase 2d)
         - heavy scan  -> warning + extra confirm
    -> 6. Connection validation   (Phase 1d)
    -> 7. Endpoint probe          (Phase 1b/1c)
    -> 8. Scan orchestration      (Phase 3+)

Phase 3b deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.estimator import ScanEstimate


# ─────────────────────────────────────────────
#  Thresholds
# ─────────────────────────────────────────────

MAX_SAFE_PROBES:   int = 300
MAX_SAFE_TIME_SEC: int = 300   # 5 minutes


# ─────────────────────────────────────────────
#  Result type
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class GuardResult:
    """
    Outcome of the safety threshold check.

    Attributes:
        is_heavy        -- True if any threshold is exceeded
        probes_exceeded -- True if total_probes > MAX_SAFE_PROBES
        time_exceeded   -- True if estimated_time_sec > MAX_SAFE_TIME_SEC
        total_probes    -- echoed from estimate
        time_sec        -- echoed from estimate
        time_min        -- echoed from estimate
    """
    is_heavy:        bool
    probes_exceeded: bool
    time_exceeded:   bool
    total_probes:    int
    time_sec:        int
    time_min:        float


# ─────────────────────────────────────────────
#  Detection
# ─────────────────────────────────────────────

def is_heavy_scan(estimate: ScanEstimate) -> GuardResult:
    """
    Check whether a scan estimate exceeds safety thresholds.

    A scan is "heavy" if EITHER:
      - total_probes > MAX_SAFE_PROBES  (300)
      - estimated_time_sec > MAX_SAFE_TIME_SEC  (300 = 5 min)

    This function is PURE: no I/O, no side effects.

    Parameters:
        estimate -- A ScanEstimate from core/estimator.py

    Returns:
        GuardResult with is_heavy=True if any threshold exceeded.
    """
    probes_over = estimate.total_probes > MAX_SAFE_PROBES
    time_over   = estimate.estimated_time_sec > MAX_SAFE_TIME_SEC

    return GuardResult(
        is_heavy=probes_over or time_over,
        probes_exceeded=probes_over,
        time_exceeded=time_over,
        total_probes=estimate.total_probes,
        time_sec=estimate.estimated_time_sec,
        time_min=estimate.estimated_time_min,
    )


# ─────────────────────────────────────────────
#  Display
# ─────────────────────────────────────────────

_DIVIDER     = "-" * 60
_MAX_ATTEMPTS = 3


def display_warning(guard: GuardResult) -> None:
    """
    Print a heavy-scan warning to stdout.

    Shows exactly which thresholds were exceeded and by how much,
    so the user can make an informed decision.
    """
    lines = [
        "",
        _DIVIDER,
        "  [!] HEAVY SCAN DETECTED",
        _DIVIDER,
        "",
    ]

    if guard.probes_exceeded:
        lines.append(
            f"  Total probes   : {guard.total_probes}  "
            f"(threshold: {MAX_SAFE_PROBES})"
        )

    if guard.time_exceeded:
        lines.append(
            f"  Est. time      : ~{guard.time_min} min  "
            f"(threshold: {MAX_SAFE_TIME_SEC // 60} min)"
        )

    lines.append("")
    lines.append("  This scan exceeds recommended safety limits.")
    lines.append("  It may take significantly longer than a standard scan")
    lines.append("  and will send a large number of adversarial probes.")

    if guard.probes_exceeded and guard.time_exceeded:
        lines.append("")
        lines.append("  Both probe count and time thresholds exceeded.")

    lines.append("")
    lines.append(_DIVIDER)

    print("\n".join(lines))


# ─────────────────────────────────────────────
#  Confirmation
# ─────────────────────────────────────────────

def confirm_heavy_scan() -> bool:
    """
    Ask the user to explicitly confirm a heavy scan.

    This is a SEPARATE confirmation from the normal Phase 2d prompt.
    It uses stronger wording to emphasize the risk.

    - Accepts: yes / y / no / n  (case-insensitive)
    - Reprompts on invalid input (up to _MAX_ATTEMPTS times)
    - After max invalid attempts: returns False (safe default)
    - Ctrl-C / EOF: returns False

    Returns:
        True  -- user explicitly confirmed the heavy scan
        False -- user declined or gave too many invalid inputs
    """
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            raw = input("  Proceed with heavy scan? [yes / no]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  Heavy scan cancelled by user.\n")
            return False

        if raw in ("yes", "y"):
            print("\n  Heavy scan confirmed. Proceeding...\n")
            return True

        if raw in ("no", "n"):
            print("\n  Heavy scan cancelled. No probes were sent.\n")
            return False

        remaining = _MAX_ATTEMPTS - attempt
        if remaining > 0:
            print(
                f"  [!] Invalid input '{raw}'. "
                f"Please type 'yes' or 'no'. "
                f"({remaining} attempt{'s' if remaining > 1 else ''} remaining)"
            )
        else:
            print(
                "  [!] Too many invalid inputs. "
                "Heavy scan aborted for safety.\n"
            )

    return False


# ─────────────────────────────────────────────
#  Orchestrator
# ─────────────────────────────────────────────

def check_scan_safety(estimate: ScanEstimate) -> bool:
    """
    Run the full safety guard flow.

    1. Check thresholds
    2. If heavy: display warning + ask extra confirmation
    3. If light: return True immediately (no extra prompt)

    Used by the CLI pipeline as the single entry point.

    Parameters:
        estimate -- A ScanEstimate from core/estimator.py

    Returns:
        True  -- scan may proceed (either light, or heavy + confirmed)
        False -- heavy scan was declined by user
    """
    guard = is_heavy_scan(estimate)

    if not guard.is_heavy:
        return True  # light scan -- no extra confirmation needed

    display_warning(guard)
    return confirm_heavy_scan()
