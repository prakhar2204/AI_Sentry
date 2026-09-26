"""
AI-SENTRY -- Report Generator
core/report_generator.py

Combines all backend outputs (ScanResult, RiskReport, RecommendationReport,
ScanManifest) into a single unified report structure that:

  1. Powers CLI text output
  2. Feeds the Electron/React UI via JSON (no transformation needed)
  3. Supports JSON + TXT file export

This is the SINGLE SOURCE OF TRUTH for report data. No downstream
consumer should need to recombine or reshape the data.

Phase 6a deliverable.
Reference: docs/TRD.md Section 2.5 (Report Generator)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

from core.manifest import ScanManifest
from core.engine_interface import ScanResult
from core.scorer import RiskReport
from core.recommender import RecommendationReport


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

REPORT_VERSION = "1.0.0"

_DIVIDER = "=" * 60
_THIN_DIVIDER = "-" * 60


# ─────────────────────────────────────────────
#  Report dataclass
# ─────────────────────────────────────────────

@dataclass
class ScanReport:
    """
    Unified report combining all scan pipeline outputs.

    This is the top-level data structure that CLI, file export,
    and Electron UI all consume. It is designed to be JSON-
    serializable without any further transformation.

    Sections:
        meta            -- Scan metadata (target, mode, IDs, timestamps)
        summary         -- Risk score + level + finding count
        breakdown       -- Severity counts {high, medium, low}
        categories      -- Per-category analysis
        findings        -- All individual findings
        recommendations -- Prioritized remediation actions
        engine          -- Engine metadata (name, probes, duration)
    """
    meta:            dict[str, Any]
    summary:         dict[str, Any]
    breakdown:       dict[str, int]
    categories:      dict[str, dict[str, Any]]
    findings:        list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    engine:          dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return the report as a plain dict, ready for JSON serialization."""
        return {
            "report_version": REPORT_VERSION,
            "meta":            self.meta,
            "summary":         self.summary,
            "breakdown":       self.breakdown,
            "categories":      self.categories,
            "findings":        self.findings,
            "recommendations": self.recommendations,
            "engine":          self.engine,
        }


# ─────────────────────────────────────────────
#  Report generation
# ─────────────────────────────────────────────

def generate_full_report(
    manifest: ScanManifest,
    scan_result: ScanResult,
    risk_report: RiskReport,
    rec_report: RecommendationReport,
) -> ScanReport:
    """
    Merge all pipeline outputs into a unified ScanReport.

    This is the primary entry point. It reads from each component's
    existing to_dict() methods and reshapes into the canonical report
    schema. No data is duplicated -- each field has one authoritative source.

    Parameters:
        manifest    -- The validated ScanManifest
        scan_result -- Engine output (ScanResult)
        risk_report -- Scoring output (RiskReport)
        rec_report  -- Recommendation output (RecommendationReport)

    Returns:
        ScanReport ready for display, export, or UI consumption.
    """
    # -- Meta --
    meta = {
        "target":       manifest.target,
        "mode":         manifest.mode.value,
        "scan_depth":   manifest.scan_depth.value,
        "categories":   [c.value for c in manifest.categories],
        "scan_id":      manifest.manifest_id,
        "timestamp":    manifest.created_at,
        "report_generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "output_dir":   manifest.output_dir,
    }

    # -- Summary --
    summary = {
        "risk_score":      risk_report.risk_score,
        "risk_level":      risk_report.risk_level,
        "total_findings":  risk_report.total_findings,
        "raw_score":       round(risk_report.raw_score, 2),
    }

    # -- Breakdown --
    breakdown = dict(risk_report.summary)

    # -- Categories --
    categories = {}
    for cat_name, bd in risk_report.category_breakdown.items():
        categories[cat_name] = {
            "count":          bd.count,
            "max_severity":   bd.max_severity,
            "avg_confidence": bd.avg_confidence,
            "raw_score":      round(bd.raw_score, 2),
        }

    # -- Findings --
    findings = [f.to_dict() for f in scan_result.findings]

    # -- Recommendations --
    recommendations = [r.to_dict() for r in rec_report.recommendations]

    # -- Engine --
    engine = {
        "name":         scan_result.engine_name,
        "total_probes": scan_result.total_probes,
        "duration_sec": scan_result.duration_sec,
        "error":        scan_result.error,
    }

    return ScanReport(
        meta=meta,
        summary=summary,
        breakdown=breakdown,
        categories=categories,
        findings=findings,
        recommendations=recommendations,
        engine=engine,
    )


# ─────────────────────────────────────────────
#  Serialization
# ─────────────────────────────────────────────

def serialize_report(report: ScanReport) -> str:
    """
    Serialize a ScanReport to a JSON string.

    Uses 2-space indentation for readability.
    All values are JSON-safe (no datetimes, no enums, no custom objects).
    """
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
#  TXT report format
# ─────────────────────────────────────────────

_SEVERITY_LABELS = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}


def format_txt_report(report: ScanReport) -> str:
    """
    Format a ScanReport as a human-readable plain text report.

    Designed for CLI display and .txt file export. Uses clean
    section headers, aligned formatting, and readable spacing.
    All output is ASCII-safe for Windows cp1252 compatibility.
    """
    lines: list[str] = []

    # ── Header ──
    lines.append("")
    lines.append(_DIVIDER)
    lines.append("  AI SENTRY -- SECURITY SCAN REPORT")
    lines.append(_DIVIDER)
    lines.append("")

    # ── Meta ──
    meta = report.meta
    lines.append(f"  Target       : {meta['target']}")
    lines.append(f"  Mode         : {meta['mode']}")
    lines.append(f"  Scan Depth   : {meta['scan_depth']}")
    lines.append(f"  Categories   : {', '.join(meta['categories'])}")
    lines.append(f"  Scan ID      : {meta['scan_id']}")
    lines.append(f"  Scan Time    : {meta['timestamp']}")
    lines.append(f"  Report Time  : {meta['report_generated_at']}")
    lines.append("")

    # ── Risk Summary ──
    lines.append(_THIN_DIVIDER)
    lines.append("  RISK SUMMARY")
    lines.append(_THIN_DIVIDER)
    lines.append("")

    s = report.summary
    level_label = _SEVERITY_LABELS.get(s["risk_level"], s["risk_level"].upper())
    lines.append(f"  Risk Score   : {s['risk_score']}/100  ({level_label})")
    lines.append(f"  Total Findings: {s['total_findings']}")
    lines.append("")

    b = report.breakdown
    lines.append(f"    HIGH       : {b.get('high', 0)}")
    lines.append(f"    MEDIUM     : {b.get('medium', 0)}")
    lines.append(f"    LOW        : {b.get('low', 0)}")
    lines.append("")

    # ── Category Breakdown ──
    if report.categories:
        lines.append(_THIN_DIVIDER)
        lines.append("  CATEGORY BREAKDOWN")
        lines.append(_THIN_DIVIDER)
        lines.append("")

        max_name = max(len(k) for k in report.categories)
        for name, cat in report.categories.items():
            padded = name.ljust(max_name)
            lines.append(
                f"    {padded}  "
                f"findings: {cat['count']}  "
                f"max: {cat['max_severity']:<6}  "
                f"avg_conf: {cat['avg_confidence']:.2f}"
            )
        lines.append("")

    # ── Findings ──
    lines.append(_THIN_DIVIDER)
    lines.append("  FINDINGS")
    lines.append(_THIN_DIVIDER)
    lines.append("")

    if not report.findings:
        lines.append("  No findings -- target passed all probes.")
        lines.append("")
    else:
        for i, f in enumerate(report.findings, 1):
            sev_tag = _SEVERITY_LABELS.get(f["severity"], "???")
            conf_pct = int(f["confidence"] * 100)
            lines.append(
                f"  #{i} [{sev_tag}] {f['category']}  "
                f"(confidence: {conf_pct}%)"
            )
            lines.append(f"     {f['evidence']}")
            source_parts = [f"Source: {f['source']}"]
            if f.get("probe_id"):
                source_parts.insert(0, f"Probe: {f['probe_id']}")
            lines.append(f"     {' | '.join(source_parts)}")
            lines.append("")

    # ── Recommendations ──
    lines.append(_THIN_DIVIDER)
    lines.append("  RECOMMENDATIONS")
    lines.append(_THIN_DIVIDER)
    lines.append("")

    if not report.recommendations:
        lines.append("  No recommendations -- no vulnerabilities found.")
        lines.append("")
    else:
        for rec in report.recommendations:
            sev_tag = _SEVERITY_LABELS.get(rec["severity"], "???")
            lines.append(f"  [{sev_tag}] {rec['category']}")
            for j, action in enumerate(rec["actions"], 1):
                lines.append(f"    {j}. {action}")
            lines.append("")

    # ── Engine Info ──
    lines.append(_THIN_DIVIDER)
    lines.append("  ENGINE INFO")
    lines.append(_THIN_DIVIDER)
    lines.append("")

    eng = report.engine
    lines.append(f"  Engine       : {eng['name']}")
    lines.append(f"  Probes Run   : {eng['total_probes']}")
    lines.append(f"  Duration     : {eng['duration_sec']:.1f} sec")
    if eng.get("error"):
        lines.append(f"  Error        : {eng['error']}")
    lines.append("")

    # ── Footer ──
    lines.append(_DIVIDER)
    lines.append("  Report generated by AI SENTRY")
    lines.append(_DIVIDER)
    lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────
#  File export
# ─────────────────────────────────────────────

@dataclass
class ExportResult:
    """Result of a file export operation."""
    ok:       bool
    path:     str
    format:   str
    error:    Optional[str] = None
    bytes_written: int = 0


def export_report(
    report: ScanReport,
    path: str,
    fmt: str = "json",
) -> ExportResult:
    """
    Export a ScanReport to a file.

    Parameters:
        report -- The ScanReport to export
        path   -- Destination file path
        fmt    -- "json" or "txt"

    Returns:
        ExportResult with success/failure details.

    Handles:
        - Invalid format
        - Permission errors
        - Directory creation
        - Write failures
    """
    if fmt not in ("json", "txt"):
        return ExportResult(
            ok=False, path=path, format=fmt,
            error=f"Unsupported format '{fmt}'. Use 'json' or 'txt'.",
        )

    try:
        # Create parent directories if needed
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        # Generate content
        if fmt == "json":
            content = serialize_report(report)
        else:
            content = format_txt_report(report)

        # Write file
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

        bytes_written = os.path.getsize(path)

        return ExportResult(
            ok=True, path=os.path.abspath(path), format=fmt,
            bytes_written=bytes_written,
        )

    except PermissionError:
        return ExportResult(
            ok=False, path=path, format=fmt,
            error=f"Permission denied: cannot write to '{path}'.",
        )
    except OSError as e:
        return ExportResult(
            ok=False, path=path, format=fmt,
            error=f"File system error: {e}",
        )


# ─────────────────────────────────────────────
#  Display helpers (CLI)
# ─────────────────────────────────────────────

def display_txt_report(report: ScanReport) -> None:
    """Print the full TXT report to stdout."""
    print(format_txt_report(report))


def print_export_result(result: ExportResult) -> None:
    """Print the result of a file export operation."""
    if result.ok:
        size_kb = result.bytes_written / 1024
        print(f"\n  [OK] Report exported successfully.")
        print(f"       Format : {result.format.upper()}")
        print(f"       Path   : {result.path}")
        print(f"       Size   : {size_kb:.1f} KB\n")
    else:
        print(f"\n  [X] Export failed: {result.error}\n")
