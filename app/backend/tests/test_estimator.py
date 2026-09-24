"""
Tests for core/estimator.py -- Phase 3a

Covers:
  - ScanEstimate dataclass
  - calculate_probes_per_category()
  - calculate_total_probes()
  - calculate_time()
  - calculate_cost()
  - estimate_scan()  -- orchestrator
  - format_estimation()
  - display_estimation()
  - Depth multiplier correctness
  - Mode-dependent time/cost behavior

Run with:
    python -m pytest tests/test_estimator.py -v
"""

import pytest
from unittest.mock import patch

from core.manifest import create_manifest, ScanMode, ScanDepth, ProbeCategory
from core.estimator import (
    ScanEstimate,
    calculate_probes_per_category,
    calculate_total_probes,
    calculate_time,
    calculate_cost,
    estimate_scan,
    format_estimation,
    display_estimation,
    BASE_PROBES_PER_CATEGORY,
    DEPTH_MULTIPLIERS,
    TIME_PER_PROBE,
    COST_PER_PROBE,
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


# ─────────────────────────────────────────────
#  Constants validation
# ─────────────────────────────────────────────

class TestConstants:

    def test_all_four_categories_have_base_probes(self):
        for cat in ("prompt_injection", "jailbreak", "data_leak", "harmful_output"):
            assert cat in BASE_PROBES_PER_CATEGORY
            assert BASE_PROBES_PER_CATEGORY[cat] > 0

    def test_all_three_depths_have_multipliers(self):
        for depth in ("quick", "standard", "deep"):
            assert depth in DEPTH_MULTIPLIERS
            assert DEPTH_MULTIPLIERS[depth] > 0

    def test_standard_multiplier_is_1(self):
        assert DEPTH_MULTIPLIERS["standard"] == 1.0

    def test_quick_multiplier_is_half(self):
        assert DEPTH_MULTIPLIERS["quick"] == 0.5

    def test_deep_multiplier_is_double(self):
        assert DEPTH_MULTIPLIERS["deep"] == 2.0

    def test_api_time_per_probe_is_1_5(self):
        assert TIME_PER_PROBE["api"] == 1.5

    def test_local_time_per_probe_is_0_8(self):
        assert TIME_PER_PROBE["local"] == 0.8

    def test_api_cost_is_0_0005(self):
        assert COST_PER_PROBE["api"] == 0.0005

    def test_local_cost_is_zero(self):
        assert COST_PER_PROBE["local"] == 0.0


# ─────────────────────────────────────────────
#  ScanEstimate
# ─────────────────────────────────────────────

class TestScanEstimate:

    def test_is_frozen(self):
        est = ScanEstimate(
            total_probes=100, estimated_time_sec=150, estimated_time_min=2.5,
            estimated_cost_usd=0.05, per_category={"jailbreak": 100},
            depth_multiplier=1.0, mode="api",
        )
        with pytest.raises(AttributeError):
            est.total_probes = 200

    def test_to_dict_contains_all_fields(self):
        est = ScanEstimate(
            total_probes=100, estimated_time_sec=150, estimated_time_min=2.5,
            estimated_cost_usd=0.05, per_category={"jailbreak": 100},
            depth_multiplier=1.0, mode="api",
        )
        d = est.to_dict()
        assert d["total_probes"] == 100
        assert d["estimated_time_sec"] == 150
        assert d["estimated_time_min"] == 2.5
        assert d["estimated_cost_usd"] == 0.05
        assert d["per_category"] == {"jailbreak": 100}
        assert d["depth_multiplier"] == 1.0
        assert d["mode"] == "api"

    def test_to_dict_returns_plain_dict(self):
        est = ScanEstimate(
            total_probes=10, estimated_time_sec=15, estimated_time_min=0.2,
            estimated_cost_usd=0.005, per_category={"jailbreak": 10},
            depth_multiplier=1.0, mode="api",
        )
        d = est.to_dict()
        assert isinstance(d, dict)
        assert isinstance(d["per_category"], dict)


# ─────────────────────────────────────────────
#  calculate_probes_per_category
# ─────────────────────────────────────────────

class TestCalculateProbesPerCategory:

    def test_standard_depth_returns_base_values(self):
        cats = [ProbeCategory.JAILBREAK]
        result = calculate_probes_per_category(cats, ScanDepth.STANDARD)
        assert result["jailbreak"] == BASE_PROBES_PER_CATEGORY["jailbreak"]

    def test_quick_depth_halves_probes(self):
        cats = [ProbeCategory.JAILBREAK]
        result = calculate_probes_per_category(cats, ScanDepth.QUICK)
        expected = int(BASE_PROBES_PER_CATEGORY["jailbreak"] * 0.5)
        assert result["jailbreak"] == expected

    def test_deep_depth_doubles_probes(self):
        cats = [ProbeCategory.JAILBREAK]
        result = calculate_probes_per_category(cats, ScanDepth.DEEP)
        expected = int(BASE_PROBES_PER_CATEGORY["jailbreak"] * 2.0)
        assert result["jailbreak"] == expected

    def test_multiple_categories(self):
        cats = [ProbeCategory.PROMPT_INJECTION, ProbeCategory.DATA_LEAK]
        result = calculate_probes_per_category(cats, ScanDepth.STANDARD)
        assert "prompt_injection" in result
        assert "data_leak" in result
        assert result["prompt_injection"] == BASE_PROBES_PER_CATEGORY["prompt_injection"]
        assert result["data_leak"] == BASE_PROBES_PER_CATEGORY["data_leak"]

    def test_all_four_categories(self):
        cats = list(ProbeCategory)
        result = calculate_probes_per_category(cats, ScanDepth.STANDARD)
        assert len(result) == 4

    def test_returns_dict_of_ints(self):
        cats = [ProbeCategory.HARMFUL_OUTPUT]
        result = calculate_probes_per_category(cats, ScanDepth.QUICK)
        for v in result.values():
            assert isinstance(v, int)

    def test_minimum_one_probe_per_category(self):
        """Even at extreme fractional multipliers, always at least 1 probe."""
        cats = [ProbeCategory.JAILBREAK]
        result = calculate_probes_per_category(cats, ScanDepth.QUICK)
        for v in result.values():
            assert v >= 1


# ─────────────────────────────────────────────
#  calculate_total_probes
# ─────────────────────────────────────────────

class TestCalculateTotalProbes:

    def test_sums_values(self):
        per_cat = {"jailbreak": 50, "data_leak": 55}
        assert calculate_total_probes(per_cat) == 105

    def test_single_category(self):
        per_cat = {"prompt_injection": 45}
        assert calculate_total_probes(per_cat) == 45

    def test_empty_dict_returns_zero(self):
        assert calculate_total_probes({}) == 0


# ─────────────────────────────────────────────
#  calculate_time
# ─────────────────────────────────────────────

class TestCalculateTime:

    def test_api_mode_uses_1_5_seconds(self):
        sec, _ = calculate_time(100, ScanMode.API)
        assert sec == 150  # 100 * 1.5

    def test_local_mode_uses_0_8_seconds(self):
        sec, _ = calculate_time(100, ScanMode.LOCAL)
        assert sec == 80  # 100 * 0.8

    def test_minutes_calculated_correctly(self):
        _, mins = calculate_time(100, ScanMode.API)
        assert mins == 2.5  # 150 / 60

    def test_zero_probes_returns_zero(self):
        sec, mins = calculate_time(0, ScanMode.API)
        assert sec == 0
        assert mins == 0.0

    def test_returns_int_seconds(self):
        sec, _ = calculate_time(10, ScanMode.API)
        assert isinstance(sec, int)

    def test_returns_float_minutes(self):
        _, mins = calculate_time(10, ScanMode.API)
        assert isinstance(mins, float)


# ─────────────────────────────────────────────
#  calculate_cost
# ─────────────────────────────────────────────

class TestCalculateCost:

    def test_api_mode_costs_money(self):
        cost = calculate_cost(100, ScanMode.API)
        assert cost == 0.05  # 100 * 0.0005

    def test_local_mode_costs_zero(self):
        cost = calculate_cost(100, ScanMode.LOCAL)
        assert cost == 0.0

    def test_zero_probes_costs_zero(self):
        assert calculate_cost(0, ScanMode.API) == 0.0

    def test_api_cost_is_deterministic(self):
        a = calculate_cost(200, ScanMode.API)
        b = calculate_cost(200, ScanMode.API)
        assert a == b


# ─────────────────────────────────────────────
#  estimate_scan -- orchestrator
# ─────────────────────────────────────────────

class TestEstimateScan:

    def test_returns_scan_estimate(self):
        m = _make_manifest()
        est = estimate_scan(m)
        assert isinstance(est, ScanEstimate)

    def test_total_probes_is_positive(self):
        m = _make_manifest()
        assert estimate_scan(m).total_probes > 0

    def test_per_category_keys_match_manifest(self):
        m = _make_manifest(categories=["jailbreak", "data_leak"])
        est = estimate_scan(m)
        assert set(est.per_category.keys()) == {"jailbreak", "data_leak"}

    def test_total_equals_sum_of_per_category(self):
        m = _make_manifest(categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"])
        est = estimate_scan(m)
        assert est.total_probes == sum(est.per_category.values())

    def test_time_sec_is_positive(self):
        m = _make_manifest()
        assert estimate_scan(m).estimated_time_sec > 0

    def test_cost_is_positive_for_api(self):
        m = _make_manifest(mode="api")
        assert estimate_scan(m).estimated_cost_usd > 0

    def test_cost_is_zero_for_local(self):
        m = _make_manifest(target="http://localhost:8080", mode="local")
        assert estimate_scan(m).estimated_cost_usd == 0.0

    def test_mode_echoed_in_result(self):
        m = _make_manifest(mode="api")
        assert estimate_scan(m).mode == "api"

    def test_depth_multiplier_echoed(self):
        m = _make_manifest(scan_depth="quick")
        assert estimate_scan(m).depth_multiplier == 0.5

    def test_quick_fewer_probes_than_standard(self):
        quick = estimate_scan(_make_manifest(scan_depth="quick"))
        standard = estimate_scan(_make_manifest(scan_depth="standard"))
        assert quick.total_probes < standard.total_probes

    def test_deep_more_probes_than_standard(self):
        standard = estimate_scan(_make_manifest(scan_depth="standard"))
        deep = estimate_scan(_make_manifest(scan_depth="deep"))
        assert deep.total_probes > standard.total_probes

    def test_more_categories_more_probes(self):
        one = estimate_scan(_make_manifest(categories=["jailbreak"]))
        four = estimate_scan(_make_manifest(
            categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"]
        ))
        assert four.total_probes > one.total_probes

    def test_local_faster_than_api(self):
        """Same probes, local should be faster."""
        cats = ["jailbreak"]
        api = estimate_scan(_make_manifest(mode="api", categories=cats))
        local = estimate_scan(_make_manifest(
            target="http://localhost:8080", mode="local", categories=cats
        ))
        assert local.estimated_time_sec < api.estimated_time_sec

    def test_deterministic(self):
        m = _make_manifest()
        a = estimate_scan(m)
        b = estimate_scan(m)
        assert a.total_probes == b.total_probes
        assert a.estimated_time_sec == b.estimated_time_sec
        assert a.estimated_cost_usd == b.estimated_cost_usd


# ─────────────────────────────────────────────
#  format_estimation
# ─────────────────────────────────────────────

class TestFormatEstimation:

    def _est(self, **kw) -> ScanEstimate:
        defaults = dict(
            total_probes=95, estimated_time_sec=142, estimated_time_min=2.4,
            estimated_cost_usd=0.0475, per_category={"jailbreak": 50, "prompt_injection": 45},
            depth_multiplier=1.0, mode="api",
        )
        defaults.update(kw)
        return ScanEstimate(**defaults)

    def test_contains_total_probes(self):
        s = format_estimation(self._est(total_probes=120))
        assert "120" in s

    def test_contains_time_minutes(self):
        s = format_estimation(self._est(estimated_time_min=2.4, estimated_time_sec=142))
        assert "2.4" in s

    def test_contains_time_seconds(self):
        s = format_estimation(self._est(estimated_time_sec=142))
        assert "142" in s

    def test_contains_cost_for_api(self):
        s = format_estimation(self._est(estimated_cost_usd=0.0475, mode="api"))
        assert "0.0475" in s

    def test_shows_zero_cost_for_local(self):
        s = format_estimation(self._est(estimated_cost_usd=0.0, mode="local"))
        assert "$0.00" in s
        assert "no API cost" in s

    def test_contains_per_category_breakdown(self):
        s = format_estimation(self._est(per_category={"jailbreak": 50, "data_leak": 55}))
        assert "jailbreak" in s
        assert "data_leak" in s
        assert "50" in s
        assert "55" in s

    def test_contains_scan_estimate_header(self):
        s = format_estimation(self._est())
        assert "SCAN ESTIMATE" in s

    def test_contains_divider(self):
        s = format_estimation(self._est())
        assert "-" * 10 in s

    def test_returns_string(self):
        assert isinstance(format_estimation(self._est()), str)

    def test_long_time_shows_hours(self):
        s = format_estimation(self._est(estimated_time_min=120.0, estimated_time_sec=7200))
        assert "hrs" in s or "hr" in s


# ─────────────────────────────────────────────
#  display_estimation
# ─────────────────────────────────────────────

class TestDisplayEstimation:

    def test_calls_print(self):
        est = ScanEstimate(
            total_probes=95, estimated_time_sec=142, estimated_time_min=2.4,
            estimated_cost_usd=0.0475, per_category={"jailbreak": 95},
            depth_multiplier=1.0, mode="api",
        )
        with patch("builtins.print") as mock_print:
            display_estimation(est)
            assert mock_print.called
