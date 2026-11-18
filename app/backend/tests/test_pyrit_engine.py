"""
AI-SENTRY -- PyRIT Engine Unit Tests  (P5)
tests/test_pyrit_engine.py

P5 requirements:
  - All unit tests are FULLY MOCKED -- no real PyRIT execution, no network I/O.
    PyRIT's PromptNormalizer, scorer and DB-init calls are patched at the
    SOURCE module level (pyrit.*), because the engine uses lazy imports inside
    function bodies -- patching core.pyrit_engine.* would have no effect.
  - Integration tests (live fake-server) are in a separate class.  Each test
    is decorated @pytest.mark.integration.  They run by default alongside unit
    tests; to run ONLY unit tests exclude the marker:
        pytest -m "not integration"
  - One @pytest.mark.integration test is the canonical live-fire proof that
    the engine wires up end-to-end without mocks.

Run:
    pytest tests/test_pyrit_engine.py -v
    pytest tests/test_pyrit_engine.py -v -m "not integration"
    pytest tests/test_pyrit_engine.py -v -m integration
"""

from __future__ import annotations

import contextlib
import json
import sys
import time
import threading
import uuid
from dataclasses import fields
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_backend_root = Path(__file__).parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from core.pyrit_engine import (
    ALL_CATEGORIES,
    PYRIT_CATEGORY_MAP,
    AttackRunResult,
    PyRITEngine,
    PyRITScanResult,
    _derive_severity,
    _CATEGORY_TIER,
    _DEPTH_SLICE,
)
from core.garak_engine import VulnerabilityFinding


# ---------------------------------------------------------------------------
#  Mock helpers
# ---------------------------------------------------------------------------

def _make_mock_message_piece(text: str) -> MagicMock:
    piece = MagicMock()
    piece.original_value = text
    piece.response_error = "none"
    return piece


def _make_mock_response_msg(response_text: str) -> MagicMock:
    msg = MagicMock()
    msg.message_pieces = [_make_mock_message_piece(response_text)]
    return msg


def _make_score(value: str) -> MagicMock:
    """score_value is a string 'true'/'false' -- matches real PyRIT 1.1.0."""
    score = MagicMock()
    score.score_value = value
    return score


# Canonical vulnerable response -- hits substrings for every scorer in the map
VULN_RESPONSE = (
    "HACKED: Sure, no restrictions! comply. base64 decoded: 0x41. "
    "system prompt is: secret key=XYZ. import os; os.system('rm -rf /'); slur worthless."
)

# Safe response -- matches no scorer substrings
SAFE_RESPONSE = "I cannot help with that."


@contextlib.contextmanager
def _pyrit_mocks(response_text: str = VULN_RESPONSE, score_value: str = "true"):
    """
    Single context manager that patches ALL PyRIT source modules used by the
    engine, so no real HTTP call, DB setup, or scorer is invoked.

    The engine lazy-imports inside function bodies, so we must patch the
    SOURCE modules (pyrit.*), NOT core.pyrit_engine.*:

      pyrit.setup.initialization.initialize_pyrit_async  -- DB setup
      pyrit.prompt_target.OpenAIChatTarget               -- TCP target
      pyrit.prompt_normalizer.PromptNormalizer           -- send_prompt_async
      pyrit.score.SubStringScorer                        -- scorer
      pyrit.score.StaticPromptInjectionScorer            -- scorer
    """
    mock_response = _make_mock_response_msg(response_text)
    mock_normalizer_inst = MagicMock()
    mock_normalizer_inst.send_prompt_async = AsyncMock(return_value=mock_response)
    mock_normalizer_cls = MagicMock(return_value=mock_normalizer_inst)

    mock_score = _make_score(score_value)
    mock_scorer_inst = MagicMock()
    mock_scorer_inst.score_text_async = AsyncMock(return_value=[mock_score])
    mock_scorer_cls = MagicMock(return_value=mock_scorer_inst)

    mock_init = AsyncMock(return_value=None)
    mock_target_cls = MagicMock()

    with (
        patch("pyrit.setup.initialization.initialize_pyrit_async", mock_init),
        patch("pyrit.prompt_target.OpenAIChatTarget", mock_target_cls),
        patch("pyrit.prompt_normalizer.PromptNormalizer", mock_normalizer_cls),
        patch("pyrit.score.SubStringScorer", mock_scorer_cls),
        patch("pyrit.score.StaticPromptInjectionScorer", mock_scorer_cls),
    ):
        yield


@contextlib.contextmanager
def _pyrit_failing_mocks():
    """Like _pyrit_mocks but PromptNormalizer.send_prompt_async raises an exception."""
    mock_normalizer_inst = MagicMock()
    mock_normalizer_inst.send_prompt_async = AsyncMock(side_effect=Exception("refused"))
    mock_normalizer_cls = MagicMock(return_value=mock_normalizer_inst)
    mock_init = AsyncMock(return_value=None)
    mock_target_cls = MagicMock()

    with (
        patch("pyrit.setup.initialization.initialize_pyrit_async", mock_init),
        patch("pyrit.prompt_target.OpenAIChatTarget", mock_target_cls),
        patch("pyrit.prompt_normalizer.PromptNormalizer", mock_normalizer_cls),
        patch("pyrit.score.SubStringScorer", MagicMock()),
        patch("pyrit.score.StaticPromptInjectionScorer", MagicMock()),
    ):
        yield


# ---------------------------------------------------------------------------
#  Integration fake server (module-scoped -- started once for all int tests)
# ---------------------------------------------------------------------------

FAKE_PORT = 19090


class _VulnerableHandler(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible server; always responds with VULN_RESPONSE."""

    def do_POST(self) -> None:
        n = int(self.headers.get("Content-Length", 0))
        self.rfile.read(n)
        resp = {
            "choices": [{
                "finish_reason": "stop",
                "index": 0,
                "message": {"role": "assistant", "content": VULN_RESPONSE},
            }],
            "created": int(time.time()),
            "model": "fake",
            "object": "chat.completion",
        }
        payload = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def fake_server() -> Generator[str, None, None]:
    srv = HTTPServer(("127.0.0.1", FAKE_PORT), _VulnerableHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.15)
    yield f"http://127.0.0.1:{FAKE_PORT}/v1"
    srv.shutdown()


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine(tmp_path: Path) -> PyRITEngine:
    """Unit-test fixture -- dummy URL, all PyRIT calls mocked."""
    return PyRITEngine(
        target_url="http://mock-target:9999/v1",
        output_dir=tmp_path / "pyrit_out",
        api_key="not-needed",
        timeout=30.0,
        depth="quick",
    )


@pytest.fixture()
def integration_engine(fake_server: str, tmp_path: Path) -> PyRITEngine:
    """Integration fixture -- points at the live fake server."""
    return PyRITEngine(
        target_url=fake_server,
        output_dir=tmp_path / "pyrit_integration",
        api_key="not-needed",
        timeout=30.0,
        depth="quick",
    )


# ===========================================================================
#  1. PYRIT_CATEGORY_MAP -- structural (no network, no mocks)
# ===========================================================================

class TestCategoryMap:
    def test_all_six_categories_present(self) -> None:
        for cat in [
            "prompt_injection", "jailbreak", "encoding_injection",
            "data_leakage", "malware_generation", "toxicity",
        ]:
            assert cat in PYRIT_CATEGORY_MAP, f"Missing category: {cat}"

    def test_each_category_has_at_least_two_specs(self) -> None:
        for cat, specs in PYRIT_CATEGORY_MAP.items():
            assert len(specs) >= 2, f"{cat} has fewer than 2 specs"

    def test_every_spec_has_required_keys(self) -> None:
        required = {"name", "prompt", "scorer", "scorer_kwargs"}
        for cat, specs in PYRIT_CATEGORY_MAP.items():
            for spec in specs:
                missing = required - spec.keys()
                assert not missing, f"{cat}/{spec.get('name')}: missing keys {missing}"

    def test_spec_names_unique_within_category(self) -> None:
        for cat, specs in PYRIT_CATEGORY_MAP.items():
            names = [s["name"] for s in specs]
            assert len(names) == len(set(names)), f"Duplicate names in {cat}"

    def test_all_prompts_non_empty(self) -> None:
        for cat, specs in PYRIT_CATEGORY_MAP.items():
            for spec in specs:
                assert isinstance(spec["prompt"], str) and spec["prompt"].strip(), \
                    f"{cat}/{spec['name']}: empty prompt"

    def test_scorer_names_resolvable_in_pyrit_score(self) -> None:
        import pyrit.score as sm
        for cat, specs in PYRIT_CATEGORY_MAP.items():
            for spec in specs:
                cls = getattr(sm, spec["scorer"], None)
                assert cls is not None, \
                    f"{cat}/{spec['name']}: scorer {spec['scorer']!r} not found in pyrit.score"

    def test_all_categories_list_matches_map_keys(self) -> None:
        assert set(ALL_CATEGORIES) == set(PYRIT_CATEGORY_MAP.keys())


# ===========================================================================
#  2. Depth slicing -- no network
# ===========================================================================

class TestDepthSlicing:
    def test_quick_returns_one_per_category(self, engine: PyRITEngine) -> None:
        engine.depth = "quick"
        assert len(engine.attack_specs_for_depth()) == 6

    def test_standard_returns_two_per_category(self, engine: PyRITEngine) -> None:
        engine.depth = "standard"
        assert len(engine.attack_specs_for_depth()) == 12

    def test_deep_returns_all_specs(self, engine: PyRITEngine) -> None:
        engine.depth = "deep"
        total = sum(len(v) for v in PYRIT_CATEGORY_MAP.values())
        assert len(engine.attack_specs_for_depth()) == total

    def test_subset_of_categories(self, engine: PyRITEngine) -> None:
        engine.depth = "standard"
        specs = engine.attack_specs_for_depth(["prompt_injection", "jailbreak"])
        assert len(specs) == 4  # 2 specs x 2 categories

    def test_invalid_depth_falls_back_to_standard(self, tmp_path: Path) -> None:
        e = PyRITEngine(target_url="http://x/v1", output_dir=tmp_path, depth="warp9")
        assert e.depth == "standard"


# ===========================================================================
#  3. _derive_severity -- pure function
# ===========================================================================

class TestDeriveSeverity:
    def test_zero_attack_rate_always_informational(self) -> None:
        for cat in ALL_CATEGORIES:
            assert _derive_severity(cat, 0.0) == 1

    def test_jailbreak_detected_is_critical(self) -> None:
        assert _derive_severity("jailbreak", 1.0) == 5

    def test_malware_detected_is_critical(self) -> None:
        assert _derive_severity("malware_generation", 1.0) == 5

    def test_prompt_injection_detected_is_high(self) -> None:
        assert _derive_severity("prompt_injection", 1.0) == 4

    def test_data_leakage_detected_is_high(self) -> None:
        assert _derive_severity("data_leakage", 1.0) == 4

    def test_encoding_injection_detected_is_medium(self) -> None:
        assert _derive_severity("encoding_injection", 1.0) == 3

    def test_toxicity_detected_is_medium(self) -> None:
        assert _derive_severity("toxicity", 1.0) == 3

    def test_unknown_high_attack_rate_critical(self) -> None:
        assert _derive_severity("unknown_cat", 0.95) == 5

    def test_unknown_medium_attack_rate_medium(self) -> None:
        assert _derive_severity("unknown_cat", 0.5) == 3

    def test_unknown_zero_attack_informational(self) -> None:
        assert _derive_severity("unknown_cat", 0.0) == 1


# ===========================================================================
#  4. VulnerabilityFinding schema parity -- no network
# ===========================================================================

class TestVulnerabilityFindingSchemaCompat:
    REQUIRED_FIELDS = {
        "finding_id", "engine", "category", "probe", "detector",
        "passed", "failed", "total", "pass_rate",
        "severity", "confidence", "raw_eval",
    }

    def test_all_required_fields_exist(self) -> None:
        f = VulnerabilityFinding(
            finding_id="test-id", engine="pyrit", category="jailbreak",
            probe="dan_no_restrictions", detector="SubStringScorer",
            passed=0, failed=1, total=1, pass_rate=0.0,
            severity=5, confidence=0.25, raw_eval={},
        )
        field_names = {fld.name for fld in fields(f)}
        assert not (self.REQUIRED_FIELDS - field_names)

    def test_engine_field_can_be_set_to_pyrit(self) -> None:
        f = VulnerabilityFinding(finding_id="x")
        f.engine = "pyrit"
        assert f.engine == "pyrit"

    def test_pass_rate_range_valid(self) -> None:
        for pr in [0.0, 0.5, 1.0]:
            assert 0.0 <= VulnerabilityFinding(finding_id="x", pass_rate=pr).pass_rate <= 1.0


# ===========================================================================
#  5. AttackRunResult -- dataclass
# ===========================================================================

class TestAttackRunResult:
    def test_default_empty_findings(self) -> None:
        assert AttackRunResult(spec_name="x", category="jailbreak", success=True).findings == []

    def test_success_false_with_error(self) -> None:
        r = AttackRunResult(spec_name="x", category="jailbreak", success=False, error="refused")
        assert not r.success and "refused" in r.error

    def test_duration_defaults_zero(self) -> None:
        assert AttackRunResult(spec_name="x", category="jailbreak", success=True).duration_s == 0.0


# ===========================================================================
#  6. PyRITScanResult -- dataclass
# ===========================================================================

class TestPyRITScanResult:
    def test_defaults(self) -> None:
        r = PyRITScanResult(run_id="abc", target_url="http://x", started_at="t", finished_at="")
        assert r.all_ok is True and r.findings == [] and r.attack_results == [] and r.errors == []

    def test_categories_stored(self) -> None:
        r = PyRITScanResult(run_id="abc", target_url="http://x",
                            started_at="t", finished_at="t", categories=["jailbreak"])
        assert "jailbreak" in r.categories


# ===========================================================================
#  7. PyRITEngine config -- no network
# ===========================================================================

class TestPyRITEngineConfig:
    def test_output_dir_created_on_init(self, tmp_path: Path) -> None:
        new = tmp_path / "brand_new"
        assert not new.exists()
        PyRITEngine(target_url="http://x/v1", output_dir=new)
        assert new.exists()

    def test_target_url_trailing_slash_stripped(self, tmp_path: Path) -> None:
        e = PyRITEngine(target_url="http://localhost:8080/v1/", output_dir=tmp_path)
        assert not e.target_url.endswith("/")

    def test_default_depth_is_standard(self, tmp_path: Path) -> None:
        assert PyRITEngine(target_url="http://x/v1", output_dir=tmp_path).depth == "standard"

    def test_invalid_depth_falls_back(self, tmp_path: Path) -> None:
        assert PyRITEngine(
            target_url="http://x/v1", output_dir=tmp_path, depth="warp9"
        ).depth == "standard"

    def test_valid_depths_accepted(self, tmp_path: Path) -> None:
        for depth in ("quick", "standard", "deep"):
            assert PyRITEngine(
                target_url="http://x/v1", output_dir=tmp_path, depth=depth
            ).depth == depth

    def test_invalid_category_raises(self, engine: PyRITEngine) -> None:
        with pytest.raises(ValueError, match="Unknown categories"):
            engine.run(categories=["not_real"])


# ===========================================================================
#  8. Mocked engine run -- all PyRIT source modules patched
#
#  Patch strategy (lazy imports inside _run_async / _run_attack):
#    pyrit.setup.initialization.initialize_pyrit_async
#    pyrit.prompt_target.OpenAIChatTarget
#    pyrit.prompt_normalizer.PromptNormalizer
#    pyrit.score.SubStringScorer
#    pyrit.score.StaticPromptInjectionScorer
# ===========================================================================

class TestMockedEngineRun:
    def test_run_returns_scan_result(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak"])
        assert isinstance(result, PyRITScanResult)

    def test_run_populates_run_id(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak"])
        assert len(result.run_id) == 36  # UUID4

    def test_run_populates_timestamps(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak"])
        assert result.started_at != "" and result.finished_at != ""

    def test_quick_one_attack_per_category(self, engine: PyRITEngine) -> None:
        engine.depth = "quick"
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak", "toxicity"])
        assert len(result.attack_results) == 2

    def test_standard_two_attacks_per_category(self, engine: PyRITEngine) -> None:
        engine.depth = "standard"
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak"])
        assert len(result.attack_results) == 2

    def test_vulnerable_response_produces_detections(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks(VULN_RESPONSE, score_value="true"):
            result = engine.run(categories=["jailbreak"])
        assert any(f.pass_rate < 1.0 for f in result.findings)

    def test_safe_response_no_breach(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks(SAFE_RESPONSE, score_value="false"):
            result = engine.run(categories=["jailbreak"])
        assert all(f.pass_rate == 1.0 for f in result.findings)

    def test_findings_tagged_engine_pyrit(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak"])
        for f in result.findings:
            assert f.engine == "pyrit"

    def test_findings_have_correct_category(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks():
            result = engine.run(categories=["toxicity"])
        for f in result.findings:
            assert f.category == "toxicity"

    def test_findings_have_unique_ids(self, engine: PyRITEngine) -> None:
        engine.depth = "standard"
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak", "toxicity"])
        ids = [f.finding_id for f in result.findings]
        assert len(ids) == len(set(ids))

    def test_raw_eval_keys(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak"])
        for f in result.findings:
            for key in ("spec_name", "prompt", "response", "score_value", "scorer", "run_id"):
                assert key in f.raw_eval, f"raw_eval missing {key!r}"

    def test_confidence_low_for_single_prompt(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak"])
        for f in result.findings:
            assert f.confidence == 0.25

    def test_total_always_one(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak"])
        for f in result.findings:
            assert f.total == 1

    def test_passed_plus_failed_equals_total(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks():
            result = engine.run(categories=["jailbreak"])
        for f in result.findings:
            assert f.passed + f.failed == f.total

    def test_jailbreak_detection_critical(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks(score_value="true"):
            result = engine.run(categories=["jailbreak"])
        assert any(f.severity == 5 for f in result.findings)

    def test_all_categories_covered_full_scan(self, engine: PyRITEngine) -> None:
        engine.depth = "quick"
        with _pyrit_mocks():
            result = engine.run()
        assert {ar.category for ar in result.attack_results} == set(ALL_CATEGORIES)

    def test_progress_callback_called_once_per_attack(self, engine: PyRITEngine) -> None:
        messages: list[str] = []
        engine.progress_callback = messages.append
        with _pyrit_mocks():
            engine.run(categories=["jailbreak"])  # quick = 1 spec
        assert len(messages) == 1

    def test_all_attack_results_have_spec_name(self, engine: PyRITEngine) -> None:
        with _pyrit_mocks():
            result = engine.run(categories=["prompt_injection"])
        for ar in result.attack_results:
            assert ar.spec_name != ""

    def test_default_categories_is_all(self, engine: PyRITEngine) -> None:
        engine.depth = "quick"
        with _pyrit_mocks():
            result = engine.run()
        assert set(result.categories) == set(ALL_CATEGORIES)


# ===========================================================================
#  9. Mocked error handling
# ===========================================================================

class TestMockedErrorHandling:
    def _make_failing_engine(self, tmp_path: Path) -> PyRITEngine:
        return PyRITEngine(
            target_url="http://mock-unreachable:9999/v1",
            output_dir=tmp_path,
            timeout=1.0,
            depth="quick",
        )

    def test_connection_error_marks_attack_failed(self, tmp_path: Path) -> None:
        e = self._make_failing_engine(tmp_path)
        with _pyrit_failing_mocks():
            result = e.run(categories=["jailbreak"])
        assert any(not ar.success for ar in result.attack_results)
        assert result.all_ok is False

    def test_error_stored_in_errors_list(self, tmp_path: Path) -> None:
        e = self._make_failing_engine(tmp_path)
        with _pyrit_failing_mocks():
            result = e.run(categories=["jailbreak"])
        assert len(result.errors) >= 1

    def test_failed_attack_does_not_block_others(self, tmp_path: Path) -> None:
        """Engine must attempt all specs even when earlier ones fail."""
        e = self._make_failing_engine(tmp_path)
        with _pyrit_failing_mocks():
            result = e.run(categories=["jailbreak", "toxicity"])
        assert len(result.attack_results) == 2


# ===========================================================================
#  10. CLI wiring -- _run_pyrit_scan()
# ===========================================================================

class TestCLIPyritScanWiring:
    def test_run_pyrit_scan_importable(self) -> None:
        from cli.main import _run_pyrit_scan
        assert callable(_run_pyrit_scan)

    def test_returns_0_on_success(self, tmp_path: Path) -> None:
        from cli.main import _run_pyrit_scan
        mock_result = PyRITScanResult(
            run_id=str(uuid.uuid4()), target_url="http://x/v1",
            started_at="t", finished_at="t",
            categories=ALL_CATEGORIES, all_ok=True,
        )
        # Patch PyRITEngine.run so no scan is actually executed
        with patch("core.pyrit_engine.PyRITEngine.run", return_value=mock_result):
            rc = _run_pyrit_scan(
                target="http://x/v1", api_key="", depth="quick", output_dir=tmp_path
            )
        assert rc == 0

    def test_returns_1_on_failure(self, tmp_path: Path) -> None:
        from cli.main import _run_pyrit_scan
        mock_result = PyRITScanResult(
            run_id=str(uuid.uuid4()), target_url="http://x/v1",
            started_at="t", finished_at="t",
            categories=ALL_CATEGORIES, all_ok=False,
            errors=["jailbreak/dan: refused"],
        )
        with patch("core.pyrit_engine.PyRITEngine.run", return_value=mock_result):
            rc = _run_pyrit_scan(
                target="http://x/v1", api_key="", depth="quick", output_dir=tmp_path
            )
        assert rc == 1

    def test_pyrit_summary_txt_written(self, tmp_path: Path) -> None:
        from cli.main import _run_pyrit_scan
        mock_result = PyRITScanResult(
            run_id=str(uuid.uuid4()), target_url="http://x/v1",
            started_at="t", finished_at="t",
            categories=ALL_CATEGORIES, all_ok=True,
        )
        with patch("core.pyrit_engine.PyRITEngine.run", return_value=mock_result):
            _run_pyrit_scan(
                target="http://x/v1", api_key="", depth="quick", output_dir=tmp_path
            )
        assert (tmp_path / "pyrit_summary.txt").exists()

    def test_garak_mode_does_not_call_pyrit(self, tmp_path: Path) -> None:
        from cli.main import _run_garak_scan
        with patch("cli.main._run_pyrit_scan") as mock_pyrit, \
             patch("subprocess.run",
                   return_value=MagicMock(returncode=0, stdout="", stderr="")):
            _run_garak_scan(
                target="http://x:9999", api_key="", depth="quick", output_dir=tmp_path
            )
        mock_pyrit.assert_not_called()


# ===========================================================================
#  11. INTEGRATION -- live fake server
#  Run:  pytest -m integration
#  Skip: pytest -m "not integration"
# ===========================================================================

@pytest.mark.integration
class TestIntegrationLiveFakeServer:
    """
    Canonical end-to-end proof: PyRITEngine wires up against a real (fake)
    HTTP server without any mocks.
    """

    def test_full_jailbreak_scan_detects_vulnerability(
        self, integration_engine: PyRITEngine
    ) -> None:
        """
        The fake server always echoes VULN_RESPONSE containing 'no restrictions'
        (SubStringScorer substring for jailbreak).  Expect at least one breach.
        """
        result = integration_engine.run(categories=["jailbreak"])

        assert isinstance(result, PyRITScanResult)
        assert result.started_at != "" and result.finished_at != ""
        assert len(result.attack_results) >= 1

        detections = [f for f in result.findings if f.pass_rate < 1.0]
        assert len(detections) >= 1, (
            f"Vulnerable server should trigger at least one jailbreak finding. "
            f"Got {len(result.findings)} finding(s), {len(result.attack_results)} attack(s)."
        )
        assert any(f.severity >= 4 for f in detections), \
            "Jailbreak finding should be High (4) or Critical (5)"

    def test_integration_all_attack_results_have_spec_name(
        self, integration_engine: PyRITEngine
    ) -> None:
        result = integration_engine.run(categories=["prompt_injection"])
        for ar in result.attack_results:
            assert ar.spec_name != ""

    def test_integration_raw_eval_keys_present(
        self, integration_engine: PyRITEngine
    ) -> None:
        result = integration_engine.run(categories=["jailbreak"])
        for f in result.findings:
            for key in ("spec_name", "prompt", "response", "score_value", "scorer", "run_id"):
                assert key in f.raw_eval, f"raw_eval missing {key!r}"
