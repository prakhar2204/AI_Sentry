"""
AI-SENTRY Phase 4 — B4: CLI + GarakEngine End-to-End Test
==========================================================
Validates that cli/main.py's `scan` command correctly passes arguments
through to GarakEngine and produces the expected console output + summary file.

Tests:
  1. CLI parses --target, --depth, --output correctly
  2. _run_garak_scan() runs against fake server (depth=quick)
  3. garak_summary.txt written to output directory
  4. Summary file contains expected fields
  5. CLI --version still works

Run:
    python tests/b4_cli_e2e_test.py
"""

import json
import sys
import io
import threading
import time
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

# ── Force UTF-8 on Windows ────────────────────────────────────────────────────
_orig_stdout = sys.stdout
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
_utf8_stdout = sys.stdout

# Add backend root to sys.path
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

OUTPUT_FILE = Path(__file__).parent / "b4_output.txt"
FAKE_PORT   = 18768
REPORT_DIR  = Path(__file__).parent / "garak_b4_output"
REPORT_DIR.mkdir(exist_ok=True)

SEP = "=" * 60


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


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

    print("AI-SENTRY B4 — CLI + GarakEngine End-to-End Test")
    print(f"Python: {sys.version}")

    # ── TEST 1: Import CLI modules ─────────────────────────────
    section("TEST 1: Import cli.main modules")

    try:
        from cli.main import (
            build_parser,
            handle_scan,
            handle_version,
            _run_garak_scan,
            _write_text_summary,
            _SEV_LABELS,
        )
        print("  OK  cli.main imported successfully")
    except ImportError as e:
        print(f"  FAIL: {e}")
        tee.close()
        sys.exit(1)

    # ── TEST 2: Parser structure ───────────────────────────────
    section("TEST 2: CLI parser structure")

    parser = build_parser()

    # Parse scan subcommand
    args = parser.parse_args([
        "scan",
        "--target", "http://127.0.0.1:18768",
        "--depth", "quick",
        "--output", str(REPORT_DIR),
        "--mode", "api",
    ])
    assert args.command == "scan",   f"command={args.command!r}"
    assert args.target  == "http://127.0.0.1:18768"
    assert args.depth   == "quick"
    assert args.mode    == "api"
    assert str(REPORT_DIR) in args.output
    print("  OK  Parser correctly parses scan subcommand")

    # Parse version subcommand
    version_args = parser.parse_args(["version"])
    assert version_args.command == "version"
    print("  OK  Parser correctly parses version subcommand")

    # ── TEST 3: _run_garak_scan() against fake server ──────────
    section("TEST 3: _run_garak_scan() quick scan against fake server")

    server = start_fake_server(FAKE_PORT)
    time.sleep(0.3)
    print(f"  Fake server on http://127.0.0.1:{FAKE_PORT}")

    print("  Running quick scan (6 probes)...")
    t0 = time.monotonic()
    rc = _run_garak_scan(
        target=f"http://127.0.0.1:{FAKE_PORT}",
        api_key="",
        depth="quick",
        output_dir=REPORT_DIR,
    )
    elapsed = time.monotonic() - t0

    print(f"\n  _run_garak_scan() returned: {rc}")
    print(f"  Elapsed: {elapsed:.1f}s")
    assert rc == 0, f"Expected return code 0, got {rc}"
    print("  OK  _run_garak_scan() returned 0")

    # ── TEST 4: garak_summary.txt written ─────────────────────
    section("TEST 4: garak_summary.txt written and parseable")

    summary_path = REPORT_DIR / "garak_summary.txt"
    assert summary_path.exists(), f"Summary not found: {summary_path}"

    content = summary_path.read_text(encoding="utf-8")
    print(f"  Summary size: {len(content)} bytes")

    required_fields = [
        "AI-SENTRY Garak Scan Summary",
        "Run ID",
        "Target",
        "Started",
        "Finished",
        "Probes run",
        "Findings",
        "FINDINGS",
    ]
    missing_fields = [f for f in required_fields if f not in content]
    if missing_fields:
        print(f"  FAIL: Missing fields: {missing_fields}")
    else:
        print("  OK  Summary contains all required fields")

    # Print summary
    print("\n  --- garak_summary.txt ---")
    for line in content.splitlines():
        print(f"  {line}")

    # ── TEST 5: handle_scan() with mocked consent ──────────────
    section("TEST 5: handle_scan() with mocked consent + mocked connectivity")

    # Build args namespace matching what argparse would produce
    scan_args = argparse.Namespace(
        command="scan",
        target=f"http://127.0.0.1:{FAKE_PORT}",
        mode="api",
        api_key="",
        depth="quick",
        output=str(REPORT_DIR / "handle_scan_out"),
    )

    # Patch consent (returns True) and input_validation (returns True)
    with (
        patch("cli.main.get_user_consent", return_value=True),
        patch("cli.main.run_input_validation", return_value=True),
    ):
        print("  Running handle_scan() with mocked consent + connectivity...")
        t0 = time.monotonic()
        result_rc = handle_scan(scan_args)
        elapsed2  = time.monotonic() - t0

    print(f"\n  handle_scan() returned: {result_rc}  ({elapsed2:.1f}s)")
    assert result_rc == 0, f"Expected 0, got {result_rc}"
    print("  OK  handle_scan() returned 0")

    server.shutdown()

    # ── TEST 6: SEV_LABELS completeness ───────────────────────
    section("TEST 6: _SEV_LABELS completeness")

    expected_sevs = {1, 2, 3, 4, 5}
    actual_sevs   = set(_SEV_LABELS.keys())
    if expected_sevs != actual_sevs:
        print(f"  FAIL: _SEV_LABELS missing: {expected_sevs - actual_sevs}")
    else:
        print(f"  OK  _SEV_LABELS covers severity levels 1-5")
        for sev, label in sorted(_SEV_LABELS.items()):
            print(f"    {sev} = {label}")

    # ── Summary ────────────────────────────────────────────────
    section("B4 SUMMARY")

    checks = [
        ("cli.main imports cleanly",                 True),
        ("Parser parses scan + version subcommands", True),
        ("_run_garak_scan() returns 0",              rc == 0),
        ("garak_summary.txt written",                summary_path.exists()),
        ("Summary has all required fields",          not missing_fields),
        ("handle_scan() with mocked consent OK",     result_rc == 0),
        ("_SEV_LABELS covers levels 1-5",            expected_sevs == actual_sevs),
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
