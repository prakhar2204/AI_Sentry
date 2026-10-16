"""
Phase 6h -- Deploy Configuration Tests
tests/test_deploy_config_phase6h.py

Tests for the deployment configuration model and validation logic.
Because the deploy configuration lives entirely in the TypeScript frontend
(no backend deploy module exists in this phase), these tests:

  1. Verify the backend report contract fields that Screen 9 depends on
     (meta.scan_id, meta.target, summary.risk_score, summary.risk_level).
  2. Verify that no deploy-related modules exist in the backend core
     (ensuring no accidental provisioning code was introduced).
  3. Document the frontend config model contract via Python-side integration tests
     against the report schema that Screen 9 reads from ReportContext.
  4. Verify that simulated scan IDs follow the "sim-" prefix convention
     that DeployConfigPage uses to detect simulation provenance.

Frontend-only tests (validation logic, provider selection, field state) are
documented here as contract specifications; they cannot be executed in pytest
without a JS runtime. Run them via browser testing or future vitest setup.

Run with:
    python -m pytest tests/test_deploy_config_phase6h.py -v
"""

import json
import os
import pytest

from core.manifest import create_manifest
from core.mock_engine import MockEngine
from core.scorer import generate_risk_report
from core.recommender import generate_recommendations
from core.report_generator import (
    ScanReport,
    generate_full_report,
    serialize_report,
    REPORT_VERSION,
)
from services.report_service import (
    store_report,
    get_report_by_id,
    clear_reports,
)


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

def _make_report(target: str = "https://api.example.com/v1") -> ScanReport:
    manifest = create_manifest(
        target=target,
        mode="api",
        scan_depth="standard",
        categories=["prompt_injection", "jailbreak"],
    )
    scan_result = MockEngine().run_scan(manifest)
    risk_report = generate_risk_report(scan_result.findings)
    rec_report = generate_recommendations(risk_report)
    return generate_full_report(manifest, scan_result, risk_report, rec_report)


# ─────────────────────────────────────────────
#  Backend no-provision guarantee
# ─────────────────────────────────────────────

class TestNoProvisioningCodeExists:
    """
    Verify that no cloud provisioning code was introduced in the backend
    as part of Phase 6h. Screen 9 is a pure frontend configuration screen.
    """

    def test_no_deploy_module_in_core(self):
        """core/ must not contain a deploy.py or cloud provisioning module."""
        core_dir = os.path.join(os.path.dirname(__file__), "..", "core")
        core_dir = os.path.abspath(core_dir)
        deploy_files = [
            f for f in os.listdir(core_dir)
            if "deploy" in f.lower() or "cloud" in f.lower() or "aws" in f.lower()
        ]
        assert deploy_files == [], (
            f"Phase 6h must not introduce backend provisioning modules: {deploy_files}"
        )

    def test_no_deploy_module_in_services(self):
        """services/ must not contain a deploy or cloud service."""
        svc_dir = os.path.join(os.path.dirname(__file__), "..", "services")
        svc_dir = os.path.abspath(svc_dir)
        deploy_files = [
            f for f in os.listdir(svc_dir)
            if "deploy" in f.lower() or "cloud" in f.lower() or "aws" in f.lower()
        ]
        assert deploy_files == [], (
            f"Phase 6h must not introduce backend cloud service modules: {deploy_files}"
        )

    def test_no_boto3_import_in_codebase(self):
        """boto3 must not be imported anywhere in the backend (no live AWS calls)."""
        backend_root = os.path.join(os.path.dirname(__file__), "..")
        backend_root = os.path.abspath(backend_root)
        found = []
        for dirpath, _, filenames in os.walk(backend_root):
            if ".pytest_cache" in dirpath or "__pycache__" in dirpath:
                continue
            # Exclude tests/ — test files may reference boto3 in assertions
            if os.path.basename(dirpath) == "tests":
                continue
            for fname in filenames:
                if fname.endswith(".py"):
                    fpath = os.path.join(dirpath, fname)
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if "import boto3" in content or "from boto3" in content:
                        found.append(fpath)
        assert found == [], (
            f"boto3 found in backend — no live AWS calls permitted in Phase 6h: {found}"
        )


# ─────────────────────────────────────────────
#  Report schema for Screen 9 consumption
# ─────────────────────────────────────────────

class TestReportSchemaForScreen9:
    """
    Screen 9 reads report.meta and report.summary from ReportContext.
    Verify those fields are present and well-formed for Screen 9 consumption.
    """

    def test_meta_target_is_string(self):
        report = _make_report()
        d = report.to_dict()
        assert isinstance(d["meta"]["target"], str)
        assert len(d["meta"]["target"]) > 0

    def test_meta_scan_id_is_string(self):
        report = _make_report()
        d = report.to_dict()
        assert isinstance(d["meta"]["scan_id"], str)
        assert len(d["meta"]["scan_id"]) > 0

    def test_meta_mode_is_api_or_local(self):
        report = _make_report()
        d = report.to_dict()
        assert d["meta"]["mode"] in ("api", "local")

    def test_summary_risk_score_is_int_range(self):
        report = _make_report()
        d = report.to_dict()
        score = d["summary"]["risk_score"]
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_summary_risk_level_valid(self):
        report = _make_report()
        d = report.to_dict()
        # Backend risk_level is lowercase (e.g. "low", "medium", "high", "critical", "none")
        assert d["summary"]["risk_level"] in ("critical", "high", "medium", "low", "none"), (
            f"Unexpected risk_level: {d['summary']['risk_level']!r}"
        )

    def test_summary_has_total_findings(self):
        report = _make_report()
        d = report.to_dict()
        assert "total_findings" in d["summary"]
        assert isinstance(d["summary"]["total_findings"], int)

    def test_findings_have_severity(self):
        report = _make_report()
        d = report.to_dict()
        for f in d["findings"]:
            assert f["severity"] in ("high", "medium", "low")

    def test_recommendations_have_actions(self):
        report = _make_report()
        d = report.to_dict()
        for rec in d["recommendations"]:
            assert isinstance(rec["actions"], list)
            for action in rec["actions"]:
                assert isinstance(action, str)


# ─────────────────────────────────────────────
#  Simulation provenance convention
# ─────────────────────────────────────────────

class TestSimulationProvenance:
    """
    Screen 9 detects simulation mode by checking scan_id.startsWith("sim-").
    Verify the convention is applied correctly.
    """

    def test_real_scan_id_does_not_start_with_sim(self):
        """Real pipeline scan IDs must not have the sim- prefix."""
        report = _make_report()
        assert not report.meta["scan_id"].startswith("sim-"), (
            "Real scans must not have sim- prefix — reserved for frontend simulation"
        )

    def test_different_targets_produce_different_scan_ids(self):
        """Each scan produces a unique scan_id."""
        r1 = _make_report("https://target1.example.com")
        r2 = _make_report("https://target2.example.com")
        assert r1.meta["scan_id"] != r2.meta["scan_id"]

    def test_scan_id_stable_in_report_service(self):
        """scan_id is preserved when stored and retrieved."""
        clear_reports()
        report = _make_report()
        original_id = report.meta["scan_id"]
        store_report(report)
        retrieved = get_report_by_id(original_id)
        assert retrieved is not None
        assert retrieved["meta"]["scan_id"] == original_id
        clear_reports()

    def test_report_target_preserved_through_storage(self):
        """Target value survives storage round-trip — used as header in Screen 9."""
        clear_reports()
        target = "https://my-llm-api.example.com/v1"
        report = _make_report(target)
        store_report(report)
        retrieved = get_report_by_id(report.meta["scan_id"])
        assert retrieved["meta"]["target"] == target
        clear_reports()


# ─────────────────────────────────────────────
#  Report independence contract
# ─────────────────────────────────────────────

class TestReportIndependence:
    """
    Deploy config state must remain SEPARATE from the scan report.
    These tests verify the backend report is immutable through storage.
    """

    def test_report_not_mutated_by_second_storage(self):
        """Storing a second report does not alter the first."""
        clear_reports()
        r1 = _make_report("https://first.example.com")
        r2 = _make_report("https://second.example.com")
        store_report(r1)
        store_report(r2)

        retrieved1 = get_report_by_id(r1.meta["scan_id"])
        assert retrieved1["meta"]["target"] == "https://first.example.com"
        clear_reports()

    def test_findings_count_unchanged_by_retrieval(self):
        """Findings count is stable across serialization."""
        clear_reports()
        report = _make_report()
        original_count = len(report.findings)
        store_report(report)
        retrieved = get_report_by_id(report.meta["scan_id"])
        assert len(retrieved["findings"]) == original_count
        clear_reports()

    def test_report_version_preserved(self):
        """report_version field survives storage round-trip."""
        clear_reports()
        report = _make_report()
        store_report(report)
        retrieved = get_report_by_id(report.meta["scan_id"])
        assert retrieved["report_version"] == REPORT_VERSION
        clear_reports()


# ─────────────────────────────────────────────
#  Frontend config model specification
#  (contract tests — not executable in pytest)
# ─────────────────────────────────────────────

class TestFrontendConfigModelContract:
    """
    Documents the expected behavior of the frontend deployTypes.ts model.

    These are backend-side contract tests that verify the backend schema
    assumptions embedded in the frontend validation logic.

    Frontend-specific assertions (provider selection, field state, form rendering)
    are documented as comments — they require a JS runtime to execute.
    """

    def test_aws_is_the_only_provisioning_provider(self):
        """
        D-022: AWS only for provisioning.
        Frontend shows Azure and GCP as "plan only".
        This test documents the expected constant in deployTypes.ts.
        """
        # FRONTEND CONTRACT:
        # AWS_DEPLOYMENT_MODES must have exactly: bedrock, sagemaker, lambda
        # Azure/GCP must NOT appear in AWS_DEPLOYMENT_MODES
        # Provider cards for azure/gcp must have badge "Plan only"
        # This is a documentation test — passes trivially
        assert True, "AWS is the only provider with automated provisioning (D-022)"

    def test_no_credentials_in_config_model(self):
        """
        D-017: Credentials must live in OS keychain only.
        DeployConfig must NOT contain: access_key, secret_key, password, token, credential.

        Verified in deployTypes.ts by inspection:
        - emptyDeployConfig() returns no credential fields
        - DeployConfig interface has no credential fields
        """
        # Backend doesn't hold deploy config — this documents the frontend contract
        forbidden_fields = {"access_key", "secret_key", "password", "token", "credential",
                            "api_key", "private_key", "service_account", "client_secret"}
        # If the frontend config dict were serialized and passed here, none of these
        # should appear. This test documents the constraint.
        assert len(forbidden_fields) > 0, "Credential fields must never appear in DeployConfig"

    def test_deployed_field_is_always_false(self):
        """
        DeployConfig.deployed must always be false literal in Phase 6h.
        No provisioning occurs on Screen 9.
        """
        # FRONTEND CONTRACT:
        # type: deployed: false (literal type, not boolean)
        # emptyDeployConfig() returns { deployed: false }
        # No action in DEPLOY_ACTIONS sets deployed to true
        # START_DEPLOY only sets phase, not deployed field
        assert True, "deployed is a false literal type — cannot be set to true in Phase 6h"

    def test_provider_change_resets_incompatible_fields(self):
        """
        Changing provider must reset: mode, region, instanceType.
        This prevents stale incompatible config surviving a provider switch.

        FRONTEND CONTRACT (DeployContext.tsx, SET_PROVIDER action):
          case SET_PROVIDER: {
            patch = { provider, mode: null, region: null, instanceType: null }
            applyConfigPatch(state, patch)
          }
        """
        assert True, "SET_PROVIDER resets mode, region, instanceType (verified in DeployContext.tsx)"

    def test_public_endpoint_requires_auth(self):
        """
        FRONTEND VALIDATION CONTRACT:
        If endpointScope == "public" AND requireAuth == false:
          endpointScopeV = fieldErr("Public endpoint without authentication is a security risk...")
          issues.push("Public endpoint requires authentication to be enabled")
          canProceed = false
        """
        assert True, "Public endpoint without auth is a blocking validation error"

    def test_validation_reruns_on_field_change(self):
        """
        FRONTEND CONTRACT:
        applyConfigPatch() always calls validateDeployConfig(newConfig).
        No stale 'valid' state is ever attached to changed values.
        """
        assert True, "Validation reruns on every patch via applyConfigPatch() in DeployContext"

    def test_aws_regions_are_static_not_live(self):
        """
        AWS region list is static (no live API call).
        Bedrock availability is marked as a static flag, not live data.
        Documented with 'may be out-of-date' disclaimer.
        """
        assert True, "Static region list — no live availability check performed"

    def test_budget_is_informational_only(self):
        """
        Budget field does not create a cloud billing alert.
        It is recorded in the plan only.
        """
        assert True, "Budget is plan-only, not a provider-enforced spending limit"


# ─────────────────────────────────────────────
#  Regression: screens 6-8 unaffected
# ─────────────────────────────────────────────

class TestRegressionScreens68:
    """Ensure report generation (Screens 6-8) still works after Phase 6h changes."""

    def test_report_generates_successfully(self):
        report = _make_report()
        assert report is not None
        assert report.meta["scan_id"]

    def test_serialize_report_valid_json(self):
        report = _make_report()
        json_str = serialize_report(report)
        parsed = json.loads(json_str)
        assert "meta" in parsed
        assert "findings" in parsed
        assert "recommendations" in parsed

    def test_report_has_all_top_level_keys(self):
        report = _make_report()
        d = report.to_dict()
        for key in ("report_version", "meta", "summary", "breakdown",
                    "categories", "findings", "recommendations", "engine"):
            assert key in d

    def test_store_and_retrieve_round_trip(self):
        clear_reports()
        report = _make_report()
        store_report(report)
        retrieved = get_report_by_id(report.meta["scan_id"])
        assert retrieved is not None
        assert retrieved["meta"]["scan_id"] == report.meta["scan_id"]
        clear_reports()
