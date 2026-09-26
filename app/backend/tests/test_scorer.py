"""
Tests for core/scorer.py -- Phase 5a

Covers:
  - score_finding()            -- per-finding weighted score
  - calculate_raw_score()      -- sum of all findings
  - normalize_score()          -- 0-100 mapping
  - classify_risk()            -- threshold classification
  - build_severity_summary()   -- severity counts
  - build_category_breakdown() -- per-category analysis
  - generate_risk_report()     -- orchestrator
  - score_scan_result()        -- convenience wrapper
  - format_risk_report()       -- CLI display
  - display_risk_report()      -- stdout output
  - CategoryBreakdown / RiskReport dataclasses
  - Edge cases (empty findings, single finding, max score)

Run with:
    python -m pytest tests/test_scorer.py -v
"""

import pytest
from unittest.mock import patch

from core.engine_interface import ScanFinding, ScanResult
from core.scorer import (
    score_finding,
    calculate_raw_score,
    normalize_score,
    classify_risk,
    build_severity_summary,
    build_category_breakdown,
    generate_risk_report,
    score_scan_result,
    format_risk_report,
    display_risk_report,
    CategoryBreakdown,
    RiskReport,
    SEVERITY_WEIGHTS,
    MAX_POSSIBLE_SCORE,
    RISK_THRESHOLD_LOW,
    RISK_THRESHOLD_MED,
)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _f(severity="high", confidence=0.9, category="jailbreak", source="mock"):
    return ScanFinding(
        category=category,
        severity=severity,
        confidence=confidence,
        evidence="Test evidence",
        source=source,
    )


def _result(findings=None):
    findings = findings or [_f()]
    return ScanResult(
        findings=findings,
        engine_name="mock",
        manifest_id="test-id",
        total_probes=len(findings),
    )


# ═══════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════

class TestConstants:

    def test_high_weight_is_10(self):
        assert SEVERITY_WEIGHTS["high"] == 10

    def test_medium_weight_is_5(self):
        assert SEVERITY_WEIGHTS["medium"] == 5

    def test_low_weight_is_2(self):
        assert SEVERITY_WEIGHTS["low"] == 2

    def test_max_possible_score_is_120(self):
        assert MAX_POSSIBLE_SCORE == 120.0

    def test_low_threshold_is_30(self):
        assert RISK_THRESHOLD_LOW == 30

    def test_med_threshold_is_70(self):
        assert RISK_THRESHOLD_MED == 70


# ═══════════════════════════════════════════════
#  score_finding
# ═══════════════════════════════════════════════

class TestScoreFinding:

    def test_high_full_confidence(self):
        assert score_finding(_f(severity="high", confidence=1.0)) == 10.0

    def test_high_partial_confidence(self):
        assert score_finding(_f(severity="high", confidence=0.5)) == 5.0

    def test_medium_full_confidence(self):
        assert score_finding(_f(severity="medium", confidence=1.0)) == 5.0

    def test_low_full_confidence(self):
        assert score_finding(_f(severity="low", confidence=1.0)) == 2.0

    def test_zero_confidence(self):
        assert score_finding(_f(severity="high", confidence=0.0)) == 0.0

    def test_returns_float(self):
        assert isinstance(score_finding(_f()), float)

    def test_deterministic(self):
        f = _f(severity="medium", confidence=0.7)
        assert score_finding(f) == score_finding(f)

    def test_specific_value(self):
        # 10 * 0.92 = 9.2
        result = score_finding(_f(severity="high", confidence=0.92))
        assert abs(result - 9.2) < 0.001


# ═══════════════════════════════════════════════
#  calculate_raw_score
# ═══════════════════════════════════════════════

class TestCalculateRawScore:

    def test_single_finding(self):
        findings = [_f(severity="high", confidence=1.0)]
        assert calculate_raw_score(findings) == 10.0

    def test_multiple_findings(self):
        findings = [
            _f(severity="high", confidence=1.0),    # 10
            _f(severity="medium", confidence=1.0),   # 5
            _f(severity="low", confidence=1.0),      # 2
        ]
        assert calculate_raw_score(findings) == 17.0

    def test_empty_findings(self):
        assert calculate_raw_score([]) == 0.0

    def test_returns_float(self):
        assert isinstance(calculate_raw_score([_f()]), float)


# ═══════════════════════════════════════════════
#  normalize_score
# ═══════════════════════════════════════════════

class TestNormalizeScore:

    def test_zero_raw(self):
        assert normalize_score(0.0) == 0

    def test_max_raw(self):
        assert normalize_score(MAX_POSSIBLE_SCORE) == 100

    def test_half_max(self):
        assert normalize_score(MAX_POSSIBLE_SCORE / 2) == 50

    def test_over_max_caps_at_100(self):
        assert normalize_score(MAX_POSSIBLE_SCORE * 2) == 100

    def test_negative_floors_at_0(self):
        assert normalize_score(-5.0) == 0

    def test_returns_int(self):
        assert isinstance(normalize_score(50.0), int)

    def test_small_value(self):
        # 10 / 120 * 100 = 8.33 -> int = 8
        assert normalize_score(10.0) == 8


# ═══════════════════════════════════════════════
#  classify_risk
# ═══════════════════════════════════════════════

class TestClassifyRisk:

    def test_zero_is_low(self):
        assert classify_risk(0) == "low"

    def test_30_is_low(self):
        assert classify_risk(30) == "low"

    def test_31_is_medium(self):
        assert classify_risk(31) == "medium"

    def test_70_is_medium(self):
        assert classify_risk(70) == "medium"

    def test_71_is_high(self):
        assert classify_risk(71) == "high"

    def test_100_is_high(self):
        assert classify_risk(100) == "high"

    def test_returns_string(self):
        assert isinstance(classify_risk(50), str)


# ═══════════════════════════════════════════════
#  build_severity_summary
# ═══════════════════════════════════════════════

class TestBuildSeveritySummary:

    def test_mixed_findings(self):
        findings = [
            _f(severity="high"),
            _f(severity="high"),
            _f(severity="medium"),
            _f(severity="low"),
        ]
        s = build_severity_summary(findings)
        assert s == {"high": 2, "medium": 1, "low": 1}

    def test_empty_findings(self):
        s = build_severity_summary([])
        assert s == {"high": 0, "medium": 0, "low": 0}

    def test_all_high(self):
        findings = [_f(severity="high")] * 5
        s = build_severity_summary(findings)
        assert s["high"] == 5
        assert s["medium"] == 0
        assert s["low"] == 0

    def test_returns_dict(self):
        assert isinstance(build_severity_summary([]), dict)


# ═══════════════════════════════════════════════
#  build_category_breakdown
# ═══════════════════════════════════════════════

class TestBuildCategoryBreakdown:

    def test_single_category(self):
        findings = [
            _f(category="jailbreak", severity="high", confidence=0.9),
            _f(category="jailbreak", severity="low", confidence=0.4),
        ]
        bd = build_category_breakdown(findings)
        assert "jailbreak" in bd
        assert bd["jailbreak"].count == 2

    def test_multiple_categories(self):
        findings = [
            _f(category="jailbreak"),
            _f(category="data_leak"),
        ]
        bd = build_category_breakdown(findings)
        assert len(bd) == 2
        assert "jailbreak" in bd
        assert "data_leak" in bd

    def test_max_severity(self):
        findings = [
            _f(category="jailbreak", severity="low", confidence=0.3),
            _f(category="jailbreak", severity="high", confidence=0.9),
            _f(category="jailbreak", severity="medium", confidence=0.5),
        ]
        bd = build_category_breakdown(findings)
        assert bd["jailbreak"].max_severity == "high"

    def test_avg_confidence(self):
        findings = [
            _f(category="jailbreak", confidence=0.8),
            _f(category="jailbreak", confidence=0.6),
        ]
        bd = build_category_breakdown(findings)
        assert bd["jailbreak"].avg_confidence == 0.7

    def test_raw_score(self):
        findings = [
            _f(category="jailbreak", severity="high", confidence=1.0),  # 10
            _f(category="jailbreak", severity="low", confidence=1.0),   # 2
        ]
        bd = build_category_breakdown(findings)
        assert bd["jailbreak"].raw_score == 12.0

    def test_empty_findings(self):
        bd = build_category_breakdown([])
        assert bd == {}

    def test_categories_sorted_alphabetically(self):
        findings = [
            _f(category="jailbreak"),
            _f(category="data_leak"),
            _f(category="prompt_injection"),
        ]
        bd = build_category_breakdown(findings)
        keys = list(bd.keys())
        assert keys == sorted(keys)

    def test_returns_category_breakdown_type(self):
        findings = [_f(category="jailbreak")]
        bd = build_category_breakdown(findings)
        assert isinstance(bd["jailbreak"], CategoryBreakdown)


# ═══════════════════════════════════════════════
#  CategoryBreakdown
# ═══════════════════════════════════════════════

class TestCategoryBreakdown:

    def test_is_frozen(self):
        cb = CategoryBreakdown(
            category="jailbreak", count=2, max_severity="high",
            avg_confidence=0.7, raw_score=12.0,
        )
        with pytest.raises(AttributeError):
            cb.count = 5

    def test_to_dict(self):
        cb = CategoryBreakdown(
            category="jailbreak", count=2, max_severity="high",
            avg_confidence=0.7, raw_score=12.0,
        )
        d = cb.to_dict()
        assert d["category"] == "jailbreak"
        assert d["count"] == 2
        assert d["max_severity"] == "high"
        assert d["avg_confidence"] == 0.7
        assert d["raw_score"] == 12.0


# ═══════════════════════════════════════════════
#  RiskReport
# ═══════════════════════════════════════════════

class TestRiskReport:

    def test_is_frozen(self):
        r = RiskReport(
            risk_score=50, risk_level="medium", raw_score=60.0,
            summary={"high": 1, "medium": 1, "low": 1},
            category_breakdown={}, total_findings=3,
        )
        with pytest.raises(AttributeError):
            r.risk_score = 99

    def test_to_dict_all_fields(self):
        r = RiskReport(
            risk_score=50, risk_level="medium", raw_score=60.0,
            summary={"high": 1, "medium": 1, "low": 1},
            category_breakdown={}, total_findings=3,
        )
        d = r.to_dict()
        assert d["risk_score"] == 50
        assert d["risk_level"] == "medium"
        assert d["total_findings"] == 3
        assert d["summary"]["high"] == 1


# ═══════════════════════════════════════════════
#  generate_risk_report -- orchestrator
# ═══════════════════════════════════════════════

class TestGenerateRiskReport:

    def test_returns_risk_report(self):
        report = generate_risk_report([_f()])
        assert isinstance(report, RiskReport)

    def test_empty_findings_zero_score(self):
        report = generate_risk_report([])
        assert report.risk_score == 0
        assert report.risk_level == "low"
        assert report.total_findings == 0

    def test_single_high_finding(self):
        report = generate_risk_report([_f(severity="high", confidence=1.0)])
        assert report.risk_score > 0
        assert report.summary["high"] == 1

    def test_all_high_findings_high_risk(self):
        findings = [_f(severity="high", confidence=1.0)] * 12
        report = generate_risk_report(findings)
        assert report.risk_score == 100
        assert report.risk_level == "high"

    def test_single_low_finding_low_risk(self):
        report = generate_risk_report([_f(severity="low", confidence=0.3)])
        assert report.risk_level == "low"

    def test_deterministic(self):
        findings = [
            _f(severity="high", confidence=0.9),
            _f(severity="medium", confidence=0.7),
        ]
        a = generate_risk_report(findings)
        b = generate_risk_report(findings)
        assert a.risk_score == b.risk_score
        assert a.risk_level == b.risk_level

    def test_category_breakdown_populated(self):
        findings = [
            _f(category="jailbreak"),
            _f(category="data_leak"),
        ]
        report = generate_risk_report(findings)
        assert "jailbreak" in report.category_breakdown
        assert "data_leak" in report.category_breakdown

    def test_summary_counts_correct(self):
        findings = [
            _f(severity="high"),
            _f(severity="medium", confidence=0.5),
            _f(severity="low", confidence=0.3),
        ]
        report = generate_risk_report(findings)
        assert report.summary == {"high": 1, "medium": 1, "low": 1}

    def test_total_findings_correct(self):
        findings = [_f()] * 7
        report = generate_risk_report(findings)
        assert report.total_findings == 7

    def test_raw_score_matches_calculation(self):
        findings = [
            _f(severity="high", confidence=1.0),    # 10
            _f(severity="medium", confidence=1.0),   # 5
        ]
        report = generate_risk_report(findings)
        assert report.raw_score == 15.0

    # Mock engine realistic scenario
    def test_mock_engine_all_categories(self):
        """Score the exact findings the mock engine produces for all 4 cats."""
        from core.mock_engine import MockEngine
        from core.manifest import create_manifest
        m = create_manifest(
            target="https://api.openai.com/v1",
            mode="api",
            scan_depth="standard",
            categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"],
        )
        result = MockEngine().run_scan(m)
        report = generate_risk_report(result.findings)
        assert report.risk_score > 0
        assert report.total_findings == 9
        assert report.risk_level in ("low", "medium", "high")
        assert len(report.category_breakdown) == 4


# ═══════════════════════════════════════════════
#  score_scan_result
# ═══════════════════════════════════════════════

class TestScoreScanResult:

    def test_returns_risk_report(self):
        sr = _result()
        report = score_scan_result(sr)
        assert isinstance(report, RiskReport)

    def test_matches_direct_call(self):
        findings = [_f(severity="high"), _f(severity="low", confidence=0.3)]
        sr = _result(findings=findings)
        direct = generate_risk_report(findings)
        wrapped = score_scan_result(sr)
        assert direct.risk_score == wrapped.risk_score


# ═══════════════════════════════════════════════
#  format_risk_report
# ═══════════════════════════════════════════════

class TestFormatRiskReport:

    def _report(self, **kw):
        defaults = dict(
            risk_score=50, risk_level="medium", raw_score=60.0,
            summary={"high": 1, "medium": 2, "low": 1},
            category_breakdown={
                "jailbreak": CategoryBreakdown(
                    category="jailbreak", count=2, max_severity="high",
                    avg_confidence=0.75, raw_score=12.0,
                ),
            },
            total_findings=4,
        )
        defaults.update(kw)
        return RiskReport(**defaults)

    def test_contains_risk_score(self):
        out = format_risk_report(self._report(risk_score=78))
        assert "78/100" in out

    def test_contains_risk_level(self):
        out = format_risk_report(self._report(risk_level="high"))
        assert "HIGH" in out

    def test_contains_severity_counts(self):
        out = format_risk_report(self._report())
        assert "HIGH" in out
        assert "MEDIUM" in out
        assert "LOW" in out

    def test_contains_category_name(self):
        out = format_risk_report(self._report())
        assert "jailbreak" in out

    def test_high_risk_warning(self):
        out = format_risk_report(self._report(risk_level="high"))
        assert "HIGH RISK" in out or "critical" in out.lower()

    def test_medium_risk_message(self):
        out = format_risk_report(self._report(risk_level="medium"))
        assert "MODERATE" in out or "review" in out.lower()

    def test_low_risk_message(self):
        out = format_risk_report(self._report(risk_level="low"))
        assert "LOW RISK" in out or "safe" in out.lower()

    def test_contains_header(self):
        out = format_risk_report(self._report())
        assert "RISK ASSESSMENT" in out

    def test_returns_string(self):
        assert isinstance(format_risk_report(self._report()), str)

    def test_empty_breakdown(self):
        out = format_risk_report(self._report(category_breakdown={}))
        assert "RISK ASSESSMENT" in out  # should still work


# ═══════════════════════════════════════════════
#  display_risk_report
# ═══════════════════════════════════════════════

class TestDisplayRiskReport:

    def test_calls_print(self):
        r = RiskReport(
            risk_score=50, risk_level="medium", raw_score=60.0,
            summary={"high": 1, "medium": 1, "low": 1},
            category_breakdown={}, total_findings=3,
        )
        with patch("builtins.print") as mp:
            display_risk_report(r)
            assert mp.called
