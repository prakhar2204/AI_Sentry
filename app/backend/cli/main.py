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
from core.validator import run_all_validations, print_validation_error
from core.manifest import (
    get_final_manifest,
    print_manifest_load_error,
    VALID_CATEGORY_NAMES,
)
from core.manifest_validator import (
    validate_manifest,
    print_manifest_validation_error,
)
from core.manifest_display import display_and_confirm
from core.estimator import estimate_scan
from core.scan_guard import check_scan_safety
from core.engine_runner import run_engine, display_results, print_scan_error
from core.scorer import score_scan_result, display_risk_report
from core.recommender import generate_recommendations, display_recommendations


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
        required=False,
        default=None,
        metavar="<url>",
        help=(
            "API endpoint URL (e.g. https://api.openai.com/v1) or "
            "local server URL (e.g. http://localhost:8080). "
            "Can also be set in a --manifest file."
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
        "--categories",
        nargs="+",
        metavar="<category>",
        default=None,
        help=(
            "Probe categories to run. Space-separated list of: "
            + "  ".join(sorted(VALID_CATEGORY_NAMES))
            + "  (default: all categories for the chosen --depth)"
        ),
    )
    scan_parser.add_argument(
        "--manifest",
        default=None,
        metavar="<path>",
        help=(
            "Path to a JSON manifest file. CLI flags override file values. "
            "See example_manifest.json for format."
        ),
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
        1. Consent gate           (Phase 1a  -- legal agreement)
        2. Manifest loading       (Phase 2b  -- file + CLI merge)
        3. Manifest validation    (Phase 2c  -- post-merge semantic check)
        4. Estimate + Display     (Phase 3a  -- probes, time, cost)
        5. Safety guard           (Phase 3b  -- heavy scan warning if needed)
        6. User confirmation      (Phase 2d  -- final yes/no)
        7. Connection validation  (Phase 1d  -- URL format + mode rules)
        8. Mode dispatch          (Phase 1b/c -- endpoint probe)
        9. Scan orchestration     (Phase 3+  -- placeholder)

    Returns an integer exit code (0 = success, non-zero = error).
    """
    # -- 1. Consent gate ------------------------------------------
    if not get_user_consent():
        return 0  # user declined -- clean exit, nothing was done

    # -- 2. Manifest loading (file + CLI merge) --------------------
    api_key: str = getattr(args, "api_key", "") or os.environ.get("AI_SENTRY_API_KEY", "")

    result = get_final_manifest(
        manifest_path=args.manifest,
        cli_target=args.target,
        cli_mode=args.mode if args.mode != MODE_API else None,
        cli_scan_depth=args.depth if args.depth != "standard" else None,
        cli_categories=args.categories,
        cli_api_key=api_key or None,
        cli_output_dir=args.output if args.output != "./aisentry-report" else None,
    )

    if not result.ok:
        print_manifest_load_error(result)
        print("  Scan aborted. Fix the issue above and retry.\n")
        return 1

    manifest = result.manifest

    # -- 3. Manifest validation (post-merge semantic check) --------
    issue = validate_manifest(manifest)
    if issue is not None:
        print_manifest_validation_error(issue)
        print("  Scan aborted. Fix the issue above and retry.\n")
        return 1

    # -- 4. Estimate + Display -------------------------------------
    estimate = estimate_scan(manifest)

    # -- 5. Safety guard (heavy scan warning if needed) ------------
    if not check_scan_safety(estimate):
        return 0  # user declined heavy scan -- clean exit

    # -- 6. Display config + normal confirmation -------------------
    if not display_and_confirm(manifest, source=result.source, estimate=estimate):
        return 0  # user declined or gave too many invalid inputs

    # -- 7. Connection validation (URL format + mode rules) --------
    validation_err = run_all_validations(mode=manifest.mode.value, target=manifest.target)
    if validation_err is not None:
        print_validation_error(validation_err)
        print("  Scan aborted. Fix the issue above and retry.\n")
        return 1

    # -- 8. Mode dispatch (endpoint probe) -------------------------
    mode = manifest.mode.value

    if mode == MODE_LOCAL:
        if api_key:
            print(
                "\n  [WARN] --api-key is ignored in --mode local. "
                "Local servers do not require authentication.\n"
            )
        reachable = run_local_validation(target=manifest.target)

    else:  # MODE_API
        reachable = run_input_validation(target=manifest.target, api_key=api_key)

    if not reachable:
        print("  Scan aborted. Please fix the issue above and try again.\n")
        return 1

    # -- 9. Scan engine execution ----------------------------------
    _print_divider()
    print("  [INFO] Starting scan engine...")
    print(f"  [INFO] Manifest ID: {manifest.manifest_id}\n")

    scan_result = run_engine(manifest)

    if not scan_result.ok:
        print_scan_error(scan_result)
        print("  Scan engine failed. Check the error above.\n")
        return 1

    display_results(scan_result)

    # -- 10. Risk scoring ------------------------------------------
    risk_report = score_scan_result(scan_result)
    display_risk_report(risk_report)

    # -- 11. Recommendations ---------------------------------------
    rec_report = generate_recommendations(risk_report)
    display_recommendations(rec_report)

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
