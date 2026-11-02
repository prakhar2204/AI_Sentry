#!/usr/bin/env python3
"""
Sentryɸ — Python Backend Build Script
scripts/build-python.py

Packages the Python IPC server (and all dependencies including garak + pyrit)
into a standalone self-contained executable using PyInstaller.

Usage:
    python scripts/build-python.py           # build for current platform
    python scripts/build-python.py --onefile # single .exe (default)
    python scripts/build-python.py --onedir  # directory bundle (faster cold start)
    python scripts/build-python.py --check   # check deps only, don't build

Output:
    dist/ipc_server/           (onedir mode)
    dist/ipc_server.exe        (onefile mode, Windows)
    dist/ipc_server            (onefile mode, Linux/Mac)

The output is then picked up by electron-builder via the extraResources config
in package.json and bundled into the installer under resources/backend/.

Engine availability in the bundle:
    - MockEngine:    always available (zero external deps)
    - GarakAdapter:  included if garak is installed in the build environment
    - PyRITAdapter:  included if pyrit is installed in the build environment

Any engine NOT installed at build time will show as unavailable at runtime,
but the app will gracefully fall back to MockEngine.
"""

from __future__ import annotations

import os
import subprocess
import sys
import importlib.util
from pathlib import Path

# ─────────────────────────────────────────────
#  Paths
# ─────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent.resolve()
FRONTEND_DIR = SCRIPT_DIR.parent          # app/frontend
BACKEND_DIR  = FRONTEND_DIR.parent / "backend"  # app/backend
DIST_DIR     = FRONTEND_DIR / "dist_python"   # output: frontend/dist_python/
ENTRY_POINT  = BACKEND_DIR / "ipc_server.py"

# ─────────────────────────────────────────────
#  Engine availability check
# ─────────────────────────────────────────────

def _engine_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def check_engines() -> dict[str, bool]:
    engines = {
        "garak":  _engine_available("garak"),
        "pyrit":  _engine_available("pyrit"),
    }
    print("\n── Engine availability ─────────────────────")
    for eng, avail in engines.items():
        status = "✓ available — will be bundled" if avail else "✗ not installed — will be skipped"
        print(f"  {eng:12s} {status}")
    print()
    return engines


# ─────────────────────────────────────────────
#  PyInstaller checks
# ─────────────────────────────────────────────

def ensure_pyinstaller() -> None:
    if importlib.util.find_spec("PyInstaller") is None:
        print("PyInstaller not found. Installing...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller>=6.0", "--quiet"]
        )
        print("PyInstaller installed.\n")


# ─────────────────────────────────────────────
#  Hidden imports
# ─────────────────────────────────────────────

ALWAYS_HIDDEN = [
    # Core backend modules (not directly imported at top level by ipc_server)
    "core.manifest",
    "core.engine_interface",
    "core.engine_runner",
    "core.mock_engine",
    "core.scorer",
    "core.recommender",
    "core.report_generator",
    "core.normalizer",
    "core.adapters",
    "core.adapters.garak_adapter",
    "core.adapters.pyrit_adapter",
    "core.validator",
    "core.estimator",
    "core.export_handler",
    # Python standard library used indirectly
    "json",
    "pathlib",
    "dataclasses",
    "enum",
    "uuid",
    "time",
    "datetime",
    # httpx (endpoint validator)
    "httpx",
    "certifi",
    "anyio",
    "sniffio",
    "h11",
]

GARAK_HIDDEN = [
    "garak",
    "garak.cli",
    "garak.generators",
    "garak.generators.rest",
    "garak.probes",
    "garak.detectors",
    "garak.harnesses",
    "garak.evaluators",
    "garak.attempt",
    "garak.report",
    "core.garak_engine",
]

PYRIT_HIDDEN = [
    "pyrit",
    "pyrit.prompt_target",
    "pyrit.orchestrator",
    "pyrit.memory",
    "pyrit.score",
    "pyrit.common",
    "core.pyrit_engine",
]


# ─────────────────────────────────────────────
#  Build
# ─────────────────────────────────────────────

def build(onefile: bool = True) -> int:
    """Run PyInstaller and return exit code."""
    engines = check_engines()
    ensure_pyinstaller()

    hidden = list(ALWAYS_HIDDEN)
    if engines["garak"]:
        hidden.extend(GARAK_HIDDEN)
    if engines["pyrit"]:
        hidden.extend(PYRIT_HIDDEN)

    # Collect data files — backend Python source (needed for relative imports in core/)
    data_specs = [
        f"{BACKEND_DIR}{os.sep}core{os.sep}*{os.sep}*.py:core",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(ENTRY_POINT),
        "--name",       "ipc_server",
        "--distpath",   str(DIST_DIR),
        "--workpath",   str(DIST_DIR / "_build"),
        "--specpath",   str(DIST_DIR / "_spec"),
        "--noconfirm",
        "--clean",
        "--log-level",  "WARN",
    ]

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # Add hidden imports
    for hi in hidden:
        cmd += ["--hidden-import", hi]

    # Add data: backend core source tree (keeps relative imports working)
    cmd += ["--paths", str(BACKEND_DIR)]

    # Add backend as a datas entry so core/ package is importable
    cmd += [
        "--add-data", f"{BACKEND_DIR}{os.pathsep}backend",
    ]

    # Exclude heavy packages that are test-only or not needed at runtime
    for exc in ["pytest", "hypothesis", "mypy", "ruff", "respx"]:
        cmd += ["--exclude-module", exc]

    print("── Building Python bundle ──────────────────")
    print(f"  Entry:  {ENTRY_POINT}")
    print(f"  Output: {DIST_DIR}")
    print(f"  Mode:   {'onefile' if onefile else 'onedir'}")
    print(f"  Engines: {', '.join(k for k, v in engines.items() if v) or 'none (mock only)'}")
    print()

    result = subprocess.run(cmd)
    return result.returncode


# ─────────────────────────────────────────────
#  Post-build: copy to frontend resource path
# ─────────────────────────────────────────────

def copy_to_resources(onefile: bool) -> None:
    """Copy the built bundle to app/frontend/resources/backend/ for electron-builder."""
    import shutil
    resources_dir = FRONTEND_DIR / "resources" / "backend"
    resources_dir.mkdir(parents=True, exist_ok=True)

    if onefile:
        # Single file
        candidates = [
            DIST_DIR / "ipc_server.exe",  # Windows
            DIST_DIR / "ipc_server",      # Linux/Mac
        ]
        for src in candidates:
            if src.exists():
                dst = resources_dir / src.name
                shutil.copy2(src, dst)
                print(f"Copied: {src} → {dst}")
                return
        print("WARNING: Could not find built ipc_server binary to copy.")
    else:
        # Directory bundle
        src_dir = DIST_DIR / "ipc_server"
        dst_dir = resources_dir / "ipc_server"
        if src_dir.exists():
            if dst_dir.exists():
                shutil.rmtree(dst_dir)
            shutil.copytree(src_dir, dst_dir)
            print(f"Copied directory: {src_dir} → {dst_dir}")
        else:
            print("WARNING: Could not find built ipc_server directory to copy.")


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Build Sentryɸ Python backend")
    parser.add_argument("--onefile", action="store_true", default=True,
                        help="Build as single executable (default)")
    parser.add_argument("--onedir",  action="store_true",
                        help="Build as directory bundle (faster cold start)")
    parser.add_argument("--check",   action="store_true",
                        help="Check dependencies only, do not build")
    args = parser.parse_args()

    if args.check:
        check_engines()
        ensure_pyinstaller()
        print("All checks passed.")
        return

    onefile = not args.onedir
    rc = build(onefile=onefile)
    if rc == 0:
        copy_to_resources(onefile=onefile)
        print("\n✓ Python backend bundle ready.\n")
        if onefile:
            print("  Location: app/frontend/resources/backend/ipc_server[.exe]")
        else:
            print("  Location: app/frontend/resources/backend/ipc_server/")
        print("\nNext step: npm run build:electron  (to package the full Electron app)")
    else:
        print(f"\n✗ PyInstaller failed with exit code {rc}", file=sys.stderr)
        sys.exit(rc)


if __name__ == "__main__":
    main()
