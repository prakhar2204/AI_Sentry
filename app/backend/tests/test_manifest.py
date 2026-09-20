"""
Tests for core/manifest.py — Phase 2a

Covers:
  - ScanManifest dataclass
  - Enumerations (ScanDepth, ScanMode, ProbeCategory, ManifestStatus)
  - create_manifest()
  - load_manifest_from_file()
  - merge_cli_and_manifest()
  - ScanManifest.advance_status()
  - format_manifest_summary()
  - ScanManifest.to_dict() / to_json()

Run with:
    python -m pytest tests/test_manifest.py -v
"""

import json
import pytest
from pathlib import Path

from core.manifest import (
    ScanManifest,
    ScanDepth,
    ScanMode,
    ProbeCategory,
    ManifestStatus,
    create_manifest,
    load_manifest_from_file,
    merge_cli_and_manifest,
    format_manifest_summary,
    generate_example_manifest,
    DEPTH_CATEGORIES,
    PROBE_COUNT_ESTIMATES,
    DEFAULT_SCAN_DEPTH,
    DEFAULT_OUTPUT_DIR,
    VALID_CATEGORY_NAMES,
)


# ─────────────────────────────────────────────
#  Enum sanity
# ─────────────────────────────────────────────

class TestEnumerations:

    def test_scan_depth_values(self):
        assert ScanDepth.QUICK.value    == "quick"
        assert ScanDepth.STANDARD.value == "standard"
        assert ScanDepth.DEEP.value     == "deep"

    def test_scan_mode_values(self):
        assert ScanMode.API.value   == "api"
        assert ScanMode.LOCAL.value == "local"

    def test_probe_category_values(self):
        assert ProbeCategory.PROMPT_INJECTION.value == "prompt_injection"
        assert ProbeCategory.JAILBREAK.value        == "jailbreak"
        assert ProbeCategory.DATA_LEAK.value        == "data_leak"
        assert ProbeCategory.HARMFUL_OUTPUT.value   == "harmful_output"

    def test_manifest_status_values(self):
        assert ManifestStatus.CREATED.value         == "created"
        assert ManifestStatus.CONSENT_PENDING.value == "consent_pending"
        assert ManifestStatus.APPROVED.value        == "approved"
        assert ManifestStatus.RUNNING.value         == "running"
        assert ManifestStatus.COMPLETED.value       == "completed"
        assert ManifestStatus.FAILED.value          == "failed"
        assert ManifestStatus.CANCELLED.value       == "cancelled"

    def test_depth_categories_cover_all_categories(self):
        all_cats = set(ProbeCategory)
        deep_cats = set(DEPTH_CATEGORIES[ScanDepth.DEEP])
        assert all_cats == deep_cats

    def test_quick_is_subset_of_standard(self):
        quick    = set(DEPTH_CATEGORIES[ScanDepth.QUICK])
        standard = set(DEPTH_CATEGORIES[ScanDepth.STANDARD])
        assert quick.issubset(standard)


# ─────────────────────────────────────────────
#  create_manifest
# ─────────────────────────────────────────────

class TestCreateManifest:

    # ── Valid basic cases ──────────────────────

    def test_minimal_creation(self):
        m = create_manifest(target="https://api.openai.com/v1")
        assert m.target == "https://api.openai.com/v1"
        assert m.mode == ScanMode.API
        assert m.scan_depth == DEFAULT_SCAN_DEPTH
        assert m.status == ManifestStatus.CREATED
        assert len(m.categories) > 0

    def test_manifest_id_is_uuid(self):
        m = create_manifest(target="https://api.openai.com/v1")
        import uuid
        assert uuid.UUID(m.manifest_id)  # does not raise

    def test_created_at_is_iso_format(self):
        m = create_manifest(target="https://api.openai.com/v1")
        # Must end with Z (UTC)
        assert m.created_at.endswith("Z")
        assert "T" in m.created_at

    def test_two_manifests_have_different_ids(self):
        m1 = create_manifest(target="https://api.openai.com/v1")
        m2 = create_manifest(target="https://api.openai.com/v1")
        assert m1.manifest_id != m2.manifest_id

    def test_whitespace_stripped_from_target(self):
        m = create_manifest(target="  https://api.openai.com/v1  ")
        assert m.target == "https://api.openai.com/v1"

    def test_api_mode_default(self):
        m = create_manifest(target="https://api.openai.com/v1")
        assert m.mode == ScanMode.API
        assert m.is_api_mode is True
        assert m.is_local_mode is False

    def test_local_mode(self):
        m = create_manifest(target="http://localhost:8080", mode="local")
        assert m.mode == ScanMode.LOCAL
        assert m.is_local_mode is True
        assert m.is_api_mode is False

    def test_mode_uppercase_accepted(self):
        m = create_manifest(target="https://api.openai.com/v1", mode="API")
        assert m.mode == ScanMode.API

    def test_quick_depth_assigns_quick_categories(self):
        m = create_manifest(target="https://api.openai.com/v1", scan_depth="quick")
        assert set(m.categories) == set(DEPTH_CATEGORIES[ScanDepth.QUICK])

    def test_standard_depth_is_default(self):
        m = create_manifest(target="https://api.openai.com/v1")
        assert m.scan_depth == ScanDepth.STANDARD
        assert set(m.categories) == set(DEPTH_CATEGORIES[ScanDepth.STANDARD])

    def test_deep_depth_covers_all_categories(self):
        m = create_manifest(target="https://api.openai.com/v1", scan_depth="deep")
        assert m.scan_depth == ScanDepth.DEEP
        assert set(m.categories) == set(ProbeCategory)

    def test_custom_categories(self):
        m = create_manifest(
            target="https://api.openai.com/v1",
            categories=["prompt_injection", "jailbreak"],
        )
        assert ProbeCategory.PROMPT_INJECTION in m.categories
        assert ProbeCategory.JAILBREAK in m.categories
        assert ProbeCategory.DATA_LEAK not in m.categories

    def test_duplicate_categories_are_deduplicated(self):
        m = create_manifest(
            target="https://api.openai.com/v1",
            categories=["jailbreak", "jailbreak", "data_leak"],
        )
        cat_values = [c.value for c in m.categories]
        assert cat_values.count("jailbreak") == 1

    def test_api_key_stored(self):
        m = create_manifest(target="https://api.openai.com/v1", api_key="sk-test")
        assert m.api_key == "sk-test"

    def test_output_dir_stored(self):
        m = create_manifest(target="https://api.openai.com/v1", output_dir="/tmp/reports")
        assert m.output_dir == "/tmp/reports"

    def test_notes_stored(self):
        m = create_manifest(target="https://api.openai.com/v1", notes="pre-launch scan")
        assert m.notes == "pre-launch scan"

    def test_source_file_is_none_by_default(self):
        m = create_manifest(target="https://api.openai.com/v1")
        assert m.source_file is None

    # ── Invalid cases ─────────────────────────

    def test_invalid_mode_raises_value_error(self):
        with pytest.raises(ValueError, match="mode"):
            create_manifest(target="https://api.openai.com/v1", mode="cloud")

    def test_invalid_depth_raises_value_error(self):
        with pytest.raises(ValueError, match="scan_depth"):
            create_manifest(target="https://api.openai.com/v1", scan_depth="extreme")

    def test_invalid_category_raises_value_error(self):
        with pytest.raises(ValueError, match="category"):
            create_manifest(
                target="https://api.openai.com/v1",
                categories=["prompt_injection", "unknown_category"],
            )

    def test_empty_categories_list_raises(self):
        with pytest.raises(ValueError):
            create_manifest(target="https://api.openai.com/v1", categories=[])


# ─────────────────────────────────────────────
#  ScanManifest properties
# ─────────────────────────────────────────────

class TestScanManifestProperties:

    def test_total_probe_estimate_quick(self):
        m = create_manifest(target="https://api.openai.com/v1", scan_depth="quick")
        quick_map = PROBE_COUNT_ESTIMATES[ScanDepth.QUICK]
        expected = sum(quick_map.get(c, 0) for c in m.categories)
        assert m.total_probe_estimate == expected

    def test_total_probe_estimate_standard(self):
        m = create_manifest(target="https://api.openai.com/v1", scan_depth="standard")
        assert m.total_probe_estimate > 0

    def test_total_probe_estimate_deep_is_greater_than_standard(self):
        m_std  = create_manifest(target="https://api.openai.com/v1", scan_depth="standard")
        m_deep = create_manifest(target="https://api.openai.com/v1", scan_depth="deep")
        assert m_deep.total_probe_estimate >= m_std.total_probe_estimate


# ─────────────────────────────────────────────
#  ScanManifest.advance_status
# ─────────────────────────────────────────────

class TestAdvanceStatus:

    def _fresh(self) -> ScanManifest:
        return create_manifest(target="https://api.openai.com/v1")

    def test_created_to_consent_pending(self):
        m = self._fresh()
        m.advance_status(ManifestStatus.CONSENT_PENDING)
        assert m.status == ManifestStatus.CONSENT_PENDING

    def test_consent_pending_to_approved(self):
        m = self._fresh()
        m.advance_status(ManifestStatus.CONSENT_PENDING)
        m.advance_status(ManifestStatus.APPROVED)
        assert m.status == ManifestStatus.APPROVED

    def test_consent_pending_to_cancelled(self):
        m = self._fresh()
        m.advance_status(ManifestStatus.CONSENT_PENDING)
        m.advance_status(ManifestStatus.CANCELLED)
        assert m.status == ManifestStatus.CANCELLED

    def test_approved_to_running(self):
        m = self._fresh()
        m.advance_status(ManifestStatus.CONSENT_PENDING)
        m.advance_status(ManifestStatus.APPROVED)
        m.advance_status(ManifestStatus.RUNNING)
        assert m.status == ManifestStatus.RUNNING

    def test_running_to_completed(self):
        m = self._fresh()
        m.advance_status(ManifestStatus.CONSENT_PENDING)
        m.advance_status(ManifestStatus.APPROVED)
        m.advance_status(ManifestStatus.RUNNING)
        m.advance_status(ManifestStatus.COMPLETED)
        assert m.status == ManifestStatus.COMPLETED

    def test_running_to_failed(self):
        m = self._fresh()
        m.advance_status(ManifestStatus.CONSENT_PENDING)
        m.advance_status(ManifestStatus.APPROVED)
        m.advance_status(ManifestStatus.RUNNING)
        m.advance_status(ManifestStatus.FAILED)
        assert m.status == ManifestStatus.FAILED

    def test_illegal_transition_raises(self):
        m = self._fresh()  # CREATED
        with pytest.raises(ValueError, match="transition"):
            m.advance_status(ManifestStatus.COMPLETED)

    def test_terminal_state_cannot_transition(self):
        m = self._fresh()
        m.advance_status(ManifestStatus.CONSENT_PENDING)
        m.advance_status(ManifestStatus.CANCELLED)
        with pytest.raises(ValueError):
            m.advance_status(ManifestStatus.APPROVED)

    def test_cannot_skip_consent_to_running(self):
        m = self._fresh()  # CREATED
        with pytest.raises(ValueError):
            m.advance_status(ManifestStatus.RUNNING)


# ─────────────────────────────────────────────
#  to_dict / to_json
# ─────────────────────────────────────────────

class TestSerialization:

    def test_to_dict_contains_required_keys(self):
        m = create_manifest(target="https://api.openai.com/v1")
        d = m.to_dict()
        for key in ("manifest_id", "created_at", "target", "mode",
                    "scan_depth", "categories", "output_dir", "status"):
            assert key in d, f"Missing key: {key}"

    def test_to_dict_mode_is_string(self):
        m = create_manifest(target="https://api.openai.com/v1")
        d = m.to_dict()
        assert isinstance(d["mode"], str)
        assert d["mode"] == "api"

    def test_to_dict_categories_are_strings(self):
        m = create_manifest(target="https://api.openai.com/v1")
        d = m.to_dict()
        assert all(isinstance(c, str) for c in d["categories"])

    def test_api_key_redacted_in_dict(self):
        m = create_manifest(target="https://api.openai.com/v1", api_key="sk-secret")
        d = m.to_dict()
        assert d["api_key"] != "sk-secret"
        assert "sk-secret" not in str(d)

    def test_empty_api_key_serialized_as_empty(self):
        m = create_manifest(target="https://api.openai.com/v1")
        d = m.to_dict()
        assert d["api_key"] == ""

    def test_to_json_is_valid_json(self):
        m = create_manifest(target="https://api.openai.com/v1")
        j = m.to_json()
        parsed = json.loads(j)  # must not raise
        assert parsed["target"] == "https://api.openai.com/v1"

    def test_total_probe_estimate_in_dict(self):
        m = create_manifest(target="https://api.openai.com/v1")
        d = m.to_dict()
        assert "total_probe_estimate" in d
        assert isinstance(d["total_probe_estimate"], int)


# ─────────────────────────────────────────────
#  load_manifest_from_file
# ─────────────────────────────────────────────

class TestLoadManifestFromFile:

    def _write_json(self, tmp_path: Path, data: dict) -> str:
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return str(p)

    def test_loads_valid_manifest(self, tmp_path):
        p = self._write_json(tmp_path, {
            "target": "https://api.openai.com/v1",
            "mode": "api",
            "scan_depth": "quick",
            "categories": ["prompt_injection"],
        })
        m = load_manifest_from_file(p)
        assert m.target == "https://api.openai.com/v1"
        assert m.scan_depth == ScanDepth.QUICK
        assert ProbeCategory.PROMPT_INJECTION in m.categories

    def test_source_file_set(self, tmp_path):
        p = self._write_json(tmp_path, {"target": "https://api.openai.com/v1"})
        m = load_manifest_from_file(p)
        assert m.source_file is not None
        assert "manifest.json" in m.source_file

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_manifest_from_file(str(tmp_path / "nonexistent.json"))

    def test_non_json_extension_raises(self, tmp_path):
        p = tmp_path / "manifest.yaml"
        p.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match=".json"):
            load_manifest_from_file(str(p))

    def test_invalid_json_raises_value_error(self, tmp_path):
        p = tmp_path / "manifest.json"
        p.write_text("not valid json {{{", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_manifest_from_file(str(p))

    def test_missing_target_raises(self, tmp_path):
        p = self._write_json(tmp_path, {"mode": "api"})
        with pytest.raises(ValueError, match="target"):
            load_manifest_from_file(p)

    def test_defaults_applied_for_missing_fields(self, tmp_path):
        p = self._write_json(tmp_path, {"target": "https://api.openai.com/v1"})
        m = load_manifest_from_file(p)
        assert m.scan_depth == DEFAULT_SCAN_DEPTH
        assert m.output_dir == DEFAULT_OUTPUT_DIR


# ─────────────────────────────────────────────
#  merge_cli_and_manifest
# ─────────────────────────────────────────────

class TestMergeCliAndManifest:

    def _file_manifest(self) -> ScanManifest:
        return create_manifest(
            target="https://file.example.com/v1",
            mode="api",
            scan_depth="quick",
            categories=["jailbreak"],
            api_key="file-key",
            output_dir="./file-report",
        )

    def test_cli_target_overrides_file(self):
        fm = self._file_manifest()
        m = merge_cli_and_manifest(fm, target="https://cli.example.com/v1")
        assert m.target == "https://cli.example.com/v1"

    def test_cli_mode_overrides_file(self):
        fm = self._file_manifest()
        m = merge_cli_and_manifest(fm, target=fm.target, mode="api")
        assert m.mode == ScanMode.API

    def test_cli_depth_overrides_file(self):
        fm = self._file_manifest()
        m = merge_cli_and_manifest(fm, target=fm.target, scan_depth="deep")
        assert m.scan_depth == ScanDepth.DEEP

    def test_cli_categories_override_file(self):
        fm = self._file_manifest()
        m = merge_cli_and_manifest(fm, target=fm.target, categories=["data_leak"])
        assert ProbeCategory.DATA_LEAK in m.categories
        assert ProbeCategory.JAILBREAK not in m.categories

    def test_cli_api_key_overrides_file(self):
        fm = self._file_manifest()
        m = merge_cli_and_manifest(fm, target=fm.target, api_key="cli-key")
        assert m.api_key == "cli-key"

    def test_cli_output_overrides_file(self):
        fm = self._file_manifest()
        m = merge_cli_and_manifest(fm, target=fm.target, output_dir="./cli-report")
        assert m.output_dir == "./cli-report"

    def test_file_values_used_when_no_cli_override(self):
        fm = self._file_manifest()
        m = merge_cli_and_manifest(fm, target=fm.target)
        assert m.scan_depth == ScanDepth.QUICK
        assert ProbeCategory.JAILBREAK in m.categories

    def test_none_file_manifest_uses_cli_defaults(self):
        m = merge_cli_and_manifest(
            None,
            target="https://api.openai.com/v1",
            mode="api",
        )
        assert m.target == "https://api.openai.com/v1"
        assert m.scan_depth == DEFAULT_SCAN_DEPTH

    def test_source_file_preserved_from_file_manifest(self):
        fm = self._file_manifest()
        fm.source_file = "/path/to/manifest.json"
        m = merge_cli_and_manifest(fm, target=fm.target)
        assert m.source_file == "/path/to/manifest.json"

    def test_original_file_manifest_not_mutated(self):
        fm = self._file_manifest()
        original_target = fm.target
        merge_cli_and_manifest(fm, target="https://different.com/v1")
        assert fm.target == original_target


# ─────────────────────────────────────────────
#  format_manifest_summary
# ─────────────────────────────────────────────

class TestFormatManifestSummary:

    def test_summary_contains_target(self):
        m = create_manifest(target="https://api.openai.com/v1")
        s = format_manifest_summary(m)
        assert "https://api.openai.com/v1" in s

    def test_summary_contains_mode(self):
        m = create_manifest(target="https://api.openai.com/v1", mode="api")
        s = format_manifest_summary(m)
        assert "api" in s

    def test_summary_contains_depth(self):
        m = create_manifest(target="https://api.openai.com/v1", scan_depth="deep")
        s = format_manifest_summary(m)
        assert "deep" in s

    def test_summary_contains_categories(self):
        m = create_manifest(
            target="https://api.openai.com/v1",
            categories=["jailbreak", "data_leak"],
        )
        s = format_manifest_summary(m)
        assert "jailbreak" in s
        assert "data_leak" in s

    def test_summary_contains_manifest_id(self):
        m = create_manifest(target="https://api.openai.com/v1")
        s = format_manifest_summary(m)
        assert m.manifest_id in s

    def test_summary_is_string(self):
        m = create_manifest(target="https://api.openai.com/v1")
        assert isinstance(format_manifest_summary(m), str)

    def test_api_key_not_in_summary(self):
        m = create_manifest(target="https://api.openai.com/v1", api_key="sk-secret")
        s = format_manifest_summary(m)
        assert "sk-secret" not in s


# ─────────────────────────────────────────────
#  generate_example_manifest
# ─────────────────────────────────────────────

class TestGenerateExampleManifest:

    def test_output_is_valid_json(self):
        j = generate_example_manifest()
        parsed = json.loads(j)
        assert isinstance(parsed, dict)

    def test_example_contains_required_fields(self):
        parsed = json.loads(generate_example_manifest())
        for key in ("target", "mode", "scan_depth", "categories"):
            assert key in parsed

    def test_custom_target_in_output(self):
        j = generate_example_manifest(target="http://localhost:8080", mode="local")
        parsed = json.loads(j)
        assert parsed["target"] == "http://localhost:8080"
        assert parsed["mode"] == "local"
