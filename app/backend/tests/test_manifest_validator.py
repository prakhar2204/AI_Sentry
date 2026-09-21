"""
Tests for core/manifest_validator.py -- Phase 2c

Covers:
  - ManifestValidationIssue dataclass
  - validate_target()
  - validate_mode()
  - validate_scan_depth()
  - validate_categories()
  - validate_output_dir()
  - validate_manifest()  -- orchestrator (all fields + ordering)
  - format_manifest_validation_error()

Run with:
    python -m pytest tests/test_manifest_validator.py -v
"""

import pytest
from core.manifest import (
    ScanManifest,
    ScanMode,
    ScanDepth,
    ProbeCategory,
    ManifestStatus,
    create_manifest,
)
from core.manifest_validator import (
    ManifestValidationIssue,
    validate_target,
    validate_mode,
    validate_scan_depth,
    validate_categories,
    validate_output_dir,
    validate_manifest,
    format_manifest_validation_error,
)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _valid_manifest(**overrides) -> ScanManifest:
    """Build a known-good manifest for mutation testing."""
    m = create_manifest(
        target="https://api.openai.com/v1",
        mode="api",
        scan_depth="standard",
        categories=["prompt_injection", "jailbreak"],
    )
    for k, v in overrides.items():
        object.__setattr__(m, k, v)
    return m


# ─────────────────────────────────────────────
#  ManifestValidationIssue
# ─────────────────────────────────────────────

class TestManifestValidationIssue:

    def test_make_factory_all_fields(self):
        issue = ManifestValidationIssue.make(
            field="target",
            value=None,
            message="target is missing",
            hint="add --target",
        )
        assert issue.field == "target"
        assert issue.value is None
        assert issue.message == "target is missing"
        assert issue.hint == "add --target"

    def test_make_factory_no_hint(self):
        issue = ManifestValidationIssue.make(field="mode", value="x", message="bad")
        assert issue.hint == ""

    def test_is_dataclass_instance(self):
        issue = ManifestValidationIssue.make(field="f", value="v", message="m")
        assert isinstance(issue, ManifestValidationIssue)


# ─────────────────────────────────────────────
#  validate_target
# ─────────────────────────────────────────────

class TestValidateTarget:

    # Valid inputs
    def test_valid_https_url(self):
        assert validate_target("https://api.openai.com/v1") is None

    def test_valid_http_url(self):
        assert validate_target("http://localhost:8080") is None

    def test_valid_url_with_path(self):
        assert validate_target("https://api.example.com/v1/chat/completions") is None

    # Invalid inputs
    def test_none_returns_issue(self):
        issue = validate_target(None)
        assert issue is not None
        assert issue.field == "target"
        assert "missing" in issue.message.lower()

    def test_empty_string_returns_issue(self):
        issue = validate_target("")
        assert issue is not None
        assert issue.field == "target"

    def test_whitespace_only_returns_issue(self):
        issue = validate_target("   ")
        assert issue is not None
        assert "whitespace" in issue.message.lower() or "empty" in issue.message.lower()

    def test_integer_returns_issue(self):
        issue = validate_target(12345)
        assert issue is not None
        assert "str" in issue.message.lower() or "int" in issue.message.lower()

    def test_list_returns_issue(self):
        issue = validate_target(["https://api.openai.com/v1"])
        assert issue is not None

    def test_too_long_url_returns_issue(self):
        long_url = "https://api.openai.com/" + "a" * 2048
        issue = validate_target(long_url)
        assert issue is not None
        assert "2048" in issue.message or "long" in issue.message.lower()

    def test_exactly_2048_chars_is_valid(self):
        url = "https://api.openai.com/" + "a" * (2048 - len("https://api.openai.com/"))
        assert len(url) == 2048
        assert validate_target(url) is None

    def test_2049_chars_returns_issue(self):
        url = "https://api.openai.com/" + "a" * (2049 - len("https://api.openai.com/"))
        assert len(url) == 2049
        issue = validate_target(url)
        assert issue is not None

    def test_issue_has_hint(self):
        issue = validate_target(None)
        assert issue.hint != ""


# ─────────────────────────────────────────────
#  validate_mode
# ─────────────────────────────────────────────

class TestValidateMode:

    # Valid inputs
    def test_api_string_is_valid(self):
        assert validate_mode("api") is None

    def test_local_string_is_valid(self):
        assert validate_mode("local") is None

    def test_scan_mode_enum_api_is_valid(self):
        assert validate_mode(ScanMode.API) is None

    def test_scan_mode_enum_local_is_valid(self):
        assert validate_mode(ScanMode.LOCAL) is None

    def test_api_uppercase_is_valid(self):
        assert validate_mode("API") is None

    def test_local_mixed_case_is_valid(self):
        assert validate_mode("LOCAL") is None

    # Invalid inputs
    def test_none_returns_issue(self):
        issue = validate_mode(None)
        assert issue is not None
        assert issue.field == "mode"
        assert "missing" in issue.message.lower()

    def test_empty_string_returns_issue(self):
        issue = validate_mode("")
        assert issue is not None
        assert issue.field == "mode"

    def test_unknown_mode_returns_issue(self):
        issue = validate_mode("cloud")
        assert issue is not None
        assert "cloud" in issue.message
        assert issue.field == "mode"

    def test_integer_mode_returns_issue(self):
        issue = validate_mode(1)
        assert issue is not None

    def test_list_mode_returns_issue(self):
        issue = validate_mode(["api"])
        assert issue is not None

    def test_error_lists_valid_options(self):
        issue = validate_mode("ssh")
        assert "api" in issue.message or "api" in issue.hint
        assert "local" in issue.message or "local" in issue.hint

    def test_issue_field_is_mode(self):
        assert validate_mode("bad").field == "mode"


# ─────────────────────────────────────────────
#  validate_scan_depth
# ─────────────────────────────────────────────

class TestValidateScanDepth:

    # Valid inputs
    def test_quick_is_valid(self):
        assert validate_scan_depth("quick") is None

    def test_standard_is_valid(self):
        assert validate_scan_depth("standard") is None

    def test_deep_is_valid(self):
        assert validate_scan_depth("deep") is None

    def test_scan_depth_enum_quick_is_valid(self):
        assert validate_scan_depth(ScanDepth.QUICK) is None

    def test_scan_depth_enum_standard_is_valid(self):
        assert validate_scan_depth(ScanDepth.STANDARD) is None

    def test_scan_depth_enum_deep_is_valid(self):
        assert validate_scan_depth(ScanDepth.DEEP) is None

    def test_quick_uppercase_is_valid(self):
        assert validate_scan_depth("QUICK") is None

    def test_deep_mixed_case_is_valid(self):
        assert validate_scan_depth("Deep") is None

    # Invalid inputs
    def test_none_returns_issue(self):
        issue = validate_scan_depth(None)
        assert issue is not None
        assert issue.field == "scan_depth"

    def test_basic_is_invalid(self):
        """'basic' is NOT a valid depth -- TRD uses quick/standard/deep."""
        issue = validate_scan_depth("basic")
        assert issue is not None
        assert issue.field == "scan_depth"
        assert "basic" in issue.message

    def test_full_is_invalid(self):
        """'full' is NOT a valid depth -- TRD uses quick/standard/deep."""
        issue = validate_scan_depth("full")
        assert issue is not None
        assert issue.field == "scan_depth"
        assert "full" in issue.message

    def test_extreme_is_invalid(self):
        issue = validate_scan_depth("extreme")
        assert issue is not None
        assert "extreme" in issue.message

    def test_integer_returns_issue(self):
        issue = validate_scan_depth(3)
        assert issue is not None

    def test_error_lists_valid_options(self):
        issue = validate_scan_depth("full")
        assert "quick" in issue.message or "quick" in issue.hint
        assert "standard" in issue.message or "standard" in issue.hint
        assert "deep" in issue.message or "deep" in issue.hint

    def test_issue_field_is_scan_depth(self):
        assert validate_scan_depth("bad").field == "scan_depth"

    def test_hint_present(self):
        assert validate_scan_depth("full").hint != ""


# ─────────────────────────────────────────────
#  validate_categories
# ─────────────────────────────────────────────

class TestValidateCategories:

    # Valid inputs
    def test_single_valid_category_string(self):
        assert validate_categories(["jailbreak"]) is None

    def test_all_four_categories_valid(self):
        cats = ["prompt_injection", "jailbreak", "data_leak", "harmful_output"]
        assert validate_categories(cats) is None

    def test_two_categories_valid(self):
        assert validate_categories(["data_leak", "harmful_output"]) is None

    def test_probe_category_enum_members_valid(self):
        cats = [ProbeCategory.PROMPT_INJECTION, ProbeCategory.JAILBREAK]
        assert validate_categories(cats) is None

    def test_mixed_enum_and_string_valid(self):
        cats = [ProbeCategory.JAILBREAK, "data_leak"]
        assert validate_categories(cats) is None

    def test_uppercase_strings_valid(self):
        assert validate_categories(["JAILBREAK", "DATA_LEAK"]) is None

    # Invalid inputs
    def test_none_returns_issue(self):
        issue = validate_categories(None)
        assert issue is not None
        assert issue.field == "categories"
        assert "missing" in issue.message.lower()

    def test_empty_list_returns_issue(self):
        issue = validate_categories([])
        assert issue is not None
        assert issue.field == "categories"
        assert "empty" in issue.message.lower()

    def test_string_instead_of_list_returns_issue(self):
        issue = validate_categories("jailbreak")
        assert issue is not None
        assert issue.field == "categories"
        assert "list" in issue.message.lower()

    def test_dict_instead_of_list_returns_issue(self):
        issue = validate_categories({"jailbreak": True})
        assert issue is not None

    def test_unknown_category_returns_issue(self):
        issue = validate_categories(["jailbreak", "xyz"])
        assert issue is not None
        assert issue.field == "categories"
        assert "xyz" in issue.message

    def test_single_unknown_category_returns_issue(self):
        issue = validate_categories(["toxicity"])
        assert issue is not None
        assert "toxicity" in issue.message

    def test_integer_item_returns_issue(self):
        issue = validate_categories([42])
        assert issue is not None
        assert issue.field == "categories"

    def test_none_item_in_list_returns_issue(self):
        issue = validate_categories([None])
        assert issue is not None

    def test_error_lists_valid_categories(self):
        issue = validate_categories(["bad_cat"])
        assert "prompt_injection" in issue.hint or "jailbreak" in issue.hint

    def test_hint_present_on_unknown(self):
        assert validate_categories(["unknown"]).hint != ""

    def test_first_bad_item_reported(self):
        """Only the first invalid item is reported (fail-fast)."""
        issue = validate_categories(["jailbreak", "bad1", "bad2"])
        assert issue is not None
        assert "bad1" in issue.message  # first bad
        assert "bad2" not in issue.message  # second bad not reported


# ─────────────────────────────────────────────
#  validate_output_dir
# ─────────────────────────────────────────────

class TestValidateOutputDir:

    def test_none_is_valid(self):
        assert validate_output_dir(None) is None

    def test_empty_string_is_valid(self):
        assert validate_output_dir("") is None

    def test_valid_path_string(self):
        assert validate_output_dir("./reports") is None

    def test_absolute_path_is_valid(self):
        assert validate_output_dir("C:\\Users\\user\\reports") is None

    def test_integer_returns_issue(self):
        issue = validate_output_dir(42)
        assert issue is not None
        assert issue.field == "output_dir"

    def test_too_long_path_returns_issue(self):
        long_path = "a" * 513
        issue = validate_output_dir(long_path)
        assert issue is not None
        assert "512" in issue.message

    def test_exactly_512_chars_is_valid(self):
        assert validate_output_dir("a" * 512) is None

    def test_513_chars_returns_issue(self):
        assert validate_output_dir("a" * 513) is not None


# ─────────────────────────────────────────────
#  validate_manifest -- orchestrator
# ─────────────────────────────────────────────

class TestValidateManifest:

    # ── Full valid manifest ────────────────────

    def test_valid_manifest_returns_none(self):
        m = _valid_manifest()
        assert validate_manifest(m) is None

    def test_valid_local_manifest_returns_none(self):
        m = create_manifest(
            target="http://localhost:8080",
            mode="local",
            scan_depth="quick",
            categories=["jailbreak"],
        )
        assert validate_manifest(m) is None

    def test_valid_deep_scan_returns_none(self):
        m = create_manifest(
            target="https://api.openai.com/v1",
            scan_depth="deep",
        )
        assert validate_manifest(m) is None

    # ── Target failures ────────────────────────

    def test_empty_target_caught(self):
        m = _valid_manifest(target="")
        issue = validate_manifest(m)
        assert issue is not None
        assert issue.field == "target"

    def test_whitespace_target_caught(self):
        m = _valid_manifest(target="   ")
        issue = validate_manifest(m)
        assert issue is not None
        assert issue.field == "target"

    # ── Mode failures ──────────────────────────

    def test_invalid_mode_string_caught(self):
        m = _valid_manifest()
        m.mode = "cloud"  # bypass enum by direct assignment
        issue = validate_manifest(m)
        assert issue is not None
        assert issue.field == "mode"

    # ── Depth failures ─────────────────────────

    def test_depth_basic_is_rejected(self):
        """'basic' is not a TRD-defined value."""
        m = _valid_manifest()
        m.scan_depth = "basic"
        issue = validate_manifest(m)
        assert issue is not None
        assert issue.field == "scan_depth"
        assert "basic" in issue.message

    def test_depth_full_is_rejected(self):
        """'full' is not a TRD-defined value."""
        m = _valid_manifest()
        m.scan_depth = "full"
        issue = validate_manifest(m)
        assert issue is not None
        assert issue.field == "scan_depth"
        assert "full" in issue.message

    def test_valid_enum_depth_passes(self):
        m = _valid_manifest()
        m.scan_depth = ScanDepth.DEEP
        assert validate_manifest(m) is None

    # ── Category failures ──────────────────────

    def test_empty_categories_caught(self):
        m = _valid_manifest(categories=[])
        issue = validate_manifest(m)
        assert issue is not None
        assert issue.field == "categories"

    def test_unknown_category_caught(self):
        m = _valid_manifest(categories=["prompt_injection", "advanced_hack"])
        issue = validate_manifest(m)
        assert issue is not None
        assert issue.field == "categories"
        assert "advanced_hack" in issue.message

    def test_categories_with_enum_members_passes(self):
        m = _valid_manifest(categories=[ProbeCategory.JAILBREAK, ProbeCategory.DATA_LEAK])
        assert validate_manifest(m) is None

    # ── Ordering: target checked first ─────────

    def test_target_checked_before_mode(self):
        m = _valid_manifest(target="", categories=[])
        issue = validate_manifest(m)
        # Target is first in pipeline -- should report target, not categories
        assert issue.field == "target"

    def test_mode_checked_before_depth(self):
        m = _valid_manifest()
        m.mode = "bad_mode"
        m.scan_depth = "bad_depth"
        issue = validate_manifest(m)
        assert issue.field == "mode"

    def test_depth_checked_before_categories(self):
        m = _valid_manifest(categories=["unknown"])
        m.scan_depth = "extreme"
        issue = validate_manifest(m)
        assert issue.field == "scan_depth"

    # ── Error quality ──────────────────────────

    def test_error_message_is_specific(self):
        m = _valid_manifest()
        m.scan_depth = "basic"
        issue = validate_manifest(m)
        assert "basic" in issue.message  # names the bad value
        assert "scan_depth" in issue.field  # names the field

    def test_error_has_hint(self):
        m = _valid_manifest()
        m.scan_depth = "basic"
        issue = validate_manifest(m)
        assert issue.hint != ""

    def test_hint_mentions_quick_standard_deep(self):
        m = _valid_manifest()
        m.scan_depth = "full"
        issue = validate_manifest(m)
        combined = issue.message + issue.hint
        assert "quick" in combined
        assert "standard" in combined
        assert "deep" in combined

    # ── Type guard ─────────────────────────────

    def test_wrong_type_raises_type_error(self):
        with pytest.raises(TypeError):
            validate_manifest({"target": "https://api.openai.com/v1"})

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError):
            validate_manifest(None)


# ─────────────────────────────────────────────
#  format_manifest_validation_error
# ─────────────────────────────────────────────

class TestFormatManifestValidationError:

    def _issue(self, field="scan_depth", value="basic", message="bad depth", hint="use quick") -> ManifestValidationIssue:
        return ManifestValidationIssue.make(field=field, value=value, message=message, hint=hint)

    def test_contains_field_name(self):
        s = format_manifest_validation_error(self._issue())
        assert "scan_depth" in s

    def test_contains_message(self):
        s = format_manifest_validation_error(self._issue())
        assert "bad depth" in s

    def test_contains_hint(self):
        s = format_manifest_validation_error(self._issue())
        assert "use quick" in s

    def test_contains_x_marker(self):
        s = format_manifest_validation_error(self._issue())
        assert "[X]" in s

    def test_no_hint_when_empty(self):
        issue = ManifestValidationIssue.make(field="mode", value="x", message="bad", hint="")
        s = format_manifest_validation_error(issue)
        assert "Hint:" not in s

    def test_returns_string(self):
        assert isinstance(format_manifest_validation_error(self._issue()), str)

    def test_multiline_hint_formatted(self):
        issue = ManifestValidationIssue.make(
            field="scan_depth",
            value="full",
            message="bad",
            hint="line one\n    line two",
        )
        s = format_manifest_validation_error(issue)
        assert "line one" in s
        assert "line two" in s
