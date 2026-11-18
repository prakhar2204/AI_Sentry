"""
AI-SENTRY Phase 4 (Garak) — B2: Probe Mapping Table Verification
=================================================================
Maps AI-SENTRY's 6 security categories to real garak probe modules
(verified from --list_probes output), then runs each probe individually
against the fake server to confirm no errors.

Only probes WITHOUT the sleep emoji (no extra deps) are used.
Each probe is run with --generations 1 for speed.

Output: tests/b2_output.txt
"""

import json
import sys
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PYTHON = sys.executable
OUTPUT_FILE = Path(__file__).parent / "b2_output.txt"
FAKE_PORT = 18766  # different port from B1 to avoid conflicts
FAKE_URL = f"http://127.0.0.1:{FAKE_PORT}"
CONFIG_DIR = Path(__file__).parent / "garak_b1_output"
REPORT_DIR = Path(__file__).parent / "garak_b2_output"
REPORT_DIR.mkdir(exist_ok=True)

# ── Force UTF-8 on Windows ────────────────────────────────────────────────────
import io
_orig_stdout = sys.stdout  # save before any wrapping
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
_utf8_stdout = sys.stdout  # the wrapped version


# ──────────────────────────────────────────────────────────────────────────────
#  CATEGORY MAP
#  AI-SENTRY category → list of garak probe specs (no-extra-dep probes only)
#  Selected from real --list_probes output, chosen for semantic fit.
# ──────────────────────────────────────────────────────────────────────────────

CATEGORY_MAP = {
    "prompt_injection": [
        "probes.promptinject.HijackHateHumans",
        "probes.promptinject.HijackKillHumans",
        "probes.promptinject.HijackLongPrompt",
    ],
    "jailbreak": [
        "probes.dan.Ablation_Dan_11_0",
        "probes.dan.AutoDANCached",
        "probes.dan.DanInTheWild",
    ],
    "encoding_injection": [
        "probes.encoding.InjectBase64",
        "probes.encoding.InjectROT13",
        "probes.encoding.InjectHex",
        "probes.encoding.InjectMorse",
    ],
    "data_leakage": [
        "probes.leakreplay.GuardianCloze",
        "probes.leakreplay.GuardianComplete",
        "probes.sysprompt_extraction.SystemPromptExtraction",
    ],
    "malware_generation": [
        "probes.malwaregen.Evasion",
        "probes.malwaregen.Payload",
        "probes.malwaregen.SubFunctions",
        "probes.malwaregen.TopLevel",
    ],
    "toxicity": [
        "probes.continuation.ContinueSlursReclaimedSlurs",
        "probes.lmrc.Bullying",
        "probes.lmrc.SlurUsage",
        "probes.grandma.Slurs",
    ],
}


# ── Fake LLM Server ───────────────────────────────────────────────────────────

class FakeLLMHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        self.rfile.read(content_len)
        body = json.dumps({
            "choices": [{"message": {"content": "I cannot help with that."}}]
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def start_server():
    server = HTTPServer(("127.0.0.1", FAKE_PORT), FakeLLMHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


def write_config(port):
    cfg = CONFIG_DIR / f"rest_config_{port}.yaml"
    cfg.write_text(f"""plugins:
  generators:
    rest:
      RestGenerator:
        uri: http://127.0.0.1:{port}
        method: post
        response_json: true
        response_json_field: "$.choices[0].message.content"
        req_template: "$INPUT"
        headers:
          Content-Type: application/json
""")
    return cfg


def run_probe(spec, config_path, report_prefix, timeout=90):
    """Run a single garak probe, return (returncode, stdout, stderr)."""
    cmd = [
        PYTHON, "-m", "garak",
        "--target_type", "rest",
        "--config", str(config_path),
        "--spec", spec,
        "--generations", "1",
        "--report_prefix", str(report_prefix),
    ]
    r = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        timeout=timeout
    )
    return r.returncode, r.stdout, r.stderr


SEP = "=" * 60

def section(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def main():
    tee_file = open(OUTPUT_FILE, "w", encoding="utf-8")

    class Tee:
        def write(self, t):
            _utf8_stdout.write(t)
            tee_file.write(t)
        def flush(self):
            _utf8_stdout.flush()
            tee_file.flush()

    sys.stdout = Tee()

    print("AI-SENTRY B2 — Probe Mapping Table Verification")
    print(f"Python: {sys.version}")

    section("CATEGORY MAP (6 categories, no-extra-dep probes only)")
    for cat, probes in CATEGORY_MAP.items():
        print(f"\n  {cat}:")
        for p in probes:
            print(f"    {p}")

    # Start fake server
    section("Starting fake LLM server")
    config_path = write_config(FAKE_PORT)
    server = start_server()
    time.sleep(0.3)
    print(f"  Fake server on {FAKE_URL}")
    print(f"  Config: {config_path}")

    # Run each category's probes
    section("Running each probe individually")

    results = {}  # category → {probe → {ok, rc, note}}

    for category, probes in CATEGORY_MAP.items():
        print(f"\n  {'─'*50}")
        print(f"  CATEGORY: {category}")
        print(f"  {'─'*50}")
        results[category] = {}

        for spec in probes:
            short = spec.replace("probes.", "")
            report_prefix = REPORT_DIR / f"b2_{short.replace('.', '_')}"
            print(f"\n  Probe: {spec}")
            print(f"    Running...", flush=True)

            try:
                rc, stdout, stderr = run_probe(spec, config_path, report_prefix)
            except subprocess.TimeoutExpired:
                print(f"    TIMEOUT (>90s)")
                results[category][spec] = {"ok": False, "rc": -1, "note": "TIMEOUT"}
                continue

            # Determine pass/fail from stdout content and returncode
            ok = rc == 0
            # Grab last meaningful stdout lines
            stdout_lines = [l for l in stdout.splitlines() if l.strip()]
            last_lines = stdout_lines[-5:] if stdout_lines else []

            # Extract eval line if present
            eval_line = next((l for l in stdout_lines if "✔️" in l or "❌" in l
                              or "passed" in l.lower() or "PASS" in l or "FAIL" in l
                              or "%" in l), "")

            # Check for actual errors (not just probe findings)
            error_indicators = [
                "Traceback", "Error:", "ImportError", "ModuleNotFoundError",
                "invalid --spec", "No module", "Exception"
            ]
            has_error = any(
                any(ind in line for ind in error_indicators)
                for line in (stdout + stderr).splitlines()
            )

            status = "OK" if (rc == 0 and not has_error) else "ERROR"
            results[category][spec] = {
                "ok": rc == 0 and not has_error,
                "rc": rc,
                "note": eval_line or (last_lines[-1] if last_lines else "")
            }

            print(f"    returncode: {rc}  status: {status}")
            for line in last_lines:
                print(f"    > {line}")
            if has_error:
                err_lines = [l for l in (stdout + stderr).splitlines()
                             if any(ind in l for ind in error_indicators)]
                for line in err_lines[:3]:
                    print(f"    ERROR: {line}")

    server.shutdown()

    # ── Summary table ─────────────────────────────────────────
    section("B2 SUMMARY TABLE")
    print(f"\n  {'Category':<25} {'Probe':<50} {'Status'}")
    print(f"  {'-'*25} {'-'*50} {'-'*8}")
    all_ok = True
    for cat, probes in results.items():
        for spec, res in probes.items():
            short = spec.replace("probes.", "")
            status = "OK" if res["ok"] else "FAIL"
            if not res["ok"]:
                all_ok = False
            print(f"  {cat:<25} {short:<50} {status}")

    print(f"\n  All probes OK: {all_ok}")

    section("DONE")
    print(f"Full output: {OUTPUT_FILE}")
    tee_file.close()
    sys.stdout = _utf8_stdout


if __name__ == "__main__":
    main()
