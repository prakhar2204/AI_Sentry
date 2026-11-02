"""
AI-SENTRY -- CLI Entry Point
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
from core.garak_engine import GarakEngine, GarakScanResult, ALL_CATEGORIES
from core.pyrit_engine import (
    PyRITEngine,
    PyRITScanResult,
    ALL_CATEGORIES as PYRIT_ALL_CATEGORIES,
)
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
        3. Garak engine scan     (Phase 4)

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

    # ── 3. Engine scan(s) ─────────────────────
    api_key  = args.api_key or os.environ.get("AI_SENTRY_API_KEY", "")
    engine   = getattr(args, "engine", "garak")   # default: garak
    out_dir  = Path(args.output)

    if engine == "garak":
        return _run_garak_scan(
            target=args.target,
            api_key=api_key,
            depth=args.depth,
            output_dir=out_dir,
        )

    elif engine == "pyrit":
        return _run_pyrit_scan(
            target=args.target,
            api_key=api_key,
            depth=args.depth,
            output_dir=out_dir,
        )

    else:  # "both" — run garak first, then pyrit; results reported separately
        print("\n  [ENGINE: both] Running Garak engine first, then PyRIT.")
        print("  Results are reported independently — no cross-engine merging.\n")
        rc_garak = _run_garak_scan(
            target=args.target,
            api_key=api_key,
            depth=args.depth,
            output_dir=out_dir,
        )
        rc_pyrit = _run_pyrit_scan(
            target=args.target,
            api_key=api_key,
            depth=args.depth,
            output_dir=out_dir,
        )
        # Return non-zero if either engine reported a problem
        return max(rc_garak, rc_pyrit)


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
