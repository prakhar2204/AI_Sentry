"""
Tests for core/validator.py — Phase 1d

Covers:
  - validate_mode()
  - validate_target() in both api and local modes
  - validate_input_combination()
  - run_all_validations() orchestrator

Run with:
    python -m pytest tests/test_validator.py -v
"""

import pytest
from core.validator import (
    validate_mode,
    validate_target,
    validate_input_combination,
    run_all_validations,
    ValidationError,
    VALID_MODES,
)


# ─────────────────────────────────────────────
#  ValidationError dataclass
# ─────────────────────────────────────────────

class TestValidationErrorDataclass:

    def test_pass_constructor(self):
        err = ValidationError.pass_()
        assert err.ok is True
        assert err.field == ""
        assert err.message == ""

    def test_fail_constructor(self):
        err = ValidationError.fail(field="--mode", message="bad mode", hint="try api")
        assert err.ok is False
        assert err.field == "--mode"
        assert err.message == "bad mode"
        assert err.hint == "try api"

    def test_fail_without_hint(self):
        err = ValidationError.fail(field="--target", message="empty")
        assert err.hint == ""


# ─────────────────────────────────────────────
#  validate_mode
# ─────────────────────────────────────────────

class TestValidateMode:

    # ── Valid inputs ───────────────────────────

    def test_api_is_valid(self):
        assert validate_mode("api").ok is True

    def test_local_is_valid(self):
        assert validate_mode("local").ok is True

    def test_api_uppercase_is_valid(self):
        assert validate_mode("API").ok is True

    def test_local_mixed_case_is_valid(self):
        assert validate_mode("LOCAL").ok is True

    def test_api_with_whitespace_is_valid(self):
        assert validate_mode("  api  ").ok is True

    # ── Invalid inputs ─────────────────────────

    def test_none_is_invalid(self):
        result = validate_mode(None)
        assert result.ok is False
        assert result.field == "--mode"

    def test_empty_string_is_invalid(self):
        result = validate_mode("")
        assert result.ok is False

    def test_whitespace_only_is_invalid(self):
        result = validate_mode("   ")
        assert result.ok is False

    def test_gibberish_is_invalid(self):
        result = validate_mode("cloud")
        assert result.ok is False
        assert "cloud" in result.message

    def test_both_combined_is_invalid(self):
        result = validate_mode("api,local")
        assert result.ok is False

    def test_partial_word_is_invalid(self):
        result = validate_mode("ap")
        assert result.ok is False

    def test_error_contains_valid_options(self):
        result = validate_mode("remote")
        assert "api" in result.message or "api" in result.hint
        assert "local" in result.message or "local" in result.hint


# ─────────────────────────────────────────────
#  validate_target — API mode
# ─────────────────────────────────────────────

class TestValidateTargetApiMode:

    # ── Valid inputs ───────────────────────────

    def test_https_url_is_valid(self):
        r = validate_target("https://api.openai.com/v1", "api")
        assert r.ok is True

    def test_http_url_is_valid(self):
        r = validate_target("http://api.example.com", "api")
        assert r.ok is True

    def test_url_with_port_is_valid(self):
        r = validate_target("https://api.example.com:8443/v1", "api")
        assert r.ok is True

    def test_url_with_path_is_valid(self):
        r = validate_target("https://api.example.com/v1/chat/completions", "api")
        assert r.ok is True

    def test_whitespace_around_url_is_trimmed(self):
        r = validate_target("  https://api.example.com/v1  ", "api")
        assert r.ok is True

    # ── Invalid inputs ─────────────────────────

    def test_none_is_invalid(self):
        r = validate_target(None, "api")
        assert r.ok is False
        assert r.field == "--target"

    def test_empty_string_is_invalid(self):
        r = validate_target("", "api")
        assert r.ok is False

    def test_whitespace_only_is_invalid(self):
        r = validate_target("   ", "api")
        assert r.ok is False

    def test_no_scheme_is_invalid(self):
        r = validate_target("api.openai.com/v1", "api")
        assert r.ok is False
        assert "scheme" in r.message.lower() or "http" in r.message.lower()

    def test_ftp_scheme_is_invalid(self):
        r = validate_target("ftp://files.example.com", "api")
        assert r.ok is False
        assert "ftp" in r.message

    def test_file_scheme_is_invalid(self):
        r = validate_target("file:///etc/passwd", "api")
        assert r.ok is False

    def test_gguf_file_path_is_invalid(self):
        r = validate_target("http://not-valid/model.gguf", "api")
        # This is caught by _validate_api_target (gguf rule)
        # or passes through — both acceptable; but plain path should fail
        r2 = validate_target("model.gguf", "api")
        assert r2.ok is False  # no scheme

    def test_extremely_long_url_is_invalid(self):
        r = validate_target("https://example.com/" + "a" * 3000, "api")
        assert r.ok is False
        assert "long" in r.message.lower() or "2048" in r.message

    def test_url_with_no_host_is_invalid(self):
        r = validate_target("https://", "api")
        assert r.ok is False
        assert "host" in r.message.lower()

    def test_mode_case_insensitive(self):
        # validate_target must handle lowercase mode
        r = validate_target("https://api.example.com/v1", "API")
        assert r.ok is True


# ─────────────────────────────────────────────
#  validate_target — LOCAL mode
# ─────────────────────────────────────────────

class TestValidateTargetLocalMode:

    # ── Valid inputs ───────────────────────────

    def test_localhost_with_port_is_valid(self):
        r = validate_target("http://localhost:8080", "local")
        assert r.ok is True

    def test_127_0_0_1_with_port_is_valid(self):
        r = validate_target("http://127.0.0.1:8080", "local")
        assert r.ok is True

    def test_localhost_with_v1_path_is_valid(self):
        r = validate_target("http://localhost:8080/v1", "local")
        assert r.ok is True

    def test_localhost_with_full_path_is_valid(self):
        r = validate_target("http://localhost:8080/v1/chat/completions", "local")
        assert r.ok is True

    def test_localhost_https_is_valid(self):
        r = validate_target("https://localhost:8443", "local")
        assert r.ok is True

    def test_different_port_numbers_are_valid(self):
        for port in (1234, 8080, 11434, 65535):
            r = validate_target(f"http://localhost:{port}", "local")
            assert r.ok is True, f"Port {port} should be valid"

    def test_whitespace_trimmed(self):
        r = validate_target("  http://localhost:8080  ", "local")
        assert r.ok is True

    # ── Invalid inputs ─────────────────────────

    def test_no_port_is_invalid(self):
        r = validate_target("http://localhost", "local")
        assert r.ok is False
        assert "port" in r.message.lower()

    def test_remote_host_is_invalid(self):
        r = validate_target("http://api.openai.com:8080", "local")
        assert r.ok is False
        assert "localhost" in r.message.lower() or "local" in r.message.lower()

    def test_public_ip_is_invalid(self):
        r = validate_target("http://8.8.8.8:8080", "local")
        assert r.ok is False

    def test_no_scheme_is_invalid(self):
        r = validate_target("localhost:8080", "local")
        assert r.ok is False

    def test_empty_is_invalid(self):
        r = validate_target("", "local")
        assert r.ok is False

    def test_port_zero_is_invalid(self):
        r = validate_target("http://localhost:0", "local")
        assert r.ok is False
        assert "range" in r.message.lower() or "port" in r.message.lower()

    def test_local_mode_hint_mentions_port(self):
        r = validate_target("http://localhost", "local")
        # Hint should tell user to add a port
        assert "8080" in r.hint or "port" in r.hint.lower()


# ─────────────────────────────────────────────
#  validate_input_combination
# ─────────────────────────────────────────────

class TestValidateInputCombination:

    # ── Valid combinations ─────────────────────

    def test_api_mode_with_remote_url_is_valid(self):
        r = validate_input_combination("api", "https://api.openai.com/v1")
        assert r.ok is True

    def test_local_mode_with_localhost_is_valid(self):
        r = validate_input_combination("local", "http://localhost:8080")
        assert r.ok is True

    def test_local_mode_with_127_0_0_1_is_valid(self):
        r = validate_input_combination("local", "http://127.0.0.1:8080")
        assert r.ok is True

    def test_none_mode_passes_through(self):
        # Missing fields handled by individual validators; combination returns pass
        r = validate_input_combination(None, "https://example.com")
        assert r.ok is True

    def test_none_target_passes_through(self):
        r = validate_input_combination("api", None)
        assert r.ok is True

    # ── Invalid combinations ───────────────────

    def test_local_mode_with_remote_host_is_invalid(self):
        r = validate_input_combination("local", "http://api.openai.com:8080")
        assert r.ok is False
        assert "local" in r.message.lower() or "localhost" in r.hint.lower()

    def test_api_mode_with_localhost_is_invalid(self):
        r = validate_input_combination("api", "http://localhost:8080")
        assert r.ok is False
        assert "local" in r.message.lower() or "local" in r.hint.lower()

    def test_api_mode_with_127_0_0_1_is_invalid(self):
        r = validate_input_combination("api", "http://127.0.0.1:8080")
        assert r.ok is False

    def test_error_field_mentions_both_args(self):
        r = validate_input_combination("api", "http://localhost:8080")
        assert "--mode" in r.field or "target" in r.field.lower()

    def test_hint_suggests_correct_mode(self):
        r = validate_input_combination("api", "http://localhost:8080")
        assert "local" in r.hint.lower()


# ─────────────────────────────────────────────
#  run_all_validations — orchestrator
# ─────────────────────────────────────────────

class TestRunAllValidations:

    # ── Passing cases ──────────────────────────

    def test_valid_api_combination_returns_none(self):
        assert run_all_validations("api", "https://api.openai.com/v1") is None

    def test_valid_local_combination_returns_none(self):
        assert run_all_validations("local", "http://localhost:8080") is None

    # ── Failing cases — mode checked first ─────

    def test_invalid_mode_caught_first(self):
        err = run_all_validations("cloud", "https://api.openai.com/v1")
        assert err is not None
        assert err.ok is False
        assert err.field == "--mode"

    def test_missing_mode_caught_first(self):
        err = run_all_validations(None, "https://api.openai.com/v1")
        assert err is not None
        assert err.field == "--mode"

    # ── Failing cases — target checked second ──

    def test_empty_target_caught_after_valid_mode(self):
        err = run_all_validations("api", "")
        assert err is not None
        assert err.field == "--target"

    def test_no_scheme_target_caught(self):
        err = run_all_validations("api", "api.openai.com")
        assert err is not None
        assert err.ok is False

    def test_local_mode_no_port_caught(self):
        err = run_all_validations("local", "http://localhost")
        assert err is not None
        assert "port" in err.message.lower()

    def test_local_mode_remote_host_target_caught(self):
        err = run_all_validations("local", "http://example.com:8080")
        assert err is not None
        assert err.ok is False

    # ── Failing cases — combination checked last

    def test_api_mode_localhost_target_combination_caught(self):
        err = run_all_validations("api", "http://localhost:8080")
        # Must fail somewhere (either target validation or combination)
        assert err is not None
        assert err.ok is False

    def test_local_mode_remote_url_combination_caught(self):
        err = run_all_validations("local", "http://remote.example.com:8080")
        assert err is not None
        assert err.ok is False

    # ── Return type check ──────────────────────

    def test_returns_none_on_full_pass(self):
        result = run_all_validations("api", "https://api.openai.com/v1")
        assert result is None

    def test_returns_validation_error_on_failure(self):
        result = run_all_validations("bad", "https://api.openai.com/v1")
        assert isinstance(result, ValidationError)
