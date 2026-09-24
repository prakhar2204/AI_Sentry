"""
AI-SENTRY -- Engine Interface
core/engine_interface.py

Defines the abstract contract that ALL scan engines must satisfy.

Every engine (Garak, PyRIT, DeepTeam, or the mock) must subclass
BaseEngine and implement run_scan(). The orchestrator (engine_runner.py)
relies on this interface to treat all engines uniformly.

Phase 3c deliverable.
Reference: docs/TRD.md Section 2.3 (Engine Adapters)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from core.manifest import ScanManifest


# ─────────────────────────────────────────────
#  Normalized finding schema
# ─────────────────────────────────────────────

# Valid severity levels (strict)
VALID_SEVERITIES = frozenset({"low", "medium", "high"})


@dataclass(frozen=True)
class ScanFinding:
    """
    A single normalized scan finding.

    This is the universal output format. Every engine must produce
    findings in this exact shape -- no engine-specific fields leak
    into the pipeline.

    Attributes:
        category   -- Which probe category triggered this finding
                      (e.g. "prompt_injection", "jailbreak")
        severity   -- "low", "medium", or "high"
        confidence -- Float 0.0 to 1.0 indicating detection certainty
        evidence   -- Human-readable description of what was found
        source     -- Which engine produced this finding
                      (e.g. "mock", "garak", "pyrit")
        probe_id   -- Optional identifier for the specific probe
    """
    category:   str
    severity:   str
    confidence: float
    evidence:   str
    source:     str
    probe_id:   str = ""

    def __post_init__(self):
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{self.severity}'. "
                f"Must be one of: {sorted(VALID_SEVERITIES)}"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"Confidence must be 0.0-1.0, got {self.confidence}"
            )

    def to_dict(self) -> dict:
        """Plain dict suitable for JSON serialization."""
        return {
            "category":   self.category,
            "severity":   self.severity,
            "confidence": self.confidence,
            "evidence":   self.evidence,
            "source":     self.source,
            "probe_id":   self.probe_id,
        }


# ─────────────────────────────────────────────
#  Scan result container
# ─────────────────────────────────────────────

@dataclass
class ScanResult:
    """
    Complete result of a scan engine run.

    Attributes:
        findings     -- List of normalized findings
        engine_name  -- Name of the engine that produced the results
        manifest_id  -- ID of the manifest that was scanned
        total_probes -- Number of probes actually executed
        duration_sec -- Wall time in seconds (0 for mock)
        error        -- Error message if the engine failed (None = success)
    """
    findings:     List[ScanFinding]
    engine_name:  str
    manifest_id:  str
    total_probes: int
    duration_sec: float = 0.0
    error:        Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "medium")

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "low")

    def to_dict(self) -> dict:
        return {
            "findings":      [f.to_dict() for f in self.findings],
            "engine_name":   self.engine_name,
            "manifest_id":   self.manifest_id,
            "total_probes":  self.total_probes,
            "duration_sec":  self.duration_sec,
            "error":         self.error,
            "summary": {
                "total":  self.finding_count,
                "high":   self.high_count,
                "medium": self.medium_count,
                "low":    self.low_count,
            },
        }


# ─────────────────────────────────────────────
#  Abstract base class
# ─────────────────────────────────────────────

class BaseEngine(ABC):
    """
    Abstract base class for all scan engines.

    Every engine must:
      1. Accept a ScanManifest
      2. Return a ScanResult with normalized ScanFinding objects
      3. Never raise exceptions to the caller -- wrap errors in
         ScanResult.error instead

    Subclasses must implement:
      - name       (property) -- engine identifier string
      - run_scan() -- execute probes and return findings
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique engine identifier (e.g. 'mock', 'garak', 'pyrit')."""
        ...

    @abstractmethod
    def run_scan(self, manifest: ScanManifest) -> ScanResult:
        """
        Execute the scan and return normalized results.

        Parameters:
            manifest -- A validated ScanManifest

        Returns:
            ScanResult with findings (may be empty on error)
        """
        ...
