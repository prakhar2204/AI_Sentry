"""
Tests for core/input_handler.py

Run with:
    pytest tests/test_input_handler.py -v
"""

import pytest
import httpx
import respx

from core.input_handler import (
    EndpointType,
    ValidationResult,
    ProbeResult,
    validate_endpoint,
    probe_endpoint,
    run_input_validation,
)


# ─────────────────────────────────────────────
#  validate_endpoint — URL format tests
# ─────────────────────────────────────────────

class TestValidateEndpoint:

    def test_valid_https_url(self):
        r = validate_endpoint("https://api.openai.com/v1")
        assert r.valid is True
        assert r.endpoint_type == EndpointType.OPENAI_COMPATIBLE
        assert r.error == ""

    def test_valid_http_url(self):
        r = validate_endpoint("http://localhost:8080/v1")
        assert r.valid is True
        assert r.endpoint_type == EndpointType.OPENAI_COMPATIBLE

    def test_trailing_slash_is_stripped(self):
        r = validate_endpoint("https://api.openai.com/v1/")
        assert r.valid is True
        assert not r.normalized_url.endswith("/")

    def test_whitespace_is_stripped(self):
        r = validate_endpoint("  https://api.openai.com/v1  ")
        assert r.valid is True

    def test_empty_string_is_invalid(self):
        r = validate_endpoint("")
        assert r.valid is False
        assert "empty" in r.error.lower()

    def test_no_scheme_is_invalid(self):
        r = validate_endpoint("api.openai.com/v1")
        assert r.valid is False
        assert "http" in r.error.lower()

    def test_ftp_scheme_is_invalid(self):
        r = validate_endpoint("ftp://files.example.com/model")
        assert r.valid is False
        assert "ftp" in r.error

    def test_gguf_file_is_rejected_with_message(self):
        r = validate_endpoint("C:\\models\\llama.gguf")
        assert r.valid is False
        assert r.endpoint_type == EndpointType.LOCAL_GGUF
        assert "phase 2" in r.error.lower()

    def test_dot_gguf_extension_detected(self):
        r = validate_endpoint("model.gguf")
        assert r.valid is False
        assert r.endpoint_type == EndpointType.LOCAL_GGUF

    def test_unix_path_detected(self):
        r = validate_endpoint("/home/user/models/llama.gguf")
        assert r.valid is False
        assert r.endpoint_type == EndpointType.LOCAL_GGUF

    def test_url_with_no_host_is_invalid(self):
        r = validate_endpoint("https://")
        assert r.valid is False


# ─────────────────────────────────────────────
#  test_endpoint — HTTP interaction tests
#  Uses respx to mock httpx without real network
# ─────────────────────────────────────────────

CHAT_URL = "https://api.example.com/v1/chat/completions"
BASE_URL  = "https://api.example.com/v1"

OPENAI_OK_RESPONSE = {
    "choices": [
        {"message": {"role": "assistant", "content": "OK"}}
    ]
}


class TestTestEndpoint:

    @respx.mock
    def test_successful_response(self):
        respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json=OPENAI_OK_RESPONSE)
        )
        result = probe_endpoint(BASE_URL)
        assert result.success is True
        assert result.status_code == 200
        assert result.response_text == "OK"
        assert result.latency_ms >= 0

    @respx.mock
    def test_401_unauthorized(self):
        respx.post(CHAT_URL).mock(return_value=httpx.Response(401))
        result = probe_endpoint(BASE_URL)
        assert result.success is False
        assert result.status_code == 401
        assert "api key" in result.error.lower() or "401" in result.error

    @respx.mock
    def test_404_not_found(self):
        respx.post(CHAT_URL).mock(return_value=httpx.Response(404))
        result = probe_endpoint(BASE_URL)
        assert result.success is False
        assert result.status_code == 404
        assert "404" in result.error or "not found" in result.error.lower()

    @respx.mock
    def test_429_rate_limited(self):
        respx.post(CHAT_URL).mock(return_value=httpx.Response(429))
        result = probe_endpoint(BASE_URL)
        assert result.success is False
        assert result.status_code == 429
        assert "rate" in result.error.lower() or "429" in result.error

    @respx.mock
    def test_500_server_error(self):
        respx.post(CHAT_URL).mock(return_value=httpx.Response(500))
        result = probe_endpoint(BASE_URL)
        assert result.success is False
        assert result.status_code == 500

    @respx.mock
    def test_connection_error(self):
        respx.post(CHAT_URL).mock(side_effect=httpx.ConnectError("refused"))
        result = probe_endpoint(BASE_URL)
        assert result.success is False
        assert "connection" in result.error.lower() or "reachable" in result.error.lower()

    @respx.mock
    def test_timeout(self):
        respx.post(CHAT_URL).mock(side_effect=httpx.ReadTimeout("timed out"))
        result = probe_endpoint(BASE_URL)
        assert result.success is False
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower()

    @respx.mock
    def test_api_key_sent_in_header(self):
        route = respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json=OPENAI_OK_RESPONSE)
        )
        probe_endpoint(BASE_URL, api_key="sk-test-123")
        assert route.called
        request = route.calls[0].request
        assert request.headers.get("authorization") == "Bearer sk-test-123"

    @respx.mock
    def test_no_api_key_no_auth_header(self):
        route = respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json=OPENAI_OK_RESPONSE)
        )
        probe_endpoint(BASE_URL, api_key="")
        request = route.calls[0].request
        assert "authorization" not in request.headers

    @respx.mock
    def test_url_already_ending_in_chat_completions(self):
        """If the base URL already ends in /chat/completions, it should not be doubled."""
        direct_url = "https://api.example.com/v1/chat/completions"
        respx.post(direct_url).mock(
            return_value=httpx.Response(200, json=OPENAI_OK_RESPONSE)
        )
        result = probe_endpoint(direct_url)
        assert result.success is True

    @respx.mock
    def test_fallback_text_extraction(self):
        """Non-standard response with a top-level 'text' key should be extracted."""
        respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json={"text": "hello from model"})
        )
        result = probe_endpoint(BASE_URL)
        assert result.success is True
        assert "hello from model" in result.response_text


# ─────────────────────────────────────────────
#  run_input_validation — integration
# ─────────────────────────────────────────────

class TestRunInputValidation:

    def test_invalid_url_returns_false(self, capsys):
        result = run_input_validation("not-a-url")
        assert result is False
        captured = capsys.readouterr()
        assert "error" in captured.out.lower()

    @respx.mock
    def test_valid_url_and_ok_response_returns_true(self, capsys):
        respx.post(CHAT_URL).mock(
            return_value=httpx.Response(200, json=OPENAI_OK_RESPONSE)
        )
        result = run_input_validation(BASE_URL)
        assert result is True
        captured = capsys.readouterr()
        assert "responsive" in captured.out.lower() or "200" in captured.out

    @respx.mock
    def test_valid_url_but_server_error_returns_false(self, capsys):
        respx.post(CHAT_URL).mock(return_value=httpx.Response(500))
        result = run_input_validation(BASE_URL)
        assert result is False
