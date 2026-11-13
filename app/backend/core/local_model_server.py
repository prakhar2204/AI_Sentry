"""
AI-SENTRY -- Local Model Server
core/local_model_server.py

Auto-loads a local .gguf model using the llama.cpp server binary with
full GPU acceleration (CUDA), starts an OpenAI-compatible HTTP server
on a free local port, and returns the server URL for the scan pipeline.

The user only needs to drop the .gguf file — no Ollama, no manual setup.
Everything is handled internally:
  1. Detect NVIDIA GPU via nvidia-smi
  2. Download llama.cpp server binary on first use (cached to bin/)
  3. Launch the server with n-gpu-layers=-1 (all layers on GPU)
  4. Wait for the server to become ready
  5. Return the OpenAI-compatible chat completions URL

GPU Usage:
  - n-gpu-layers=-1  → all transformer layers on VRAM (fastest)
  - Falls back to CPU if no NVIDIA GPU or CUDA libraries not available

Lifecycle:
  start(path)  → server_url (blocks until ready, up to 120s)
  stop()       → terminates the server process and frees VRAM

Binary source:
  https://github.com/ggerganov/llama.cpp/releases
  Windows CUDA 12 release: llama-b<N>-bin-win-cuda12-x64.zip
  Contains: llama-server.exe + CUDA DLLs
"""

from __future__ import annotations

import os
import io
import json
import socket
import pathlib
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from typing import Callable, Optional


# ─────────────────────────────────────────────
#  Paths
# ─────────────────────────────────────────────

_BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
_BIN_DIR     = _BACKEND_DIR / "bin"
_SERVER_EXE  = _BIN_DIR / "llama-server.exe"

# GitHub release — CUDA 12 build for Windows x64
# Pin to a known-good release tag for reproducibility
_LLAMA_RELEASE_TAG  = "b4556"
_LLAMA_ASSET_NAME   = f"llama-{_LLAMA_RELEASE_TAG}-bin-win-cuda12-x64.zip"
_LLAMA_DOWNLOAD_URL = (
    f"https://github.com/ggerganov/llama.cpp/releases/download/"
    f"{_LLAMA_RELEASE_TAG}/{_LLAMA_ASSET_NAME}"
)

# Fallback: CPU-only build (smaller, no CUDA DLLs required)
_LLAMA_ASSET_CPU    = f"llama-{_LLAMA_RELEASE_TAG}-bin-win-noavx-x64.zip"
_LLAMA_DOWNLOAD_CPU = (
    f"https://github.com/ggerganov/llama.cpp/releases/download/"
    f"{_LLAMA_RELEASE_TAG}/{_LLAMA_ASSET_CPU}"
)


# ─────────────────────────────────────────────
#  GPU Detection
# ─────────────────────────────────────────────

def detect_gpu() -> dict:
    """
    Query NVIDIA GPU info via nvidia-smi.
    Returns: { available, name, vram_total_mb, vram_free_mb }
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = [p.strip() for p in result.stdout.strip().split(",")]
            return {
                "available":     True,
                "name":          parts[0] if parts else "Unknown GPU",
                "vram_total_mb": int(parts[1]) if len(parts) > 1 else 0,
                "vram_free_mb":  int(parts[2]) if len(parts) > 2 else 0,
            }
    except Exception:
        pass
    return {"available": False, "name": None, "vram_total_mb": 0, "vram_free_mb": 0}


# ─────────────────────────────────────────────
#  Binary management
# ─────────────────────────────────────────────

def _find_free_port(start: int = 11500) -> int:
    """Find a free TCP port starting from `start`."""
    for port in range(start, start + 300):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free port found in range 11500-11800")


def _wait_for_port(host: str, port: int, timeout: float = 120.0) -> bool:
    """Block until the given port accepts connections or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.5)
    return False


def _ensure_server_binary(
    on_log: Optional[Callable[[str], None]] = None,
    gpu_available: bool = True,
) -> pathlib.Path:
    """
    Ensure the llama-server.exe binary exists in bin/.
    Downloads and extracts it from GitHub releases on first use.

    Returns the path to llama-server.exe.
    """
    _BIN_DIR.mkdir(parents=True, exist_ok=True)

    if _SERVER_EXE.exists():
        return _SERVER_EXE

    # Choose build: CUDA if GPU available, else CPU
    asset_name   = _LLAMA_ASSET_NAME   if gpu_available else _LLAMA_ASSET_CPU
    download_url = _LLAMA_DOWNLOAD_URL  if gpu_available else _LLAMA_DOWNLOAD_CPU
    build_type   = "CUDA 12" if gpu_available else "CPU"

    if on_log:
        on_log(f"Downloading llama.cpp server ({build_type}) — first-time setup, ~50-150 MB...")
        on_log(f"Source: {download_url}")

    # Download with progress
    zip_path = _BIN_DIR / asset_name
    try:
        def _report_progress(block_num, block_size, total_size):
            if total_size > 0 and on_log:
                pct = min(100, int(block_num * block_size * 100 / total_size))
                if pct % 10 == 0:
                    on_log(f"  Downloading llama.cpp binary: {pct}%")

        urllib.request.urlretrieve(download_url, zip_path, _report_progress)
    except Exception as e:
        # Try CPU fallback if CUDA download failed
        if gpu_available:
            if on_log:
                on_log(f"CUDA build download failed ({e}), trying CPU build...")
            try:
                urllib.request.urlretrieve(_LLAMA_DOWNLOAD_CPU, zip_path)
            except Exception as e2:
                raise RuntimeError(
                    f"Failed to download llama.cpp binary.\n"
                    f"CUDA error: {e}\nCPU error: {e2}\n"
                    f"Please download manually from:\n{_LLAMA_DOWNLOAD_URL}\n"
                    f"and place llama-server.exe in: {_BIN_DIR}"
                )
        else:
            raise RuntimeError(
                f"Failed to download llama.cpp binary: {e}\n"
                f"Please download manually from:\n{_LLAMA_DOWNLOAD_CPU}\n"
                f"and place llama-server.exe in: {_BIN_DIR}"
            )

    if on_log:
        on_log("Download complete — extracting llama-server.exe...")

    # Extract all files from the zip
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Find llama-server.exe (may be in a subdirectory)
        for name in zf.namelist():
            # Extract all .exe and .dll files to bin/
            if name.endswith(".exe") or name.endswith(".dll"):
                # Flatten path — extract to bin/ directly
                file_data = zf.read(name)
                dest = _BIN_DIR / pathlib.Path(name).name
                dest.write_bytes(file_data)

    # Clean up zip
    try:
        zip_path.unlink()
    except Exception:
        pass

    if not _SERVER_EXE.exists():
        # Try alternative names
        for candidate in _BIN_DIR.glob("*server*.exe"):
            candidate.rename(_SERVER_EXE)
            break
        for candidate in _BIN_DIR.glob("server.exe"):
            candidate.rename(_SERVER_EXE)
            break

    if not _SERVER_EXE.exists():
        raise RuntimeError(
            f"llama-server.exe not found after extraction in {_BIN_DIR}.\n"
            f"Files found: {list(_BIN_DIR.glob('*.exe'))}"
        )

    if on_log:
        on_log(f"llama-server.exe ready at {_SERVER_EXE}")

    return _SERVER_EXE


# ─────────────────────────────────────────────
#  LocalModelServer
# ─────────────────────────────────────────────

class LocalModelServer:
    """
    Manages the lifecycle of a local llama.cpp model server.

    Usage:
        server = LocalModelServer()
        url = server.start("/path/to/model.gguf", on_log=print)
        # → "http://127.0.0.1:11500/v1/chat/completions"
        # ... run scan against url ...
        server.stop()
    """

    def __init__(self):
        self._process:    Optional[subprocess.Popen] = None
        self._port:       Optional[int]              = None
        self._model_path: Optional[str]              = None

    # ── Public API ─────────────────────────────

    def start(
        self,
        model_path: str,
        on_log: Optional[Callable[[str], None]] = None,
        context_size: int = 4096,
        n_threads: Optional[int] = None,
    ) -> str:
        """
        Load the GGUF model and start the OpenAI-compatible server.

        Parameters
        ----------
        model_path   : Full path to the .gguf model file.
        on_log       : Optional log line callback.
        context_size : Context window in tokens (default 4096).
        n_threads    : CPU threads to use (default: half of CPU count).

        Returns
        -------
        str : Chat completions endpoint, e.g.
              "http://127.0.0.1:11500/v1/chat/completions"
        """
        model_path_obj = pathlib.Path(model_path).resolve()
        if not model_path_obj.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}\n"
                "Provide the full path to your .gguf file."
            )

        gpu = detect_gpu()
        n_gpu_layers = -1 if gpu["available"] else 0

        # Ensure binary is available (downloads on first use)
        server_bin = _ensure_server_binary(on_log=on_log, gpu_available=gpu["available"])

        self._port = _find_free_port(11500)
        self._model_path = str(model_path_obj)

        threads = n_threads or max(1, (os.cpu_count() or 4) // 2)

        cmd = [
            str(server_bin),
            "--model",         str(model_path_obj),
            "--n-gpu-layers",  str(n_gpu_layers),
            "--ctx-size",      str(context_size),
            "--threads",       str(threads),
            "--host",          "127.0.0.1",
            "--port",          str(self._port),
            "--log-disable",                   # suppress verbose llama.cpp logs
            "--no-mmap",                       # safer on Windows
        ]

        if on_log:
            accel = f"{gpu['name']} (CUDA)" if gpu["available"] else "CPU"
            on_log(f"Starting llama.cpp server: {model_path_obj.name}")
            on_log(f"Acceleration: {accel} | GPU layers: {'all' if n_gpu_layers == -1 else n_gpu_layers}")
            on_log(f"Context: {context_size} tokens | Threads: {threads} | Port: {self._port}")

        # Set DLL search path so CUDA DLLs in bin/ are found
        env = os.environ.copy()
        env["PATH"] = str(_BIN_DIR) + os.pathsep + env.get("PATH", "")

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
            cwd=str(_BIN_DIR),
        )

        # Stream logs in background
        if on_log:
            threading.Thread(
                target=self._stream_logs,
                args=(self._process, on_log),
                daemon=True,
            ).start()

        # Wait for server to accept connections
        if on_log:
            on_log("Waiting for model to load (this may take 10-60 seconds)...")

        ready = _wait_for_port("127.0.0.1", self._port, timeout=120.0)

        if not ready:
            stderr_tail = ""
            try:
                self._process.terminate()
            except Exception:
                pass
            raise RuntimeError(
                f"Model server failed to start within 120 seconds.\n"
                f"Model: {model_path}\n"
                "Possible causes:\n"
                "  - Insufficient VRAM or RAM for this model\n"
                "  - Unsupported GGUF quantization format\n"
                "  - Missing CUDA runtime DLLs\n"
                f"Try a smaller model or use --n-gpu-layers 0 for CPU-only mode."
            )

        url = f"http://127.0.0.1:{self._port}/v1/chat/completions"
        if on_log:
            on_log(f"Model loaded and ready at http://127.0.0.1:{self._port}/v1")
        return url

    def stop(self) -> None:
        """Terminate the model server process, freeing VRAM."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process    = None
        self._port       = None
        self._model_path = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @staticmethod
    def _stream_logs(
        process: subprocess.Popen,
        on_log: Callable[[str], None],
    ) -> None:
        try:
            for line in process.stdout:
                line = line.rstrip()
                if line and not line.startswith("llama"):  # skip verbose llama internals
                    on_log(f"[model] {line}")
        except Exception:
            pass


# ─────────────────────────────────────────────
#  Module-level singleton
# ─────────────────────────────────────────────

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
    """
    Start the local model server and return its chat completions URL.

    This is the main entry point called by ipc_server.py.

    Parameters
    ----------
    model_path   : Full path to the .gguf file.
    on_log       : Log callback (each call = one log line).
    context_size : Token context window size.

    Returns
    -------
    str : "http://127.0.0.1:<port>/v1/chat/completions"
    """
    server = get_or_create_server()
    return server.start(model_path, on_log=on_log, context_size=context_size)


def stop_local_model() -> None:
    """Stop the running local model server and free VRAM."""
    global _server_instance
    if _server_instance is not None:
        _server_instance.stop()
