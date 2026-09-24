"""
AI-SENTRY -- Engine Runner (Orchestrator)
core/engine_runner.py

Orchestrates engine execution and result display.

This module:
  1. Instantiates the appropriate engine (mock for now)
  2. Runs the scan via the engine's run_scan() method
  3. Formats and displays the results
  4. Returns the ScanResult for downstream processing

When real engines (Garak, PyRIT, DeepTeam) are integrated, this module
will select the engine based on configuration. The mock engine is the
default fallback.

Phase 3c deliverable.
Reference: docs/TRD.md Section 2.3 (Engine Adapters)
"""

from __future__ import annotations

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
#  Engine execution
# ─────────────────────────────────────────────

def run_engine(manifest: ScanManifest) -> ScanResult:
    """
    Execute the scan using the appropriate engine.

    Currently uses MockEngine. When real engines are available,
    this function will select based on manifest configuration or
    a separate engine registry.

    Parameters:
        manifest -- A validated ScanManifest (after Phase 2c)

    Returns:
        ScanResult with normalized findings
    """
    engine = MockEngine()
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
