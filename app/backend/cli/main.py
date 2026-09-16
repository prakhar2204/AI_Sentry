"""
AI-SENTRY -- CLI Entry Point
app/backend/cli/main.py

Parses top-level commands and dispatches to the appropriate
backend module. Every destructive command passes through the
consent gate before any work begins.

Usage:
    python __main__.py scan --target <url>                         # API mode (default)
    python __main__.py scan --mode api --target <url> --api-key <key>
    python __main__.py scan --mode local --target http://localhost:8080
    python __main__.py healthcheck
    python __main__.py version
"""

import argparse
import os
import sys

from core.consent import get_user_consent
from core.input_handler import run_input_validation
from core.local_handler import run_local_validation


# ─────────────────────────────────────────────
#  Version
# ─────────────────────────────────────────────

__version__ = "0.1.0-dev"


# ─────────────────────────────────────────────
#  Scan modes
# ─────────────────────────────────────────────

MODE_API   = "api"
MODE_LOCAL = "local"
VALID_MODES = (MODE_API, MODE_LOCAL)


# ─────────────────────────────────────────────
#  Top-level parser
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-sentry",
        description=(
            "AI-SENTRY -- LLM Security Orchestration Platform\n"
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
        description=(
            "Perform adversarial security testing on an LLM endpoint or local model.\n\n"
            "Examples:\n"
            "  # Remote API endpoint\n"
            "  python __main__.py scan --target https://api.openai.com/v1 --api-key sk-...\n\n"
            "  # Local llama.cpp server\n"
            "  python __main__.py scan --mode local --target http://localhost:8080"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    scan_parser.add_argument(
        "--target",
        required=True,
        metavar="<url>",
        help=(
            "API endpoint URL (e.g. https://api.openai.com/v1) or "
            "local server URL (e.g. http://localhost:8080)."
        ),
    )
    scan_parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default=MODE_API,
        metavar="<mode>",
        help=(
            "Connection mode: 'api' for remote endpoints (default), "
            "'local' for a local llama.cpp server."
        ),
    )
    scan_parser.add_argument(
        "--api-key",
        default="",
        metavar="<key>",
        help=(
            "API key for remote endpoints (--mode api only). "
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
            "Runs a pre-flight check: confirms Python version, httpx, "
            "Garak, PyRIT, and DeepTeam are installed at the correct "
            "pinned versions, and that sufficient disk space is available."
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
        1. Consent gate          (mandatory -- cannot be skipped)
        2. Mode dispatch:
             --mode api   -> API endpoint validation + probe  (Phase 1b)
             --mode local -> local server validation + probe  (Phase 1c)
        3. Scan orchestration    (Phase 3 -- placeholder for now)

    Returns an integer exit code (0 = success, non-zero = error).
    """
    # ── 1. Consent gate ───────────────────────
    if not get_user_consent():
        return 0  # user declined -- clean exit, nothing was done

    # ── 2. Mode dispatch ──────────────────────
    mode = args.mode

    _print_divider()
    print(f"  Mode: {'Remote API' if mode == MODE_API else 'Local Model (llama.cpp)'}")
    _print_divider()

    if mode == MODE_LOCAL:
        # Warn if --api-key was supplied with --mode local (it is ignored)
        if args.api_key:
            print(
                "\n  [WARN] --api-key is ignored in --mode local. "
                "Local servers do not require authentication.\n"
            )
        reachable = run_local_validation(target=args.target)

    else:  # MODE_API (default)
        # Resolve API key: CLI flag > environment variable > empty
        api_key: str = args.api_key or os.environ.get("AI_SENTRY_API_KEY", "")
        reachable = run_input_validation(target=args.target, api_key=api_key)

    if not reachable:
        print("  Scan aborted. Please fix the issue above and try again.\n")
        return 1

    # ── 3. Scan orchestration (Phase 3) ───────
    _print_divider()
    print(f"\n  Target  : {args.target}")
    print(f"  Mode    : {mode}")
    print(f"  Depth   : {args.depth}")
    print(f"  Output  : {args.output}")
    print()
    print("  [INFO] Scan engine is not yet implemented (Phase 3).")
    print("  [INFO] Connection test passed -- the target is ready to be scanned.\n")

    return 0


def handle_healthcheck() -> int:
    """
    Entry point for the `healthcheck` command.
    No consent required -- read-only operation.
    """
    # TODO (Phase 1d): Replace with real EnvironmentChecker implementation.
    print("\nAI-SENTRY -- Environment Health Check\n")
    print("  [Phase 1 placeholder] Health check logic will be implemented")
    print("  as part of the EnvironmentChecker module in Phase 1d.\n")
    return 0


def handle_version() -> int:
    print(f"\nAI-SENTRY {__version__}\n")
    return 0


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _print_divider() -> None:
    print("-" * 60)


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
