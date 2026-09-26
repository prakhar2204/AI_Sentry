"""
Tests for core/recommender.py -- Phase 5b

Covers:
  - get_actions_for_category()     -- action lookup + dedup
  - prioritize_recommendations()   -- sorting logic
  - generate_recommendations()     -- orchestrator
  - Recommendation / RecommendationReport dataclasses
  - format_recommendations()       -- CLI display
  - display_recommendations()      -- stdout output
  - Edge cases (empty report, unknown category, all severities)

Run with:
    python -m pytest tests/test_recommender.py -v
"""

import pytest
from unittest.mock import patch

from core.scorer import (
    RiskReport,
    CategoryBreakdown,
)
from core.recommender import (
    get_actions_for_category,
    prioritize_recommendations,
    generate_recommendations,
    Recommendation,
    RecommendationReport,
    format_recommendations,
    display_recommendations,
    _ACTION_DATABASE,
)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _bd(category="jailbreak", count=2, max_severity="high",
        avg_confidence=0.75, raw_score=12.0):
    return CategoryBreakdown(
        category=category, count=count, max_severity=max_severity,
        avg_confidence=avg_confidence, raw_score=raw_score,
    )


def _report(breakdown=None, risk_level="medium", risk_score=50):
    if breakdown is None:
        breakdown = {"jailbreak": _bd()}
    return RiskReport(
        risk_score=risk_score,
        risk_level=risk_level,
        raw_score=60.0,
        summary={"high": 1, "medium": 1, "low": 1},
        category_breakdown=breakdown,
        total_findings=3,
    )


def _rec(category="jailbreak", severity="high", actions=("action1",)):
    return Recommendation(category=category, severity=severity, actions=actions)


# ═══════════════════════════════════════════════
#  Action database coverage
# ═══════════════════════════════════════════════

class TestActionDatabase:

    def test_all_four_categories_present(self):
        expected = {"prompt_injection", "jailbreak", "data_leak", "harmful_output"}
        assert expected == set(_ACTION_DATABASE.keys())

    def test_each_category_has_all_three_severities(self):
        for cat, tiers in _ACTION_DATABASE.items():
            assert "high" in tiers, f"{cat} missing 'high'"
            assert "medium" in tiers, f"{cat} missing 'medium'"
            assert "low" in tiers, f"{cat} missing 'low'"

    def test_each_tier_has_at_least_two_actions(self):
        for cat, tiers in _ACTION_DATABASE.items():
            for sev, actions in tiers.items():
                assert len(actions) >= 2, f"{cat}/{sev} has < 2 actions"

    def test_high_tier_has_most_actions(self):
        for cat, tiers in _ACTION_DATABASE.items():
            assert len(tiers["high"]) >= len(tiers["medium"]), cat
            assert len(tiers["high"]) >= len(tiers["low"]), cat


# ═══════════════════════════════════════════════
#  get_actions_for_category
# ═══════════════════════════════════════════════

class TestGetActionsForCategory:

    def test_returns_list(self):
        result = get_actions_for_category("jailbreak", "high")
        assert isinstance(result, list)

    def test_high_returns_actions(self):
        result = get_actions_for_category("prompt_injection", "high")
        assert len(result) >= 3

    def test_medium_returns_actions(self):
        result = get_actions_for_category("data_leak", "medium")
        assert len(result) >= 2

    def test_low_returns_actions(self):
        result = get_actions_for_category("harmful_output", "low")
        assert len(result) >= 2

    def test_unknown_category_returns_generic(self):
        result = get_actions_for_category("unknown_cat", "high")
        assert len(result) == 1
        assert "unknown_cat" in result[0]

    def test_unknown_severity_returns_generic(self):
        result = get_actions_for_category("jailbreak", "critical")
        assert len(result) == 1

    def test_actions_are_strings(self):
        for action in get_actions_for_category("jailbreak", "high"):
            assert isinstance(action, str)
            assert len(action) > 10  # meaningful text

    def test_no_duplicates_in_result(self):
        result = get_actions_for_category("prompt_injection", "high")
        assert len(result) == len(set(result))

    def test_deterministic(self):
        a = get_actions_for_category("data_leak", "high")
        b = get_actions_for_category("data_leak", "high")
        assert a == b


# ═══════════════════════════════════════════════
#  prioritize_recommendations
# ═══════════════════════════════════════════════

class TestPrioritizeRecommendations:

    def test_high_before_medium(self):
        recs = [
            _rec(category="b", severity="medium"),
            _rec(category="a", severity="high"),
        ]
        result = prioritize_recommendations(recs)
        assert result[0].severity == "high"
        assert result[1].severity == "medium"

    def test_medium_before_low(self):
        recs = [
            _rec(category="b", severity="low"),
            _rec(category="a", severity="medium"),
        ]
        result = prioritize_recommendations(recs)
        assert result[0].severity == "medium"

    def test_same_severity_sorted_alphabetically(self):
        recs = [
            _rec(category="jailbreak", severity="high"),
            _rec(category="data_leak", severity="high"),
        ]
        result = prioritize_recommendations(recs)
        assert result[0].category == "data_leak"
        assert result[1].category == "jailbreak"

    def test_full_sort_order(self):
        recs = [
            _rec(category="z", severity="low"),
            _rec(category="a", severity="high"),
            _rec(category="m", severity="medium"),
            _rec(category="b", severity="high"),
        ]
        result = prioritize_recommendations(recs)
        assert [r.severity for r in result] == ["high", "high", "medium", "low"]
        assert result[0].category == "a"
        assert result[1].category == "b"

    def test_empty_list(self):
        assert prioritize_recommendations([]) == []

    def test_single_item(self):
        recs = [_rec(severity="medium")]
        result = prioritize_recommendations(recs)
        assert len(result) == 1

    def test_returns_list(self):
        result = prioritize_recommendations([_rec()])
        assert isinstance(result, list)


# ═══════════════════════════════════════════════
#  Recommendation dataclass
# ═══════════════════════════════════════════════

class TestRecommendation:

    def test_is_frozen(self):
        r = _rec()
        with pytest.raises(AttributeError):
            r.category = "other"

    def test_to_dict(self):
        r = _rec(category="jailbreak", severity="high", actions=("a1", "a2"))
        d = r.to_dict()
        assert d["category"] == "jailbreak"
        assert d["severity"] == "high"
        assert d["actions"] == ["a1", "a2"]  # list, not tuple

    def test_actions_is_tuple(self):
        r = _rec(actions=("a", "b"))
        assert isinstance(r.actions, tuple)


# ═══════════════════════════════════════════════
#  RecommendationReport dataclass
# ═══════════════════════════════════════════════

class TestRecommendationReport:

    def test_is_frozen(self):
        rr = RecommendationReport(
            recommendations=(), risk_level="low",
            risk_score=10, total_actions=0,
        )
        with pytest.raises(AttributeError):
            rr.risk_score = 99

    def test_to_dict(self):
        r = _rec(category="jailbreak", severity="high", actions=("a1",))
        rr = RecommendationReport(
            recommendations=(r,), risk_level="high",
            risk_score=80, total_actions=1,
        )
        d = rr.to_dict()
        assert d["risk_level"] == "high"
        assert d["risk_score"] == 80
        assert d["total_actions"] == 1
        assert len(d["recommendations"]) == 1

    def test_empty_recommendations(self):
        rr = RecommendationReport(
            recommendations=(), risk_level="low",
            risk_score=0, total_actions=0,
        )
        d = rr.to_dict()
        assert d["recommendations"] == []


# ═══════════════════════════════════════════════
#  generate_recommendations -- orchestrator
# ═══════════════════════════════════════════════

class TestGenerateRecommendations:

    def test_returns_report(self):
        report = generate_recommendations(_report())
        assert isinstance(report, RecommendationReport)

    def test_single_category(self):
        report = generate_recommendations(_report(
            breakdown={"jailbreak": _bd(max_severity="high")}
        ))
        assert len(report.recommendations) == 1
        assert report.recommendations[0].category == "jailbreak"

    def test_multiple_categories(self):
        report = generate_recommendations(_report(
            breakdown={
                "jailbreak": _bd(category="jailbreak", max_severity="high"),
                "data_leak": _bd(category="data_leak", max_severity="medium"),
            }
        ))
        assert len(report.recommendations) == 2

    def test_sorted_by_severity(self):
        report = generate_recommendations(_report(
            breakdown={
                "data_leak": _bd(category="data_leak", max_severity="low"),
                "jailbreak": _bd(category="jailbreak", max_severity="high"),
                "harmful_output": _bd(category="harmful_output", max_severity="medium"),
            }
        ))
        sevs = [r.severity for r in report.recommendations]
        assert sevs == ["high", "medium", "low"]

    def test_echoes_risk_level(self):
        report = generate_recommendations(_report(risk_level="high"))
        assert report.risk_level == "high"

    def test_echoes_risk_score(self):
        report = generate_recommendations(_report(risk_score=78))
        assert report.risk_score == 78

    def test_total_actions_counted(self):
        report = generate_recommendations(_report(
            breakdown={"jailbreak": _bd(max_severity="high")}
        ))
        assert report.total_actions == len(report.recommendations[0].actions)
        assert report.total_actions >= 3

    def test_empty_breakdown_produces_no_recs(self):
        report = generate_recommendations(_report(breakdown={}))
        assert len(report.recommendations) == 0
        assert report.total_actions == 0

    def test_deterministic(self):
        r = _report(breakdown={
            "jailbreak": _bd(max_severity="high"),
            "data_leak": _bd(category="data_leak", max_severity="medium"),
        })
        a = generate_recommendations(r)
        b = generate_recommendations(r)
        assert a.total_actions == b.total_actions
        for ra, rb in zip(a.recommendations, b.recommendations):
            assert ra.category == rb.category
            assert ra.actions == rb.actions

    def test_all_four_categories(self):
        breakdown = {
            "prompt_injection": _bd(category="prompt_injection", max_severity="high"),
            "jailbreak": _bd(category="jailbreak", max_severity="high"),
            "data_leak": _bd(category="data_leak", max_severity="medium"),
            "harmful_output": _bd(category="harmful_output", max_severity="low"),
        }
        report = generate_recommendations(_report(breakdown=breakdown))
        assert len(report.recommendations) == 4
        cats = {r.category for r in report.recommendations}
        assert cats == {"prompt_injection", "jailbreak", "data_leak", "harmful_output"}

    # Mock engine integration test
    def test_with_real_mock_engine_output(self):
        from core.manifest import create_manifest
        from core.mock_engine import MockEngine
        from core.scorer import generate_risk_report

        m = create_manifest(
            target="https://api.openai.com/v1", mode="api",
            scan_depth="standard",
            categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"],
        )
        result = MockEngine().run_scan(m)
        risk_report = generate_risk_report(result.findings)
        rec_report = generate_recommendations(risk_report)

        assert len(rec_report.recommendations) == 4
        assert rec_report.total_actions > 0
        assert rec_report.risk_level in ("low", "medium", "high")


# ═══════════════════════════════════════════════
#  format_recommendations
# ═══════════════════════════════════════════════

class TestFormatRecommendations:

    def _make_report(self, **kw):
        defaults = dict(
            recommendations=(
                _rec(category="jailbreak", severity="high",
                     actions=("Fix A", "Fix B")),
            ),
            risk_level="high", risk_score=80, total_actions=2,
        )
        defaults.update(kw)
        return RecommendationReport(**defaults)

    def test_contains_header(self):
        out = format_recommendations(self._make_report())
        assert "RECOMMENDATIONS" in out

    def test_contains_category(self):
        out = format_recommendations(self._make_report())
        assert "jailbreak" in out

    def test_contains_severity_tag(self):
        out = format_recommendations(self._make_report())
        assert "[HIGH]" in out

    def test_contains_actions(self):
        out = format_recommendations(self._make_report())
        assert "Fix A" in out
        assert "Fix B" in out

    def test_actions_numbered(self):
        out = format_recommendations(self._make_report())
        assert "1." in out
        assert "2." in out

    def test_contains_total_actions(self):
        out = format_recommendations(self._make_report(total_actions=5))
        assert "5" in out

    def test_empty_report(self):
        r = RecommendationReport(
            recommendations=(), risk_level="low",
            risk_score=0, total_actions=0,
        )
        out = format_recommendations(r)
        assert "No recommendations" in out or "no findings" in out.lower()

    def test_medium_severity_tag(self):
        r = self._make_report(
            recommendations=(
                _rec(category="data_leak", severity="medium", actions=("Fix",)),
            ),
        )
        out = format_recommendations(r)
        assert "[MED ]" in out

    def test_low_severity_tag(self):
        r = self._make_report(
            recommendations=(
                _rec(category="harmful_output", severity="low", actions=("Fix",)),
            ),
        )
        out = format_recommendations(r)
        assert "[LOW ]" in out

    def test_returns_string(self):
        assert isinstance(format_recommendations(self._make_report()), str)


# ═══════════════════════════════════════════════
#  display_recommendations
# ═══════════════════════════════════════════════

class TestDisplayRecommendations:

    def test_calls_print(self):
        r = RecommendationReport(
            recommendations=(), risk_level="low",
            risk_score=0, total_actions=0,
        )
        with patch("builtins.print") as mp:
            display_recommendations(r)
            assert mp.called
