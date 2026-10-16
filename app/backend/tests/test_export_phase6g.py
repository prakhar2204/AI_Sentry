"""
Phase 6g -- Export Report Tests
tests/test_export_phase6g.py

Focused tests for the export workflow added in Phase 6g.
Tests backend export_report() edge cases not covered by test_report.py,
and documents frontend export contract expectations.

Run with:
    python -m pytest tests/test_export_phase6g.py -v

Note: Frontend serializers (serializeToTxt, serializeToHtml) are pure JS
functions with no Python equivalent. Their contract is tested here via
the backend canonical format so both stay in sync.
"""

import json
import os
import tempfile
import pytest

from core.report_generator import (
    ScanReport,
    export_report,
    serialize_report,
    format_txt_report,
    ExportResult,
    REPORT_VERSION,
)
from core.engine_interface import ScanFinding, ScanResult
from core.manifest import create_manifest
from core.mock_engine import MockEngine
from core.scorer import generate_risk_report
from core.recommender import generate_recommendations
from core.report_generator import generate_full_report


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

def _make_report() -> ScanReport:
    """Full pipeline report for general testing."""
    manifest = create_manifest(
        target="https://api.example.com/v1",
        mode="api",
        scan_depth="standard",
        categories=["prompt_injection", "jailbreak"],
    )
    scan_result = MockEngine().run_scan(manifest)
    risk_report = generate_risk_report(scan_result.findings)
    rec_report = generate_recommendations(risk_report)
    return generate_full_report(manifest, scan_result, risk_report, rec_report)


def _empty_finding_report() -> ScanReport:
    """Report with zero findings (all probes passed)."""
    manifest = create_manifest(
        target="https://safe.example.com",
        mode="api",
        scan_depth="quick",
        categories=["data_leak"],
    )
    # Build a minimal ScanResult with no findings
    empty_result = ScanResult(
        findings=[],
        engine_name="MockEngine",
        manifest_id=manifest.manifest_id,
        total_probes=10,
        duration_sec=1.5,
        error=None,
    )
    risk_report = generate_risk_report([])
    rec_report = generate_recommendations(risk_report)
    return generate_full_report(manifest, empty_result, risk_report, rec_report)


def _html_injection_report() -> ScanReport:
    """Report with evidence containing HTML/script injection attempts."""
    manifest = create_manifest(
        target="<script>alert(1)</script>",
        mode="api",
        scan_depth="standard",
        categories=["prompt_injection"],
    )
    malicious_finding = ScanFinding(
        category="prompt_injection",
        severity="high",
        confidence=0.99,
        evidence='Response: <img src=x onerror="alert(\'XSS\')"> & "quoted" & \'apos\'',
        source="Test<Source>",
        probe_id="<pi-xss>",
    )
    scan_result = ScanResult(
        findings=[malicious_finding],
        engine_name="MockEngine",
        manifest_id=manifest.manifest_id,
        total_probes=5,
        duration_sec=1.0,
        error=None,
    )
    risk_report = generate_risk_report([malicious_finding])
    rec_report = generate_recommendations(risk_report)
    return generate_full_report(manifest, scan_result, risk_report, rec_report)


# ─────────────────────────────────────────────
#  Report schema contract
# ─────────────────────────────────────────────

class TestReportSchema:
    """Verify the canonical report schema fields for Phase 6g."""

    def test_report_version_field_present(self):
        report = _make_report()
        d = report.to_dict()
        assert "report_version" in d
        assert d["report_version"] == REPORT_VERSION

    def test_meta_fields_present(self):
        report = _make_report()
        meta = report.to_dict()["meta"]
        for field in ("target", "mode", "scan_depth", "categories",
                      "scan_id", "timestamp", "report_generated_at"):
            assert field in meta, f"meta.{field} missing"

    def test_summary_fields_present(self):
        report = _make_report()
        summary = report.to_dict()["summary"]
        for field in ("risk_score", "risk_level", "total_findings", "raw_score"):
            assert field in summary, f"summary.{field} missing"

    def test_risk_score_range(self):
        report = _make_report()
        score = report.to_dict()["summary"]["risk_score"]
        assert 0 <= score <= 100

    def test_breakdown_keys(self):
        report = _make_report()
        bd = report.to_dict()["breakdown"]
        for k in ("high", "medium", "low"):
            assert k in bd

    def test_findings_have_required_fields(self):
        report = _make_report()
        for f in report.to_dict()["findings"]:
            for field in ("category", "severity", "confidence", "evidence", "source", "probe_id"):
                assert field in f, f"finding.{field} missing"

    def test_recommendations_have_required_fields(self):
        report = _make_report()
        for rec in report.to_dict()["recommendations"]:
            for field in ("category", "severity", "actions"):
                assert field in rec, f"recommendation.{field} missing"
            # actions is always a list (may be empty)
            assert isinstance(rec["actions"], list)

    def test_no_synthetic_finding_fields(self):
        """Backend recommendations must not have rationale/verification/probe_id."""
        report = _make_report()
        for rec in report.to_dict()["recommendations"]:
            assert "rationale" not in rec, "Fabricated rationale field found"
            assert "verification" not in rec, "Fabricated verification field found"
            assert "priority" not in rec, "Fabricated priority field (use severity)"

    def test_simulated_scan_id_convention(self):
        """Verify sim- prefix convention used in frontend provenance detection."""
        # Real scan from MockEngine does NOT start with "sim-"
        report = _make_report()
        assert not report.meta["scan_id"].startswith("sim-"), (
            "Real pipeline report must not have sim- prefix — "
            "that prefix is reserved for frontend simulation mode"
        )


# ─────────────────────────────────────────────
#  JSON export
# ─────────────────────────────────────────────

class TestJsonExport:
    """JSON serialization tests."""

    def test_serialize_produces_valid_json(self):
        report = _make_report()
        json_str = serialize_report(report)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_json_has_all_top_level_keys(self):
        report = _make_report()
        parsed = json.loads(serialize_report(report))
        for key in ("report_version", "meta", "summary", "breakdown",
                    "categories", "findings", "recommendations", "engine"):
            assert key in parsed

    def test_json_preserves_target(self):
        report = _make_report()
        parsed = json.loads(serialize_report(report))
        assert parsed["meta"]["target"] == report.meta["target"]

    def test_json_preserves_findings_count(self):
        report = _make_report()
        parsed = json.loads(serialize_report(report))
        assert len(parsed["findings"]) == len(report.findings)

    def test_json_preserves_special_characters(self):
        """Unicode and special characters must survive serialization."""
        report = _make_report()
        # Patch one finding to include unicode
        report.findings[0]["evidence"] = "Résultat: <script> & 'quotes' \\n newline"
        json_str = serialize_report(report)
        parsed = json.loads(json_str)
        assert "Résultat" in parsed["findings"][0]["evidence"]
        assert "<script>" in parsed["findings"][0]["evidence"]

    def test_export_json_file_written(self, tmp_path):
        report = _make_report()
        path = str(tmp_path / "report.json")
        result = export_report(report, path, fmt="json")
        assert result.ok
        assert os.path.exists(path)
        assert result.bytes_written > 0

    def test_export_json_file_is_valid_json(self, tmp_path):
        report = _make_report()
        path = str(tmp_path / "report.json")
        export_report(report, path, fmt="json")
        with open(path, encoding="utf-8") as f:
            parsed = json.load(f)
        assert "meta" in parsed

    def test_export_json_extension_matches_content(self, tmp_path):
        """The file extension must be .json and content must be JSON, not HTML."""
        report = _make_report()
        path = str(tmp_path / "report.json")
        export_report(report, path, fmt="json")
        with open(path) as f:
            first_char = f.read(1)
        assert first_char == "{", "JSON export must begin with '{'"

    def test_export_json_returns_absolute_path(self, tmp_path):
        report = _make_report()
        path = str(tmp_path / "report.json")
        result = export_report(report, path, fmt="json")
        assert os.path.isabs(result.path)


# ─────────────────────────────────────────────
#  TXT export
# ─────────────────────────────────────────────

class TestTxtExport:
    """TXT format tests — mirrors frontend serializeToTxt() contract."""

    def test_txt_contains_header(self):
        report = _make_report()
        txt = format_txt_report(report)
        assert "Sentryɸ" in txt or "SentryPhi" in txt

    def test_txt_contains_target(self):
        report = _make_report()
        txt = format_txt_report(report)
        assert report.meta["target"] in txt

    def test_txt_contains_scan_id(self):
        report = _make_report()
        txt = format_txt_report(report)
        assert report.meta["scan_id"] in txt

    def test_txt_contains_risk_score(self):
        report = _make_report()
        txt = format_txt_report(report)
        assert str(report.summary["risk_score"]) in txt

    def test_txt_contains_findings_section(self):
        report = _make_report()
        txt = format_txt_report(report)
        assert "FINDINGS" in txt

    def test_txt_contains_recommendations_section(self):
        report = _make_report()
        txt = format_txt_report(report)
        assert "RECOMMENDATIONS" in txt

    def test_txt_contains_engine_info(self):
        report = _make_report()
        txt = format_txt_report(report)
        assert "ENGINE" in txt

    def test_txt_zero_findings_note(self):
        report = _empty_finding_report()
        txt = format_txt_report(report)
        assert "No findings" in txt

    def test_txt_zero_recs_note(self):
        report = _empty_finding_report()
        txt = format_txt_report(report)
        assert "No recommendations" in txt

    def test_export_txt_file_written(self, tmp_path):
        report = _make_report()
        path = str(tmp_path / "report.txt")
        result = export_report(report, path, fmt="txt")
        assert result.ok
        assert os.path.exists(path)

    def test_export_txt_is_not_json(self, tmp_path):
        report = _make_report()
        path = str(tmp_path / "report.txt")
        export_report(report, path, fmt="txt")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Must not be JSON
        assert not content.strip().startswith("{")
        # Must be human-readable text
        assert "FINDINGS" in content or "SCAN" in content.upper()


# ─────────────────────────────────────────────
#  HTML escaping contract (backend-side verification)
# ─────────────────────────────────────────────

class TestHtmlEscapingContract:
    """
    Verifies that evidence, target, and source data contain characters
    that MUST be escaped by the HTML exporter.

    The frontend ExportPage.tsx serializeToHtml() is responsible for escaping.
    These tests confirm the backend does NOT pre-escape — raw values are stored —
    so the frontend must always escape before interpolating into HTML.
    """

    def test_evidence_may_contain_html_angle_brackets(self):
        """Backend stores raw evidence — frontend must escape it."""
        report = _html_injection_report()
        evidence = report.findings[0]["evidence"]
        # Raw evidence contains < and > — these must NOT be left unescaped in HTML
        assert "<" in evidence or ">" in evidence, (
            "Test fixture should contain angle brackets in evidence"
        )

    def test_evidence_may_contain_script_tag(self):
        """Evidence with <script> tags must be escaped in HTML output."""
        report = _html_injection_report()
        evidence = report.findings[0]["evidence"]
        assert "onerror" in evidence or "<img" in evidence or "<script" in evidence

    def test_target_may_contain_html(self):
        """Target field is user-supplied and may contain HTML."""
        report = _html_injection_report()
        target = report.meta["target"]
        assert "<" in target

    def test_recommendations_not_fabricated(self):
        """Recommendations must not have invented fields beyond category/severity/actions."""
        report = _make_report()
        for rec in report.recommendations:
            d = rec.to_dict() if hasattr(rec, "to_dict") else rec
            allowed = {"category", "severity", "actions"}
            extra = set(d.keys()) - allowed
            assert not extra, f"Unexpected recommendation fields: {extra}"


# ─────────────────────────────────────────────
#  Export failure handling
# ─────────────────────────────────────────────

class TestExportFailures:
    """Verify error states are properly returned."""

    def test_unsupported_format_returns_error(self):
        report = _make_report()
        result = export_report(report, "/tmp/report.pdf", fmt="pdf")
        assert not result.ok
        assert result.error is not None
        assert "pdf" in result.error.lower() or "unsupported" in result.error.lower()

    def test_unsupported_format_html_from_backend(self):
        """HTML is not supported by backend export_report() — frontend generates it."""
        report = _make_report()
        result = export_report(report, "/tmp/report.html", fmt="html")
        assert not result.ok

    def test_export_result_format_on_failure(self):
        report = _make_report()
        result = export_report(report, "/tmp/report.pdf", fmt="pdf")
        assert result.format == "pdf"
        assert not result.ok
        assert result.bytes_written == 0

    def test_permission_denied_returns_error(self, tmp_path):
        """Write to a read-only directory."""
        report = _make_report()
        ro_dir = tmp_path / "readonly"
        ro_dir.mkdir()
        path = str(ro_dir / "report.json")
        # Make the directory read-only
        ro_dir.chmod(0o444)
        result = export_report(report, path, fmt="json")
        # On Windows chmod may not prevent writes — accept either outcome
        if not result.ok:
            assert result.error is not None
        # Restore permissions for cleanup
        ro_dir.chmod(0o755)


# ─────────────────────────────────────────────
#  Empty / edge case reports
# ─────────────────────────────────────────────

class TestEdgeCaseReports:
    """Empty findings, zero recommendations, and incomplete assessments."""

    def test_empty_findings_serializes(self):
        report = _empty_finding_report()
        json_str = serialize_report(report)
        parsed = json.loads(json_str)
        assert parsed["findings"] == []
        assert parsed["summary"]["total_findings"] == 0

    def test_zero_score_with_no_findings(self):
        report = _empty_finding_report()
        d = report.to_dict()
        assert d["summary"]["risk_score"] == 0

    def test_zero_recs_with_no_findings(self):
        report = _empty_finding_report()
        d = report.to_dict()
        assert d["recommendations"] == []

    def test_empty_findings_txt_is_readable(self):
        report = _empty_finding_report()
        txt = format_txt_report(report)
        assert len(txt) > 100  # Should still produce a usable document
        assert "No findings" in txt

    def test_empty_report_does_not_claim_secure(self):
        """Zero findings must not assert the target is 'secure'."""
        report = _empty_finding_report()
        txt = format_txt_report(report)
        txt_lower = txt.lower()
        # These words would be misleading for a zero-finding report
        # The format uses "passed all probes" rather than "secure"
        assert "target is secure" not in txt_lower
        assert "confirmed secure" not in txt_lower

    def test_export_json_with_empty_findings(self, tmp_path):
        report = _empty_finding_report()
        path = str(tmp_path / "empty.json")
        result = export_report(report, path, fmt="json")
        assert result.ok
        with open(path, encoding="utf-8") as f:
            parsed = json.load(f)
        assert parsed["findings"] == []

    def test_engine_error_preserved_in_output(self):
        """Engine error field must survive into exported report."""
        manifest = create_manifest(
            target="https://error.example.com",
            mode="api",
            scan_depth="quick",
            categories=["prompt_injection"],
        )
        failed_result = ScanResult(
            findings=[],
            engine_name="MockEngine",
            manifest_id=manifest.manifest_id,
            total_probes=0,
            duration_sec=0.1,
            error="Connection refused",
        )
        risk = generate_risk_report([])
        from core.recommender import generate_recommendations
        recs = generate_recommendations(risk)
        report = generate_full_report(manifest, failed_result, risk, recs)

        d = report.to_dict()
        assert d["engine"]["error"] == "Connection refused"

        json_str = serialize_report(report)
        parsed = json.loads(json_str)
        assert parsed["engine"]["error"] == "Connection refused"


# ─────────────────────────────────────────────
#  Frontend export contract documentation
# ─────────────────────────────────────────────

class TestFrontendExportContract:
    """
    Documents the expected behavior of the frontend ExportPage.tsx serializers.
    These are documentation-style assertions against the backend schema;
    they do not test frontend code directly (no JS runtime available in pytest).
    """

    def test_json_export_should_preserve_report_version(self):
        """Frontend JSON export should include report_version from ScanReport."""
        report = _make_report()
        d = report.to_dict()
        assert "report_version" in d
        assert d["report_version"] == "1.0.0"

    def test_frontend_html_must_not_include_output_dir(self):
        """
        output_dir may contain local filesystem paths.
        Frontend HTML exporter should not expose this field.
        This test documents the expectation — enforced in ExportPage.tsx.
        """
        report = _make_report()
        assert "output_dir" in report.meta, "output_dir exists in meta"
        # The frontend ExportPage.tsx PreviewMetaRow does NOT render output_dir
        # (it is a local path and not relevant for the exported document)

    def test_frontend_formats_do_not_include_pdf(self):
        """
        PDF is not supported. Backend export_report() rejects 'pdf'.
        Frontend FORMATS constant must not include pdf.
        This test documents the backend rejection.
        """
        report = _make_report()
        result = export_report(report, "/tmp/report.pdf", fmt="pdf")
        assert not result.ok
        # This confirms frontend is right to not offer PDF

    def test_all_recommendation_actions_are_strings(self):
        """Actions list must be str[] — frontend renders each as a text node."""
        report = _make_report()
        for rec in report.to_dict()["recommendations"]:
            for action in rec["actions"]:
                assert isinstance(action, str), f"Action is not str: {action!r}"

    def test_confidence_is_float_zero_to_one(self):
        """Frontend confidence display expects 0.0-1.0 float, not percentage."""
        report = _make_report()
        for f in report.to_dict()["findings"]:
            c = f["confidence"]
            assert isinstance(c, float)
            assert 0.0 <= c <= 1.0, f"Confidence out of range: {c}"
