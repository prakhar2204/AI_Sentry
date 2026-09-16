"""
AI-SENTRY -- Local Model Handler
core/local_handler.py

Validates and tests a locally-running llama.cpp (or compatible)
OpenAI-style server at a loopback / LAN address.

Phase 1c deliverable.

Expected server setup (user must run this themselves):
    llama-server -m model.gguf --host 0.0.0.0 --port 8080
    # Then target: http://localhost:8080

The server exposes an OpenAI-compatible API at:
    POST /v1/chat/completions
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from core.input_handler import ProbeResult  # reuse shared result type


# ─────────────────────────────────────────────
#  Types
# ─────────────────────────────────────────────

@dataclass
class LocalValidationResult:
    """Result of validate_local_endpoint()."""
    valid:         bool
    normalized_url: str = ""
    error:         str  = ""


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

_CONNECT_TIMEOUT = 5.0     # local servers should respond instantly
_READ_TIMEOUT    = 60.0    # local inference can be slow (large models)
_TEST_PROMPT     = "Reply only with the word: OK"

_CHAT_PATH = "/v1/chat/completions"

_DIVIDER = "-" * 60

# Hosts considered "local" — anything else triggers a warning but is allowed
_LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
}


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def validate_local_endpoint(target: str) -> LocalValidationResult:
    """
    Validate a user-supplied target for local-mode operation.

    Rules:
      - Must be an http:// URL (local servers rarely use TLS)
      - https:// is also accepted
      - Should point to localhost / 127.0.0.1 (warning otherwise)
      - Path is optional — /v1/chat/completions is appended automatically

    Returns a LocalValidationResult with .valid, .normalized_url, .error.
    """
    target = target.strip()

    if not target:
        return LocalValidationResult(
            valid=False,
            error="Target cannot be empty. Example: http://localhost:8080",
        )

    parsed = urlparse(target)

    # Scheme check
    if parsed.scheme not in ("http", "https"):
        return LocalValidationResult(
            valid=False,
            error=(
                f"Invalid URL scheme '{parsed.scheme or '(none)'}'. "
                "Local endpoints must use http:// or https://  "
                "Example: http://localhost:8080"
            ),
        )

    # Host check
    if not parsed.netloc:
        return LocalValidationResult(
            valid=False,
            error=(
                "No host in URL. "
                "Example: http://localhost:8080"
            ),
        )

    # Warn if not obviously local (but still allow — user may be on LAN)
    hostname = parsed.hostname or ""
    if hostname not in _LOCAL_HOSTS and not hostname.startswith("192.168.") \
            and not hostname.startswith("10.") and not hostname.startswith("172."):
        _print_warn(
            f"Host '{hostname}' does not look like a local address. "
            "Use --mode api for remote endpoints."
        )

    normalized = target.rstrip("/")

    return LocalValidationResult(valid=True, normalized_url=normalized)


def probe_local_model(url: str) -> ProbeResult:
    """
    Send a minimal chat request to a locally running llama.cpp server.

    Constructs the full /v1/chat/completions path automatically.
    Does not send an API key (local servers do not require one).

    Returns a ProbeResult with .success, .status_code, .response_text,
    .latency_ms, and .error populated.
    """
    chat_url = _build_chat_url(url)
    payload  = _build_test_payload()
    headers  = {"Content-Type": "application/json"}

    _print_status(f"  Connecting to: {chat_url}")

    try:
        with httpx.Client(
            timeout=httpx.Timeout(
                connect=_CONNECT_TIMEOUT,
                read=_READ_TIMEOUT,
                write=10.0,
                pool=5.0,
            )
        ) as client:
            t0 = time.monotonic()
            response = client.post(chat_url, json=payload, headers=headers)
            latency_ms = (time.monotonic() - t0) * 1000

    except httpx.ConnectError as exc:
        # Most likely: server not running or wrong port
        return ProbeResult(
            success=False,
            error=(
                "Connection refused -- is the llama.cpp server running?\n"
                f"  Detail: {exc}\n\n"
                "  Start the server with:\n"
                "    llama-server -m <your-model.gguf> --host 0.0.0.0 --port 8080\n"
                "  Then retry:\n"
                "    python __main__.py scan --mode local --target http://localhost:8080"
            ),
        )

    except httpx.TimeoutException:
        return ProbeResult(
            success=False,
            error=(
                f"Request timed out after {_READ_TIMEOUT}s. "
                "The model may still be loading. Wait a few seconds and retry."
            ),
        )

    except httpx.RequestError as exc:
        return ProbeResult(
            success=False,
            error=f"Network error: {exc}",
        )

    return _interpret_response(response, latency_ms)


# ─────────────────────────────────────────────
#  CLI-facing orchestrator
# ─────────────────────────────────────────────

def run_local_validation(target: str) -> bool:
    """
    Full pipeline for --mode local:

        1. Validate the target URL format
        2. Send a test chat request to the local server
        3. Print human-readable result

    Returns True on success, False on any failure.
    Called by cli/main.py after the consent gate passes.
    """
    print(f"\n{_DIVIDER}")
    print("  LOCAL MODEL CONNECTION TEST")
    print(_DIVIDER)

    # ── Step 1: Validate URL ───────────────────
    print(f"\n  [1/2] Validating local target: {target}")
    validation = validate_local_endpoint(target)

    if not validation.valid:
        _print_error(validation.error)
        return False

    _print_ok("Local endpoint URL is valid.")

    # ── Step 2: Probe the server ───────────────
    print(f"\n  [2/2] Sending test prompt to local model...")
    result = probe_local_model(validation.normalized_url)

    if not result.success:
        _print_error(result.error)
        if result.status_code:
            print(f"  HTTP status: {result.status_code}")
        return False

    _print_ok(
        f"Local model is responsive.  "
        f"(HTTP {result.status_code}, {result.latency_ms:.0f} ms)"
    )

    if result.response_text:
        preview = result.response_text[:200].replace("\n", " ").strip()
        print(f"\n  Model response: \"{preview}\"")

    print(f"\n{_DIVIDER}\n")
    return True


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────

def _build_chat_url(base_url: str) -> str:
    """
    Append /v1/chat/completions to the base URL unless already present.

    Handles these cases:
      http://localhost:8080          -> http://localhost:8080/v1/chat/completions
      http://localhost:8080/v1       -> http://localhost:8080/v1/chat/completions
      http://localhost:8080/v1/chat/completions  -> unchanged
    """
    url = base_url.rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/completions"):
        return url
    if url.endswith("/v1"):
        return url + "/chat/completions"
    return url + _CHAT_PATH


def _build_test_payload() -> dict:
    """
    Build a minimal OpenAI-compatible chat request.

    llama.cpp does not require a real model name — we send an empty
    string or a placeholder; the server ignores it and uses the
    loaded model.
    """
    return {
        "model":       "local-model",     # ignored by llama.cpp server
        "messages":    [{"role": "user", "content": _TEST_PROMPT}],
        "max_tokens":  10,
        "temperature": 0.0,
        "stream":      False,
    }


def _interpret_response(response: httpx.Response, latency_ms: float) -> ProbeResult:
    """Parse the HTTP response from the local server."""

    if response.status_code == 404:
        return ProbeResult(
            success=False,
            status_code=response.status_code,
            error=(
                "Endpoint not found (HTTP 404). "
                "Check the server is running with OpenAI-compatible API. "
                "llama.cpp uses /v1/chat/completions — verify your --target includes the right base."
            ),
        )

    if response.status_code == 400:
        body = response.text[:300]
        return ProbeResult(
            success=False,
            status_code=response.status_code,
            error=f"Bad request (HTTP 400). Server says: {body}",
        )

    if response.status_code >= 500:
        return ProbeResult(
            success=False,
            status_code=response.status_code,
            error=(
                f"Server error (HTTP {response.status_code}). "
                "The local model server crashed or is overloaded."
            ),
        )

    if not response.is_success:
        return ProbeResult(
            success=False,
            status_code=response.status_code,
            error=f"Unexpected HTTP {response.status_code}: {response.text[:200]}",
        )

    # 2xx — extract the assistant content
    content = _extract_content(response)

    return ProbeResult(
        success=True,
        status_code=response.status_code,
        response_text=content,
        latency_ms=latency_ms,
    )


def _extract_content(response: httpx.Response) -> str:
    """
    Extract the assistant reply from the response JSON.

    Supports:
      - Standard OpenAI: choices[0].message.content
      - llama.cpp legacy: content (top-level)
      - Fallback: raw text
    """
    try:
        data = response.json()
    except ValueError:
        return response.text[:500]

    # OpenAI-compatible format (llama.cpp --chat-format supports this)
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError):
        pass

    # llama.cpp may also return {"content": "..."} at top level in some modes
    if "content" in data:
        return str(data["content"])

    # Last resort: stringify entire payload
    return str(data)[:300]


# ─────────────────────────────────────────────
#  Print helpers
# ─────────────────────────────────────────────

def _print_ok(msg: str) -> None:
    print(f"  [OK]   {msg}")

def _print_error(msg: str) -> None:
    print(f"\n  [FAIL] ERROR: {msg}\n")

def _print_warn(msg: str) -> None:
    print(f"  [WARN] {msg}")

def _print_status(msg: str) -> None:
    print(msg)
