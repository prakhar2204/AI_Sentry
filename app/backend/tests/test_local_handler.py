"""
Tests for core/local_handler.py

Run with:
    python -m pytest tests/test_local_handler.py -v
"""

import pytest
import httpx
import respx

from core.local_handler import (
    validate_local_endpoint,
    probe_local_model,
    run_local_validation,
    _build_chat_url,
)
from core.input_handler import ProbeResult


# ─────────────────────────────────────────────
#  validate_local_endpoint
# ─────────────────────────────────────────────

class TestValidateLocalEndpoint:

    def test_valid_localhost_http(self):
        r = validate_local_endpoint("http://localhost:8080")
        assert r.valid is True
        assert r.normalized_url == "http://localhost:8080"
        assert r.error == ""

    def test_valid_127_0_0_1(self):
        r = validate_local_endpoint("http://127.0.0.1:8080")
        assert r.valid is True

    def test_valid_with_v1_path(self):
        r = validate_local_endpoint("http://localhost:8080/v1")
        assert r.valid is True
        assert r.normalized_url == "http://localhost:8080/v1"

    def test_trailing_slash_stripped(self):
        r = validate_local_endpoint("http://localhost:8080/")
        assert r.valid is True
        assert not r.normalized_url.endswith("/")

    def test_whitespace_stripped(self):
        r = validate_local_endpoint("  http://localhost:8080  ")
        assert r.valid is True

    def test_empty_target_is_invalid(self):
        r = validate_local_endpoint("")
        assert r.valid is False
        assert "empty" in r.error.lower()

    def test_no_scheme_is_invalid(self):
        r = validate_local_endpoint("localhost:8080")
        assert r.valid is False
        assert "http" in r.error.lower()

    def test_ftp_scheme_is_invalid(self):
        r = validate_local_endpoint("ftp://localhost:8080")
        assert r.valid is False

    def test_https_is_accepted(self):
        r = validate_local_endpoint("https://localhost:8080")
        assert r.valid is True

    def test_no_host_is_invalid(self):
        r = validate_local_endpoint("http://")
        assert r.valid is False

    def test_remote_host_warns_but_valid(self, capsys):
        # Non-local host triggers a warning but is still accepted
        r = validate_local_endpoint("http://192.168.1.100:8080")
        assert r.valid is True  # LAN addresses are allowed

    def test_public_host_warns_but_valid(self, capsys):
        r = validate_local_endpoint("http://my-server.example.com:8080")
        assert r.valid is True
        captured = capsys.readouterr()
        assert "warn" in captured.out.lower()


# ─────────────────────────────────────────────
#  _build_chat_url helper
# ─────────────────────────────────────────────

class TestBuildChatUrl:

    def test_bare_host_gets_full_path(self):
        assert _build_chat_url("http://localhost:8080") == \
               "http://localhost:8080/v1/chat/completions"

    def test_v1_path_gets_chat_completions(self):
        assert _build_chat_url("http://localhost:8080/v1") == \
               "http://localhost:8080/v1/chat/completions"

    def test_full_path_unchanged(self):
        url = "http://localhost:8080/v1/chat/completions"
        assert _build_chat_url(url) == url

    def test_trailing_slash_removed_before_appending(self):
        result = _build_chat_url("http://localhost:8080/")
        assert result == "http://localhost:8080/v1/chat/completions"

    def test_completions_path_unchanged(self):
        url = "http://localhost:8080/v1/completions"
        assert _build_chat_url(url) == url


# ─────────────────────────────────────────────
#  test_local_model — HTTP mocks via respx
# ─────────────────────────────────────────────

CHAT_URL    = "http://localhost:8080/v1/chat/completions"
BASE_URL    = "http://localhost:8080"

LLAMA_OK_RESPONSE = {
    "choices": [
        {"message": {"role": "assistant", "content": "OK"}}
    ]
}


class TestTestLocalModel:

    @respx.mock
    def test_successful_response(self):
        respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json=LLAMA_OK_RESPONSE)
        )
        result = probe_local_model(BASE_URL)
        assert result.success is True
        assert result.status_code == 200
        assert result.response_text == "OK"
        assert result.latency_ms >= 0

    @respx.mock
    def test_connection_refused(self):
        respx.post(CHAT_URL).mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        result = probe_local_model(BASE_URL)
        assert result.success is False
        assert "connection refused" in result.error.lower() or \
               "llama.cpp" in result.error.lower() or \
               "running" in result.error.lower()

    @respx.mock
    def test_timeout(self):
        respx.post(CHAT_URL).mock(
            side_effect=httpx.ReadTimeout("timed out")
        )
        result = probe_local_model(BASE_URL)
        assert result.success is False
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower()

    @respx.mock
    def test_404_endpoint_not_found(self):
        respx.post(CHAT_URL).mock(return_value=httpx.Response(404))
        result = probe_local_model(BASE_URL)
        assert result.success is False
        assert result.status_code == 404
        assert "404" in result.error or "not found" in result.error.lower()

    @respx.mock
    def test_400_bad_request(self):
        respx.post(CHAT_URL).mock(
            return_value=httpx.Response(400, text="model not loaded")
        )
        result = probe_local_model(BASE_URL)
        assert result.success is False
        assert result.status_code == 400

    @respx.mock
    def test_500_server_error(self):
        respx.post(CHAT_URL).mock(return_value=httpx.Response(500))
        result = probe_local_model(BASE_URL)
        assert result.success is False
        assert result.status_code == 500

    @respx.mock
    def test_no_api_key_sent(self):
        """Local mode must never send an Authorization header."""
        route = respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json=LLAMA_OK_RESPONSE)
        )
        probe_local_model(BASE_URL)
        request = route.calls[0].request
        assert "authorization" not in request.headers

    @respx.mock
    def test_model_field_is_local_model(self):
        """Payload must use 'local-model' as the model name."""
        route = respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json=LLAMA_OK_RESPONSE)
        )
        probe_local_model(BASE_URL)
        import json
        body = json.loads(route.calls[0].request.content)
        assert body["model"] == "local-model"

    @respx.mock
    def test_stream_is_false(self):
        """stream=False must be set so we get a single JSON response."""
        route = respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json=LLAMA_OK_RESPONSE)
        )
        probe_local_model(BASE_URL)
        import json
        body = json.loads(route.calls[0].request.content)
        assert body.get("stream") is False

    @respx.mock
    def test_fallback_top_level_content(self):
        """llama.cpp legacy format: top-level 'content' key."""
        respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json={"content": "Hello from llama"})
        )
        result = probe_local_model(BASE_URL)
        assert result.success is True
        assert "Hello from llama" in result.response_text

    @respx.mock
    def test_url_with_v1_path(self):
        """Base URL ending in /v1 should append /chat/completions correctly."""
        v1_url = "http://localhost:8080/v1"
        chat_url = "http://localhost:8080/v1/chat/completions"
        respx.post(chat_url).mock(
            return_value=httpx.Response(200, json=LLAMA_OK_RESPONSE)
        )
        result = probe_local_model(v1_url)
        assert result.success is True


# ─────────────────────────────────────────────
#  run_local_validation — integration
# ─────────────────────────────────────────────

class TestRunLocalValidation:

    def test_invalid_url_returns_false(self, capsys):
        result = run_local_validation("not-a-url")
        assert result is False
        captured = capsys.readouterr()
        assert "error" in captured.out.lower()

    @respx.mock
    def test_valid_and_responsive_returns_true(self, capsys):
        respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json=LLAMA_OK_RESPONSE)
        )
        result = run_local_validation(BASE_URL)
        assert result is True
        captured = capsys.readouterr()
        assert "responsive" in captured.out.lower() or "ok" in captured.out.lower()

    @respx.mock
    def test_server_error_returns_false(self, capsys):
        respx.post(CHAT_URL).mock(return_value=httpx.Response(500))
        result = run_local_validation(BASE_URL)
        assert result is False
