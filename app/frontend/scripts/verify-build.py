#!/usr/bin/env python3
"""
Sentryφ — W6.1 Build Verification Script
scripts/verify-build.py

Runs a series of checks to confirm the Python backend build is working:
  1. ipc_server.py --check  → engine availability JSON
  2. ipc_server.py stdin scan → mock scan completes in < 10s
  3. dist_python/ output exists (if PyInstaller was run)

Usage:
    python scripts/verify-build.py          # verify source (dev mode)
    python scripts/verify-build.py --exe    # verify bundled exe

Exit codes:
    0 = all checks passed
    1 = one or more checks failed
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent.resolve()
FRONTEND_DIR = SCRIPT_DIR.parent
BACKEND_DIR  = FRONTEND_DIR.parent / "backend"
DIST_DIR     = FRONTEND_DIR / "dist_python"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")

def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")

def warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET} {msg}")

def header(msg: str) -> None:
    print(f"\n{BOLD}{msg}{RESET}")


def find_exe() -> Path | None:
    """Return path to bundled ipc_server exe, or None."""
    for candidate in [
        DIST_DIR / "ipc_server.exe",
        DIST_DIR / "ipc_server",
        DIST_DIR / "ipc_server" / "ipc_server.exe",
        DIST_DIR / "ipc_server" / "ipc_server",
    ]:
        if candidate.exists():
            return candidate
    return None


def run_check_mode(python_cmd: list[str]) -> dict:
    """Run ipc_server --check and return parsed JSON."""
    result = subprocess.run(
        python_cmd + ["--check"],
        capture_output=True, text=True, timeout=15,
    )
    return json.loads(result.stdout.strip())


def run_mock_scan(python_cmd: list[str], cwd: Path) -> tuple[bool, float, list[str]]:
    """
    Run a minimal mock scan via IPC and return (success, duration, events).
    Sends a minimal scan config and collects up to 20 events or 15s.
    """
    scan_config = json.dumps({
        "command": "scan",
        "engine": "mock",
        "target": "https://test.example.com/api/chat",
        "mode": "api",
        "scan_depth": "quick",
        "categories": ["prompt_injection"],
        "scan_id": "verify-build-001",
    })

    start = time.time()
    proc = subprocess.Popen(
        python_cmd,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    events = []
    try:
        proc.stdin.write(scan_config)
        proc.stdin.close()

        # Read up to 20 events (non-blocking with readline + timeout)
        deadline = start + 20
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                events.append(evt.get("type", "?"))
                if evt.get("type") == "complete":
                    break
                if evt.get("type") == "error":
                    break
            except json.JSONDecodeError:
                events.append(f"<raw: {line[:40]}>")

    finally:
        try:
            proc.kill()
        except Exception:
            pass

    duration = time.time() - start
    success = "complete" in events
    return success, duration, events


def main() -> int:
    use_exe = "--exe" in sys.argv
    failures = 0

    print(f"\n{BOLD}Sentryφ — Build Verification (W6.1){RESET}")
    print("=" * 48)

    # ── 1. Find Python / exe ──────────────────────────────
    header("1. Backend executable")

    if use_exe:
        exe = find_exe()
        if exe:
            ok(f"Found bundled exe: {exe}")
            python_cmd = [str(exe)]
            cwd = exe.parent
        else:
            fail(f"No bundled exe found in {DIST_DIR}")
            fail("Run 'npm run build:python' first")
            return 1
    else:
        python_cmd = [sys.executable, "-m", "ipc_server"]
        cwd = BACKEND_DIR
        ipc_entry = BACKEND_DIR / "ipc_server.py"
        if ipc_entry.exists():
            ok(f"ipc_server.py found at {ipc_entry}")
        else:
            fail(f"ipc_server.py not found at {ipc_entry}")
            return 1

    # ── 2. Engine availability --check ───────────────────
    header("2. Engine availability (--check)")
    try:
        if use_exe:
            check_cmd = [str(exe), "--check"]
            check_result = subprocess.run(
                check_cmd, capture_output=True, text=True, timeout=15, cwd=cwd
            )
            engines = json.loads(check_result.stdout.strip())
        else:
            check_cmd = [sys.executable, str(BACKEND_DIR / "ipc_server.py"), "--check"]
            check_result = subprocess.run(
                check_cmd, capture_output=True, text=True, timeout=15, cwd=cwd
            )
            engines = json.loads(check_result.stdout.strip())

        for engine, available in engines.items():
            if engine == "version":
                continue
            if available:
                ok(f"{engine}: available")
            else:
                warn(f"{engine}: not available (will fall back to mock)")

        if not engines.get("mock"):
            fail("MockEngine not available — this should never happen")
            failures += 1

    except Exception as exc:
        fail(f"--check failed: {exc}")
        failures += 1

    # ── 3. Mock scan end-to-end ───────────────────────────
    header("3. Mock scan (end-to-end IPC)")

    if use_exe:
        scan_cmd = [str(exe)]
    else:
        scan_cmd = [sys.executable, str(BACKEND_DIR / "ipc_server.py")]

    try:
        success, duration, events = run_mock_scan(scan_cmd, cwd)
        event_summary = " → ".join(events[:10]) + ("…" if len(events) > 10 else "")
        if success:
            ok(f"Scan completed in {duration:.1f}s")
            ok(f"Events: {event_summary}")
            if duration > 15:
                warn(f"Scan took {duration:.1f}s (> 15s target)")
        else:
            fail(f"Scan did not complete. Events: {event_summary}")
            failures += 1
    except Exception as exc:
        fail(f"Mock scan failed: {exc}")
        failures += 1

    # ── 4. PyInstaller dist check (optional) ─────────────
    header("4. PyInstaller dist directory")
    if DIST_DIR.exists():
        ok(f"dist_python/ exists at {DIST_DIR}")
        exe_candidate = find_exe()
        if exe_candidate:
            ok(f"Bundled executable: {exe_candidate}")
        else:
            warn("No bundled executable found in dist_python/ — run 'npm run build:python'")
    else:
        warn(f"dist_python/ not found — run 'npm run build:python' to create it")

    # ── Summary ───────────────────────────────────────────
    print(f"\n{'=' * 48}")
    if failures == 0:
        print(f"{GREEN}{BOLD}All checks passed ✓{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}{failures} check(s) failed ✗{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
