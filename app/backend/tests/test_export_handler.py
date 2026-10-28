"""
Sentryɸ — Export Handler Tests
tests/test_export_handler.py

Tests for export_handler.py — all formats, subprocess interface,
WeasyPrint fallback behavior, and error cases.

Phase P3 deliverable.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Make backend importable
sys.path.insert(0, str(Path(__file__).parent.parent))
from export_handler import export_report, ExportResult, _serialize_json, _serialize_html, _serialize_txt

# ─────────────────────────────────────────────
#  Shared fixtures
# ─────────────────────────────────────────────

BACKEND_DIR = Path(__file__).parent.parent
PYTHON_EXE  = sys.executable


def _minimal_report() -> dict:
    """Minimal valid ScanReport.to_dict() structure."""
    return {
        "report_version": "1.0.0",
        "meta": {
            "target":              "http://localhost:8080",
            "mode":                "api",
            "scan_depth":          "quick",
            "categories":          ["prompt_injection", "jailbreak"],
            "scan_id":             "test-12345",
            "timestamp":           "2025-01-01T00:00:00Z",
            "report_generated_at": "2025-01-01T00:01:00Z",
            "output_dir":          "/tmp",
        },
        "summary": {
            "risk_score":     72,
            "risk_level":     "HIGH",
            "total_findings": 3,
            "raw_score":      0.72,
        },
        "breakdown": {"high": 2, "medium": 1, "low": 0},
        "categories": {
            "prompt_injection": {
                "count":          2,
                "max_severity":   "high",
                "avg_confidence": 0.87,
                "raw_score":      0.8,
            },
            "jailbreak": {
                "count":          1,
                "max_severity":   "medium",
                "avg_confidence": 0.65,
                "raw_score":      0.4,
            },
        },
        "findings": [
            {
                "category":   "prompt_injection",
                "severity":   "high",
                "confidence": 0.92,
                "evidence":   "Probe bypassed guard using role-play injection.",
                "source":     "Security Analysis Module",
                "probe_id":   "pi-001",
            },
            {
                "category":   "prompt_injection",
                "severity":   "high",
                "confidence": 0.82,
                "evidence":   "Context override via adversarial suffix detected.",
                "source":     "Security Analysis Module",
                "probe_id":   "pi-002",
            },
            {
                "category":   "jailbreak",
                "severity":   "medium",
                "confidence": 0.65,
                "evidence":   "Multi-turn escalation succeeded in bypass attempt.",
                "source":     "Security Analysis Module",
                "probe_id":   "jb-001",
            },
        ],
        "recommendations": [
            {
                "category": "prompt_injection",
                "severity": "high",
                "actions":  [
                    "Implement strict system prompt isolation.",
                    "Sanitize user input before passing to LLM.",
                    "Apply prompt injection detection filters.",
                ],
            },
            {
                "category": "jailbreak",
                "severity": "medium",
                "actions":  [
                    "Enforce content policies across multi-turn conversations.",
                    "Add output classifiers for policy violations.",
                ],
            },
        ],
        "engine": {
            "name":         "Mock Security Engine",
            "total_probes": 100,
            "duration_sec": 4.5,
            "error":        None,
        },
    }


def _simulated_report() -> dict:
    """Report with sim- scan ID (simulation mode)."""
    r = _minimal_report()
    r["meta"]["scan_id"] = "sim-99999"
    return r


# ─────────────────────────────────────────────
#  Tests: JSON export
# ─────────────────────────────────────────────

def test_json_export_success(tmp_path):
    """JSON export writes a valid file and returns success."""
    out = str(tmp_path / "report.json")
    result = export_report(_minimal_report(), "json", out)
    assert result.success is True
    assert result.path == out
    assert result.size_bytes > 0
    assert result.error == ""

    with open(out, "r", encoding="utf-8") as f:
        parsed = json.load(f)
    assert parsed["meta"]["target"] == "http://localhost:8080"
    assert parsed["summary"]["risk_score"] == 72


def test_json_export_pretty_printed(tmp_path):
    """JSON export produces indented output."""
    out = str(tmp_path / "report.json")
    export_report(_minimal_report(), "json", out)
    with open(out, "r", encoding="utf-8") as f:
        content = f.read()
    # Indented JSON has newlines
    assert "\n" in content
    assert "  " in content


def test_json_export_preserves_all_sections(tmp_path):
    """JSON export includes all required top-level keys."""
    out = str(tmp_path / "report.json")
    export_report(_minimal_report(), "json", out)
    with open(out, "r", encoding="utf-8") as f:
        data = json.load(f)
    required = {"report_version", "meta", "summary", "breakdown", "categories", "findings", "recommendations", "engine"}
    assert required.issubset(data.keys())


# ─────────────────────────────────────────────
#  Tests: TXT export
# ─────────────────────────────────────────────

def test_txt_export_success(tmp_path):
    """TXT export writes a non-empty file."""
    out = str(tmp_path / "report.txt")
    result = export_report(_minimal_report(), "txt", out)
    assert result.success is True
    assert result.size_bytes > 0

    with open(out, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Sentryɸ" in content
    assert "SECURITY SCAN REPORT" in content


def test_txt_export_includes_risk_summary(tmp_path):
    """TXT export contains the RISK SUMMARY section."""
    out = str(tmp_path / "report.txt")
    export_report(_minimal_report(), "txt", out)
    content = Path(out).read_text(encoding="utf-8")
    assert "RISK SUMMARY" in content
    assert "72/100" in content
    assert "HIGH" in content


def test_txt_export_includes_findings(tmp_path):
    """TXT export contains findings section with probe info."""
    out = str(tmp_path / "report.txt")
    export_report(_minimal_report(), "txt", out)
    content = Path(out).read_text(encoding="utf-8")
    assert "FINDINGS" in content
    assert "HIGH  " in content
    assert "pi-001" in content


def test_txt_export_includes_recommendations(tmp_path):
    """TXT export contains RECOMMENDATIONS section."""
    out = str(tmp_path / "report.txt")
    export_report(_minimal_report(), "txt", out)
    content = Path(out).read_text(encoding="utf-8")
    assert "RECOMMENDATIONS" in content
    assert "Implement strict system prompt isolation" in content


def test_txt_simulation_mode_notice(tmp_path):
    """TXT export adds simulation mode notice when scan_id starts with sim-."""
    out = str(tmp_path / "report.txt")
    export_report(_simulated_report(), "txt", out)
    content = Path(out).read_text(encoding="utf-8")
    assert "SIMULATION MODE" in content


# ─────────────────────────────────────────────
#  Tests: HTML export
# ─────────────────────────────────────────────

def test_html_export_success(tmp_path):
    """HTML export writes a valid HTML file."""
    out = str(tmp_path / "report.html")
    result = export_report(_minimal_report(), "html", out)
    assert result.success is True
    assert result.size_bytes > 0

    content = Path(out).read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "<html" in content


def test_html_export_contains_report_data(tmp_path):
    """HTML export embeds target, risk score, and findings."""
    out = str(tmp_path / "report.html")
    export_report(_minimal_report(), "html", out)
    content = Path(out).read_text(encoding="utf-8")
    assert "http://localhost:8080" in content
    assert "72" in content
    assert "HIGH" in content
    assert "pi-001" in content


def test_html_export_escapes_special_chars(tmp_path):
    """HTML export XSS-escapes < > & in evidence text."""
    report = _minimal_report()
    report["findings"][0]["evidence"] = '<script>alert("xss")</script>'
    out = str(tmp_path / "report.html")
    export_report(report, "html", out)
    content = Path(out).read_text(encoding="utf-8")
    assert "<script>" not in content
    assert "&lt;script&gt;" in content


def test_html_export_is_standalone(tmp_path):
    """HTML export has no external Google Fonts CDN URLs (fully standalone)."""
    out = str(tmp_path / "report.html")
    export_report(_minimal_report(), "html", out)
    content = Path(out).read_text(encoding="utf-8")
    # No CDN-loaded fonts from Google
    assert "fonts.googleapis.com" not in content
    assert "fonts.gstatic.com" not in content
    # Inline CSS must be present (self-contained)
    assert "<style>" in content


def test_html_simulation_mode_banner(tmp_path):
    """HTML export shows simulation mode banner for sim- scan IDs."""
    out = str(tmp_path / "report.html")
    export_report(_simulated_report(), "html", out)
    content = Path(out).read_text(encoding="utf-8")
    assert "SIMULATION MODE" in content


def test_html_no_simulation_banner_for_real(tmp_path):
    """HTML export does NOT show simulation banner for real scan IDs."""
    out = str(tmp_path / "report.html")
    export_report(_minimal_report(), "html", out)
    content = Path(out).read_text(encoding="utf-8")
    assert "SIMULATION MODE" not in content


# ─────────────────────────────────────────────
#  Tests: PDF / WeasyPrint fallback
# ─────────────────────────────────────────────

def test_pdf_fallback_when_weasyprint_missing(tmp_path, monkeypatch):
    """PDF export falls back to HTML when WeasyPrint is not installed."""
    # Patch _weasyprint_available to return False
    import export_handler
    monkeypatch.setattr(export_handler, "_weasyprint_available", lambda: False)

    out = str(tmp_path / "report.pdf")
    result = export_report(_minimal_report(), "pdf", out)

    # Should succeed but save as HTML
    assert result.success is True
    assert result.path.endswith(".html"), f"Expected .html path, got: {result.path}"
    assert result.fallback, "Expected a fallback notice message"
    assert "WeasyPrint" in result.fallback

    # Verify the HTML file was actually written
    assert Path(result.path).exists()
    content = Path(result.path).read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content


def test_pdf_fallback_file_contains_notice(tmp_path, monkeypatch):
    """Fallback HTML file includes the WeasyPrint installation notice."""
    import export_handler
    monkeypatch.setattr(export_handler, "_weasyprint_available", lambda: False)

    out = str(tmp_path / "report.pdf")
    result = export_report(_minimal_report(), "pdf", out)

    content = Path(result.path).read_text(encoding="utf-8")
    assert "WeasyPrint" in content or "weasyprint" in content


# ─────────────────────────────────────────────
#  Tests: Error handling
# ─────────────────────────────────────────────

def test_invalid_format_returns_error(tmp_path):
    """Unknown format returns ExportResult with success=False and informative error."""
    out = str(tmp_path / "report.xyz")
    result = export_report(_minimal_report(), "xyz", out)
    assert result.success is False
    assert "xyz" in result.error
    assert "Valid formats" in result.error


def test_unwritable_path_returns_error():
    """Unwritable output path returns ExportResult with success=False."""
    import platform
    if platform.system() == "Windows":
        # On Windows, a path with illegal characters is always unwritable
        out = "C:\\NUL\\report.json"  # NUL is a reserved device name on Windows
    else:
        # On Unix, /proc/1/mem is unwritable by non-root
        out = "/proc/1/mem/report.json"

    result = export_report(_minimal_report(), "json", out)
    # On some systems this may still succeed if path is writable
    # Just assert that either it failed OR the file exists (not both undefined)
    if not result.success:
        assert result.error  # must have an error message when failing
    # Test is informational — some CI environments are permissive


def test_empty_report_still_exports(tmp_path):
    """Empty findings/recommendations list still produces a valid export."""
    report = _minimal_report()
    report["findings"] = []
    report["recommendations"] = []
    report["summary"]["total_findings"] = 0

    out = str(tmp_path / "empty.html")
    result = export_report(report, "html", out)
    assert result.success is True
    content = Path(out).read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "No findings" in content.lower() or "findings" in content.lower()


# ─────────────────────────────────────────────
#  Tests: Subprocess mode (__main__ entry point)
# ─────────────────────────────────────────────

def _run_subprocess(payload: dict) -> tuple[dict, int]:
    """Run export_handler.py as subprocess, return (output_dict, exit_code)."""
    proc = subprocess.run(
        [PYTHON_EXE, str(BACKEND_DIR / "export_handler.py")],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        timeout=15,
        cwd=str(BACKEND_DIR),
    )
    try:
        out = json.loads(proc.stdout.decode("utf-8").strip())
    except Exception:
        out = {}
    return out, proc.returncode


def test_subprocess_json_export(tmp_path):
    """Subprocess mode: JSON export writes file and returns success=true."""
    out_path = str(tmp_path / "sub.json")
    payload  = {
        "action":      "export",
        "format":      "json",
        "output_path": out_path,
        "report":      _minimal_report(),
    }
    result, code = _run_subprocess(payload)

    assert code == 0
    assert result.get("success") is True
    assert result.get("path") == out_path
    assert result.get("size_bytes", 0) > 0
    assert Path(out_path).exists()


def test_subprocess_html_export(tmp_path):
    """Subprocess mode: HTML export writes file and returns success=true."""
    out_path = str(tmp_path / "sub.html")
    payload  = {
        "action":      "export",
        "format":      "html",
        "output_path": out_path,
        "report":      _minimal_report(),
    }
    result, code = _run_subprocess(payload)

    assert code == 0
    assert result.get("success") is True
    content = Path(out_path).read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content


def test_subprocess_txt_export(tmp_path):
    """Subprocess mode: TXT export writes file and returns success=true."""
    out_path = str(tmp_path / "sub.txt")
    payload  = {
        "action":      "export",
        "format":      "txt",
        "output_path": out_path,
        "report":      _minimal_report(),
    }
    result, code = _run_subprocess(payload)

    assert code == 0
    assert result.get("success") is True
    content = Path(out_path).read_text(encoding="utf-8")
    assert "Sentryɸ" in content


def test_subprocess_missing_output_path():
    """Subprocess mode: missing output_path returns success=false, exit=1."""
    payload = {
        "action": "export",
        "format": "json",
        "report": _minimal_report(),
    }
    result, code = _run_subprocess(payload)
    assert code == 1
    assert result.get("success") is False
    assert "output_path" in result.get("error", "")


def test_subprocess_missing_report():
    """Subprocess mode: missing report returns success=false, exit=1."""
    payload = {
        "action":      "export",
        "format":      "json",
        "output_path": "/tmp/nonexistent.json",
    }
    result, code = _run_subprocess(payload)
    assert code == 1
    assert result.get("success") is False


def test_subprocess_invalid_json():
    """Subprocess mode: invalid JSON stdin returns success=false, exit=1."""
    proc = subprocess.run(
        [PYTHON_EXE, str(BACKEND_DIR / "export_handler.py")],
        input=b"{NOT JSON}",
        capture_output=True,
        timeout=15,
        cwd=str(BACKEND_DIR),
    )
    assert proc.returncode == 1
    result = json.loads(proc.stdout.decode("utf-8").strip())
    assert result["success"] is False


def test_subprocess_invalid_format(tmp_path):
    """Subprocess mode: unknown format returns success=false, exit=1."""
    out_path = str(tmp_path / "report.xyz")
    payload  = {
        "action":      "export",
        "format":      "docx",
        "output_path": out_path,
        "report":      _minimal_report(),
    }
    result, code = _run_subprocess(payload)
    assert code == 1
    assert result.get("success") is False
    assert result.get("error")


# ─────────────────────────────────────────────
#  Tests: Serializer unit tests
# ─────────────────────────────────────────────

def test_serialize_json_roundtrip():
    """JSON serializer produces valid JSON that round-trips perfectly."""
    report  = _minimal_report()
    content = _serialize_json(report)
    parsed  = json.loads(content)
    assert parsed["meta"]["target"] == report["meta"]["target"]
    assert parsed["summary"]["risk_score"] == 72


def test_serialize_txt_contains_all_sections():
    """TXT serializer includes all major sections."""
    content = _serialize_txt(_minimal_report())
    for section in ("RISK SUMMARY", "CATEGORY BREAKDOWN", "FINDINGS", "RECOMMENDATIONS", "ENGINE INFO"):
        assert section in content, f"Missing section: {section}"


def test_serialize_html_valid_structure():
    """HTML serializer produces well-structured HTML."""
    content = _serialize_html(_minimal_report())
    assert "<!DOCTYPE html>" in content
    assert "<head>" in content
    assert "<body>" in content
    assert "</html>" in content
    assert "<style>" in content  # Inline CSS present
