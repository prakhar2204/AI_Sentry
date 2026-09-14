"""
AI-SENTRY — CLI Entry Point
app/backend/cli/main.py

Parses top-level commands and dispatches to the appropriate
backend module. Every destructive command passes through the
consent gate before any work begins.

Usage:
    python -m aisentry scan --target <endpoint_or_path>
    python -m aisentry scan --target <url> --api-key <key>
    python -m aisentry healthcheck
    python -m aisentry version
"""

import argparse
import os
import sys

from core.consent import get_user_consent
from core.input_handler import run_input_validation


# ─────────────────────────────────────────────
#  Version
# ─────────────────────────────────────────────

__version__ = "0.1.0-dev"


# ─────────────────────────────────────────────
#  Top-level parser
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-sentry",
        description=(
            "AI-SENTRY — LLM Security Orchestration Platform\n"
            "Run multi-engine adversarial scans on language models."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"AI-SENTRY {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="<command>",
        help="Available commands",
    )
    subparsers.required = True

    # ── scan ──────────────────────────────────
    scan_parser = subparsers.add_parser(
        "scan",
        help="Run a security scan against a target model.",
        description="Perform adversarial security testing on an LLM endpoint or local model.",
    )
    scan_parser.add_argument(
        "--target",
        required=True,
        metavar="<endpoint_or_path>",
        help=(
            "API endpoint URL (e.g. https://api.openai.com/v1) "
            "or path to a local GGUF model file."
        ),
    )
    scan_parser.add_argument(
        "--api-key",
        default="",
        metavar="<key>",
        help=(
            "API key for the target endpoint. "
            "Can also be set via the AI_SENTRY_API_KEY environment variable."
        ),
    )
    scan_parser.add_argument(
        "--depth",
        choices=["quick", "standard", "deep"],
        default="standard",
        metavar="<depth>",
        help="Scan depth profile: quick | standard | deep  (default: standard)",
    )
    scan_parser.add_argument(
        "--output",
        default="./aisentry-report",
        metavar="<path>",
        help="Directory to write scan reports into  (default: ./aisentry-report)",
    )

    # ── healthcheck ───────────────────────────
    subparsers.add_parser(
        "healthcheck",
        help="Verify that all bundled engines and dependencies are functional.",
        description=(
            "Runs a pre-flight check: confirms that Garak, PyRIT, and DeepTeam are "
            "installed at the correct pinned versions, the OS keychain is accessible, "
            "and sufficient disk space is available."
        ),
    )

    # ── version ───────────────────────────────
    subparsers.add_parser(
        "version",
        help="Print the AI-SENTRY version and exit.",
    )

    return parser


# ─────────────────────────────────────────────
#  Command handlers
# ─────────────────────────────────────────────

def handle_scan(args: argparse.Namespace) -> int:
    """
    Entry point for the `scan` command.

    Pipeline:
        1. Consent gate  (mandatory — cannot be skipped)
        2. Endpoint validation + test request  (Phase 1b)
        3. Scan orchestration  (Phase 3 — placeholder for now)

    Returns an integer exit code (0 = success, non-zero = error).
    """
    # ── 1. Consent gate ───────────────────────
    if not get_user_consent():
        return 0  # User declined — clean exit, nothing was done.

    # ── 2. Resolve API key ────────────────────
    # CLI flag takes priority; environment variable is the fallback.
    api_key: str = args.api_key or os.environ.get("AI_SENTRY_API_KEY", "")

    # ── 3. Endpoint validation + test request ─
    reachable = run_input_validation(target=args.target, api_key=api_key)

    if not reachable:
        print("  Scan aborted. Please fix the endpoint issue and try again.\n")
        return 1

    # ── 4. Scan orchestration (Phase 3) ───────
    print(f"  Target  : {args.target}")
    print(f"  Depth   : {args.depth}")
    print(f"  Output  : {args.output}")
    print()
    print("  Scan engine is not yet implemented (Phase 3).")
    print("  Endpoint validation passed — the target is ready to be scanned.\n")

    return 0


def handle_healthcheck() -> int:
    """
    Entry point for the `healthcheck` command.

    No consent required — read-only operation.
    Returns an integer exit code.
    """
    # TODO (Phase 1): Replace with real EnvironmentChecker implementation.
    print("\nAI-SENTRY — Environment Health Check\n")
    print("  [Phase 1 placeholder] Health check logic will be implemented")
    print("  as part of the EnvironmentChecker module in Phase 1.\n")
    return 0


def handle_version() -> int:
    print(f"\nAI-SENTRY {__version__}\n")
    return 0


# ─────────────────────────────────────────────
#  Main dispatch
# ─────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "scan":        lambda: handle_scan(args),
        "healthcheck": handle_healthcheck,
        "version":     handle_version,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    exit_code = handler()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
