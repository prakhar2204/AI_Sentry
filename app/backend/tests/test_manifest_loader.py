"""
Tests for Phase 2b -- Manifest Loader System

Covers:
  - ManifestLoadResult dataclass
  - validate_manifest_structure()
  - load_manifest_file()
  - get_final_manifest() -- all three scenarios:
      A. CLI flags only
      B. JSON file only
      C. Both (CLI overrides file)

Run with:
    python -m pytest tests/test_manifest_loader.py -v
"""

import json
import pytest
from pathlib import Path

from core.manifest import (
    ManifestLoadResult,
    validate_manifest_structure,
    load_manifest_file,
    get_final_manifest,
    ScanManifest,
    ScanDepth,
    ScanMode,
    ProbeCategory,
    ManifestStatus,
)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def write_manifest(tmp_path: Path, data: dict, filename: str = "manifest.json") -> str:
    p = tmp_path / filename
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)

def write_raw(tmp_path: Path, content: str, filename: str = "manifest.json") -> str:
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return str(p)


# ─────────────────────────────────────────────
#  ManifestLoadResult
# ─────────────────────────────────────────────

class TestManifestLoadResult:

    def test_success_factory(self):
        from core.manifest import create_manifest
        m = create_manifest(target="https://api.openai.com/v1")
        r = ManifestLoadResult.success(manifest=m, source="cli")
        assert r.ok is True
        assert r.manifest is m
        assert r.source == "cli"
        assert r.error == ""

    def test_failure_factory(self):
        r = ManifestLoadResult.failure(error="oops", hint="try again")
        assert r.ok is False
        assert r.manifest is None
        assert r.error == "oops"
        assert r.hint == "try again"

    def test_failure_without_hint(self):
        r = ManifestLoadResult.failure(error="oops")
        assert r.hint == ""

    def test_source_values(self):
        from core.manifest import create_manifest
        m = create_manifest(target="https://api.openai.com/v1")
        for src in ("cli", "file", "merged"):
            r = ManifestLoadResult.success(manifest=m, source=src)
            assert r.source == src


# ─────────────────────────────────────────────
#  validate_manifest_structure
# ─────────────────────────────────────────────

class TestValidateManifestStructure:

    # ── Valid structures ───────────────────────

    def test_valid_minimal(self):
        assert validate_manifest_structure({"target": "https://api.openai.com/v1"}) is None

    def test_valid_full(self):
        raw = {
            "target": "https://api.openai.com/v1",
            "mode": "api",
            "scan_depth": "standard",
            "categories": ["jailbreak", "data_leak"],
        }
        assert validate_manifest_structure(raw) is None

    def test_comment_keys_ignored(self):
        raw = {
            "_comment": "this is a comment",
            "target": "https://api.openai.com/v1",
        }
        assert validate_manifest_structure(raw) is None

    def test_all_comment_keys_with_valid_target(self):
        raw = {"_x": "ignore", "target": "https://api.openai.com/v1"}
        assert validate_manifest_structure(raw) is None

    # ── Invalid structures ─────────────────────

    def test_none_returns_error(self):
        err = validate_manifest_structure(None)
        assert err is not None
        assert "null" in err.lower() or "empty" in err.lower()

    def test_list_returns_error(self):
        err = validate_manifest_structure([{"target": "https://api.openai.com/v1"}])
        assert err is not None
        assert "array" in err.lower() or "list" in err.lower()

    def test_string_returns_error(self):
        err = validate_manifest_structure("https://api.openai.com/v1")
        assert err is not None

    def test_empty_dict_returns_error(self):
        err = validate_manifest_structure({})
        assert err is not None
        assert "empty" in err.lower() or "target" in err.lower()

    def test_missing_target_returns_error(self):
        err = validate_manifest_structure({"mode": "api"})
        assert err is not None
        assert "target" in err.lower()

    def test_empty_target_string_returns_error(self):
        err = validate_manifest_structure({"target": "   "})
        assert err is not None
        assert "target" in err.lower()

    def test_null_target_returns_error(self):
        err = validate_manifest_structure({"target": None})
        assert err is not None

    def test_integer_target_returns_error(self):
        err = validate_manifest_structure({"target": 12345})
        assert err is not None

    def test_mode_as_int_returns_error(self):
        err = validate_manifest_structure({"target": "https://api.openai.com/v1", "mode": 1})
        assert err is not None
        assert "mode" in err.lower()

    def test_scan_depth_as_list_returns_error(self):
        err = validate_manifest_structure({"target": "https://api.openai.com/v1", "scan_depth": ["deep"]})
        assert err is not None
        assert "scan_depth" in err.lower()

    def test_categories_as_string_returns_error(self):
        err = validate_manifest_structure({"target": "https://api.openai.com/v1", "categories": "jailbreak"})
        assert err is not None
        assert "categories" in err.lower()

    def test_categories_with_int_item_returns_error(self):
        err = validate_manifest_structure({
            "target": "https://api.openai.com/v1",
            "categories": ["jailbreak", 42],
        })
        assert err is not None
        assert "categories" in err.lower()


# ─────────────────────────────────────────────
#  load_manifest_file
# ─────────────────────────────────────────────

class TestLoadManifestFile:

    # ── Valid cases ────────────────────────────

    def test_loads_minimal_manifest(self, tmp_path):
        p = write_manifest(tmp_path, {"target": "https://api.openai.com/v1"})
        m = load_manifest_file(p)
        assert isinstance(m, ScanManifest)
        assert m.target == "https://api.openai.com/v1"

    def test_loads_full_manifest(self, tmp_path):
        p = write_manifest(tmp_path, {
            "target": "https://api.openai.com/v1",
            "mode": "api",
            "scan_depth": "quick",
            "categories": ["jailbreak"],
            "output_dir": "./custom-out",
            "notes": "test run",
        })
        m = load_manifest_file(p)
        assert m.scan_depth == ScanDepth.QUICK
        assert ProbeCategory.JAILBREAK in m.categories
        assert m.output_dir == "./custom-out"
        assert m.notes == "test run"

    def test_source_file_is_set(self, tmp_path):
        p = write_manifest(tmp_path, {"target": "https://api.openai.com/v1"})
        m = load_manifest_file(p)
        assert m.source_file is not None
        assert "manifest.json" in m.source_file

    def test_comment_keys_stripped(self, tmp_path):
        p = write_manifest(tmp_path, {
            "_comment": "this is ignored",
            "target": "https://api.openai.com/v1",
        })
        m = load_manifest_file(p)
        assert m.target == "https://api.openai.com/v1"

    def test_target_whitespace_stripped(self, tmp_path):
        p = write_manifest(tmp_path, {"target": "  https://api.openai.com/v1  "})
        m = load_manifest_file(p)
        assert m.target == "https://api.openai.com/v1"

    # ── File error cases ───────────────────────

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_manifest_file(str(tmp_path / "nonexistent.json"))

    def test_non_json_extension_raises_value_error(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match=".json"):
            load_manifest_file(str(p))

    def test_empty_file_raises_value_error(self, tmp_path):
        p = write_raw(tmp_path, "")
        with pytest.raises(ValueError, match="empty"):
            load_manifest_file(p)

    def test_whitespace_only_file_raises_value_error(self, tmp_path):
        p = write_raw(tmp_path, "   \n\t  ")
        with pytest.raises(ValueError, match="empty"):
            load_manifest_file(p)

    def test_invalid_json_raises_value_error(self, tmp_path):
        p = write_raw(tmp_path, "{bad json >>>}")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_manifest_file(p)

    def test_json_array_raises_value_error(self, tmp_path):
        p = write_raw(tmp_path, '[{"target": "https://api.openai.com/v1"}]')
        with pytest.raises(ValueError, match="array"):
            load_manifest_file(p)

    def test_json_null_raises_value_error(self, tmp_path):
        p = write_raw(tmp_path, "null")
        with pytest.raises(ValueError):
            load_manifest_file(p)

    def test_empty_json_object_raises_value_error(self, tmp_path):
        p = write_raw(tmp_path, "{}")
        with pytest.raises(ValueError, match="empty"):
            load_manifest_file(p)

    def test_missing_target_key_raises_value_error(self, tmp_path):
        p = write_manifest(tmp_path, {"mode": "api", "scan_depth": "quick"})
        with pytest.raises(ValueError, match="target"):
            load_manifest_file(p)

    def test_invalid_mode_value_raises_value_error(self, tmp_path):
        p = write_manifest(tmp_path, {"target": "https://api.openai.com/v1", "mode": "cloud"})
        with pytest.raises(ValueError):
            load_manifest_file(p)

    def test_invalid_category_name_raises_value_error(self, tmp_path):
        p = write_manifest(tmp_path, {
            "target": "https://api.openai.com/v1",
            "categories": ["unknown_category"],
        })
        with pytest.raises(ValueError, match="category"):
            load_manifest_file(p)


# ─────────────────────────────────────────────
#  get_final_manifest — Scenario A: CLI only
# ─────────────────────────────────────────────

class TestGetFinalManifestCliOnly:

    def test_cli_only_returns_ok(self):
        r = get_final_manifest(cli_target="https://api.openai.com/v1")
        assert r.ok is True
        assert r.manifest is not None

    def test_cli_only_source_is_cli(self):
        r = get_final_manifest(cli_target="https://api.openai.com/v1")
        assert r.source == "cli"

    def test_cli_target_used(self):
        r = get_final_manifest(cli_target="https://api.openai.com/v1")
        assert r.manifest.target == "https://api.openai.com/v1"

    def test_cli_mode_used(self):
        r = get_final_manifest(
            cli_target="http://localhost:8080",
            cli_mode="local",
        )
        assert r.manifest.mode == ScanMode.LOCAL

    def test_cli_scan_depth_used(self):
        r = get_final_manifest(
            cli_target="https://api.openai.com/v1",
            cli_scan_depth="quick",
        )
        assert r.manifest.scan_depth == ScanDepth.QUICK

    def test_cli_categories_used(self):
        r = get_final_manifest(
            cli_target="https://api.openai.com/v1",
            cli_categories=["jailbreak"],
        )
        assert ProbeCategory.JAILBREAK in r.manifest.categories
        assert ProbeCategory.DATA_LEAK not in r.manifest.categories

    def test_no_target_at_all_returns_failure(self):
        r = get_final_manifest()  # no file, no CLI target
        assert r.ok is False
        assert "target" in r.error.lower()

    def test_failure_has_hint(self):
        r = get_final_manifest()
        assert r.hint != ""

    def test_invalid_mode_returns_failure(self):
        r = get_final_manifest(
            cli_target="https://api.openai.com/v1",
            cli_mode="cloud",
        )
        assert r.ok is False

    def test_invalid_category_returns_failure(self):
        r = get_final_manifest(
            cli_target="https://api.openai.com/v1",
            cli_categories=["not_real"],
        )
        assert r.ok is False

    def test_manifest_id_generated(self):
        r = get_final_manifest(cli_target="https://api.openai.com/v1")
        import uuid
        assert uuid.UUID(r.manifest.manifest_id)

    def test_manifest_status_is_created(self):
        r = get_final_manifest(cli_target="https://api.openai.com/v1")
        assert r.manifest.status == ManifestStatus.CREATED


# ─────────────────────────────────────────────
#  get_final_manifest — Scenario B: File only
# ─────────────────────────────────────────────

class TestGetFinalManifestFileOnly:

    def test_file_only_returns_ok(self, tmp_path):
        p = write_manifest(tmp_path, {"target": "https://file.example.com/v1"})
        r = get_final_manifest(manifest_path=p)
        assert r.ok is True

    def test_file_only_source_is_file(self, tmp_path):
        p = write_manifest(tmp_path, {"target": "https://file.example.com/v1"})
        r = get_final_manifest(manifest_path=p)
        assert r.source == "file"

    def test_file_target_used(self, tmp_path):
        p = write_manifest(tmp_path, {"target": "https://file.example.com/v1"})
        r = get_final_manifest(manifest_path=p)
        assert r.manifest.target == "https://file.example.com/v1"

    def test_file_mode_used(self, tmp_path):
        p = write_manifest(tmp_path, {
            "target": "https://file.example.com/v1",
            "mode": "api",
        })
        r = get_final_manifest(manifest_path=p)
        assert r.manifest.mode == ScanMode.API

    def test_file_depth_used(self, tmp_path):
        p = write_manifest(tmp_path, {
            "target": "https://file.example.com/v1",
            "scan_depth": "deep",
        })
        r = get_final_manifest(manifest_path=p)
        assert r.manifest.scan_depth == ScanDepth.DEEP

    def test_file_categories_used(self, tmp_path):
        p = write_manifest(tmp_path, {
            "target": "https://file.example.com/v1",
            "categories": ["data_leak", "harmful_output"],
        })
        r = get_final_manifest(manifest_path=p)
        assert ProbeCategory.DATA_LEAK in r.manifest.categories
        assert ProbeCategory.JAILBREAK not in r.manifest.categories

    def test_missing_file_returns_failure(self, tmp_path):
        r = get_final_manifest(manifest_path=str(tmp_path / "none.json"))
        assert r.ok is False
        assert "not found" in r.error.lower()

    def test_empty_file_returns_failure(self, tmp_path):
        p = write_raw(tmp_path, "")
        r = get_final_manifest(manifest_path=p)
        assert r.ok is False
        assert "empty" in r.error.lower()

    def test_invalid_json_file_returns_failure(self, tmp_path):
        p = write_raw(tmp_path, "{invalid}")
        r = get_final_manifest(manifest_path=p)
        assert r.ok is False
        assert "json" in r.error.lower() or "invalid" in r.error.lower()

    def test_failure_hint_suggests_fix(self, tmp_path):
        p = write_raw(tmp_path, "")
        r = get_final_manifest(manifest_path=p)
        assert r.hint != ""

    def test_source_file_recorded_in_manifest(self, tmp_path):
        p = write_manifest(tmp_path, {"target": "https://file.example.com/v1"})
        r = get_final_manifest(manifest_path=p)
        assert r.manifest.source_file is not None


# ─────────────────────────────────────────────
#  get_final_manifest — Scenario C: Both (merged)
# ─────────────────────────────────────────────

class TestGetFinalManifestMerged:

    def _file(self, tmp_path: Path) -> str:
        return write_manifest(tmp_path, {
            "target": "https://file.example.com/v1",
            "mode": "api",
            "scan_depth": "quick",
            "categories": ["jailbreak"],
            "output_dir": "./file-report",
        })

    def test_merged_source_label(self, tmp_path):
        p = self._file(tmp_path)
        r = get_final_manifest(manifest_path=p, cli_target="https://cli.example.com/v1")
        assert r.source == "merged"

    def test_cli_target_overrides_file_target(self, tmp_path):
        p = self._file(tmp_path)
        r = get_final_manifest(manifest_path=p, cli_target="https://cli.example.com/v1")
        assert r.ok is True
        assert r.manifest.target == "https://cli.example.com/v1"

    def test_cli_depth_overrides_file_depth(self, tmp_path):
        p = self._file(tmp_path)
        r = get_final_manifest(manifest_path=p, cli_scan_depth="deep")
        assert r.manifest.scan_depth == ScanDepth.DEEP

    def test_cli_categories_override_file_categories(self, tmp_path):
        p = self._file(tmp_path)
        r = get_final_manifest(manifest_path=p, cli_categories=["data_leak"])
        assert ProbeCategory.DATA_LEAK in r.manifest.categories
        assert ProbeCategory.JAILBREAK not in r.manifest.categories

    def test_file_values_used_when_cli_silent(self, tmp_path):
        p = self._file(tmp_path)
        # No CLI overrides for depth or categories
        r = get_final_manifest(manifest_path=p)
        # source == "file" because no CLI override
        assert r.source == "file"
        assert r.manifest.scan_depth == ScanDepth.QUICK
        assert ProbeCategory.JAILBREAK in r.manifest.categories

    def test_partial_override_depth_only(self, tmp_path):
        p = self._file(tmp_path)
        r = get_final_manifest(manifest_path=p, cli_scan_depth="standard")
        assert r.manifest.scan_depth == ScanDepth.STANDARD
        # File target preserved
        assert r.manifest.target == "https://file.example.com/v1"

    def test_cli_api_key_overrides_file_api_key(self, tmp_path):
        p = write_manifest(tmp_path, {
            "target": "https://file.example.com/v1",
            "api_key": "file-key",
        })
        r = get_final_manifest(manifest_path=p, cli_api_key="cli-key")
        assert r.manifest.api_key == "cli-key"

    def test_merged_manifest_id_is_fresh(self, tmp_path):
        """Merged result should have a NEW manifest_id, not the file's."""
        p = self._file(tmp_path)
        file_r = get_final_manifest(manifest_path=p)
        merged_r = get_final_manifest(manifest_path=p, cli_scan_depth="deep")
        assert file_r.manifest.manifest_id != merged_r.manifest.manifest_id

    def test_file_source_file_preserved_in_merged(self, tmp_path):
        p = self._file(tmp_path)
        r = get_final_manifest(manifest_path=p, cli_scan_depth="deep")
        assert r.manifest.source_file is not None
        assert "manifest.json" in r.manifest.source_file

    def test_file_missing_returns_failure_even_with_cli(self, tmp_path):
        r = get_final_manifest(
            manifest_path=str(tmp_path / "missing.json"),
            cli_target="https://api.openai.com/v1",
        )
        assert r.ok is False
        assert "not found" in r.error.lower()

    def test_invalid_cli_mode_with_valid_file_returns_failure(self, tmp_path):
        p = self._file(tmp_path)
        r = get_final_manifest(manifest_path=p, cli_mode="garbage")
        assert r.ok is False

    def test_invalid_cli_category_with_valid_file_returns_failure(self, tmp_path):
        p = self._file(tmp_path)
        r = get_final_manifest(manifest_path=p, cli_categories=["nonexistent"])
        assert r.ok is False


# ─────────────────────────────────────────────
#  Priority verification
# ─────────────────────────────────────────────

class TestMergePriority:
    """
    Explicit priority: CLI > file > default

    Each test directly verifies a specific priority rule.
    """

    def test_cli_beats_file_target(self, tmp_path):
        p = write_manifest(tmp_path, {"target": "https://file.example.com/v1"})
        r = get_final_manifest(manifest_path=p, cli_target="https://cli.example.com/v1")
        assert r.manifest.target == "https://cli.example.com/v1"

    def test_file_beats_default_depth(self, tmp_path):
        # Default depth is "standard"; file sets "deep"
        p = write_manifest(tmp_path, {
            "target": "https://file.example.com/v1",
            "scan_depth": "deep",
        })
        r = get_final_manifest(manifest_path=p)
        assert r.manifest.scan_depth == ScanDepth.DEEP

    def test_cli_beats_file_depth_and_both_beat_default(self, tmp_path):
        # Default=standard, file=quick, cli=deep -> deep
        p = write_manifest(tmp_path, {
            "target": "https://file.example.com/v1",
            "scan_depth": "quick",
        })
        r = get_final_manifest(manifest_path=p, cli_scan_depth="deep")
        assert r.manifest.scan_depth == ScanDepth.DEEP

    def test_file_beats_default_categories(self, tmp_path):
        # Default categories are depth-based; file restricts to one
        p = write_manifest(tmp_path, {
            "target": "https://file.example.com/v1",
            "categories": ["harmful_output"],
        })
        r = get_final_manifest(manifest_path=p)
        assert r.manifest.categories == [ProbeCategory.HARMFUL_OUTPUT]

    def test_cli_categories_beat_file_categories(self, tmp_path):
        p = write_manifest(tmp_path, {
            "target": "https://file.example.com/v1",
            "categories": ["jailbreak", "data_leak"],
        })
        r = get_final_manifest(manifest_path=p, cli_categories=["prompt_injection"])
        assert r.manifest.categories == [ProbeCategory.PROMPT_INJECTION]
