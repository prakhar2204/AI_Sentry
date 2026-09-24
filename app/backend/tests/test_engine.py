"""
Tests for Phase 3c -- Engine Adapter System

Covers:
  - core/engine_interface.py  (ScanFinding, ScanResult, BaseEngine)
  - core/mock_engine.py       (MockEngine determinism + correctness)
  - core/engine_runner.py     (run_engine, format_finding, format_results)

Run with:
    python -m pytest tests/test_engine.py -v
"""

import pytest
from unittest.mock import patch

from core.manifest import create_manifest, ProbeCategory
from core.engine_interface import (
    ScanFinding,
    ScanResult,
    BaseEngine,
    VALID_SEVERITIES,
)
from core.mock_engine import MockEngine, _FINDING_TEMPLATES
from core.engine_runner import (
    run_engine,
    format_finding,
    format_results,
    display_results,
    print_scan_error,
)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _make_manifest(
    target="https://api.openai.com/v1",
    mode="api",
    scan_depth="standard",
    categories=None,
):
    return create_manifest(
        target=target,
        mode=mode,
        scan_depth=scan_depth,
        categories=categories or ["prompt_injection", "jailbreak"],
    )


def _make_finding(**kw):
    defaults = dict(
        category="jailbreak",
        severity="high",
        confidence=0.88,
        evidence="Test evidence",
        source="mock",
        probe_id="JB-001",
    )
    defaults.update(kw)
    return ScanFinding(**defaults)


def _make_result(**kw):
    defaults = dict(
        findings=[_make_finding()],
        engine_name="mock",
        manifest_id="test-id",
        total_probes=1,
        duration_sec=0.0,
        error=None,
    )
    defaults.update(kw)
    return ScanResult(**defaults)


# ═══════════════════════════════════════════════
#  ScanFinding
# ═══════════════════════════════════════════════

class TestScanFinding:

    def test_is_frozen(self):
        f = _make_finding()
        with pytest.raises(AttributeError):
            f.severity = "low"

    def test_valid_severities(self):
        for sev in ("low", "medium", "high"):
            f = _make_finding(severity=sev)
            assert f.severity == sev

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="Invalid severity"):
            _make_finding(severity="critical")

    def test_confidence_at_zero(self):
        f = _make_finding(confidence=0.0)
        assert f.confidence == 0.0

    def test_confidence_at_one(self):
        f = _make_finding(confidence=1.0)
        assert f.confidence == 1.0

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValueError, match="Confidence"):
            _make_finding(confidence=-0.1)

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValueError, match="Confidence"):
            _make_finding(confidence=1.1)

    def test_to_dict_contains_all_fields(self):
        f = _make_finding(probe_id="X-99")
        d = f.to_dict()
        assert d["category"] == "jailbreak"
        assert d["severity"] == "high"
        assert d["confidence"] == 0.88
        assert d["evidence"] == "Test evidence"
        assert d["source"] == "mock"
        assert d["probe_id"] == "X-99"

    def test_to_dict_returns_plain_dict(self):
        assert isinstance(_make_finding().to_dict(), dict)

    def test_default_probe_id_is_empty(self):
        f = ScanFinding(
            category="test", severity="low",
            confidence=0.5, evidence="e", source="s",
        )
        assert f.probe_id == ""


# ═══════════════════════════════════════════════
#  ScanResult
# ═══════════════════════════════════════════════

class TestScanResult:

    def test_ok_is_true_when_no_error(self):
        r = _make_result(error=None)
        assert r.ok is True

    def test_ok_is_false_when_error(self):
        r = _make_result(error="Something broke")
        assert r.ok is False

    def test_finding_count(self):
        findings = [_make_finding(), _make_finding(severity="low", confidence=0.3)]
        r = _make_result(findings=findings)
        assert r.finding_count == 2

    def test_high_count(self):
        findings = [
            _make_finding(severity="high"),
            _make_finding(severity="high", confidence=0.9),
            _make_finding(severity="low", confidence=0.3),
        ]
        r = _make_result(findings=findings)
        assert r.high_count == 2

    def test_medium_count(self):
        findings = [_make_finding(severity="medium", confidence=0.5)]
        r = _make_result(findings=findings)
        assert r.medium_count == 1

    def test_low_count(self):
        findings = [
            _make_finding(severity="low", confidence=0.2),
            _make_finding(severity="low", confidence=0.3),
        ]
        r = _make_result(findings=findings)
        assert r.low_count == 2

    def test_empty_findings(self):
        r = _make_result(findings=[])
        assert r.finding_count == 0
        assert r.high_count == 0
        assert r.medium_count == 0
        assert r.low_count == 0

    def test_to_dict_contains_summary(self):
        r = _make_result()
        d = r.to_dict()
        assert "summary" in d
        assert d["summary"]["total"] == 1
        assert d["summary"]["high"] == 1

    def test_to_dict_contains_findings(self):
        r = _make_result()
        d = r.to_dict()
        assert isinstance(d["findings"], list)
        assert len(d["findings"]) == 1

    def test_to_dict_contains_metadata(self):
        r = _make_result(engine_name="mock", manifest_id="abc")
        d = r.to_dict()
        assert d["engine_name"] == "mock"
        assert d["manifest_id"] == "abc"


# ═══════════════════════════════════════════════
#  BaseEngine (abstract)
# ═══════════════════════════════════════════════

class TestBaseEngine:

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseEngine()

    def test_subclass_must_implement_run_scan(self):
        class IncompleteEngine(BaseEngine):
            @property
            def name(self):
                return "incomplete"
        with pytest.raises(TypeError):
            IncompleteEngine()

    def test_subclass_must_implement_name(self):
        class NoNameEngine(BaseEngine):
            def run_scan(self, manifest):
                return _make_result()
        with pytest.raises(TypeError):
            NoNameEngine()

    def test_valid_subclass_can_be_instantiated(self):
        class GoodEngine(BaseEngine):
            @property
            def name(self):
                return "good"
            def run_scan(self, manifest):
                return _make_result()
        e = GoodEngine()
        assert e.name == "good"


# ═══════════════════════════════════════════════
#  MockEngine
# ═══════════════════════════════════════════════

class TestMockEngine:

    def test_name_is_mock(self):
        assert MockEngine().name == "mock"

    def test_is_subclass_of_base_engine(self):
        assert issubclass(MockEngine, BaseEngine)

    def test_returns_scan_result(self):
        m = _make_manifest()
        result = MockEngine().run_scan(m)
        assert isinstance(result, ScanResult)

    def test_result_ok_is_true(self):
        m = _make_manifest()
        result = MockEngine().run_scan(m)
        assert result.ok is True

    def test_result_has_no_error(self):
        m = _make_manifest()
        result = MockEngine().run_scan(m)
        assert result.error is None

    def test_engine_name_in_result(self):
        m = _make_manifest()
        result = MockEngine().run_scan(m)
        assert result.engine_name == "mock"

    def test_manifest_id_in_result(self):
        m = _make_manifest()
        result = MockEngine().run_scan(m)
        assert result.manifest_id == m.manifest_id

    # Category coverage
    def test_prompt_injection_produces_2_findings(self):
        m = _make_manifest(categories=["prompt_injection"])
        result = MockEngine().run_scan(m)
        assert result.finding_count == 2

    def test_jailbreak_produces_3_findings(self):
        m = _make_manifest(categories=["jailbreak"])
        result = MockEngine().run_scan(m)
        assert result.finding_count == 3

    def test_data_leak_produces_2_findings(self):
        m = _make_manifest(categories=["data_leak"])
        result = MockEngine().run_scan(m)
        assert result.finding_count == 2

    def test_harmful_output_produces_2_findings(self):
        m = _make_manifest(categories=["harmful_output"])
        result = MockEngine().run_scan(m)
        assert result.finding_count == 2

    def test_all_four_categories_produces_9_findings(self):
        m = _make_manifest(
            categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"]
        )
        result = MockEngine().run_scan(m)
        assert result.finding_count == 9  # 2+3+2+2

    # Determinism
    def test_deterministic_across_calls(self):
        m = _make_manifest()
        a = MockEngine().run_scan(m)
        b = MockEngine().run_scan(m)
        assert a.finding_count == b.finding_count
        for fa, fb in zip(a.findings, b.findings):
            assert fa.category == fb.category
            assert fa.severity == fb.severity
            assert fa.confidence == fb.confidence
            assert fa.evidence == fb.evidence

    def test_deterministic_across_instances(self):
        m = _make_manifest(categories=["data_leak"])
        a = MockEngine().run_scan(m)
        b = MockEngine().run_scan(m)
        assert a.findings[0].evidence == b.findings[0].evidence

    # Finding quality
    def test_all_findings_have_valid_severity(self):
        m = _make_manifest(
            categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"]
        )
        result = MockEngine().run_scan(m)
        for f in result.findings:
            assert f.severity in VALID_SEVERITIES

    def test_all_findings_have_valid_confidence(self):
        m = _make_manifest(
            categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"]
        )
        result = MockEngine().run_scan(m)
        for f in result.findings:
            assert 0.0 <= f.confidence <= 1.0

    def test_all_findings_have_non_empty_evidence(self):
        m = _make_manifest(
            categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"]
        )
        result = MockEngine().run_scan(m)
        for f in result.findings:
            assert len(f.evidence) > 20  # meaningful evidence

    def test_all_findings_source_is_mock(self):
        m = _make_manifest(
            categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"]
        )
        result = MockEngine().run_scan(m)
        for f in result.findings:
            assert f.source == "mock"

    def test_all_findings_have_probe_id(self):
        m = _make_manifest(
            categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"]
        )
        result = MockEngine().run_scan(m)
        for f in result.findings:
            assert f.probe_id != ""

    def test_finding_categories_match_manifest(self):
        cats = ["jailbreak", "data_leak"]
        m = _make_manifest(categories=cats)
        result = MockEngine().run_scan(m)
        finding_cats = {f.category for f in result.findings}
        assert finding_cats == set(cats)

    def test_templates_exist_for_all_categories(self):
        for cat in ("prompt_injection", "jailbreak", "data_leak", "harmful_output"):
            assert cat in _FINDING_TEMPLATES
            assert len(_FINDING_TEMPLATES[cat]) > 0


# ═══════════════════════════════════════════════
#  format_finding
# ═══════════════════════════════════════════════

class TestFormatFinding:

    def test_contains_severity_tag(self):
        f = _make_finding(severity="high")
        out = format_finding(f, 1)
        assert "[HIGH]" in out

    def test_contains_medium_tag(self):
        f = _make_finding(severity="medium", confidence=0.5)
        out = format_finding(f, 1)
        assert "[MED ]" in out

    def test_contains_low_tag(self):
        f = _make_finding(severity="low", confidence=0.3)
        out = format_finding(f, 1)
        assert "[LOW ]" in out

    def test_contains_category(self):
        f = _make_finding(category="data_leak")
        out = format_finding(f, 1)
        assert "data_leak" in out

    def test_contains_evidence(self):
        f = _make_finding(evidence="Specific evidence text here")
        out = format_finding(f, 1)
        assert "Specific evidence text here" in out

    def test_contains_confidence(self):
        f = _make_finding(confidence=0.88)
        out = format_finding(f, 1)
        assert "0.88" in out

    def test_contains_index(self):
        f = _make_finding()
        out = format_finding(f, 42)
        assert "#42" in out

    def test_contains_probe_id(self):
        f = _make_finding(probe_id="PI-001")
        out = format_finding(f, 1)
        assert "PI-001" in out

    def test_contains_source(self):
        f = _make_finding(source="mock")
        out = format_finding(f, 1)
        assert "mock" in out

    def test_returns_string(self):
        assert isinstance(format_finding(_make_finding(), 1), str)


# ═══════════════════════════════════════════════
#  format_results
# ═══════════════════════════════════════════════

class TestFormatResults:

    def test_contains_header(self):
        r = _make_result()
        out = format_results(r)
        assert "SCAN RESULTS" in out

    def test_contains_engine_name(self):
        r = _make_result(engine_name="mock")
        out = format_results(r)
        assert "mock" in out

    def test_contains_manifest_id(self):
        r = _make_result(manifest_id="test-123")
        out = format_results(r)
        assert "test-123" in out

    def test_contains_probe_count(self):
        r = _make_result(total_probes=42)
        out = format_results(r)
        assert "42" in out

    def test_contains_severity_counts(self):
        findings = [
            _make_finding(severity="high"),
            _make_finding(severity="medium", confidence=0.5),
            _make_finding(severity="low", confidence=0.3),
        ]
        r = _make_result(findings=findings)
        out = format_results(r)
        assert "HIGH" in out
        assert "MEDIUM" in out
        assert "LOW" in out

    def test_high_findings_trigger_warning(self):
        r = _make_result(findings=[_make_finding(severity="high")])
        out = format_results(r)
        assert "critical" in out.lower() or "vulnerabilit" in out.lower()

    def test_medium_only_shows_review(self):
        r = _make_result(findings=[_make_finding(severity="medium", confidence=0.5)])
        out = format_results(r)
        assert "review" in out.lower() or "recommend" in out.lower()

    def test_low_only_shows_safe(self):
        r = _make_result(findings=[_make_finding(severity="low", confidence=0.3)])
        out = format_results(r)
        assert "safe" in out.lower() or "OK" in out

    def test_empty_findings_shows_no_findings(self):
        r = _make_result(findings=[])
        out = format_results(r)
        assert "No findings" in out or "passed all" in out

    def test_error_result_shows_error(self):
        r = _make_result(error="Engine crashed", findings=[])
        out = format_results(r)
        assert "ERROR" in out
        assert "Engine crashed" in out

    def test_findings_sorted_by_severity(self):
        findings = [
            _make_finding(severity="low", category="a", confidence=0.2),
            _make_finding(severity="high", category="b"),
            _make_finding(severity="medium", category="c", confidence=0.5),
        ]
        r = _make_result(findings=findings)
        out = format_results(r)
        high_pos = out.index("[HIGH]")
        med_pos = out.index("[MED ]")
        low_pos = out.index("[LOW ]")
        assert high_pos < med_pos < low_pos

    def test_returns_string(self):
        assert isinstance(format_results(_make_result()), str)


# ═══════════════════════════════════════════════
#  display_results / print_scan_error
# ═══════════════════════════════════════════════

class TestDisplayResults:

    def test_display_calls_print(self):
        r = _make_result()
        with patch("builtins.print") as mp:
            display_results(r)
            assert mp.called

    def test_print_scan_error_calls_print(self):
        r = _make_result(error="Test error")
        with patch("builtins.print") as mp:
            print_scan_error(r)
            assert mp.called


# ═══════════════════════════════════════════════
#  run_engine (orchestrator)
# ═══════════════════════════════════════════════

class TestRunEngine:

    def test_returns_scan_result(self):
        m = _make_manifest()
        result = run_engine(m)
        assert isinstance(result, ScanResult)

    def test_result_ok(self):
        m = _make_manifest()
        assert run_engine(m).ok is True

    def test_uses_mock_engine(self):
        m = _make_manifest()
        result = run_engine(m)
        assert result.engine_name == "mock"

    def test_manifest_id_matches(self):
        m = _make_manifest()
        result = run_engine(m)
        assert result.manifest_id == m.manifest_id

    def test_findings_match_categories(self):
        m = _make_manifest(categories=["data_leak"])
        result = run_engine(m)
        for f in result.findings:
            assert f.category == "data_leak"

    def test_deterministic(self):
        m = _make_manifest()
        a = run_engine(m)
        b = run_engine(m)
        assert a.finding_count == b.finding_count
