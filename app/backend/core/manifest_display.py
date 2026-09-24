"""
AI-SENTRY -- Manifest Display & Pre-Scan Confirmation
core/manifest_display.py

Displays the final resolved ScanManifest to the user in a clear,
unambiguous format, then asks for explicit confirmation before the
scan engine is allowed to proceed.

Purpose:
    The user sees EXACTLY what will run -- target, mode, depth, and
    categories -- before any network probes are sent. This is the
    last human decision point in the pipeline.

Design decisions:
    - No modification of the manifest at any point
    - Yes/no prompt with a 3-attempt limit (same pattern as consent gate)
    - Invalid input is re-prompted, not silently ignored
    - "n", "no", Ctrl-C all result in a clean, non-error exit (code 0)
    - Output is plain ASCII only (no Unicode, no emojis)

Position in pipeline:
    CLI
    -> 1. Consent gate            (Phase 1a)
    -> 2. Manifest load + merge   (Phase 2b)
    -> 3. Manifest validation     (Phase 2c)
    -> 4. DISPLAY + CONFIRM       (Phase 2d)  <- this module
    -> 5. Connection validation   (Phase 1d)
    -> 6. Endpoint probe          (Phase 1b/1c)
    -> 7. Scan orchestration      (Phase 3)

Phase 2d deliverable.
Reference: docs/PRD.md User Story U-02 (pre-scan review)
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from core.manifest import ScanManifest

if TYPE_CHECKING:
    from core.estimator import ScanEstimate


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

_DIVIDER     = "-" * 60
_MAX_ATTEMPTS = 3

_CATEGORY_DESCRIPTIONS = {
    "prompt_injection": (
        "Tests whether the model can be manipulated via crafted inputs\n"
        "    to ignore its system prompt or execute injected instructions."
    ),
    "jailbreak": (
        "Tests whether the model can be induced to violate its training\n"
        "    objectives via DAN-style prompts or roleplay scenarios."
    ),
    "data_leak": (
        "Tests whether the model leaks PII, training data, or produces\n"
        "    outputs that enable downstream injection attacks."
    ),
    "harmful_output": (
        "Tests for toxic, biased, or dangerous content generation\n"
        "    including hallucination and targeted bias."
    ),
}


# ─────────────────────────────────────────────
#  Display
# ─────────────────────────────────────────────

def display_manifest(
    manifest: ScanManifest,
    source: str = "",
    estimate: "Optional[ScanEstimate]" = None,
) -> None:
    """
    Print the final resolved ScanManifest to stdout in a clear,
    human-readable format.

    If a ScanEstimate is provided, the total probe count is taken
    from the estimate. Otherwise the probe count is omitted.

    Parameters:
        manifest -- The final resolved ScanManifest (after Phase 2c)
        source   -- Where the config came from: "cli", "file", or "merged"
        estimate -- Optional ScanEstimate from core/estimator.py
    """
    source_label = ""
    if source:
        source_label = f"  Config source  : {source}\n"

    lines = [
        "",
        _DIVIDER,
        "  SCAN CONFIGURATION",
        _DIVIDER,
        f"  Target         : {manifest.target}",
        f"  Mode           : {manifest.mode.value}",
        f"  Scan depth     : {manifest.scan_depth.value}",
    ]

    if estimate is not None:
        lines.append(f"  Est. probes    : ~{estimate.total_probes}")

    lines.append("")
    lines.append("  Categories:")

    for cat in manifest.categories:
        desc = _CATEGORY_DESCRIPTIONS.get(cat.value, "")
        lines.append(f"    [{cat.value}]")
        if desc:
            lines.append(f"    {desc}")
        lines.append("")

    lines.append(f"  Output dir     : {manifest.output_dir}")

    if manifest.source_file:
        lines.append(f"  Config file    : {manifest.source_file}")

    if source_label:
        lines.append(source_label.rstrip())

    if manifest.notes:
        lines.append(f"  Notes          : {manifest.notes}")

    lines.append(f"\n  Manifest ID    : {manifest.manifest_id}")
    lines.append(f"  Created        : {manifest.created_at}")
    lines.append(_DIVIDER)

    print("\n".join(lines))


def display_manifest_compact(manifest: ScanManifest) -> None:
    """
    Print a compact one-line-per-field summary.
    Used in non-interactive / CI contexts (future use).
    """
    cats = ", ".join(c.value for c in manifest.categories)
    print(
        f"\n  Target: {manifest.target} | Mode: {manifest.mode.value} | "
        f"Depth: {manifest.scan_depth.value} | Categories: {cats}"
    )


# ─────────────────────────────────────────────
#  Confirmation prompt
# ─────────────────────────────────────────────

def confirm_execution() -> bool:
    """
    Ask the user to explicitly confirm they want to proceed with the scan.

    - Shows a clear prompt with valid options
    - Accepts: yes / y / no / n  (case-insensitive)
    - Reprompts on invalid input (up to _MAX_ATTEMPTS times)
    - After max invalid attempts: exits cleanly (returns False)

    Returns:
        True  -- user confirmed, scan may proceed
        False -- user declined or gave too many invalid inputs
    """
    print()
    print("  The above configuration will be used for the scan.")
    print("  Once started, the scan will send adversarial probes to the target.")
    print()

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            raw = input("  Proceed with scan? [yes / no]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  Scan cancelled by user.\n")
            return False

        if raw in ("yes", "y"):
            print("\n  Confirmed. Starting scan...\n")
            return True

        if raw in ("no", "n"):
            print("\n  Scan cancelled by user. No probes were sent.\n")
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
                "Scan aborted for safety.\n"
            )

    return False


# ─────────────────────────────────────────────
#  Combined helper
# ─────────────────────────────────────────────

def display_and_confirm(
    manifest: ScanManifest,
    source: str = "",
    estimate: "Optional[ScanEstimate]" = None,
) -> bool:
    """
    Display the manifest (+ estimation if provided) then ask for confirmation.

    Convenience wrapper used by the CLI pipeline.

    Returns:
        True  -- user confirmed, scan may proceed
        False -- user declined or gave invalid inputs
    """
    display_manifest(manifest, source=source, estimate=estimate)
    if estimate is not None:
        from core.estimator import display_estimation
        display_estimation(estimate)
    return confirm_execution()
