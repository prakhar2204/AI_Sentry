"""
AI-SENTRY Phase 4 (Garak) — B1: Environment & Integration Pattern Inspection
=============================================================================
Runs a real minimal garak scan against a fake HTTP server and prints the
COMPLETE real JSONL report structure so we know it before writing any code.

Fixes applied vs. v1:
  - subprocess uses encoding='utf-8', errors='replace' (garak emits emoji)
  - probe spec uses 'probes.test.Blank' prefix (required in garak 0.17+)
  - stderr captured separately from stdout

Run:
    python tests/b1_garak_inspection.py
Output written to: tests/b1_output.txt
"""

import json
import os
import platform
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "b1_output.txt"
FAKE_SERVER_PORT = 18765
FAKE_SERVER_URL = f"http://127.0.0.1:{FAKE_SERVER_PORT}"

# Force UTF-8 on Windows to handle garak's emoji output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
PYTHON = sys.executable


# ── Tee ──────────────────────────────────────────────────────────────────────

class Tee:
    def __init__(self, filepath):
        self.file = open(filepath, "w", encoding="utf-8")
        self._stdout = sys.stdout
    def write(self, text):
        self._stdout.write(text)
        self.file.write(text)
    def flush(self):
        self._stdout.flush()
        self.file.flush()
    def close(self):
        self.file.close()


# ── Fake LLM HTTP server ──────────────────────────────────────────────────────

class FakeLLMHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        self.rfile.read(content_len)
        body = json.dumps({
            "choices": [{"message": {"content": "I cannot help with that."}}]
        })
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # suppress access logs


def start_fake_server():
    server = HTTPServer(("127.0.0.1", FAKE_SERVER_PORT), FakeLLMHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ── Helpers ───────────────────────────────────────────────────────────────────

SEP = "=" * 60

def section(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def run(cmd, timeout=120, cwd=None):
    """Run command, capture stdout+stderr with utf-8, return CompletedProcess."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=cwd,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    tee = Tee(OUTPUT_FILE)
    sys.stdout = tee

    print("AI-SENTRY B1 — Garak Integration Inspection")
    print(f"Python:     {sys.version}")
    print(f"Executable: {PYTHON}")
    print(f"Platform:   {platform.platform()}")

    # ── TEST 1: garak importable ──────────────────────────────
    section("TEST 1: garak Python import")
    try:
        import garak
        ver = getattr(garak, "__version__", "unknown")
        print(f"  OK  garak {ver}")
        print(f"  Location: {garak.__file__}")
    except ImportError as e:
        print(f"  FAIL: {e}")
        tee.close(); sys.exit(1)

    # ── TEST 2: CLI version ───────────────────────────────────
    section("TEST 2: garak CLI version")
    r = run([PYTHON, "-m", "garak", "--version"])
    print(f"  returncode: {r.returncode}")
    print(f"  stdout: {r.stdout.strip()}")
    if r.stderr.strip():
        print(f"  stderr: {r.stderr.strip()[:300]}")

    # ── TEST 3: list_probes (first 80 lines) ──────────────────
    section("TEST 3: --list_probes (first 80 lines, zz=needs extra deps)")
    r = run([PYTHON, "-m", "garak", "--list_probes"], timeout=60)
    lines = (r.stdout + r.stderr).splitlines()
    for line in lines[:80]:
        print(f"  {line}")
    print(f"  ... ({len(lines)} total lines, showing first 80)")

    # ── TEST 4: Real garak run against fake server ─────────────
    section("TEST 4: Real garak run — fake HTTP server + probes.test.Blank")

    print(f"  Starting fake LLM server on {FAKE_SERVER_URL} ...")
    server = start_fake_server()
    time.sleep(0.3)
    print(f"  Server ready.")

    report_dir = Path(__file__).parent / "garak_b1_output"
    report_dir.mkdir(exist_ok=True)

    # In garak 0.17+, spec must use "probes." prefix
    # garak 0.17+: URI must come from --config YAML, not --target_name.
    # Structure: plugins.generators.rest.RestGenerator.uri
    config_path = report_dir / "garak_rest_config.yaml"

    cmd = [
        PYTHON, "-m", "garak",
        "--target_type", "rest",
        "--config", str(config_path),
        "--spec", "probes.test.Blank",
        "--generations", "1",
        "--report_prefix", str(report_dir / "b1_run"),
    ]
    print(f"\n  Command:\n    {' '.join(cmd)}\n")
    print(f"  Running (up to 90s)...")

    r = run(cmd, timeout=120, cwd=str(report_dir))

    print(f"\n  garak returncode: {r.returncode}")
    print(f"\n  --- STDOUT ---")
    for line in r.stdout.splitlines():
        print(f"    {line}")
    if r.stderr.strip():
        print(f"\n  --- STDERR ---")
        for line in r.stderr.strip().splitlines():
            print(f"    {line}")

    server.shutdown()

    # ── TEST 5: Find and parse real report JSONL ──────────────
    section("TEST 5: Real report JSONL — complete field inspection")

    # Look in our explicit prefix directory first, then garak's default data dir
    report_files = sorted(report_dir.glob("*.jsonl"))

    if not report_files:
        if platform.system() == "Windows":
            default_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "garak" / "garak_runs"
        else:
            default_dir = Path.home() / ".local" / "share" / "garak" / "garak_runs"
        if default_dir.exists():
            report_files = sorted(default_dir.glob("garak.*.report.jsonl"))

    print(f"  Report files found: {len(report_files)}")
    for rf in report_files:
        print(f"    {rf} ({rf.stat().st_size} bytes)")

    if not report_files:
        print("\n  WARNING: No JSONL found. Check stderr above for the report path garak printed.")
    else:
        report_path = report_files[-1]
        print(f"\n  Parsing: {report_path}")

        records = []
        with open(report_path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"  [line {i}] JSON error: {e} → {line[:120]}")

        print(f"\n  Total records: {len(records)}")

        # Deduplicate by entry_type — keep one example of each
        seen = {}
        for rec in records:
            et = rec.get("entry_type", "UNKNOWN")
            if et not in seen:
                seen[et] = rec

        print(f"  Unique entry_types: {list(seen.keys())}\n")

        for et, rec in seen.items():
            print(f"  {'─'*50}")
            print(f"  entry_type: '{et}'")
            print(f"  Top-level keys: {list(rec.keys())}")
            for k, v in rec.items():
                if k == "entry_type":
                    continue
                v_str = json.dumps(v, ensure_ascii=False)
                if len(v_str) > 400:
                    v_str = v_str[:400] + "... [TRUNCATED]"
                print(f"    {k}: {v_str}")
            print()

    section("DONE")
    print(f"Full output: {OUTPUT_FILE}")
    tee.close()
    sys.stdout = tee._stdout


if __name__ == "__main__":
    main()
