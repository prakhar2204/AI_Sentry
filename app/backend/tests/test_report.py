"""
Tests for Phase 6a -- Report Generator + Report Service

Covers:
  - core/report_generator.py
    - generate_full_report()  -- unified report creation
    - ScanReport.to_dict()    -- JSON structure
    - serialize_report()      -- JSON string output
    - format_txt_report()     -- human-readable text
    - export_report()         -- file export (JSON + TXT)
    - ExportResult            -- success/failure tracking
  - services/report_service.py
    - store_report()          -- in-memory storage
    - get_report_by_id()      -- retrieval by ID
    - get_latest_report()     -- most recent report
    - list_report_ids()       -- all stored IDs
    - clear_reports()         -- cleanup

Run with:
    python -m pytest tests/test_report.py -v
"""

import json
import os
import pytest
from unittest.mock import patch

from core.manifest import create_manifest
from core.mock_engine import MockEngine
from core.scorer import generate_risk_report
from core.recommender import generate_recommendations
from core.engine_interface import ScanFinding, ScanResult
from core.report_generator import (
    ScanReport,
    generate_full_report,
    serialize_report,
    format_txt_report,
    display_txt_report,
    export_report,
    print_export_result,
    ExportResult,
    REPORT_VERSION,
)
from services.report_service import (
    store_report,
    get_report_by_id,
    get_latest_report,
    get_latest_report_object,
    list_report_ids,
    get_report_count,
    clear_reports,
)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _full_pipeline():
    """Run the complete pipeline and return all components."""
    manifest = create_manifest(
        target="https://api.openai.com/v1",
        mode="api",
        scan_depth="standard",
        categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"],
    )
    scan_result = MockEngine().run_scan(manifest)
    risk_report = generate_risk_report(scan_result.findings)
    rec_report = generate_recommendations(risk_report)
    return manifest, scan_result, risk_report, rec_report


def _make_report():
    """Generate a full ScanReport from the mock pipeline."""
    m, sr, rr, rec = _full_pipeline()
    return generate_full_report(m, sr, rr, rec)


def _single_cat_report():
    """Single category report for simpler assertions."""
    manifest = create_manifest(
        target="http://localhost:8080",
        mode="local",
        scan_depth="quick",
        categories=["harmful_output"],
    )
    scan_result = MockEngine().run_scan(manifest)
    risk_report = generate_risk_report(scan_result.findings)
    rec_report = generate_recommendations(risk_report)
    return generate_full_report(manifest, scan_result, risk_report, rec_report)


def _empty_report():
    """Report with no findings (empty categories)."""
    manifest = create_manifest(
        target="https://api.openai.com/v1",
        mode="api",
        scan_depth="standard",
        categories=["prompt_injection"],
    )
    scan_result = ScanResult(
        findings=[], engine_name="mock",
        manifest_id=manifest.manifest_id, total_probes=0,
    )
    risk_report = generate_risk_report(scan_result.findings)
    rec_report = generate_recommendations(risk_report)
    return generate_full_report(manifest, scan_result, risk_report, rec_report)


# ═══════════════════════════════════════════════
#  generate_full_report
# ═══════════════════════════════════════════════

class TestGenerateFullReport:

    def test_returns_scan_report(self):
        report = _make_report()
        assert isinstance(report, ScanReport)

    def test_meta_contains_target(self):
        report = _make_report()
        assert report.meta["target"] == "https://api.openai.com/v1"

    def test_meta_contains_mode(self):
        report = _make_report()
        assert report.meta["mode"] == "api"

    def test_meta_contains_scan_depth(self):
        report = _make_report()
        assert report.meta["scan_depth"] == "standard"

    def test_meta_contains_categories(self):
        report = _make_report()
        assert len(report.meta["categories"]) == 4

    def test_meta_contains_scan_id(self):
        report = _make_report()
        assert len(report.meta["scan_id"]) > 10  # UUID

    def test_meta_contains_timestamp(self):
        report = _make_report()
        assert "T" in report.meta["timestamp"]

    def test_meta_contains_report_generated_at(self):
        report = _make_report()
        assert "report_generated_at" in report.meta

    def test_summary_risk_score(self):
        report = _make_report()
        assert 0 <= report.summary["risk_score"] <= 100

    def test_summary_risk_level(self):
        report = _make_report()
        assert report.summary["risk_level"] in ("low", "medium", "high")

    def test_summary_total_findings(self):
        report = _make_report()
        assert report.summary["total_findings"] == 9

    def test_breakdown_has_all_severities(self):
        report = _make_report()
        assert "high" in report.breakdown
        assert "medium" in report.breakdown
        assert "low" in report.breakdown

    def test_breakdown_counts_correct(self):
        report = _make_report()
        total = sum(report.breakdown.values())
        assert total == 9

    def test_categories_populated(self):
        report = _make_report()
        assert len(report.categories) == 4

    def test_category_has_required_fields(self):
        report = _make_report()
        for cat in report.categories.values():
            assert "count" in cat
            assert "max_severity" in cat
            assert "avg_confidence" in cat

    def test_findings_is_list(self):
        report = _make_report()
        assert isinstance(report.findings, list)
        assert len(report.findings) == 9

    def test_finding_has_schema_fields(self):
        report = _make_report()
        for f in report.findings:
            assert "category" in f
            assert "severity" in f
            assert "confidence" in f
            assert "evidence" in f
            assert "source" in f

    def test_recommendations_is_list(self):
        report = _make_report()
        assert isinstance(report.recommendations, list)
        assert len(report.recommendations) == 4

    def test_recommendation_has_actions(self):
        report = _make_report()
        for r in report.recommendations:
            assert "category" in r
            assert "severity" in r
            assert "actions" in r
            assert len(r["actions"]) >= 1

    def test_engine_metadata(self):
        report = _make_report()
        assert report.engine["name"] == "mock"
        assert report.engine["total_probes"] == 9

    def test_deterministic(self):
        a = _make_report()
        b = _make_report()
        assert a.summary["risk_score"] == b.summary["risk_score"]
        assert len(a.findings) == len(b.findings)


# ═══════════════════════════════════════════════
#  ScanReport.to_dict
# ═══════════════════════════════════════════════

class TestScanReportToDict:

    def test_returns_dict(self):
        d = _make_report().to_dict()
        assert isinstance(d, dict)

    def test_has_report_version(self):
        d = _make_report().to_dict()
        assert d["report_version"] == REPORT_VERSION

    def test_has_all_sections(self):
        d = _make_report().to_dict()
        for key in ("meta", "summary", "breakdown", "categories",
                     "findings", "recommendations", "engine"):
            assert key in d, f"Missing key: {key}"

    def test_json_serializable(self):
        d = _make_report().to_dict()
        # Should not raise
        result = json.dumps(d)
        assert isinstance(result, str)


# ═══════════════════════════════════════════════
#  serialize_report
# ═══════════════════════════════════════════════

class TestSerializeReport:

    def test_returns_string(self):
        result = serialize_report(_make_report())
        assert isinstance(result, str)

    def test_valid_json(self):
        result = serialize_report(_make_report())
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_contains_report_version(self):
        result = serialize_report(_make_report())
        parsed = json.loads(result)
        assert parsed["report_version"] == REPORT_VERSION

    def test_contains_all_sections(self):
        result = serialize_report(_make_report())
        parsed = json.loads(result)
        for key in ("meta", "summary", "breakdown", "findings"):
            assert key in parsed

    def test_indented(self):
        result = serialize_report(_make_report())
        assert "\n" in result  # indented = multiline


# ═══════════════════════════════════════════════
#  format_txt_report
# ═══════════════════════════════════════════════

class TestFormatTxtReport:

    def test_returns_string(self):
        out = format_txt_report(_make_report())
        assert isinstance(out, str)

    def test_contains_header(self):
        out = format_txt_report(_make_report())
        assert "AI SENTRY" in out

    def test_contains_target(self):
        out = format_txt_report(_make_report())
        assert "api.openai.com" in out

    def test_contains_risk_score(self):
        out = format_txt_report(_make_report())
        assert "/100" in out

    def test_contains_risk_level(self):
        out = format_txt_report(_make_report())
        level = _make_report().summary["risk_level"].upper()
        assert level in out

    def test_contains_finding_details(self):
        out = format_txt_report(_make_report())
        assert "[HIGH]" in out
        assert "confidence" in out.lower()

    def test_contains_recommendations(self):
        out = format_txt_report(_make_report())
        assert "RECOMMENDATIONS" in out
        assert "1." in out

    def test_contains_engine_info(self):
        out = format_txt_report(_make_report())
        assert "ENGINE INFO" in out
        assert "mock" in out

    def test_contains_footer(self):
        out = format_txt_report(_make_report())
        assert "Report generated by AI SENTRY" in out

    def test_empty_findings(self):
        out = format_txt_report(_empty_report())
        assert "No findings" in out or "passed all" in out

    def test_empty_recommendations(self):
        out = format_txt_report(_empty_report())
        assert "No recommendations" in out or "no vulnerabilities" in out.lower()

    def test_single_category(self):
        out = format_txt_report(_single_cat_report())
        assert "harmful_output" in out

    def test_ascii_safe(self):
        """All output should be ASCII-safe for Windows cp1252."""
        out = format_txt_report(_make_report())
        out.encode("ascii")  # should not raise


# ═══════════════════════════════════════════════
#  display_txt_report
# ═══════════════════════════════════════════════

class TestDisplayTxtReport:

    def test_calls_print(self):
        with patch("builtins.print") as mp:
            display_txt_report(_make_report())
            assert mp.called


# ═══════════════════════════════════════════════
#  export_report
# ═══════════════════════════════════════════════

class TestExportReport:

    def test_json_export_creates_file(self, tmp_path):
        path = str(tmp_path / "test_report.json")
        result = export_report(_make_report(), path, fmt="json")
        assert result.ok is True
        assert os.path.exists(path)

    def test_json_export_valid_json(self, tmp_path):
        path = str(tmp_path / "test_report.json")
        export_report(_make_report(), path, fmt="json")
        with open(path) as f:
            data = json.load(f)
        assert "meta" in data
        assert "findings" in data

    def test_txt_export_creates_file(self, tmp_path):
        path = str(tmp_path / "test_report.txt")
        result = export_report(_make_report(), path, fmt="txt")
        assert result.ok is True
        assert os.path.exists(path)

    def test_txt_export_contains_header(self, tmp_path):
        path = str(tmp_path / "test_report.txt")
        export_report(_make_report(), path, fmt="txt")
        with open(path) as f:
            content = f.read()
        assert "AI SENTRY" in content

    def test_invalid_format_returns_error(self, tmp_path):
        path = str(tmp_path / "test.xyz")
        result = export_report(_make_report(), path, fmt="xml")
        assert result.ok is False
        assert "Unsupported" in result.error

    def test_creates_parent_directories(self, tmp_path):
        path = str(tmp_path / "deep" / "nested" / "report.json")
        result = export_report(_make_report(), path, fmt="json")
        assert result.ok is True
        assert os.path.exists(path)

    def test_bytes_written_positive(self, tmp_path):
        path = str(tmp_path / "test.json")
        result = export_report(_make_report(), path, fmt="json")
        assert result.bytes_written > 0

    def test_path_is_absolute(self, tmp_path):
        path = str(tmp_path / "test.json")
        result = export_report(_make_report(), path, fmt="json")
        assert os.path.isabs(result.path)

    def test_format_echoed(self, tmp_path):
        path = str(tmp_path / "test.json")
        result = export_report(_make_report(), path, fmt="json")
        assert result.format == "json"

    def test_empty_report_export(self, tmp_path):
        path = str(tmp_path / "empty.json")
        result = export_report(_empty_report(), path, fmt="json")
        assert result.ok is True


# ═══════════════════════════════════════════════
#  ExportResult
# ═══════════════════════════════════════════════

class TestExportResult:

    def test_success_result(self):
        r = ExportResult(ok=True, path="/tmp/test.json", format="json", bytes_written=1024)
        assert r.ok is True

    def test_failure_result(self):
        r = ExportResult(ok=False, path="/tmp/test.json", format="json", error="Denied")
        assert r.ok is False
        assert r.error == "Denied"


# ═══════════════════════════════════════════════
#  print_export_result
# ═══════════════════════════════════════════════

class TestPrintExportResult:

    def test_success_prints_ok(self):
        r = ExportResult(ok=True, path="/tmp/test.json", format="json", bytes_written=2048)
        with patch("builtins.print") as mp:
            print_export_result(r)
            output = " ".join(str(c) for c in mp.call_args_list)
            assert "OK" in output

    def test_failure_prints_error(self):
        r = ExportResult(ok=False, path="/tmp/test.json", format="json", error="Permission denied")
        with patch("builtins.print") as mp:
            print_export_result(r)
            output = " ".join(str(c) for c in mp.call_args_list)
            assert "failed" in output.lower() or "X" in output


# ═══════════════════════════════════════════════
#  Report Service
# ═══════════════════════════════════════════════

class TestReportService:

    def setup_method(self):
        clear_reports()

    def test_store_returns_scan_id(self):
        report = _make_report()
        scan_id = store_report(report)
        assert scan_id == report.meta["scan_id"]

    def test_get_by_id_returns_dict(self):
        report = _make_report()
        scan_id = store_report(report)
        retrieved = get_report_by_id(scan_id)
        assert isinstance(retrieved, dict)

    def test_get_by_id_has_all_sections(self):
        report = _make_report()
        scan_id = store_report(report)
        retrieved = get_report_by_id(scan_id)
        for key in ("meta", "summary", "breakdown", "findings"):
            assert key in retrieved

    def test_get_by_id_not_found(self):
        assert get_report_by_id("nonexistent") is None

    def test_get_latest_report(self):
        report = _make_report()
        store_report(report)
        latest = get_latest_report()
        assert latest is not None
        assert latest["meta"]["scan_id"] == report.meta["scan_id"]

    def test_get_latest_report_empty(self):
        assert get_latest_report() is None

    def test_get_latest_report_object(self):
        report = _make_report()
        store_report(report)
        obj = get_latest_report_object()
        assert isinstance(obj, ScanReport)

    def test_multiple_stores_latest_is_last(self):
        r1 = _make_report()
        r2 = _single_cat_report()
        store_report(r1)
        store_report(r2)
        latest = get_latest_report()
        assert latest["meta"]["scan_id"] == r2.meta["scan_id"]

    def test_list_report_ids(self):
        r1 = _make_report()
        r2 = _single_cat_report()
        store_report(r1)
        store_report(r2)
        ids = list_report_ids()
        assert len(ids) == 2

    def test_get_report_count(self):
        store_report(_make_report())
        store_report(_single_cat_report())
        assert get_report_count() == 2

    def test_clear_reports(self):
        store_report(_make_report())
        cleared = clear_reports()
        assert cleared == 1
        assert get_report_count() == 0
        assert get_latest_report() is None
