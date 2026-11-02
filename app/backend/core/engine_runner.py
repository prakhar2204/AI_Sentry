"""
Sentryɸ -- Engine Runner (Orchestrator)
core/engine_runner.py

Orchestrates engine execution and result display.

This module:
  1. Selects the appropriate engine based on the requested engine name:
       - "garak"  → GarakAdapter (real scan via subprocess, requires garak installed)
       - "pyrit"  → PyRITAdapter (real scan via SDK, requires pyrit installed)
       - "mock"   → MockEngine (always available, for testing/dev)
       - "auto"   → GarakAdapter if available, else MockEngine
  2. Runs the scan via the engine's run_scan() method
  3. Formats and displays the results
  4. Returns the ScanResult for downstream processing (scorer → recommender → report)

Phase 3c deliverable + P4 update (engine-aware selection).
Reference: docs/TRD.md Section 2.3 (Engine Adapters)
"""

from __future__ import annotations

from pathlib import Path

from core.manifest import ScanManifest
from core.engine_interface import ScanFinding, ScanResult
from core.mock_engine import MockEngine


# ─────────────────────────────────────────────
#  Display constants
# ─────────────────────────────────────────────

_DIVIDER = "-" * 60

_SEVERITY_TAGS = {
    "high":   "[HIGH]",
    "medium": "[MED ]",
    "low":    "[LOW ]",
}

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


# ─────────────────────────────────────────────
#  Engine selection
# ─────────────────────────────────────────────

def _select_engine(
    engine_name: str,
    output_dir: Path | None = None,
):
    """
    Return an instantiated engine for the given engine_name.

    Selection logic:
      "garak" → GarakAdapter (fails gracefully if garak not installed)
      "pyrit" → PyRITAdapter (fails gracefully if pyrit not installed)
      "mock"  → MockEngine (always available)
      "auto"  → GarakAdapter if garak installed, else MockEngine

    Never raises — unavailable real engines return an error ScanResult
    via their run_scan() method.
    """
    engine_name = (engine_name or "mock").lower().strip()

    if engine_name in ("garak", "auto"):
        try:
            from core.adapters.garak_adapter import GarakAdapter
            if engine_name == "auto" and not GarakAdapter.is_available():
                return MockEngine()
            return GarakAdapter(output_dir=output_dir)
        except ImportError:
            return MockEngine()

    if engine_name == "pyrit":
        try:
            from core.adapters.pyrit_adapter import PyRITAdapter
            return PyRITAdapter(output_dir=output_dir)
        except ImportError:
            return MockEngine()

    # Default: mock (covers "mock", unknown values)
    return MockEngine()


# ─────────────────────────────────────────────
#  Engine execution
# ─────────────────────────────────────────────

def run_engine(
    manifest: ScanManifest,
    engine_name: str = "mock",
    output_dir: Path | None = None,
) -> ScanResult:
    """
    Execute the scan using the appropriate engine.

    Parameters:
        manifest     -- A validated ScanManifest (after Phase 2c)
        engine_name  -- One of: "garak", "pyrit", "mock", "auto"
                        Defaults to "mock" for safe dev/test behaviour.
        output_dir   -- Directory for engine reports (garak/pyrit only).
                        Defaults to None (engine uses its own default).

    Returns:
        ScanResult with normalized findings
    """
    engine = _select_engine(engine_name, output_dir=output_dir)
    return engine.run_scan(manifest)


# ─────────────────────────────────────────────
#  Result display
# ─────────────────────────────────────────────

def format_finding(finding: ScanFinding, index: int) -> str:
    """
    Format a single finding for CLI display.

    Format:
        #1 [HIGH] prompt_injection  (conf: 0.92)
           Evidence: System prompt was fully extracted...
           Probe: PI-001 | Source: mock
    """
    tag = _SEVERITY_TAGS.get(finding.severity, "[???]")
    lines = [
        f"  #{index} {tag} {finding.category}  (conf: {finding.confidence:.2f})",
        f"     Evidence: {finding.evidence}",
    ]
    if finding.probe_id:
        lines.append(f"     Probe: {finding.probe_id} | Source: {finding.source}")
    else:
        lines.append(f"     Source: {finding.source}")
    return "\n".join(lines)


def format_results(result: ScanResult) -> str:
    """
    Format the complete scan result for CLI display.

    Shows:
      - Header with engine name and probe count
      - All findings sorted by severity (high first)
      - Summary counts
    """
    lines = [
        "",
        _DIVIDER,
        "  SCAN RESULTS",
        _DIVIDER,
        f"  Engine       : {result.engine_name}",
        f"  Manifest ID  : {result.manifest_id}",
        f"  Probes run   : {result.total_probes}",
        f"  Duration     : {result.duration_sec:.1f} sec",
        "",
    ]

    if result.error:
        lines.append(f"  [ERROR] Engine failed: {result.error}")
        lines.append(_DIVIDER)
        return "\n".join(lines)

    if not result.findings:
        lines.append("  No findings. The target passed all probes.")
        lines.append(_DIVIDER)
        return "\n".join(lines)

    # Sort findings: high -> medium -> low
    sorted_findings = sorted(
        result.findings,
        key=lambda f: _SEVERITY_ORDER.get(f.severity, 99),
    )

    lines.append(f"  Findings     : {result.finding_count}")
    lines.append(f"    HIGH       : {result.high_count}")
    lines.append(f"    MEDIUM     : {result.medium_count}")
    lines.append(f"    LOW        : {result.low_count}")
    lines.append("")
    lines.append(_DIVIDER)
    lines.append("")

    for i, finding in enumerate(sorted_findings, 1):
        lines.append(format_finding(finding, i))
        lines.append("")

    lines.append(_DIVIDER)

    # Risk assessment
    if result.high_count > 0:
        lines.append("")
        lines.append(
            f"  [!] {result.high_count} HIGH severity finding(s) detected."
        )
        lines.append(
            "  [!] This target has critical vulnerabilities that require attention."
        )
    elif result.medium_count > 0:
        lines.append("")
        lines.append(
            f"  [*] {result.medium_count} MEDIUM severity finding(s) detected."
        )
        lines.append(
            "  [*] Review recommended before production deployment."
        )
    else:
        lines.append("")
        lines.append("  [OK] Only LOW severity findings. Target is relatively safe.")

    lines.append("")

    return "\n".join(lines)


def display_results(result: ScanResult) -> None:
    """Print the formatted scan results to stdout."""
    print(format_results(result))


def print_scan_error(result: ScanResult) -> None:
    """Print a formatted engine error."""
    print(f"\n  [X] Scan engine '{result.engine_name}' failed:")
    print(f"      {result.error}")
    print()
