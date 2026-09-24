"""
Tests for core/scan_guard.py -- Phase 3b

Covers:
  - GuardResult dataclass
  - is_heavy_scan()       -- threshold detection
  - display_warning()     -- output content verification
  - confirm_heavy_scan()  -- yes/no prompt with retries
  - check_scan_safety()   -- orchestrator (light vs heavy flow)

Run with:
    python -m pytest tests/test_scan_guard.py -v
"""

import pytest
from unittest.mock import patch

from core.estimator import ScanEstimate
from core.scan_guard import (
    GuardResult,
    is_heavy_scan,
    display_warning,
    confirm_heavy_scan,
    check_scan_safety,
    MAX_SAFE_PROBES,
    MAX_SAFE_TIME_SEC,
    _MAX_ATTEMPTS,
)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _make_estimate(
    total_probes=100,
    time_sec=150,
    time_min=2.5,
    cost=0.05,
    mode="api",
) -> ScanEstimate:
    return ScanEstimate(
        total_probes=total_probes,
        estimated_time_sec=time_sec,
        estimated_time_min=time_min,
        estimated_cost_usd=cost,
        per_category={"jailbreak": total_probes},
        depth_multiplier=1.0,
        mode=mode,
    )


def _light_estimate() -> ScanEstimate:
    """Well under both thresholds."""
    return _make_estimate(total_probes=50, time_sec=75, time_min=1.2)


def _heavy_probes_estimate() -> ScanEstimate:
    """Exceeds probe threshold only."""
    return _make_estimate(total_probes=400, time_sec=200, time_min=3.3)


def _heavy_time_estimate() -> ScanEstimate:
    """Exceeds time threshold only."""
    return _make_estimate(total_probes=200, time_sec=600, time_min=10.0)


def _heavy_both_estimate() -> ScanEstimate:
    """Exceeds both thresholds."""
    return _make_estimate(total_probes=500, time_sec=750, time_min=12.5)


def _boundary_probes_estimate() -> ScanEstimate:
    """Exactly at probe threshold (not exceeded)."""
    return _make_estimate(total_probes=MAX_SAFE_PROBES, time_sec=200, time_min=3.3)


def _boundary_time_estimate() -> ScanEstimate:
    """Exactly at time threshold (not exceeded)."""
    return _make_estimate(total_probes=100, time_sec=MAX_SAFE_TIME_SEC, time_min=5.0)


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

class TestConstants:

    def test_max_safe_probes_is_300(self):
        assert MAX_SAFE_PROBES == 300

    def test_max_safe_time_sec_is_300(self):
        assert MAX_SAFE_TIME_SEC == 300

    def test_max_attempts_is_3(self):
        assert _MAX_ATTEMPTS == 3


# ─────────────────────────────────────────────
#  GuardResult
# ─────────────────────────────────────────────

class TestGuardResult:

    def test_is_frozen(self):
        gr = GuardResult(
            is_heavy=True, probes_exceeded=True, time_exceeded=False,
            total_probes=400, time_sec=200, time_min=3.3,
        )
        with pytest.raises(AttributeError):
            gr.is_heavy = False

    def test_fields_accessible(self):
        gr = GuardResult(
            is_heavy=True, probes_exceeded=True, time_exceeded=True,
            total_probes=500, time_sec=750, time_min=12.5,
        )
        assert gr.is_heavy is True
        assert gr.probes_exceeded is True
        assert gr.time_exceeded is True
        assert gr.total_probes == 500
        assert gr.time_sec == 750
        assert gr.time_min == 12.5


# ─────────────────────────────────────────────
#  is_heavy_scan
# ─────────────────────────────────────────────

class TestIsHeavyScan:

    # Light scans
    def test_light_scan_not_heavy(self):
        result = is_heavy_scan(_light_estimate())
        assert result.is_heavy is False

    def test_light_scan_no_probes_exceeded(self):
        result = is_heavy_scan(_light_estimate())
        assert result.probes_exceeded is False

    def test_light_scan_no_time_exceeded(self):
        result = is_heavy_scan(_light_estimate())
        assert result.time_exceeded is False

    # Heavy: probes only
    def test_heavy_probes_only(self):
        result = is_heavy_scan(_heavy_probes_estimate())
        assert result.is_heavy is True
        assert result.probes_exceeded is True
        assert result.time_exceeded is False

    # Heavy: time only
    def test_heavy_time_only(self):
        result = is_heavy_scan(_heavy_time_estimate())
        assert result.is_heavy is True
        assert result.probes_exceeded is False
        assert result.time_exceeded is True

    # Heavy: both
    def test_heavy_both(self):
        result = is_heavy_scan(_heavy_both_estimate())
        assert result.is_heavy is True
        assert result.probes_exceeded is True
        assert result.time_exceeded is True

    # Boundary: exactly at threshold (NOT exceeded)
    def test_boundary_probes_not_heavy(self):
        """Exactly 300 probes should NOT trigger (> not >=)."""
        result = is_heavy_scan(_boundary_probes_estimate())
        assert result.probes_exceeded is False

    def test_boundary_time_not_heavy(self):
        """Exactly 300 seconds should NOT trigger (> not >=)."""
        result = is_heavy_scan(_boundary_time_estimate())
        assert result.time_exceeded is False

    def test_boundary_both_at_threshold_not_heavy(self):
        est = _make_estimate(total_probes=MAX_SAFE_PROBES, time_sec=MAX_SAFE_TIME_SEC)
        result = is_heavy_scan(est)
        assert result.is_heavy is False

    # One over boundary
    def test_one_over_probes_is_heavy(self):
        est = _make_estimate(total_probes=MAX_SAFE_PROBES + 1)
        result = is_heavy_scan(est)
        assert result.is_heavy is True
        assert result.probes_exceeded is True

    def test_one_over_time_is_heavy(self):
        est = _make_estimate(time_sec=MAX_SAFE_TIME_SEC + 1)
        result = is_heavy_scan(est)
        assert result.is_heavy is True
        assert result.time_exceeded is True

    # Echoed fields
    def test_echoes_total_probes(self):
        est = _make_estimate(total_probes=42)
        result = is_heavy_scan(est)
        assert result.total_probes == 42

    def test_echoes_time_sec(self):
        est = _make_estimate(time_sec=99)
        result = is_heavy_scan(est)
        assert result.time_sec == 99

    def test_echoes_time_min(self):
        est = _make_estimate(time_min=1.7)
        result = is_heavy_scan(est)
        assert result.time_min == 1.7

    # Returns correct type
    def test_returns_guard_result(self):
        result = is_heavy_scan(_light_estimate())
        assert isinstance(result, GuardResult)


# ─────────────────────────────────────────────
#  display_warning
# ─────────────────────────────────────────────

class TestDisplayWarning:

    def _capture(self, guard: GuardResult) -> str:
        with patch("builtins.print") as mock_print:
            display_warning(guard)
            return "\n".join(
                " ".join(str(a) for a in c.args)
                for c in mock_print.call_args_list
            )

    def test_contains_heavy_scan_header(self):
        guard = is_heavy_scan(_heavy_both_estimate())
        out = self._capture(guard)
        assert "HEAVY SCAN" in out

    def test_shows_probe_count_when_exceeded(self):
        guard = is_heavy_scan(_heavy_probes_estimate())
        out = self._capture(guard)
        assert "400" in out
        assert str(MAX_SAFE_PROBES) in out

    def test_shows_time_when_exceeded(self):
        guard = is_heavy_scan(_heavy_time_estimate())
        out = self._capture(guard)
        assert "10.0" in out

    def test_shows_both_when_both_exceeded(self):
        guard = is_heavy_scan(_heavy_both_estimate())
        out = self._capture(guard)
        assert "500" in out  # probes
        assert "12.5" in out  # time

    def test_mentions_both_thresholds_text(self):
        guard = is_heavy_scan(_heavy_both_estimate())
        out = self._capture(guard)
        assert "Both" in out or "both" in out

    def test_contains_safety_message(self):
        guard = is_heavy_scan(_heavy_probes_estimate())
        out = self._capture(guard)
        assert "safety" in out.lower() or "limit" in out.lower()

    def test_calls_print(self):
        guard = is_heavy_scan(_heavy_probes_estimate())
        with patch("builtins.print") as mock_print:
            display_warning(guard)
            assert mock_print.called


# ─────────────────────────────────────────────
#  confirm_heavy_scan
# ─────────────────────────────────────────────

class TestConfirmHeavyScan:

    # User confirms
    def test_yes_returns_true(self):
        with patch("builtins.input", return_value="yes"):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is True

    def test_y_returns_true(self):
        with patch("builtins.input", return_value="y"):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is True

    def test_yes_uppercase_returns_true(self):
        with patch("builtins.input", return_value="YES"):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is True

    # User declines
    def test_no_returns_false(self):
        with patch("builtins.input", return_value="no"):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is False

    def test_n_returns_false(self):
        with patch("builtins.input", return_value="n"):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is False

    # Invalid input handling
    def test_invalid_then_yes(self):
        with patch("builtins.input", side_effect=["maybe", "yes"]):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is True

    def test_invalid_then_no(self):
        with patch("builtins.input", side_effect=["oops", "no"]):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is False

    def test_two_invalid_then_yes(self):
        with patch("builtins.input", side_effect=["bad", "bad2", "yes"]):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is True

    # Max attempts
    def test_max_invalid_returns_false(self):
        invalids = ["bad"] * _MAX_ATTEMPTS
        with patch("builtins.input", side_effect=invalids):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is False

    def test_does_not_loop_beyond_max(self):
        call_count = []
        def counting_input(prompt=""):
            call_count.append(1)
            return "invalid"

        with patch("builtins.input", side_effect=counting_input):
            with patch("builtins.print"):
                confirm_heavy_scan()
        assert len(call_count) == _MAX_ATTEMPTS

    # Ctrl-C / EOF
    def test_keyboard_interrupt_returns_false(self):
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is False

    def test_eof_error_returns_false(self):
        with patch("builtins.input", side_effect=EOFError):
            with patch("builtins.print"):
                assert confirm_heavy_scan() is False

    # Prompt text
    def test_prompt_mentions_heavy(self):
        prompts = []
        def capture(prompt=""):
            prompts.append(prompt)
            return "no"
        with patch("builtins.input", side_effect=capture):
            with patch("builtins.print"):
                confirm_heavy_scan()
        assert any("heavy" in p.lower() for p in prompts)

    def test_confirmation_message_on_yes(self):
        printed = []
        with patch("builtins.input", return_value="yes"):
            with patch("builtins.print", side_effect=lambda *a, **k: printed.append(str(a))):
                confirm_heavy_scan()
        combined = " ".join(printed).lower()
        assert "confirm" in combined or "proceed" in combined

    def test_cancellation_message_on_no(self):
        printed = []
        with patch("builtins.input", return_value="no"):
            with patch("builtins.print", side_effect=lambda *a, **k: printed.append(str(a))):
                confirm_heavy_scan()
        combined = " ".join(printed).lower()
        assert "cancel" in combined


# ─────────────────────────────────────────────
#  check_scan_safety -- orchestrator
# ─────────────────────────────────────────────

class TestCheckScanSafety:

    # Light scans: no prompt, returns True
    def test_light_scan_returns_true_immediately(self):
        """Light scans should NOT show any warning or prompt."""
        est = _light_estimate()
        # No input mock needed -- should not call input()
        result = check_scan_safety(est)
        assert result is True

    def test_light_scan_does_not_call_input(self):
        est = _light_estimate()
        with patch("builtins.input") as mock_input:
            check_scan_safety(est)
            mock_input.assert_not_called()

    def test_boundary_does_not_call_input(self):
        est = _boundary_probes_estimate()
        with patch("builtins.input") as mock_input:
            check_scan_safety(est)
            mock_input.assert_not_called()

    # Heavy scans: warning + prompt
    def test_heavy_scan_confirmed_returns_true(self):
        est = _heavy_probes_estimate()
        with patch("builtins.print"):
            with patch("builtins.input", return_value="yes"):
                assert check_scan_safety(est) is True

    def test_heavy_scan_declined_returns_false(self):
        est = _heavy_probes_estimate()
        with patch("builtins.print"):
            with patch("builtins.input", return_value="no"):
                assert check_scan_safety(est) is False

    def test_heavy_time_confirmed_returns_true(self):
        est = _heavy_time_estimate()
        with patch("builtins.print"):
            with patch("builtins.input", return_value="yes"):
                assert check_scan_safety(est) is True

    def test_heavy_both_declined_returns_false(self):
        est = _heavy_both_estimate()
        with patch("builtins.print"):
            with patch("builtins.input", return_value="no"):
                assert check_scan_safety(est) is False

    def test_heavy_scan_shows_warning_before_prompt(self):
        """Warning must be displayed before the input prompt."""
        call_order = []
        def track_print(*a, **k):
            call_order.append("print")
        def track_input(prompt=""):
            call_order.append("input")
            return "no"

        est = _heavy_probes_estimate()
        with patch("builtins.print", side_effect=track_print):
            with patch("builtins.input", side_effect=track_input):
                check_scan_safety(est)

        assert "print" in call_order
        assert "input" in call_order
        assert call_order.index("print") < call_order.index("input")

    def test_heavy_scan_keyboard_interrupt_returns_false(self):
        est = _heavy_both_estimate()
        with patch("builtins.print"):
            with patch("builtins.input", side_effect=KeyboardInterrupt):
                assert check_scan_safety(est) is False
