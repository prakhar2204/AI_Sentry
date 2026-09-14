"""
Tests for core/consent.py

Run with:
    pytest tests/test_consent.py -v
"""

import sys
from io import StringIO
from unittest.mock import patch

import pytest

from core.consent import get_user_consent


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _run_with_input(*responses: str) -> bool:
    """
    Call get_user_consent() with a sequence of simulated user inputs.
    Returns the bool result, or raises SystemExit if consent exhausted.
    """
    inputs = iter(responses)
    with patch("builtins.input", side_effect=inputs):
        return get_user_consent()


# ─────────────────────────────────────────────
#  Happy path
# ─────────────────────────────────────────────

def test_consent_granted_on_yes(capsys):
    """User types 'yes' → function returns True."""
    result = _run_with_input("yes")
    assert result is True


def test_consent_granted_case_insensitive(capsys):
    """Input is lowercased before comparison — 'YES' or 'Yes' both work."""
    for variant in ("YES", "Yes", "yEs", " yes ", "yes\n"):
        # strip() is applied inside get_user_consent()
        result = _run_with_input(variant.strip())
        assert result is True, f"Failed for input {variant!r}"


def test_consent_declined_on_no(capsys):
    """User types 'no' → function returns False."""
    result = _run_with_input("no")
    assert result is False


def test_consent_declined_case_insensitive(capsys):
    """'NO', 'No', 'nO' all result in False."""
    for variant in ("NO", "No", "nO"):
        result = _run_with_input(variant)
        assert result is False, f"Failed for input {variant!r}"


# ─────────────────────────────────────────────
#  Invalid input handling
# ─────────────────────────────────────────────

def test_invalid_then_yes(capsys):
    """One invalid response, then 'yes' → returns True."""
    result = _run_with_input("maybe", "yes")
    assert result is True


def test_invalid_then_no(capsys):
    """One invalid response, then 'no' → returns False."""
    result = _run_with_input("sure", "no")
    assert result is False


def test_invalid_twice_then_yes(capsys):
    """Two invalid responses, then 'yes' → still returns True (3 retries allowed)."""
    result = _run_with_input("hmm", "ok", "yes")
    assert result is True


def test_too_many_invalid_inputs_exits(capsys):
    """
    Exhausting all retry attempts calls sys.exit(0).
    MAX_RETRIES = 3, so three invalid inputs trigger exit.
    """
    with pytest.raises(SystemExit) as exc_info:
        _run_with_input("maybe", "perhaps", "let me think")
    assert exc_info.value.code == 0


# ─────────────────────────────────────────────
#  Non-interactive environments
# ─────────────────────────────────────────────

def test_eof_returns_false(capsys):
    """EOFError (non-interactive pipe / redirected stdin) → returns False."""
    with patch("builtins.input", side_effect=EOFError):
        result = get_user_consent()
    assert result is False


def test_keyboard_interrupt_returns_false(capsys):
    """Ctrl-C during prompt → returns False (no exception propagated)."""
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        result = get_user_consent()
    assert result is False


# ─────────────────────────────────────────────
#  Output content checks
# ─────────────────────────────────────────────

def test_notice_contains_key_phrases(capsys):
    """The responsible-use notice must mention authorization and legal compliance."""
    _run_with_input("no")
    captured = capsys.readouterr()
    assert "AUTHORIZATION" in captured.out
    assert "LEGAL COMPLIANCE" in captured.out
    assert "are not" in captured.out.lower()  # notice says "are not\n     responsible"


def test_decline_message_shown_on_no(capsys):
    """Declining shows a clear cancellation message."""
    _run_with_input("no")
    captured = capsys.readouterr()
    assert "cancelled" in captured.out.lower() or "no action" in captured.out.lower()


def test_acceptance_message_shown_on_yes(capsys):
    """Accepting shows a clear confirmation message."""
    _run_with_input("yes")
    captured = capsys.readouterr()
    assert "consent" in captured.out.lower() or "proceeding" in captured.out.lower()
