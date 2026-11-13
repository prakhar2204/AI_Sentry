"""
AI-SENTRY — Local Model Server
core/local_model_server.py

Auto-loads a local .gguf model using the llama.cpp server binary with
GPU acceleration (Vulkan — works on NVIDIA/AMD/Intel without CUDA toolkit),
starts an OpenAI-compatible HTTP server on a free local port, and returns
the server URL for the scan pipeline.

The user only drops the .gguf file — everything else is automatic:
  1. Detect GPU via nvidia-smi
  2. Download llama.cpp server binary on first use (cached in bin/)
     - Primary: Vulkan build (~36 MB, works on all modern GPUs)
     - Fallback: CPU build (~23 MB)
  3. Launch llama-server.exe with -ngl 99 (offload layers to GPU)
  4. Wait for server to accept connections
  5. Return OpenAI-compatible chat completions URL

Binary management:
  - Auto-discovers latest release tag from ggml-org/llama.cpp GitHub API
  - Downloads and caches in app/backend/bin/
  - Re-uses cached binary on subsequent scans
"""

from __future__ import annotations

import json
import os
import pathlib
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from typing import Callable, Optional


# ─── Paths ────────────────────────────────────────────────────────────────────

_BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
_BIN_DIR     = _BACKEND_DIR / "bin"
_SERVER_EXE  = _BIN_DIR / "llama-server.exe"

_GITHUB_API  = "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=5"


# ─── GPU Detection ───────────────────────────────────────────────────────────

def detect_gpu() -> dict:
    """Query NVIDIA GPU info via nvidia-smi."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            parts = [p.strip() for p in r.stdout.strip().split(",")]
            return {
                "available":     True,
                "name":          parts[0] if parts else "Unknown",
                "vram_total_mb": int(parts[1]) if len(parts) > 1 else 0,
                "vram_free_mb":  int(parts[2]) if len(parts) > 2 else 0,
            }
    except Exception:
        pass
    return {"available": False, "name": None, "vram_total_mb": 0, "vram_free_mb": 0}


# ─── Port Utilities ──────────────────────────────────────────────────────────

def _find_free_port(start: int = 11500) -> int:
    for port in range(start, start + 300):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free port in range 11500-11800")


def _wait_for_port(host: str, port: int, timeout: float = 120.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.5)
    return False


# ─── Binary Management ───────────────────────────────────────────────────────

def _discover_release_url(
    prefer_vulkan: bool = True,
    on_log: Optional[Callable[[str], None]] = None,
) -> tuple[str, str]:
    """
    Query GitHub API to find the latest llama.cpp release with Windows binaries.

    Returns (download_url, asset_name).

    Strategy:
      1. Vulkan x64 build (preferred — universal GPU, small ~36 MB)
      2. CPU x64 build (fallback — ~23 MB)
    """
    try:
        req = urllib.request.Request(_GITHUB_API)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "AI-Sentry-Scanner")
        with urllib.request.urlopen(req, timeout=15) as resp:
            releases = json.loads(resp.read())
    except Exception as e:
        raise RuntimeError(f"Cannot reach GitHub API: {e}")

    for rel in releases:
        tag = rel.get("tag_name", "")
        assets = rel.get("assets", [])

        # First pass: find vulkan-x64 (preferred — works on all GPUs)
        if prefer_vulkan:
            for a in assets:
                name = a["name"].lower()
                if "win" in name and "vulkan" in name and "x64" in name:
                    if on_log:
                        on_log(f"Found Vulkan build: {a['name']} ({a['size']//1024//1024} MB)")
                    return a["browser_download_url"], a["name"]

        # Second pass: find cpu-x64 (always works)
        for a in assets:
            name = a["name"].lower()
            if "win" in name and "cpu" in name and "x64" in name:
                if on_log:
                    on_log(f"Found CPU build: {a['name']} ({a['size']//1024//1024} MB)")
                return a["browser_download_url"], a["name"]

    raise RuntimeError("No suitable Windows build found in recent llama.cpp releases")


def _ensure_server_binary(
    on_log: Optional[Callable[[str], None]] = None,
    gpu_available: bool = True,
) -> pathlib.Path:
    """
    Ensure llama-server.exe exists in bin/.
    Downloads from GitHub releases on first use.
    """
    _BIN_DIR.mkdir(parents=True, exist_ok=True)

    if _SERVER_EXE.exists():
        return _SERVER_EXE

    if on_log:
        on_log("First-time setup: downloading llama.cpp server binary...")

    download_url, asset_name = _discover_release_url(
        prefer_vulkan=gpu_available, on_log=on_log,
    )

    zip_path = _BIN_DIR / asset_name

    if on_log:
        on_log(f"Downloading: {download_url}")

    try:
        def _progress(block_num, block_size, total_size):
            if total_size > 0 and on_log and block_num % 50 == 0:
                pct = min(100, int(block_num * block_size * 100 / total_size))
                on_log(f"  Download progress: {pct}%")

        urllib.request.urlretrieve(download_url, zip_path, _progress)
    except Exception as e:
        raise RuntimeError(
            f"Failed to download llama.cpp binary: {e}\n"
            f"URL: {download_url}\n"
            f"Please download manually and place llama-server.exe in: {_BIN_DIR}"
        )

    if on_log:
        on_log("Download complete — extracting llama-server.exe...")

    # Extract all .exe and .dll files to bin/ (flatten paths)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for entry in zf.namelist():
            if entry.endswith(".exe") or entry.endswith(".dll"):
                data = zf.read(entry)
                dest = _BIN_DIR / pathlib.Path(entry).name
                dest.write_bytes(data)

    try:
        zip_path.unlink()
    except Exception:
        pass

    # Find the server executable (may be named llama-server.exe or server.exe)
    if not _SERVER_EXE.exists():
        for candidate in _BIN_DIR.glob("*server*.exe"):
            candidate.rename(_SERVER_EXE)
            break

    if not _SERVER_EXE.exists():
        found = [f.name for f in _BIN_DIR.glob("*.exe")]
        raise RuntimeError(
            f"llama-server.exe not found after extraction.\n"
            f"Files in {_BIN_DIR}: {found}"
        )

    if on_log:
        on_log(f"llama-server.exe ready ({_SERVER_EXE})")

    return _SERVER_EXE


# ─── Local Model Server ─────────────────────────────────────────────────────

class LocalModelServer:
    """
    Lifecycle manager for a local llama.cpp model server.

        server = LocalModelServer()
        url = server.start("/path/to/model.gguf", on_log=print)
        # url → "http://127.0.0.1:11500/v1/chat/completions"
        server.stop()
    """

    def __init__(self):
        self._process:    Optional[subprocess.Popen] = None
        self._port:       Optional[int]              = None
        self._model_path: Optional[str]              = None

    def start(
        self,
        model_path: str,
        on_log: Optional[Callable[[str], None]] = None,
        context_size: int = 4096,
        n_threads: Optional[int] = None,
    ) -> str:
        model_path_obj = pathlib.Path(model_path).resolve()
        if not model_path_obj.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        gpu = detect_gpu()
        ngl = 99 if gpu["available"] else 0   # 99 = offload all layers to GPU

        server_bin = _ensure_server_binary(on_log=on_log, gpu_available=gpu["available"])

        self._port = _find_free_port(11500)
        self._model_path = str(model_path_obj)
        threads = n_threads or max(1, (os.cpu_count() or 4) // 2)

        cmd = [
            str(server_bin),
            "--model",    str(model_path_obj),
            "-ngl",       str(ngl),
            "-c",         str(context_size),
            "-t",         str(threads),
            "--host",     "127.0.0.1",
            "--port",     str(self._port),
        ]

        if on_log:
            accel = f"{gpu['name']} (Vulkan)" if gpu["available"] else "CPU"
            on_log(f"Starting: {model_path_obj.name} | {accel} | Port {self._port}")

        env = os.environ.copy()
        env["PATH"] = str(_BIN_DIR) + os.pathsep + env.get("PATH", "")

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            bufsize=1, env=env, cwd=str(_BIN_DIR),
        )

        if on_log:
            threading.Thread(
                target=self._stream_logs,
                args=(self._process, on_log),
                daemon=True,
            ).start()

        if on_log:
            on_log("Waiting for model to load (10-60 seconds)...")

        if not _wait_for_port("127.0.0.1", self._port, timeout=120.0):
            self.stop()
            raise RuntimeError(
                f"Model server timed out (120s). Model: {model_path_obj.name}\n"
                "Possible causes: insufficient VRAM/RAM, unsupported GGUF format."
            )

        url = f"http://127.0.0.1:{self._port}/v1/chat/completions"
        if on_log:
            on_log(f"Model loaded — server ready at http://127.0.0.1:{self._port}/v1")
        return url

    def stop(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = self._port = self._model_path = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @staticmethod
    def _stream_logs(process: subprocess.Popen, on_log: Callable[[str], None]):
        try:
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    on_log(f"[model] {line}")
        except Exception:
            pass


# ─── Module-level singleton ─────────────────────────────────────────────────

_server_instance: Optional[LocalModelServer] = None


def get_or_create_server() -> LocalModelServer:
    global _server_instance
    if _server_instance is None:
        _server_instance = LocalModelServer()
    return _server_instance


def start_local_model(
    model_path: str,
    on_log: Optional[Callable[[str], None]] = None,
    context_size: int = 4096,
) -> str:
    """Start the local model server. Returns chat completions URL."""
    server = get_or_create_server()
    return server.start(model_path, on_log=on_log, context_size=context_size)


def stop_local_model() -> None:
    """Stop the running local model server and free GPU memory."""
    global _server_instance
    if _server_instance is not None:
        _server_instance.stop()
