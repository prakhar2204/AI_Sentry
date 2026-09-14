"""
AI-SENTRY — Endpoint Input Handler
core/input_handler.py

Validates an LLM API endpoint and sends a lightweight test
request to confirm the model is reachable and responding.

Phase 1b deliverable.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

import httpx


# ─────────────────────────────────────────────
#  Types
# ─────────────────────────────────────────────

class EndpointType(Enum):
    OPENAI_COMPATIBLE = "openai_compatible"
    LOCAL_GGUF        = "local_gguf"
    UNKNOWN           = "unknown"


@dataclass
class ValidationResult:
    """Result of validate_endpoint()."""
    valid:         bool
    endpoint_type: EndpointType  = EndpointType.UNKNOWN
    normalized_url: str          = ""
    error:         str           = ""


@dataclass
class ProbeResult:
    """Result of probe_endpoint()."""
    success:       bool
    status_code:   int           = 0
    response_text: str           = ""
    latency_ms:    float         = 0.0
    error:         str           = ""


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

_CONNECT_TIMEOUT = 10.0    # seconds — fail fast on bad hosts
_READ_TIMEOUT    = 30.0    # seconds — model may be slow
_TEST_PROMPT     = "Hello. Please respond with exactly the word: OK"

_OPENAI_CHAT_PATH = "/chat/completions"

_DIVIDER = "-" * 60


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def validate_endpoint(target: str) -> ValidationResult:
    """
    Validate and classify a user-supplied target string.

    Accepts:
      - An HTTP/HTTPS URL  → classified as OPENAI_COMPATIBLE
      - A local file path  → classified as LOCAL_GGUF (stub — Phase 2)

    Returns a ValidationResult with .valid, .endpoint_type,
    .normalized_url, and .error populated.
    """
    target = target.strip()

    if not target:
        return ValidationResult(valid=False, error="Target cannot be empty.")

    # ── Local GGUF path detection ──────────────
    if _looks_like_file_path(target):
        return ValidationResult(
            valid=False,
            endpoint_type=EndpointType.LOCAL_GGUF,
            error=(
                "Local GGUF model support is planned for Phase 2. "
                "Please provide an HTTP/HTTPS API endpoint for now."
            ),
        )

    # ── URL validation ─────────────────────────
    parsed = urlparse(target)

    if parsed.scheme not in ("http", "https"):
        return ValidationResult(
            valid=False,
            error=(
                f"Invalid URL scheme '{parsed.scheme or '(none)'}'. "
                "Endpoint must start with http:// or https://"
            ),
        )

    if not parsed.netloc:
        return ValidationResult(
            valid=False,
            error="URL has no host. Expected format: https://api.example.com/v1",
        )

    # Normalise: strip trailing slash
    normalized = target.rstrip("/")

    return ValidationResult(
        valid=True,
        endpoint_type=EndpointType.OPENAI_COMPATIBLE,
        normalized_url=normalized,
    )


def probe_endpoint(url: str, api_key: str = "") -> ProbeResult:
    """
    Send a minimal OpenAI-compatible chat request to the endpoint.

    Tries <base_url>/chat/completions first.
    Falls back to <base_url> directly if the path already ends in
    /chat/completions or /completions.

    Returns a ProbeResult with .success, .status_code, .response_text,
    .latency_ms, and .error populated.
    """
    chat_url = _build_chat_url(url)
    headers  = _build_headers(api_key)
    payload  = _build_test_payload()

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
            import time
            t0 = time.monotonic()
            response = client.post(chat_url, json=payload, headers=headers)
            latency_ms = (time.monotonic() - t0) * 1000

    except httpx.ConnectError as exc:
        return ProbeResult(
            success=False,
            error=f"Connection failed — is the endpoint reachable?\n  Detail: {exc}",
        )
    except httpx.TimeoutException as exc:
        return ProbeResult(
            success=False,
            error=(
                f"Request timed out after {_READ_TIMEOUT}s. "
                "The endpoint may be overloaded or the URL is wrong."
            ),
        )
    except httpx.RequestError as exc:
        return ProbeResult(
            success=False,
            error=f"Network error: {exc}",
        )

    # ── Interpret the HTTP response ────────────
    return _interpret_response(response, latency_ms)


# ─────────────────────────────────────────────
#  CLI-facing entry point
# ─────────────────────────────────────────────

def run_input_validation(target: str, api_key: str = "") -> bool:
    """
    Orchestrate the full validation + test-request pipeline.

    Prints human-readable output to stdout.
    Returns True if the endpoint is valid and responsive.
    Returns False on any failure (with an error message printed).

    Called by cli/main.py after the consent gate passes.
    """
    print(f"\n{_DIVIDER}")
    print("  ENDPOINT VALIDATION")
    print(_DIVIDER)

    # ── Step 1: Validate the URL format ───────
    print(f"\n  [1/2] Validating target: {target}")
    result = validate_endpoint(target)

    if not result.valid:
        _print_error(result.error)
        return False

    _print_ok(f"Valid {result.endpoint_type.value} endpoint detected.")

    # ── Step 2: Send test request ──────────────
    print(f"\n  [2/2] Sending test request...")
    test = probe_endpoint(result.normalized_url, api_key=api_key)

    if not test.success:
        _print_error(test.error)
        if test.status_code:
            print(f"  HTTP status: {test.status_code}")
        return False

    _print_ok(
        f"Endpoint is responsive.  "
        f"(HTTP {test.status_code}, {test.latency_ms:.0f} ms)"
    )

    if test.response_text:
        preview = test.response_text[:120].replace("\n", " ")
        print(f"\n  Model response preview: \"{preview}\"")

    print(f"\n{_DIVIDER}\n")
    return True


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────

def _looks_like_file_path(target: str) -> bool:
    """Return True if the target looks like a local file path rather than a URL."""
    import os
    # Covers Windows absolute (C:\...), Unix absolute (/...), and relative with extension
    if os.path.sep in target or target.startswith("/"):
        return True
    if len(target) > 2 and target[1] == ":" and target[2] in ("/", "\\"):
        return True  # Windows drive letter
    if target.lower().endswith(".gguf"):
        return True
    return False


def _build_chat_url(base_url: str) -> str:
    """Append /chat/completions unless already present."""
    if base_url.endswith("/chat/completions") or base_url.endswith("/completions"):
        return base_url
    return base_url.rstrip("/") + _OPENAI_CHAT_PATH


def _build_headers(api_key: str) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _build_test_payload() -> dict:
    return {
        "model": "gpt-3.5-turbo",   # most providers accept this as a default
        "messages": [
            {"role": "user", "content": _TEST_PROMPT},
        ],
        "max_tokens": 10,
        "temperature": 0,
    }


def _interpret_response(response: httpx.Response, latency_ms: float) -> ProbeResult:
    """Parse the HTTP response and extract the assistant message."""

    # Non-2xx responses
    if response.status_code == 401:
        return ProbeResult(
            success=False,
            status_code=response.status_code,
            error=(
                "Authentication failed (HTTP 401). "
                "The endpoint requires an API key. "
                "Set AI_SENTRY_API_KEY in your environment."
            ),
        )

    if response.status_code == 403:
        return ProbeResult(
            success=False,
            status_code=response.status_code,
            error="Access forbidden (HTTP 403). Check your API key permissions.",
        )

    if response.status_code == 404:
        return ProbeResult(
            success=False,
            status_code=response.status_code,
            error=(
                "Endpoint not found (HTTP 404). "
                "Verify the URL includes the correct path, e.g. /v1"
            ),
        )

    if response.status_code == 429:
        return ProbeResult(
            success=False,
            status_code=response.status_code,
            error="Rate limited (HTTP 429). Wait a moment and try again.",
        )

    if response.status_code >= 500:
        return ProbeResult(
            success=False,
            status_code=response.status_code,
            error=f"Server error (HTTP {response.status_code}). The endpoint is having issues.",
        )

    if not response.is_success:
        return ProbeResult(
            success=False,
            status_code=response.status_code,
            error=f"Unexpected HTTP {response.status_code}: {response.text[:200]}",
        )

    # 2xx — try to extract the assistant message
    response_text = _extract_content(response)

    return ProbeResult(
        success=True,
        status_code=response.status_code,
        response_text=response_text,
        latency_ms=latency_ms,
    )


def _extract_content(response: httpx.Response) -> str:
    """
    Try to extract the assistant message text from the response.
    Handles OpenAI-compatible format. Falls back to raw text.
    """
    try:
        data = response.json()
        # Standard OpenAI chat completion format
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        pass

    try:
        # Some providers use {"text": "..."} or {"response": "..."}
        data = response.json()
        for key in ("text", "response", "output", "result", "content"):
            if key in data:
                return str(data[key])
        return str(data)
    except ValueError:
        return response.text[:500]


# ─────────────────────────────────────────────
#  Print helpers
# ─────────────────────────────────────────────

def _print_ok(msg: str) -> None:
    print(f"  [OK]  {msg}")


def _print_error(msg: str) -> None:
    print(f"\n  [FAIL]  ERROR: {msg}\n")


def _print_status(msg: str) -> None:
    print(msg)
