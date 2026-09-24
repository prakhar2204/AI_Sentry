"""
Tests for core/manifest_display.py -- Phase 2d + 3a updates

Covers:
  - display_manifest()          -- output content verification
  - display_manifest_compact()  -- compact format
  - confirm_execution()         -- yes/no prompt, invalid input handling
  - display_and_confirm()       -- combined wrapper with estimation

Run with:
    python -m pytest tests/test_manifest_display.py -v
"""

import pytest
from unittest.mock import patch, call
from io import StringIO

from core.manifest import create_manifest, ScanMode, ScanDepth, ProbeCategory
from core.estimator import estimate_scan
from core.manifest_display import (
    display_manifest,
    display_manifest_compact,
    confirm_execution,
    display_and_confirm,
    _DIVIDER,
    _MAX_ATTEMPTS,
)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _make_manifest(
    target="https://api.openai.com/v1",
    mode="api",
    scan_depth="standard",
    categories=None,
    output_dir="./reports",
    notes="",
):
    return create_manifest(
        target=target,
        mode=mode,
        scan_depth=scan_depth,
        categories=categories or ["prompt_injection", "jailbreak"],
        output_dir=output_dir,
        notes=notes,
    )



class TestDisplayManifest:

    def _capture(self, manifest, source="") -> str:
        """Run display_manifest and capture stdout."""
        est = estimate_scan(manifest)
        with patch("builtins.print") as mock_print:
            display_manifest(manifest, source=source, estimate=est)
            all_output = "\n".join(
                " ".join(str(a) for a in c.args)
                for c in mock_print.call_args_list
            )
        return all_output

    def test_contains_divider(self):
        m = _make_manifest()
        out = self._capture(m)
        assert _DIVIDER in out or "-" * 10 in out

    def test_contains_target(self):
        m = _make_manifest(target="https://api.openai.com/v1")
        out = self._capture(m)
        assert "https://api.openai.com/v1" in out

    def test_contains_mode(self):
        m = _make_manifest(mode="api")
        out = self._capture(m)
        assert "api" in out

    def test_contains_scan_depth(self):
        m = _make_manifest(scan_depth="quick")
        out = self._capture(m)
        assert "quick" in out

    def test_contains_all_selected_categories(self):
        m = _make_manifest(categories=["data_leak", "harmful_output"])
        out = self._capture(m)
        assert "data_leak" in out
        assert "harmful_output" in out

    def test_does_not_contain_unselected_categories(self):
        m = _make_manifest(categories=["jailbreak"])
        out = self._capture(m)
        # Only jailbreak should appear; others should not
        assert "prompt_injection" not in out
        assert "data_leak" not in out
        assert "harmful_output" not in out

    def test_contains_output_dir(self):
        m = _make_manifest(output_dir="./my-custom-dir")
        out = self._capture(m)
        assert "my-custom-dir" in out

    def test_contains_manifest_id(self):
        m = _make_manifest()
        out = self._capture(m)
        assert m.manifest_id in out

    def test_contains_probe_estimate(self):
        m = _make_manifest()
        out = self._capture(m)
        # Should contain a number after ~
        assert "~" in out

    def test_source_label_included_when_provided(self):
        m = _make_manifest()
        out = self._capture(m, source="merged")
        assert "merged" in out

    def test_source_label_omitted_when_empty(self):
        m = _make_manifest()
        out = self._capture(m, source="")
        assert "Config source" not in out

    def test_notes_included_when_present(self):
        m = _make_manifest(notes="CI run 42")
        out = self._capture(m)
        assert "CI run 42" in out

    def test_notes_omitted_when_empty(self):
        m = _make_manifest(notes="")
        out = self._capture(m)
        assert "Notes" not in out

    def test_source_file_included_when_set(self):
        m = _make_manifest()
        m.source_file = "/path/to/manifest.json"
        out = self._capture(m)
        assert "manifest.json" in out

    def test_source_file_omitted_when_not_set(self):
        m = _make_manifest()
        m.source_file = ""
        out = self._capture(m)
        assert "Config file" not in out

    def test_calls_print(self):
        """display_manifest must actually call print (not return string silently)."""
        m = _make_manifest()
        with patch("builtins.print") as mock_print:
            display_manifest(m)
            assert mock_print.called

    def test_scan_configuration_header_present(self):
        m = _make_manifest()
        out = self._capture(m)
        assert "SCAN CONFIGURATION" in out

    def test_all_four_categories_displayed(self):
        m = _make_manifest(
            categories=["prompt_injection", "jailbreak", "data_leak", "harmful_output"]
        )
        out = self._capture(m)
        for cat in ("prompt_injection", "jailbreak", "data_leak", "harmful_output"):
            assert cat in out

    def test_local_mode_displayed(self):
        m = _make_manifest(target="http://localhost:8080", mode="local")
        out = self._capture(m)
        assert "local" in out

    def test_deep_depth_displayed(self):
        m = _make_manifest(scan_depth="deep")
        out = self._capture(m)
        assert "deep" in out


# ─────────────────────────────────────────────
#  display_manifest_compact
# ─────────────────────────────────────────────

class TestDisplayManifestCompact:

    def _capture(self, manifest) -> str:
        with patch("builtins.print") as mock_print:
            display_manifest_compact(manifest)
            return "\n".join(
                " ".join(str(a) for a in c.args)
                for c in mock_print.call_args_list
            )

    def test_contains_target(self):
        m = _make_manifest(target="https://api.openai.com/v1")
        assert "https://api.openai.com/v1" in self._capture(m)

    def test_contains_mode(self):
        assert "api" in self._capture(_make_manifest())

    def test_contains_depth(self):
        assert "standard" in self._capture(_make_manifest())

    def test_contains_categories(self):
        m = _make_manifest(categories=["jailbreak"])
        assert "jailbreak" in self._capture(m)


# ─────────────────────────────────────────────
#  confirm_execution
# ─────────────────────────────────────────────

class TestConfirmExecution:

    # ── User confirms ──────────────────────────

    def test_yes_returns_true(self):
        with patch("builtins.input", return_value="yes"):
            with patch("builtins.print"):
                assert confirm_execution() is True

    def test_y_returns_true(self):
        with patch("builtins.input", return_value="y"):
            with patch("builtins.print"):
                assert confirm_execution() is True

    def test_yes_uppercase_returns_true(self):
        with patch("builtins.input", return_value="YES"):
            with patch("builtins.print"):
                assert confirm_execution() is True

    def test_yes_mixed_case_returns_true(self):
        with patch("builtins.input", return_value="Yes"):
            with patch("builtins.print"):
                assert confirm_execution() is True

    # ── User declines ──────────────────────────

    def test_no_returns_false(self):
        with patch("builtins.input", return_value="no"):
            with patch("builtins.print"):
                assert confirm_execution() is False

    def test_n_returns_false(self):
        with patch("builtins.input", return_value="n"):
            with patch("builtins.print"):
                assert confirm_execution() is False

    def test_no_uppercase_returns_false(self):
        with patch("builtins.input", return_value="NO"):
            with patch("builtins.print"):
                assert confirm_execution() is False

    # ── Invalid then valid ─────────────────────

    def test_invalid_then_yes_returns_true(self):
        with patch("builtins.input", side_effect=["maybe", "yes"]):
            with patch("builtins.print"):
                assert confirm_execution() is True

    def test_invalid_then_no_returns_false(self):
        with patch("builtins.input", side_effect=["oops", "no"]):
            with patch("builtins.print"):
                assert confirm_execution() is False

    def test_two_invalid_then_yes_returns_true(self):
        with patch("builtins.input", side_effect=["bad", "nope", "yes"]):
            with patch("builtins.print"):
                assert confirm_execution() is True

    # ── Max attempts ───────────────────────────

    def test_max_invalid_inputs_returns_false(self):
        """After _MAX_ATTEMPTS invalid inputs, should return False."""
        invalid_inputs = ["bad"] * _MAX_ATTEMPTS
        with patch("builtins.input", side_effect=invalid_inputs):
            with patch("builtins.print"):
                assert confirm_execution() is False

    def test_does_not_loop_beyond_max_attempts(self):
        """Should ask at most _MAX_ATTEMPTS times then give up."""
        call_count = []
        def counting_input(prompt=""):
            call_count.append(1)
            return "invalid"

        with patch("builtins.input", side_effect=counting_input):
            with patch("builtins.print"):
                confirm_execution()
        assert len(call_count) == _MAX_ATTEMPTS

    # ── Ctrl-C / EOF ───────────────────────────

    def test_keyboard_interrupt_returns_false(self):
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with patch("builtins.print"):
                assert confirm_execution() is False

    def test_eof_error_returns_false(self):
        with patch("builtins.input", side_effect=EOFError):
            with patch("builtins.print"):
                assert confirm_execution() is False

    # ── Prompt text ────────────────────────────

    def test_prompt_shows_yes_no_options(self):
        """The input prompt must include 'yes' and 'no'."""
        prompts_seen = []
        def capture_input(prompt=""):
            prompts_seen.append(prompt)
            return "yes"

        with patch("builtins.input", side_effect=capture_input):
            with patch("builtins.print"):
                confirm_execution()

        assert any("yes" in p.lower() and "no" in p.lower() for p in prompts_seen)

    def test_confirmation_message_printed_on_yes(self):
        """On 'yes', should print a confirmation message, not proceed silently."""
        printed = []
        with patch("builtins.input", return_value="yes"):
            with patch("builtins.print", side_effect=lambda *a, **k: printed.append(str(a))):
                confirm_execution()
        combined = " ".join(printed).lower()
        assert "confirm" in combined or "start" in combined or "proceeding" in combined or "starting" in combined

    def test_cancellation_message_printed_on_no(self):
        """On 'no', should print a cancellation message."""
        printed = []
        with patch("builtins.input", return_value="no"):
            with patch("builtins.print", side_effect=lambda *a, **k: printed.append(str(a))):
                confirm_execution()
        combined = " ".join(printed).lower()
        assert "cancel" in combined or "abort" in combined


# ─────────────────────────────────────────────
#  display_and_confirm
# ─────────────────────────────────────────────

class TestDisplayAndConfirm:

    def test_returns_true_when_user_confirms(self):
        m = _make_manifest()
        with patch("builtins.print"):
            with patch("builtins.input", return_value="yes"):
                assert display_and_confirm(m) is True

    def test_returns_false_when_user_declines(self):
        m = _make_manifest()
        with patch("builtins.print"):
            with patch("builtins.input", return_value="no"):
                assert display_and_confirm(m) is False

    def test_display_called_before_confirm(self):
        """display_manifest must run before the confirmation prompt."""
        call_order = []

        m = _make_manifest()
        original_print = print
        original_input = input

        def track_print(*a, **k):
            call_order.append("print")

        def track_input(prompt=""):
            call_order.append("input")
            return "no"

        with patch("builtins.print", side_effect=track_print):
            with patch("builtins.input", side_effect=track_input):
                display_and_confirm(m)

        # print must appear before input in the call order
        assert "print" in call_order
        assert "input" in call_order
        assert call_order.index("print") < call_order.index("input")

    def test_source_passed_to_display(self):
        """Source label should appear in output when provided."""
        m = _make_manifest()
        printed = []
        with patch("builtins.print", side_effect=lambda *a, **k: printed.append(str(a))):
            with patch("builtins.input", return_value="no"):
                display_and_confirm(m, source="merged")
        combined = " ".join(printed)
        assert "merged" in combined

    def test_does_not_modify_manifest(self):
        """display_and_confirm must never change the manifest."""
        m = _make_manifest()
        original_target = m.target
        original_depth  = m.scan_depth
        original_cats   = list(m.categories)

        with patch("builtins.print"):
            with patch("builtins.input", return_value="no"):
                display_and_confirm(m)

        assert m.target == original_target
        assert m.scan_depth == original_depth
        assert m.categories == original_cats

    def test_keyboard_interrupt_returns_false(self):
        m = _make_manifest()
        with patch("builtins.print"):
            with patch("builtins.input", side_effect=KeyboardInterrupt):
                assert display_and_confirm(m) is False
