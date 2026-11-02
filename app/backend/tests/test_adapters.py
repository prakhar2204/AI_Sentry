"""
Tests for core/adapters/garak_adapter.py and core/adapters/pyrit_adapter.py

Covers:
  - is_available() returns bool (True or False depending on installation)
  - run_scan() returns ScanResult with correct shape when engines NOT installed
  - _convert_severity() maps all int levels correctly
  - _build_evidence() produces non-empty strings
  - GarakAdapter / PyRITAdapter satisfy BaseEngine interface
  - engine_runner._select_engine() routes correctly for mock/garak/pyrit/auto
"""

import pytest

from core.engine_interface import BaseEngine, ScanFinding, ScanResult
from core.adapters.garak_adapter import GarakAdapter, _convert_severity, _build_evidence
from core.adapters.pyrit_adapter import PyRITAdapter
from core.engine_runner import _select_engine, run_engine
from core.mock_engine import MockEngine


# ─────────────────────────────────────────────────────────────────────────────
#  Severity conversion
# ─────────────────────────────────────────────────────────────────────────────

class TestConvertSeverity:
    def test_5_maps_to_high(self):
        assert _convert_severity(5) == "high"

    def test_4_maps_to_high(self):
        assert _convert_severity(4) == "high"

    def test_3_maps_to_medium(self):
        assert _convert_severity(3) == "medium"

    def test_2_maps_to_low(self):
        assert _convert_severity(2) == "low"

    def test_1_maps_to_low(self):
        assert _convert_severity(1) == "low"

    def test_unknown_maps_to_low(self):
        assert _convert_severity(99) == "low"

    def test_zero_maps_to_low(self):
        assert _convert_severity(0) == "low"

    def test_all_valid_values_produce_valid_severities(self):
        valid = {"low", "medium", "high"}
        for i in range(1, 6):
            assert _convert_severity(i) in valid


# ─────────────────────────────────────────────────────────────────────────────
#  Evidence builder
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildEvidence:
    def _make_finding(self, pass_rate=0.5, total=10, failed=5, probe="probes.dan.Dan", severity=4, confidence=0.8):
        from dataclasses import dataclass
        @dataclass
        class FakeFinding:
            pass_rate: float
            total: int
            failed: int
            probe: str
            severity: int
            confidence: float
            detector: str = "detectors.always.Fail"
        return FakeFinding(pass_rate=pass_rate, total=total, failed=failed,
                           probe=probe, severity=severity, confidence=confidence)

    def test_breach_evidence_non_empty(self):
        f = self._make_finding(pass_rate=0.3)
        ev = _build_evidence(f)
        assert isinstance(ev, str) and len(ev) > 10

    def test_breach_evidence_contains_percentage(self):
        f = self._make_finding(pass_rate=0.3)
        ev = _build_evidence(f)
        assert "70.0%" in ev or "%" in ev

    def test_passing_evidence_different_message(self):
        f = self._make_finding(pass_rate=1.0)
        ev = _build_evidence(f)
        assert "passed" in ev.lower() or "0%" in ev

    def test_probe_short_name_in_evidence(self):
        f = self._make_finding(probe="probes.dan.AutoDANCached")
        ev = _build_evidence(f)
        assert "AutoDANCached" in ev

    def test_dotless_probe_name_works(self):
        f = self._make_finding(probe="SimpleProbe")
        ev = _build_evidence(f)
        assert "SimpleProbe" in ev


# ─────────────────────────────────────────────────────────────────────────────
#  GarakAdapter interface
# ─────────────────────────────────────────────────────────────────────────────

class TestGarakAdapterInterface:
    def test_is_subclass_of_base_engine(self):
        assert issubclass(GarakAdapter, BaseEngine)

    def test_name_property(self):
        adapter = GarakAdapter()
        assert adapter.name == "garak"

    def test_is_available_returns_bool(self):
        result = GarakAdapter.is_available()
        assert isinstance(result, bool)

    def test_run_scan_when_not_available_returns_error_result(self):
        """When garak is not installed, run_scan returns a ScanResult with error."""
        if GarakAdapter.is_available():
            pytest.skip("Garak is installed — not testing unavailable path")

        from core.manifest import create_manifest
        manifest = create_manifest(
            target="http://localhost:8080/v1/chat/completions",
            mode="api",
            scan_depth="quick",
        )
        adapter = GarakAdapter()
        result = adapter.run_scan(manifest)

        assert isinstance(result, ScanResult)
        assert result.engine_name == "garak"
        assert result.error is not None
        assert "not installed" in result.error.lower() or "garak" in result.error.lower()
        assert result.findings == []

    def test_run_scan_error_result_has_correct_manifest_id(self):
        if GarakAdapter.is_available():
            pytest.skip("Garak is installed — not testing unavailable path")

        from core.manifest import create_manifest
        manifest = create_manifest(
            target="http://localhost:8080/v1/chat/completions",
            mode="api",
        )
        adapter = GarakAdapter()
        result = adapter.run_scan(manifest)
        assert result.manifest_id == manifest.manifest_id


# ─────────────────────────────────────────────────────────────────────────────
#  PyRITAdapter interface
# ─────────────────────────────────────────────────────────────────────────────

class TestPyRITAdapterInterface:
    def test_is_subclass_of_base_engine(self):
        assert issubclass(PyRITAdapter, BaseEngine)

    def test_name_property(self):
        adapter = PyRITAdapter()
        assert adapter.name == "pyrit"

    def test_is_available_returns_bool(self):
        result = PyRITAdapter.is_available()
        assert isinstance(result, bool)

    def test_run_scan_when_not_available_returns_error_result(self):
        """When pyrit is not installed, run_scan returns a ScanResult with error."""
        if PyRITAdapter.is_available():
            pytest.skip("PyRIT is installed — not testing unavailable path")

        from core.manifest import create_manifest
        manifest = create_manifest(
            target="http://localhost:8080/v1/chat/completions",
            mode="api",
            scan_depth="quick",
        )
        adapter = PyRITAdapter()
        result = adapter.run_scan(manifest)

        assert isinstance(result, ScanResult)
        assert result.engine_name == "pyrit"
        assert result.error is not None
        assert "not installed" in result.error.lower() or "pyrit" in result.error.lower()
        assert result.findings == []


# ─────────────────────────────────────────────────────────────────────────────
#  engine_runner._select_engine
# ─────────────────────────────────────────────────────────────────────────────

class TestSelectEngine:
    def test_mock_returns_mock_engine(self):
        engine = _select_engine("mock")
        assert isinstance(engine, MockEngine)

    def test_unknown_returns_mock_engine(self):
        engine = _select_engine("unknown_xyz")
        assert isinstance(engine, MockEngine)

    def test_empty_returns_mock_engine(self):
        engine = _select_engine("")
        assert isinstance(engine, MockEngine)

    def test_garak_returns_garak_adapter_or_mock(self):
        engine = _select_engine("garak")
        # Either GarakAdapter (if installed) or MockEngine (graceful fallback)
        assert isinstance(engine, (GarakAdapter, MockEngine))

    def test_pyrit_returns_pyrit_adapter_or_mock(self):
        engine = _select_engine("pyrit")
        assert isinstance(engine, (PyRITAdapter, MockEngine))

    def test_auto_returns_garak_or_mock(self):
        engine = _select_engine("auto")
        assert isinstance(engine, (GarakAdapter, MockEngine))

    def test_auto_without_garak_falls_back_to_mock(self):
        if GarakAdapter.is_available():
            pytest.skip("Garak installed — testing fallback only when absent")
        engine = _select_engine("auto")
        assert isinstance(engine, MockEngine)

    def test_case_insensitive_garak(self):
        engine = _select_engine("GARAK")
        assert isinstance(engine, (GarakAdapter, MockEngine))

    def test_case_insensitive_pyrit(self):
        engine = _select_engine("PYRIT")
        assert isinstance(engine, (PyRITAdapter, MockEngine))


# ─────────────────────────────────────────────────────────────────────────────
#  run_engine integration (using mock engine)
# ─────────────────────────────────────────────────────────────────────────────

class TestRunEngine:
    def _make_manifest(self):
        from core.manifest import create_manifest
        return create_manifest(
            target="http://localhost:8080/v1/chat/completions",
            mode="api",
            scan_depth="quick",
        )

    def test_mock_engine_returns_scan_result(self):
        manifest = self._make_manifest()
        result = run_engine(manifest, engine_name="mock")
        assert isinstance(result, ScanResult)
        assert result.engine_name == "mock"
        assert result.ok

    def test_mock_findings_have_valid_severities(self):
        manifest = self._make_manifest()
        result = run_engine(manifest, engine_name="mock")
        for f in result.findings:
            assert f.severity in ("low", "medium", "high")
            assert 0.0 <= f.confidence <= 1.0

    def test_garak_returns_result_with_correct_engine_name(self):
        if GarakAdapter.is_available():
            pytest.skip("Skipping unavailable path test — garak is installed")
        manifest = self._make_manifest()
        result = run_engine(manifest, engine_name="garak")
        # When not installed: GarakAdapter.run_scan returns error ScanResult
        assert isinstance(result, ScanResult)
        # Either error (not installed) or success with findings
        assert result.engine_name in ("garak", "mock")

    def test_default_engine_name_is_mock(self):
        manifest = self._make_manifest()
        result = run_engine(manifest)  # no engine_name arg
        assert result.engine_name == "mock"
