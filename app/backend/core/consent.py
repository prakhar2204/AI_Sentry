"""
AI-SENTRY — Responsible Use Consent Gate
core/consent.py

Enforces user consent before any scan begins.
This module is the first gate in every scan workflow.
"""

import sys
import textwrap


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

_DIVIDER = "─" * 60

_RESPONSIBLE_USE_NOTICE = """
AI-SENTRY — RESPONSIBLE USE NOTICE

This tool performs active adversarial security testing on
AI language models. Before proceeding, you must confirm
that ALL of the following apply to your situation:

  1. AUTHORIZATION
     You own the target model or have explicit written
     permission from the owner to perform security testing.

  2. SCOPE
     Testing is limited to the endpoint or model you specify.
     No other systems will be targeted.

  3. LEGAL COMPLIANCE
     You are operating within the laws and regulations of
     your jurisdiction. Unauthorized testing of AI systems
     may be a criminal offense in many countries.

  4. DATA RESPONSIBILITY
     Adversarial probes sent to API-based models may be
     logged by the model provider. You are responsible for
     ensuring this is acceptable under your agreements.

  5. NO LIABILITY
     The creators and contributors of AI-SENTRY are not
     responsible for any direct or indirect consequences
     of its use. This tool is provided for defensive
     security research only.

By proceeding, you confirm that you have read, understood,
and agree to all of the above conditions.
"""

_PROMPT_TEXT   = "Do you agree to proceed? [yes / no]: "
_DECLINE_TEXT  = "\nScan cancelled. No action was taken.\n"
_INVALID_TEXT  = "  Please type 'yes' to proceed or 'no' to cancel."
_MAX_RETRIES   = 3


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def get_user_consent() -> bool:
    """
    Display the responsible-use notice and prompt for consent.

    Returns True if the user explicitly consents.
    Returns False if the user declines.
    Calls sys.exit(0) after too many invalid responses.

    This function must be called before any scanning logic runs.
    """
    _print_notice()

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = input(_PROMPT_TEXT).strip().lower()
        except (EOFError, KeyboardInterrupt):
            # Non-interactive environment or Ctrl-C: treat as decline.
            _print_decline()
            return False

        if response == "yes":
            _print_accepted()
            return True

        if response == "no":
            _print_decline()
            return False

        # Invalid input — give the user another chance (up to the limit).
        remaining = _MAX_RETRIES - attempt
        if remaining > 0:
            print(f"{_INVALID_TEXT} ({remaining} attempt(s) remaining)")
        else:
            print(f"\n  Too many invalid responses. Exiting.\n")
            sys.exit(0)

    # Should never be reached, but satisfies the type checker.
    return False  # pragma: no cover


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────

def _print_notice() -> None:
    print(f"\n{_DIVIDER}")
    # Preserve intentional formatting; strip only the overall indent.
    for line in _RESPONSIBLE_USE_NOTICE.splitlines():
        print(line)
    print(_DIVIDER)


def _print_accepted() -> None:
    print(f"\n  Consent recorded. Proceeding with scan.\n")
    print(_DIVIDER + "\n")


def _print_decline() -> None:
    print(_DECLINE_TEXT)
    print(_DIVIDER + "\n")
