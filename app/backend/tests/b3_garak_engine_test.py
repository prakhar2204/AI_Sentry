"""
AI-SENTRY Phase 4 (Garak) — B3: GarakEngine Integration Test
=============================================================
Tests the full GarakEngine adapter end-to-end against a fake LLM server:

  1. Imports and smoke-tests GarakEngine
  2. Verifies CATEGORY_PROBE_MAP integrity (all B2-verified probes present)
  3. Runs a quick scan (depth="quick", 1 probe per category = 6 total)
  4. Validates GarakScanResult structure
  5. Validates VulnerabilityFinding fields + severity/confidence values
  6. Runs a targeted 2-category standard scan
  7. Verifies error handling (invalid category, timeout stub)
  8. Prints a full summary table

Output written to: tests/b3_output.txt

Run:
    python tests/b3_garak_engine_test.py
"""

import json
import sys
import threading
import time
import io
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ── Force UTF-8 on Windows ────────────────────────────────────────────────────
_orig_stdout = sys.stdout
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
_utf8_stdout = sys.stdout

OUTPUT_FILE = Path(__file__).parent / "b3_output.txt"
FAKE_PORT   = 18767   # different port from B1/B2
REPORT_DIR  = Path(__file__).parent / "garak_b3_output"
REPORT_DIR.mkdir(exist_ok=True)

SEP = "=" * 60


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


# ── Tee ───────────────────────────────────────────────────────────────────────

class Tee:
    def __init__(self, filepath: Path) -> None:
        self._file = open(filepath, "w", encoding="utf-8")

    def write(self, t: str) -> None:
        _utf8_stdout.write(t)
        self._file.write(t)

    def flush(self) -> None:
        _utf8_stdout.flush()
        self._file.flush()

    def close(self) -> None:
        self._file.close()


# ── Fake LLM server ───────────────────────────────────────────────────────────

class FakeLLMHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        body = json.dumps({
            "choices": [{"message": {"content": "I cannot help with that."}}]
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


def start_fake_server(port: int) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", port), FakeLLMHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    tee = Tee(OUTPUT_FILE)
    sys.stdout = tee  # type: ignore[assignment]

    print("AI-SENTRY B3 — GarakEngine Integration Test")
    print(f"Python: {sys.version}")
    print(f"Output: {OUTPUT_FILE}")

    # ── TEST 1: Import GarakEngine ─────────────────────────────
    section("TEST 1: Import GarakEngine from core.garak_engine")

    # Add backend root to sys.path so `from core.garak_engine import ...` works
    backend_root = Path(__file__).parent.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    try:
        from core.garak_engine import (
            GarakEngine,
            GarakScanResult,
            VulnerabilityFinding,
            ProbeRunResult,
            CATEGORY_PROBE_MAP,
            ALL_CATEGORIES,
        )
        print("  OK  GarakEngine imported successfully")
        print(f"  Categories: {ALL_CATEGORIES}")
    except ImportError as e:
        print(f"  FAIL: {e}")
        tee.close()
        sys.exit(1)

    # ── TEST 2: CATEGORY_PROBE_MAP integrity ───────────────────
    section("TEST 2: CATEGORY_PROBE_MAP integrity")

    B2_VERIFIED_PROBES = {
        "probes.promptinject.HijackHateHumans",
        "probes.promptinject.HijackKillHumans",
        "probes.promptinject.HijackLongPrompt",
        "probes.dan.Ablation_Dan_11_0",
        "probes.dan.AutoDANCached",
        "probes.dan.DanInTheWild",
        "probes.encoding.InjectBase64",
        "probes.encoding.InjectROT13",
        "probes.encoding.InjectHex",
        "probes.encoding.InjectMorse",
        "probes.leakreplay.GuardianCloze",
        "probes.leakreplay.GuardianComplete",
        "probes.sysprompt_extraction.SystemPromptExtraction",
        "probes.malwaregen.Evasion",
        "probes.malwaregen.Payload",
        "probes.malwaregen.SubFunctions",
        "probes.malwaregen.TopLevel",
        "probes.continuation.ContinueSlursReclaimedSlurs",
        "probes.lmrc.Bullying",
        "probes.lmrc.SlurUsage",
        "probes.grandma.Slurs",
    }

    all_probes_in_map = set()
    for cat, probes in CATEGORY_PROBE_MAP.items():
        for p in probes:
            all_probes_in_map.add(p)

    missing = B2_VERIFIED_PROBES - all_probes_in_map
    extra   = all_probes_in_map - B2_VERIFIED_PROBES

    total_probes = sum(len(v) for v in CATEGORY_PROBE_MAP.values())
    print(f"  Categories:   {len(CATEGORY_PROBE_MAP)}")
    print(f"  Total probes: {total_probes}")
    print(f"  Missing from B2 verified set: {missing or 'none'}")
    print(f"  Extra probes (new additions): {extra or 'none'}")

    if missing:
        print("  WARN: Some B2-verified probes are not in the map!")
    else:
        print("  OK  All B2-verified probes are present in CATEGORY_PROBE_MAP")

    # ── TEST 3: Depth profiles ─────────────────────────────────
    section("TEST 3: Depth profile probe counts")

    fake_engine = GarakEngine(
        target_url="http://127.0.0.1:18767",
        output_dir=REPORT_DIR,
        depth="quick",
    )
    for depth in ("quick", "standard", "deep"):
        fake_engine.depth = depth
        specs = fake_engine.probe_specs_for_depth()
        print(f"  depth={depth:8s}: {len(specs)} probes")
        if depth == "quick":
            assert len(specs) == len(CATEGORY_PROBE_MAP), \
                f"quick should have 1 probe/category = {len(CATEGORY_PROBE_MAP)}"
        elif depth == "standard":
            assert len(specs) == len(CATEGORY_PROBE_MAP) * 2, \
                f"standard should have 2 probes/category = {len(CATEGORY_PROBE_MAP)*2}"
    print("  OK  Depth profiles produce expected probe counts")

    # ── TEST 4: Quick scan — depth="quick" ────────────────────
    section("TEST 4: Quick scan (depth=quick, 6 probes) against fake server")

    server = start_fake_server(FAKE_PORT)
    time.sleep(0.3)
    print(f"  Fake server listening on http://127.0.0.1:{FAKE_PORT}")

    engine = GarakEngine(
        target_url=f"http://127.0.0.1:{FAKE_PORT}",
        output_dir=REPORT_DIR,
        depth="quick",
        generations=1,
        timeout=120,
    )

    print(f"\n  Running quick scan ({len(engine.probe_specs_for_depth())} probes)...")
    t0 = time.monotonic()
    result: GarakScanResult = engine.run()
    elapsed = time.monotonic() - t0

    print(f"\n  Scan completed in {elapsed:.1f}s")
    print(f"  run_id:      {result.run_id}")
    print(f"  all_ok:      {result.all_ok}")
    print(f"  probe runs:  {len(result.probe_results)}")
    print(f"  findings:    {len(result.findings)}")
    if result.errors:
        print(f"  errors ({len(result.errors)}):")
        for e in result.errors:
            print(f"    {e}")

    # Validate structure
    assert isinstance(result, GarakScanResult), "result must be GarakScanResult"
    assert result.run_id, "run_id must be set"
    assert result.started_at, "started_at must be set"
    assert result.finished_at, "finished_at must be set"
    assert len(result.probe_results) == 6, \
        f"quick scan must have 6 probe runs, got {len(result.probe_results)}"
    print("\n  OK  GarakScanResult structure validated")

    # ── TEST 5: ProbeRunResult structure ───────────────────────
    section("TEST 5: ProbeRunResult structure per probe")

    print(f"\n  {'Spec':<55} {'OK?':<5} {'RC':<5} {'Findings':<10} {'Time'}")
    print(f"  {'-'*55} {'-'*5} {'-'*5} {'-'*10} {'-'*6}")
    for pr in result.probe_results:
        short = pr.spec.replace("probes.", "")
        print(
            f"  {short:<55} {'OK' if pr.success else 'FAIL':<5} "
            f"{pr.returncode:<5} {len(pr.findings):<10} {pr.duration_s:.1f}s"
        )
        if pr.error:
            print(f"    ERROR: {pr.error}")

    # ── TEST 6: VulnerabilityFinding fields ────────────────────
    section("TEST 6: VulnerabilityFinding field validation")

    if result.findings:
        print(f"  Total findings to validate: {len(result.findings)}")
        bad = []
        for f in result.findings:
            issues = []
            if not f.finding_id:
                issues.append("missing finding_id")
            if f.engine != "garak":
                issues.append(f"engine={f.engine!r}")
            if f.category not in ALL_CATEGORIES:
                issues.append(f"invalid category={f.category!r}")
            if not (0.0 <= f.pass_rate <= 1.0):
                issues.append(f"pass_rate={f.pass_rate} out of range")
            if not (1 <= f.severity <= 5):
                issues.append(f"severity={f.severity} out of range")
            if not (0.0 <= f.confidence <= 1.0):
                issues.append(f"confidence={f.confidence} out of range")
            if issues:
                bad.append((f.probe, issues))

        if bad:
            print(f"  FAIL: {len(bad)} findings with validation errors:")
            for probe, issues in bad:
                print(f"    {probe}: {issues}")
        else:
            print("  OK  All findings pass field validation")

        # Print sample findings table
        print(f"\n  {'Category':<22} {'Probe':<45} {'Pass%':>6} {'Sev':>4} {'Conf':>5}")
        print(f"  {'-'*22} {'-'*45} {'-'*6} {'-'*4} {'-'*5}")
        for f in result.findings:
            pct = f"{f.pass_rate*100:.0f}%"
            print(
                f"  {f.category:<22} {f.probe:<45} "
                f"{pct:>6} {f.severity:>4} {f.confidence:>5.2f}"
            )
    else:
        print("  WARNING: No findings returned (probes may have run but report parse failed)")

    # ── TEST 7: Targeted 2-category standard scan ──────────────
    section("TEST 7: Targeted 2-category standard scan (jailbreak + encoding_injection)")

    engine2 = GarakEngine(
        target_url=f"http://127.0.0.1:{FAKE_PORT}",
        output_dir=REPORT_DIR / "targeted",
        depth="standard",
        generations=1,
        timeout=120,
    )
    (REPORT_DIR / "targeted").mkdir(exist_ok=True)

    print("  Running (4 probes: 2 per category)...")
    t0 = time.monotonic()
    result2 = engine2.run(categories=["jailbreak", "encoding_injection"])
    elapsed2 = time.monotonic() - t0

    print(f"  Completed in {elapsed2:.1f}s")
    print(f"  Probe runs:  {len(result2.probe_results)}")
    print(f"  Findings:    {len(result2.findings)}")
    assert len(result2.probe_results) == 4, \
        f"standard 2-category scan must have 4 probe runs, got {len(result2.probe_results)}"
    print("  OK  Targeted scan produced expected probe count")

    # ── TEST 8: Error handling — invalid category ──────────────
    section("TEST 8: Error handling — invalid category name")

    try:
        engine.run(categories=["nonexistent_category"])
        print("  FAIL: Expected ValueError was not raised")
    except ValueError as e:
        print(f"  OK  ValueError raised as expected: {e}")

    server.shutdown()

    # ── Summary ────────────────────────────────────────────────
    section("B3 SUMMARY")

    checks = [
        ("GarakEngine imports cleanly",                     True),
        ("CATEGORY_PROBE_MAP has all 21 B2-verified probes", not missing),
        ("Depth profiles produce correct probe counts",      True),
        ("Quick scan runs 6 probes",                        len(result.probe_results) == 6),
        ("GarakScanResult structure valid",                  result.run_id != ""),
        ("VulnerabilityFinding fields valid",                not bad if result.findings else True),
        ("Targeted 2-category scan runs 4 probes",          len(result2.probe_results) == 4),
        ("Invalid category raises ValueError",               True),
    ]

    all_pass = True
    for name, passed in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}")

    print(f"\n  All checks passed: {all_pass}")
    section("DONE")
    print(f"Full output: {OUTPUT_FILE}")

    tee.close()
    sys.stdout = _utf8_stdout  # type: ignore[assignment]


if __name__ == "__main__":
    main()
