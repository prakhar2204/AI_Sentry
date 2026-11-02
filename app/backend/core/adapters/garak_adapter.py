"""
Sentryɸ — Garak Engine Adapter
core/adapters/garak_adapter.py

Bridges GarakEngine (harshit branch) → BaseEngine / ScanFinding / ScanResult
(prakhar branch pipeline contract).

Schema translation:
  VulnerabilityFinding (int severity 1-5, float pass_rate, str probe)
  → ScanFinding (str severity "low/medium/high", float confidence, str evidence)

Severity mapping (D-004):
  VulnerabilityFinding.severity 5 → "high"
  VulnerabilityFinding.severity 4 → "high"
  VulnerabilityFinding.severity 3 → "medium"
  VulnerabilityFinding.severity 2 → "low"
  VulnerabilityFinding.severity 1 → "low"  (informational → treated as low)
"""

from __future__ import annotations

import time
from pathlib import Path

from core.engine_interface import BaseEngine, ScanFinding, ScanResult
from core.manifest import ScanManifest


# ─────────────────────────────────────────────
#  Severity conversion (D-004)
# ─────────────────────────────────────────────

_INT_TO_STR_SEVERITY: dict[int, str] = {
    5: "high",
    4: "high",
    3: "medium",
    2: "low",
    1: "low",   # informational → low (no breach means findings still recorded)
}


def _convert_severity(int_sev: int) -> str:
    """Convert int severity (1-5) to str severity ('low'/'medium'/'high')."""
    return _INT_TO_STR_SEVERITY.get(int_sev, "low")


def _build_evidence(finding) -> str:
    """Build a human-readable evidence string from a VulnerabilityFinding."""
    breach_pct = round((1.0 - finding.pass_rate) * 100, 1)
    probe_short = finding.probe.split(".")[-1] if "." in finding.probe else finding.probe
    if finding.pass_rate >= 1.0:
        return (
            f"Probe '{probe_short}' passed all {finding.total} prompts "
            f"(0% attack success). No vulnerability confirmed."
        )
    return (
        f"Probe '{probe_short}' ({finding.detector}): "
        f"{breach_pct}% attack success rate "
        f"({finding.failed}/{finding.total} prompts breached). "
        f"Confidence: {finding.confidence:.2f}."
    )


# ─────────────────────────────────────────────
#  Adapter
# ─────────────────────────────────────────────

class GarakAdapter(BaseEngine):
    """
    Wraps GarakEngine (harshit) to satisfy the BaseEngine contract.

    Garak is only imported when is_available() returns True —
    if garak is not installed, this adapter falls back gracefully
    (engine_runner will use MockEngine instead).
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        timeout: int = 120,
        request_timeout: int = 60,
        prompt_cap: int = 50,
    ) -> None:
        self._output_dir = output_dir or Path("./aisentry-garak-reports")
        self._timeout = timeout
        self._request_timeout = request_timeout
        self._prompt_cap = prompt_cap

    @property
    def name(self) -> str:
        return "garak"

    @staticmethod
    def is_available() -> bool:
        """Return True if garak is installed in the current environment."""
        try:
            import importlib
            importlib.import_module("garak")
            return True
        except ImportError:
            return False

    def run_scan(self, manifest: ScanManifest) -> ScanResult:
        """
        Execute a Garak scan against the manifest target.

        Returns a ScanResult with normalized ScanFinding objects.
        Never raises — all exceptions are wrapped in ScanResult.error.
        """
        if not self.is_available():
            return ScanResult(
                findings=[],
                engine_name=self.name,
                manifest_id=manifest.manifest_id,
                total_probes=0,
                error=(
                    "Garak is not installed. "
                    "Install it with: pip install 'aisentry[engines]'"
                ),
            )

        try:
            from core.garak_engine import GarakEngine, ALL_CATEGORIES

            # Map manifest categories → garak category subset
            requested = [c for c in manifest.categories if c in ALL_CATEGORIES]
            if not requested:
                # If none match, run all known categories
                requested = list(ALL_CATEGORIES)

            depth = manifest.scan_depth if hasattr(manifest, "scan_depth") else "standard"

            engine = GarakEngine(
                target_url=manifest.target,
                output_dir=self._output_dir,
                api_key=manifest.api_key if hasattr(manifest, "api_key") else "",
                timeout=self._timeout,
                depth=depth,
                request_timeout=self._request_timeout,
                prompt_cap=self._prompt_cap,
            )

            t0 = time.monotonic()
            garak_result = engine.run(categories=requested)
            duration = time.monotonic() - t0

            # Convert VulnerabilityFinding → ScanFinding
            scan_findings = [
                ScanFinding(
                    category=vf.category,
                    severity=_convert_severity(vf.severity),
                    confidence=vf.confidence,
                    evidence=_build_evidence(vf),
                    source="garak",
                    probe_id=vf.probe,
                )
                for vf in garak_result.findings
            ]

            total_probes = sum(
                len(pr.findings) for pr in garak_result.probe_results
            ) or len(garak_result.probe_results)

            error = garak_result.errors[0] if garak_result.errors else None

            return ScanResult(
                findings=scan_findings,
                engine_name=self.name,
                manifest_id=manifest.manifest_id,
                total_probes=total_probes,
                duration_sec=round(duration, 2),
                error=error,
            )

        except Exception as exc:  # noqa: BLE001
            return ScanResult(
                findings=[],
                engine_name=self.name,
                manifest_id=manifest.manifest_id,
                total_probes=0,
                error=f"GarakAdapter error: {exc}",
            )
