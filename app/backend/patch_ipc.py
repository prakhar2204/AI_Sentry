"""Full end-to-end test of scan pipeline with local GGUF model."""
import sys, json, subprocess, threading, time

config = {
    "target": "http://127.0.0.1:11500/v1/chat/completions",
    "mode": "local",
    "scan_depth": "quick",
    "categories": ["prompt_injection", "jailbreak"],
    "engine": "auto",
    "local_model_path": r"F:\models\dolphin-phi.gguf",
}

proc = subprocess.Popen(
    [sys.executable, "-m", "ipc_server"],
    cwd=r"d:\AI_Sentry\app\backend",
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True, encoding="utf-8",
)

proc.stdin.write(json.dumps(config) + "\n")
proc.stdin.flush()
proc.stdin.close()

stdout_lines = []
stderr_lines = []

def read_out():
    for line in proc.stdout:
        stdout_lines.append(line.rstrip())

def read_err():
    for line in proc.stderr:
        stderr_lines.append(line.rstrip())

t1 = threading.Thread(target=read_out, daemon=True)
t2 = threading.Thread(target=read_err, daemon=True)
t1.start(); t2.start()

try:
    proc.wait(timeout=60)
except subprocess.TimeoutExpired:
    proc.terminate()
    print("TIMEOUT after 60s")

t1.join(timeout=2); t2.join(timeout=2)

print("=== STDOUT EVENTS ===")
for i, line in enumerate(stdout_lines):
    try:
        event = json.loads(line)
        etype = event.get("type", "?")
        if etype == "progress":
            print(f"  [{etype}] {event.get('stage', '')} {event.get('percent', '')}% | {event.get('message', '')}")
        elif etype == "stage":
            print(f"  [{etype}] {event.get('stage', '')} — {event.get('message', '')}")
        elif etype == "finding":
            print(f"  [{etype}] {event.get('category', '')} | {event.get('severity', '')} | {event.get('evidence', '')[:60]}")
        elif etype == "activity":
            print(f"  [{etype}] [{event.get('severity', '')}] {event.get('message', '')[:100]}")
        elif etype == "complete":
            report = event.get("report", {})
            print(f"  [{etype}] risk={report.get('risk_score', '?')}/100 | findings={len(report.get('findings', []))}")
        elif etype == "error":
            print(f"  [{etype}] {event.get('message', '')[:150]}")
        else:
            print(f"  [{etype}] {line[:150]}")
    except Exception:
        print(f"  [raw] {line[:150]}")

print(f"\nTotal events: {len(stdout_lines)}")
print(f"Return code: {proc.returncode}")

if stderr_lines:
    print(f"\n=== STDERR (first 5 lines) ===")
    for line in stderr_lines[:5]:
        print(f"  {line[:200]}")
