"""
Sentryɸ — PyRIT Engine Adapter
core/adapters/pyrit_adapter.py

Bridges PyRITEngine (harshit branch) → BaseEngine / ScanFinding / ScanResult
(prakhar branch pipeline contract).

PyRIT uses the same VulnerabilityFinding schema as GarakEngine (imported from
core.garak_engine), so the severity conversion is identical.

Schema translation (same as garak_adapter):
  VulnerabilityFinding.severity int(1-5) → ScanFinding.severity str("low/medium/high")
"""

from __future__ import annotations

import time
from pathlib import Path

from core.engine_interface import BaseEngine, ScanFinding, ScanResult
from core.manifest import ScanManifest
from core.adapters.garak_adapter import _convert_severity, _build_evidence


# ─────────────────────────────────────────────
#  Adapter
# ─────────────────────────────────────────────

class PyRITAdapter(BaseEngine):
    """
    Wraps PyRITEngine (harshit) to satisfy the BaseEngine contract.

    PyRIT is only imported when is_available() returns True —
    if pyrit is not installed, this adapter falls back gracefully
    (engine_runner will use MockEngine instead).
    """

    def __init__(
        self,
        output_dir: Path | None = None,
    ) -> None:
        self._output_dir = output_dir or Path("./aisentry-pyrit-reports")

    @property
    def name(self) -> str:
        return "pyrit"

    @staticmethod
    def is_available() -> bool:
        """Return True if pyrit is installed in the current environment."""
        try:
            import importlib
            importlib.import_module("pyrit")
            return True
        except ImportError:
            return False

    def run_scan(self, manifest: ScanManifest) -> ScanResult:
        """
        Execute a PyRIT scan against the manifest target.

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
                    "PyRIT is not installed. "
                    "Install it with: pip install 'aisentry[engines]'"
                ),
            )

        try:
            from core.pyrit_engine import PyRITEngine, ALL_CATEGORIES

            # Map manifest categories → pyrit category subset
            requested = [c for c in manifest.categories if c in ALL_CATEGORIES]
            if not requested:
                requested = list(ALL_CATEGORIES)

            depth = manifest.scan_depth if hasattr(manifest, "scan_depth") else "standard"

            engine = PyRITEngine(
                target_url=manifest.target,
                output_dir=self._output_dir,
                api_key=manifest.api_key if hasattr(manifest, "api_key") else "",
                depth=depth,
            )

            t0 = time.monotonic()
            pyrit_result = engine.run(categories=requested)
            duration = time.monotonic() - t0

            # Convert VulnerabilityFinding → ScanFinding
            scan_findings = [
                ScanFinding(
                    category=vf.category,
                    severity=_convert_severity(vf.severity),
                    confidence=vf.confidence,
                    evidence=_build_evidence(vf),
                    source="pyrit",
                    probe_id=vf.probe,
                )
                for vf in pyrit_result.findings
            ]

            total_probes = len(pyrit_result.attack_results)
            error = pyrit_result.errors[0] if pyrit_result.errors else None

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
                error=f"PyRITAdapter error: {exc}",
            )
