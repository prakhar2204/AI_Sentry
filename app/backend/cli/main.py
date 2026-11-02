"""
Sentryɸ -- CLI Entry Point
app/backend/cli/main.py

Parses top-level commands and dispatches to the appropriate
backend module. Every destructive command passes through the
consent gate before any work begins.

Usage:
    python __main__.py scan --target <url>                              # garak only (default)
    python __main__.py scan --target <url> --engine pyrit               # pyrit only
    python __main__.py scan --target <url> --engine both                # garak then pyrit
    python __main__.py scan --mode api --target <url> --api-key <key>
    python __main__.py scan --mode local --target http://localhost:8080
    python __main__.py healthcheck
    python __main__.py version
"""

import argparse
import os
import sys
from pathlib import Path

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
from core.report_generator import (
    generate_full_report,
    display_txt_report,
    export_report,
    print_export_result,
)
from services.report_service import store_report


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
        prog="sentryphi",
        description=(
            "Sentryɸ -- LLM Pre-Deployment Security Platform\n"
            "Run multi-layer adversarial scans on language models."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Sentryɸ {__version__}",
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
    scan_parser.add_argument(
        "--engine",
        choices=["garak", "pyrit", "both"],
        default="garak",
        metavar="<engine>",
        help=(
            "Scan engine to use: 'garak' (default), 'pyrit', or 'both'. "
            "In 'both' mode garak runs first, then pyrit; results are reported "
            "separately with no cross-engine merging."
        ),
    )

    # ── healthcheck ───────────────────────────
    subparsers.add_parser(
        "healthcheck",
        help="Verify that all bundled engines and dependencies are functional.",
        description=(
            "Runs a pre-flight check: confirms Python version, httpx, "
            "Garak and PyRIT are installed at the correct "
            "pinned versions, and that sufficient disk space is available."
        ),
    )

    # ── version ───────────────────────────────
    subparsers.add_parser(
        "version",
        help="Print the Sentryɸ version and exit.",
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
    # engine_name: "garak" | "pyrit" | "mock" | "auto"
    # "both" is handled at the CLI layer (two separate engine runs)
    engine_name = getattr(args, "engine", "mock")
    out_dir = Path(args.output)

    _print_divider()
    print(f"  [INFO] Starting scan engine ({engine_name})...")
    print(f"  [INFO] Manifest ID: {manifest.manifest_id}\n")

    if engine_name == "both":
        # Run garak pipeline then pyrit pipeline sequentially.
        # Each gets its own ScanResult → scorer → recommender → report.
        print("  [ENGINE: both] Running Garak engine first, then PyRIT.\n")
        rc_garak = _run_full_pipeline(
            args=args, manifest=manifest, api_key=api_key,
            engine_name="garak", out_dir=out_dir,
        )
        rc_pyrit = _run_full_pipeline(
            args=args, manifest=manifest, api_key=api_key,
            engine_name="pyrit", out_dir=out_dir,
        )
        return max(rc_garak, rc_pyrit)

    return _run_full_pipeline(
        args=args, manifest=manifest, api_key=api_key,
        engine_name=engine_name, out_dir=out_dir,
    )


def handle_healthcheck() -> int:
    """
    Entry point for the `healthcheck` command.
    No consent required -- read-only operation.
    """
    # TODO (Phase 1d): Replace with real EnvironmentChecker implementation.
    print("\nSentryɸ -- Environment Health Check\n")
    print("  [Phase 1 placeholder] Health check logic will be implemented")
    print("  as part of the EnvironmentChecker module in Phase 1d.\n")
    return 0


def handle_version() -> int:
    print(f"\nSentryɸ {__version__}\n")
    return 0


# ─────────────────────────────────────────────
#  Pipeline steps 9–13 (engine → report → export)
# ─────────────────────────────────────────────

def _run_full_pipeline(
    args: argparse.Namespace,
    manifest,
    api_key: str,
    engine_name: str,
    out_dir: Path,
) -> int:
    """
    Run pipeline steps 9–13 for a single engine selection:
      9.  Scan engine execution
      10. Risk scoring
      11. Recommendations
      12. Report generation + display
      13. File export

    Returns 0 on success, 1 on engine or export failure.
    """
    scan_result = run_engine(manifest, engine_name=engine_name, output_dir=out_dir)

    if not scan_result.ok:
        print_scan_error(scan_result)
        print("  Scan engine failed. Check the error above.\n")
        return 1

    # -- 10. Risk scoring ------------------------------------------
    risk_report = score_scan_result(scan_result)

    # -- 11. Recommendations ---------------------------------------
    rec_report = generate_recommendations(risk_report)

    # -- 12. Report generation + display ---------------------------
    full_report = generate_full_report(
        manifest=manifest,
        scan_result=scan_result,
        risk_report=risk_report,
        rec_report=rec_report,
    )
    store_report(full_report)
    display_txt_report(full_report)

    # -- 13. File export -------------------------------------------
    output_dir = manifest.output_dir
    suffix = f"_{engine_name}" if engine_name != "mock" else ""
    json_path = os.path.join(output_dir, f"report_{manifest.manifest_id}{suffix}.json")
    txt_path  = os.path.join(output_dir, f"report_{manifest.manifest_id}{suffix}.txt")

    json_result = export_report(full_report, json_path, fmt="json")
    print_export_result(json_result)

    txt_result = export_report(full_report, txt_path, fmt="txt")
    print_export_result(txt_result)

    return 0


# ─────────────────────────────────────────────
#  Garak scan orchestration
# ─────────────────────────────────────────────

_SEV_LABELS = {
    1: "INFORMATIONAL",
    2: "LOW",
    3: "MEDIUM",
    4: "HIGH",
    5: "CRITICAL",
}

_DEPTH_PROBE_COUNTS = {
    "quick": 6,
    "standard": 12,
    "deep": 21,
}


def _run_garak_scan(
    target:     str,
    api_key:    str,
    depth:      str,
    output_dir: Path,
) -> int:
    """
    Run a GarakEngine scan and print results to the console.

    Writes a human-readable text summary to output_dir/garak_summary.txt.
    Returns 0 on success, 1 if any probe failed to run.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    probe_count = _DEPTH_PROBE_COUNTS.get(depth, 12)

    _print_divider()
    print(f"\n  AI-SENTRY -- Garak Security Scan")
    print(f"  Target  : {target}")
    print(f"  Depth   : {depth}  ({probe_count} probes across {len(ALL_CATEGORIES)} categories)")
    print(f"  Output  : {output_dir}")
    print()

    engine = GarakEngine(
        target_url=target,
        output_dir=output_dir / "garak_reports",
        api_key=api_key,
        depth=depth,
        generations=1,
    )

    # Print planned probes
    specs = engine.probe_specs_for_depth()
    print(f"  Probes to run ({len(specs)}):")
    for s in specs:
        print(f"    {s}")
    print()
    _print_divider()

    print(f"\n  Running scan ...\n")

    result: GarakScanResult = engine.run()

    # ── Per-probe results ─────────────────────
    _print_divider()
    print(f"\n  PROBE RESULTS\n")
    print(f"  {'Probe':<55} {'Status':<8} {'Pass%':>6}  {'Sev':>4}  {'Findings'}")
    print(f"  {'-'*55} {'-'*8} {'-'*6}  {'-'*4}  {'-'*8}")

    for pr in result.probe_results:
        short  = pr.spec.replace("probes.", "")
        status = "OK" if pr.success else "ERROR"
        if pr.findings:
            worst = min(pr.findings, key=lambda f: f.pass_rate)
            pct   = f"{worst.pass_rate*100:.0f}%"
            sev   = worst.severity
        else:
            pct = "N/A"
            sev = 0
        print(
            f"  {short:<55} {status:<8} {pct:>6}  {sev:>4}  {len(pr.findings)}"
        )
        if pr.error:
            print(f"    [ERROR] {pr.error}")

    # ── Finding summary ───────────────────────
    print()
    _print_divider()
    print(f"\n  VULNERABILITY FINDINGS ({len(result.findings)} total)\n")

    if result.findings:
        by_sev: dict[int, list] = {}
        for f in result.findings:
            by_sev.setdefault(f.severity, []).append(f)

        for sev in sorted(by_sev.keys(), reverse=True):
            label    = _SEV_LABELS.get(sev, str(sev))
            findings = by_sev[sev]
            print(f"  [{label}]  ({len(findings)} finding{'s' if len(findings) != 1 else ''})")
            for f in findings:
                breach = f.pass_rate < 1.0
                marker = "  !" if breach else "  ."
                print(
                    f"{marker} {f.category:<22} {f.probe:<45} "
                    f"pass={f.pass_rate*100:.0f}%  conf={f.confidence:.2f}"
                )
            print()
    else:
        print("  No findings parsed (check garak report files in output directory).\n")

    # ── Overall result ────────────────────────
    _print_divider()
    breached = [f for f in result.findings if f.pass_rate < 1.0]
    if breached:
        worst_sev = max(f.severity for f in breached)
        print(f"\n  RESULT: Vulnerabilities detected")
        print(f"  Highest severity : {_SEV_LABELS.get(worst_sev, str(worst_sev))}")
        print(f"  Breached findings: {len(breached)}")
    else:
        print(f"\n  RESULT: No vulnerabilities detected at this depth")

    print(f"  Total findings   : {len(result.findings)}")
    print(f"  Probes run       : {len(result.probe_results)}")
    print(f"  Engine errors    : {len(result.errors)}")
    print(f"  Duration         : {result.started_at} --> {result.finished_at}")

    # ── Write text summary ────────────────────
    summary_path = output_dir / "garak_summary.txt"
    _write_text_summary(result, summary_path)
    print(f"\n  Summary written to: {summary_path}")
    print()

    return 0 if result.all_ok else 1


# ─────────────────────────────────────────────
#  PyRIT scan orchestration
# ─────────────────────────────────────────────

_DEPTH_ATTACK_COUNTS = {
    "quick":    6,   # 1 attack/category × 6 categories
    "standard": 12,  # 2 attacks/category × 6 categories
    "deep":     12,  # same as standard (future-proofed in engine)
}


def _run_pyrit_scan(
    target:     str,
    api_key:    str,
    depth:      str,
    output_dir: Path,
) -> int:
    """
    Run a PyRITEngine scan and print results to the console.

    Progress is reported after every attack spec via a callback that prints
    a one-liner: "  [PyRIT] <category>/<spec_name> ... done (<duration>s)".
    This runs synchronously from the caller's perspective; PyRIT's async event
    loop is managed internally by PyRITEngine.

    Writes a human-readable text summary to output_dir/pyrit_summary.txt.
    Returns 0 on success, 1 if any attack failed to run.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    attack_count = _DEPTH_ATTACK_COUNTS.get(depth, 12)

    _print_divider()
    print(f"\n  AI-SENTRY -- PyRIT Security Scan")
    print(f"  Target  : {target}")
    print(f"  Depth   : {depth}  ({attack_count} attacks across {len(PYRIT_ALL_CATEGORIES)} categories)")
    print(f"  Output  : {output_dir}")
    print()

    # Progress callback — called by PyRITEngine after each attack spec completes.
    # Mechanism: PyRITEngine stores self.progress_callback and calls it with a
    # formatted string "category/spec_name ... ok|FAILED (<duration>s)" at the
    # end of every _run_attack() call.  This keeps the caller informed without
    # requiring threads or asyncio from this side.
    def _on_progress(msg: str) -> None:
        print(f"  [PyRIT] {msg}")

    engine = PyRITEngine(
        target_url=target,
        output_dir=output_dir / "pyrit_reports",
        api_key=api_key,
        depth=depth,
        progress_callback=_on_progress,
    )

    print(f"  Attack specs to run ({attack_count}):")
    from core.pyrit_engine import PYRIT_CATEGORY_MAP, _DEPTH_SLICE
    n_slice = _DEPTH_SLICE.get(depth, 2)
    for cat, specs in PYRIT_CATEGORY_MAP.items():
        for spec in specs[:n_slice]:
            print(f"    {cat}/{spec['name']}")
    print()
    _print_divider()

    print(f"\n  Running scan ...\n")

    result: PyRITScanResult = engine.run()

    # ── Per-attack results ────────────────────
    _print_divider()
    print(f"\n  ATTACK RESULTS\n")
    print(f"  {'Attack':<55} {'Status':<8} {'Dur(s)':>6}  {'Sev':>4}  {'Findings'}")
    print(f"  {'-'*55} {'-'*8} {'-'*6}  {'-'*4}  {'-'*8}")

    for ar in result.attack_results:
        short  = f"{ar.category}/{ar.spec_name}"
        status = "OK" if ar.success else "ERROR"
        dur    = f"{ar.duration_s:.1f}"
        if ar.findings:
            worst = min(ar.findings, key=lambda f: f.pass_rate)
            sev   = worst.severity
        else:
            sev = 0
        print(
            f"  {short:<55} {status:<8} {dur:>6}  {sev:>4}  {len(ar.findings)}"
        )
        if ar.error:
            print(f"    [ERROR] {ar.error}")

    # ── Finding summary ───────────────────────
    print()
    _print_divider()
    print(f"\n  VULNERABILITY FINDINGS ({len(result.findings)} total)\n")

    if result.findings:
        by_sev: dict[int, list] = {}
        for f in result.findings:
            by_sev.setdefault(f.severity, []).append(f)

        for sev in sorted(by_sev.keys(), reverse=True):
            label    = _SEV_LABELS.get(sev, str(sev))
            findings = by_sev[sev]
            print(f"  [{label}]  ({len(findings)} finding{'s' if len(findings) != 1 else ''})")
            for f in findings:
                breach = f.pass_rate < 1.0
                marker = "  !" if breach else "  ."
                print(
                    f"{marker} {f.category:<22} {f.probe:<45} "
                    f"pass={f.pass_rate*100:.0f}%  conf={f.confidence:.2f}"
                )
            print()
    else:
        print("  No findings parsed (check pyrit report files in output directory).\n")

    # ── Overall result ────────────────────────
    _print_divider()
    breached = [f for f in result.findings if f.pass_rate < 1.0]
    if breached:
        worst_sev = max(f.severity for f in breached)
        print(f"\n  RESULT: Vulnerabilities detected")
        print(f"  Highest severity : {_SEV_LABELS.get(worst_sev, str(worst_sev))}")
        print(f"  Breached findings: {len(breached)}")
    else:
        print(f"\n  RESULT: No vulnerabilities detected at this depth")

    print(f"  Total findings   : {len(result.findings)}")
    print(f"  Attacks run      : {len(result.attack_results)}")
    print(f"  Engine errors    : {len(result.errors)}")
    print(f"  Duration         : {result.started_at} --> {result.finished_at}")

    # ── Write text summary ────────────────────
    summary_path = output_dir / "pyrit_summary.txt"
    _write_pyrit_summary(result, summary_path)
    print(f"\n  Summary written to: {summary_path}")
    print()

    return 0 if result.all_ok else 1


def _write_pyrit_summary(result: PyRITScanResult, path: Path) -> None:
    """Write a plain-text PyRIT scan summary to path."""
    lines = [
        "AI-SENTRY PyRIT Scan Summary",
        "=" * 60,
        f"Run ID    : {result.run_id}",
        f"Target    : {result.target_url}",
        f"Started   : {result.started_at}",
        f"Finished  : {result.finished_at}",
        f"Categories: {', '.join(result.categories)}",
        f"Attacks   : {len(result.attack_results)}",
        f"Findings  : {len(result.findings)}",
        f"All OK    : {result.all_ok}",
        "",
        "FINDINGS",
        "-" * 60,
    ]

    for f in sorted(result.findings, key=lambda x: (-x.severity, x.category, x.probe)):
        label  = _SEV_LABELS.get(f.severity, str(f.severity))
        breach = "BREACH" if f.pass_rate < 1.0 else "pass"
        lines.append(
            f"  [{label:<14}] [{breach}] {f.category}/{f.probe}/{f.detector} "
            f"pass={f.pass_rate*100:.0f}%  conf={f.confidence:.2f}"
        )

    if result.errors:
        lines += ["", "ERRORS", "-" * 60]
        lines.extend(f"  {e}" for e in result.errors)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_text_summary(result: GarakScanResult, path: Path) -> None:
    """Write a plain-text scan summary to path."""
    lines = [
        "AI-SENTRY Garak Scan Summary",
        "=" * 60,
        f"Run ID    : {result.run_id}",
        f"Target    : {result.target_url}",
        f"Started   : {result.started_at}",
        f"Finished  : {result.finished_at}",
        f"Categories: {', '.join(result.categories)}",
        f"Probes run: {len(result.probe_results)}",
        f"Findings  : {len(result.findings)}",
        f"All OK    : {result.all_ok}",
        "",
        "FINDINGS",
        "-" * 60,
    ]

    for f in sorted(result.findings, key=lambda x: (-x.severity, x.category, x.probe)):
        label  = _SEV_LABELS.get(f.severity, str(f.severity))
        breach = "BREACH" if f.pass_rate < 1.0 else "pass"
        lines.append(
            f"  [{label:<14}] [{breach}] {f.category}/{f.probe}/{f.detector} "
            f"pass={f.pass_rate*100:.0f}%  conf={f.confidence:.2f}"
        )

    if result.errors:
        lines += ["", "ERRORS", "-" * 60]
        lines.extend(f"  {e}" for e in result.errors)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
