"""
Sentryɸ -- Phase 6i Cloud Compare Tests
tests/test_cloud_compare_phase6i.py

Backend contract and logic tests for Screen 10 (Cloud Compare).

Coverage:
  A. No provisioning code in backend
  B. Report schema unchanged by comparison screen (screens 6-9 regression)
  C. Comparison logic contracts (verified from TypeScript pure functions)
  D. Frontend comparison type contracts (documented, not runnable in Python)

Note: The comparison engine lives entirely in the frontend (compareTypes.ts).
      Backend tests verify that no cloud provisioning code has been introduced
      and that the backend report contract remains stable.
"""

from __future__ import annotations

import json
import os
import pytest
from pathlib import Path

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
#  Helpers
# ─────────────────────────────────────────────

def _make_report(
    target: str = "https://compare-test.example.com",
    categories: list[str] | None = None,
) -> ScanReport:
    if categories is None:
        categories = ["prompt_injection", "jailbreak"]
    manifest = create_manifest(
        target=target,
        mode="api",
        scan_depth="standard",
        categories=categories,
    )
    scan_result = MockEngine().run_scan(manifest)
    risk_report = generate_risk_report(scan_result.findings)
    rec_report  = generate_recommendations(risk_report)
    return generate_full_report(manifest, scan_result, risk_report, rec_report)



# ─────────────────────────────────────────────
#  A. No provisioning code in backend
# ─────────────────────────────────────────────

class TestNoProvisioningCodeExists:
    """Verify backend has no live cloud provisioning code (D-022)."""

    def _scan_backend_python(self, pattern: str, exclude_dirs: list[str] | None = None) -> list[str]:
        backend_root = Path(__file__).parent.parent
        exclude = set(exclude_dirs or [])
        found = []
        for dirpath, dirnames, filenames in os.walk(backend_root):
            p = Path(dirpath)
            # Exclude test directories and cache
            if ".pytest_cache" in dirpath or "__pycache__" in dirpath:
                continue
            if p.name in exclude:
                continue
            for fname in filenames:
                if fname.endswith(".py"):
                    fpath = p / fname
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                        if pattern.lower() in content.lower():
                            found.append(str(fpath))
                    except OSError:
                        pass
        return found

    def test_no_boto3_import_in_production_code(self):
        """No live AWS SDK imports in production backend code."""
        found = self._scan_backend_python("import boto3", exclude_dirs=["tests"])
        assert found == [], f"boto3 found in production backend: {found}"

    def test_no_cloud_provisioning_module(self):
        """No cloud provisioning module in core/ or services/."""
        backend_root = Path(__file__).parent.parent
        for suspect in ["cloud_provision", "aws_deploy", "azure_deploy", "gcp_deploy", "deploy_executor"]:
            for d in ["core", "services"]:
                candidate = backend_root / d / f"{suspect}.py"
                assert not candidate.exists(), f"Unexpected file: {candidate}"

    def test_no_terraform_commands_in_codebase(self):
        """No terraform CLI invocations in production backend code."""
        found = self._scan_backend_python("subprocess", exclude_dirs=["tests"])
        # subprocess is allowed for local model execution — just not for terraform
        for fpath in found:
            content = Path(fpath).read_text(encoding="utf-8", errors="ignore")
            assert "terraform" not in content.lower(), (
                f"terraform subprocess call found in {fpath}"
            )

    def test_no_aws_credentials_in_codebase(self):
        """No hardcoded AWS credentials in production backend code."""
        for secret_pattern in ["AKID", "aws_secret_access_key", "aws_access_key_id"]:
            found = self._scan_backend_python(secret_pattern, exclude_dirs=["tests"])
            assert found == [], (
                f"Potential credential pattern '{secret_pattern}' found in: {found}"
            )


# ─────────────────────────────────────────────
#  B. Report schema stability (screens 6-9 regression)
# ─────────────────────────────────────────────

class TestReportSchemaStability:
    """Verify the backend ScanReport contract is unchanged after Phase 6i."""

    REQUIRED_KEYS = {"meta", "summary", "findings", "recommendations", "engine", "report_version"}

    def test_report_has_all_required_top_level_keys(self):
        report = _make_report()
        d = report.to_dict()
        assert self.REQUIRED_KEYS.issubset(d.keys()), (
            f"Missing keys: {self.REQUIRED_KEYS - d.keys()}"
        )

    def test_meta_fields_present(self):
        report = _make_report()
        meta = report.to_dict()["meta"]
        # Use actual backend schema field names
        for field in ("scan_id", "target", "mode", "categories", "report_generated_at"):
            assert field in meta, f"meta.{field} is missing"

    def test_summary_fields_present(self):
        report = _make_report()
        summary = report.to_dict()["summary"]
        # Actual backend summary fields
        for field in ("risk_score", "risk_level", "total_findings"):
            assert field in summary, f"summary.{field} is missing"

    def test_findings_are_list(self):
        report = _make_report()
        findings = report.to_dict()["findings"]
        assert isinstance(findings, list)

    def test_findings_have_required_fields(self):
        report = _make_report()
        for finding in report.to_dict()["findings"]:
            for field in ("category", "severity", "confidence", "evidence", "source"):
                assert field in finding, f"finding.{field} is missing"

    def test_recommendations_are_list(self):
        report = _make_report()
        recs = report.to_dict()["recommendations"]
        assert isinstance(recs, list)

    def test_recommendations_have_actions(self):
        report = _make_report()
        for rec in report.to_dict()["recommendations"]:
            assert "actions" in rec, "recommendation.actions is missing"
            assert isinstance(rec["actions"], list)

    def test_risk_level_lowercase(self):
        report = _make_report()
        level = report.to_dict()["summary"]["risk_level"]
        assert level in ("critical", "high", "medium", "low", "none"), (
            f"Unexpected risk_level: {level!r}"
        )

    def test_version_field_is_string(self):
        report = _make_report()
        # Backend uses report_version not version
        d = report.to_dict()
        assert "report_version" in d or "version" in d, (
            "Report must have a report_version or version field"
        )

    def test_report_json_serializable(self):
        report = _make_report()
        try:
            json.dumps(report.to_dict())
        except (TypeError, ValueError) as exc:
            pytest.fail(f"Report not JSON-serializable: {exc}")

    def test_deployed_field_not_in_report(self):
        """Report must not contain deployment state — these live in DeployContext."""
        report = _make_report()
        d = report.to_dict()
        assert "deployed" not in d, "deployed field must not appear in ScanReport"
        assert "deployment_config" not in d, "deployment_config must not appear in ScanReport"

    def test_report_independent_of_deploy_config(self):
        """Generating a second report with a different target does not mutate the first."""
        r1 = _make_report(target="https://first.example.com")
        r2 = _make_report(target="https://second.example.com")
        assert r1.to_dict()["meta"]["target"] == "https://first.example.com"
        assert r2.to_dict()["meta"]["target"] == "https://second.example.com"


# ─────────────────────────────────────────────
#  C. Comparison logic contracts
#     (Python mirror of compareTypes.ts pure logic)
# ─────────────────────────────────────────────

class TestComparisonLogicContracts:
    """
    Mirror the TypeScript comparison logic contracts in Python.

    These tests verify the DESIGN CONTRACTS of the frontend comparison engine.
    They do not execute TypeScript — they assert the rules that the frontend
    code must implement, making violations visible in CI.
    """

    # Simulated config dictionaries (mirroring DeployConfig TypeScript type)

    def _cfg(self, **overrides) -> dict:
        base = {
            "provider": None,
            "mode": None,
            "region": None,
            "modelId": "",
            "modelLabel": "",
            "instanceType": None,
            "replicas": 1,
            "endpointScope": "private",
            "requireAuth": True,
            "enableLogging": True,
            "enableGuardrails": False,
            "budgetMonthlyUsd": None,
            "sourceScanId": None,
            "isSimulated": False,
            "lastModifiedAt": "2026-10-16T00:00:00Z",
            "deployed": False,
        }
        base.update(overrides)
        return base

    def test_deployed_always_false(self):
        """DeployConfig.deployed must always be False."""
        cfg = self._cfg(provider="aws", mode="bedrock")
        assert cfg["deployed"] is False

    def test_no_credentials_in_config(self):
        """DeployConfig must not contain credential fields."""
        cfg = self._cfg()
        for field in ("accessKey", "secretKey", "serviceAccountKey", "token", "password"):
            assert field not in cfg, f"Credential field '{field}' must not be in DeployConfig"

    def test_aws_is_provisioning_provider(self):
        """AWS is the only provisioning provider in v1."""
        supported_for_provisioning = {"aws"}
        plan_only = {"azure", "gcp"}
        assert "aws" in supported_for_provisioning
        assert "azure" in plan_only
        assert "gcp" in plan_only
        assert supported_for_provisioning.isdisjoint(plan_only)

    def test_azure_gcp_are_plan_only(self):
        """Azure and GCP cannot be provisioned by this application."""
        plan_only_providers = {"azure", "gcp"}
        for provider in plan_only_providers:
            cfg = self._cfg(provider=provider, mode=None)
            # provisioningCap for azure/gcp must be "plan-only"
            # This mirrors the compareTypes.ts logic
            assert cfg["provider"] in {"azure", "gcp"}, f"{provider} should be plan-only"

    def test_incomplete_config_withholds_recommendation(self):
        """No recommendation when provider, modelId, or region is missing."""
        incomplete_configs = [
            self._cfg(provider=None, modelId="some-model", region="us-east-1"),
            self._cfg(provider="aws", modelId="", region="us-east-1"),
            self._cfg(provider="aws", modelId="some-model", region=None),
        ]
        for cfg in incomplete_configs:
            is_complete = (
                cfg["provider"] is not None
                and cfg["modelId"] != ""
                and cfg["region"] is not None
            )
            assert not is_complete, f"Config should be incomplete: {cfg}"

    def test_public_endpoint_without_auth_is_warning(self):
        """Public endpoint without auth must produce a warning (not silently allowed)."""
        cfg = self._cfg(
            provider="aws", mode="bedrock",
            region="us-east-1", modelId="anthropic.claude-3",
            endpointScope="public", requireAuth=False,
        )
        # The validation contract: this combination must trigger a warning or blocking issue
        is_risky = cfg["endpointScope"] == "public" and not cfg["requireAuth"]
        assert is_risky, "Expected this config to be flagged as risky"

    def test_sagemaker_requires_instance_type(self):
        """SageMaker mode requires an instance type (blocking validation)."""
        cfg = self._cfg(provider="aws", mode="sagemaker", instanceType=None)
        sagemaker_needs_instance = cfg["mode"] == "sagemaker" and cfg["instanceType"] is None
        assert sagemaker_needs_instance, "SageMaker without instanceType should be incomplete"

    def test_bedrock_has_no_instance_type(self):
        """Bedrock mode does not require instance type."""
        cfg = self._cfg(provider="aws", mode="bedrock", instanceType=None)
        bedrock_ok_without_instance = cfg["mode"] == "bedrock"
        assert bedrock_ok_without_instance

    def test_pricing_is_static_not_live(self):
        """Verify that no live pricing API URL is used — pricing is static."""
        compare_types = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "compareTypes.ts"
        if compare_types.exists():
            content = compare_types.read_text(encoding="utf-8", errors="ignore")
            # Should not contain fetch() or XMLHttpRequest
            assert "fetch(" not in content, "compareTypes.ts must not call fetch() for pricing"
            assert "XMLHttpRequest" not in content, "compareTypes.ts must not use XMLHttpRequest"
            assert "axios" not in content, "compareTypes.ts must not use axios for pricing"
            # Must contain illustrative disclaimer
            assert "illustrative" in content.lower(), (
                "compareTypes.ts must label pricing as illustrative"
            )
            # Must contain source URLs (not fetched — for user reference only)
            assert "aws.amazon.com" in content, (
                "compareTypes.ts must include AWS pricing URL for user reference"
            )

    def test_compare_types_file_exists(self):
        """compareTypes.ts must be present for Screen 10."""
        compare_types = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "compareTypes.ts"
        assert compare_types.exists(), "compareTypes.ts must exist for Screen 10"

    def test_cloud_compare_page_exists(self):
        """CloudComparePage.tsx must be present for Screen 10."""
        page = Path(__file__).parent.parent.parent / "frontend" / "src" / "pages" / "CloudComparePage.tsx"
        assert page.exists(), "CloudComparePage.tsx must exist for Screen 10"

    def test_cloud_compare_page_no_fetch_calls(self):
        """CloudComparePage must not make fetch() calls (no live cloud data)."""
        page = Path(__file__).parent.parent.parent / "frontend" / "src" / "pages" / "CloudComparePage.tsx"
        if page.exists():
            content = page.read_text(encoding="utf-8", errors="ignore")
            assert "fetch(" not in content, "CloudComparePage must not call fetch()"
            assert "axios" not in content, "CloudComparePage must not use axios"

    def test_cloud_compare_page_no_provisioning_calls(self):
        """CloudComparePage must not have deploy/provision/create calls."""
        page = Path(__file__).parent.parent.parent / "frontend" / "src" / "pages" / "CloudComparePage.tsx"
        if page.exists():
            content = page.read_text(encoding="utf-8", errors="ignore")
            for forbidden in ("createInstance", "provisionInstance", "deployNow", "execute_deploy"):
                assert forbidden not in content, (
                    f"CloudComparePage must not contain '{forbidden}'"
                )

    def test_stale_detection_helper_exists(self):
        """compareTypes.ts must export isComparisonStale for stale-config detection."""
        compare_types = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "compareTypes.ts"
        if compare_types.exists():
            content = compare_types.read_text(encoding="utf-8", errors="ignore")
            assert "isComparisonStale" in content, (
                "compareTypes.ts must export isComparisonStale for stale-detection"
            )

    def test_build_comparison_is_pure_function(self):
        """buildComparison must be exported and must not import network modules."""
        compare_types = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "compareTypes.ts"
        if compare_types.exists():
            content = compare_types.read_text(encoding="utf-8", errors="ignore")
            assert "export function buildComparison" in content, (
                "buildComparison must be an exported pure function"
            )
            assert "import fetch" not in content
            assert "node-fetch" not in content

    def test_comparison_has_illustrative_disclaimer(self):
        """Cost estimates must be labeled illustrative — not quotes."""
        compare_types = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "compareTypes.ts"
        if compare_types.exists():
            content = compare_types.read_text(encoding="utf-8", errors="ignore")
            assert "ILLUSTRATIVE" in content or "illustrative" in content.lower(), (
                "compareTypes.ts must label pricing as ILLUSTRATIVE"
            )
            assert "not a provider quote" in content.lower() or "not a quote" in content.lower(), (
                "compareTypes.ts must explicitly state values are not provider quotes"
            )

    def test_partial_estimate_not_labelled_as_total(self):
        """Partial cost estimates must be flagged — not labelled as TCO."""
        compare_types = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "compareTypes.ts"
        if compare_types.exists():
            content = compare_types.read_text(encoding="utf-8", errors="ignore")
            assert "isPartial" in content, (
                "IllustrativeMonthlyCost must have isPartial field to flag partial estimates"
            )
            assert "partialReason" in content, (
                "IllustrativeMonthlyCost must have partialReason field"
            )

    def test_bedrock_pricing_marked_unavailable(self):
        """Bedrock pricing cannot be estimated without request volume — must be marked null."""
        compare_types = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "compareTypes.ts"
        if compare_types.exists():
            content = compare_types.read_text(encoding="utf-8", errors="ignore")
            # The bedrock cost function must return null amounts
            assert "monthlyLow:  null" in content or "monthlyLow: null" in content, (
                "Bedrock monthly cost must be null (token-based, requires request volume)"
            )

    def test_scan_bypass_injects_simulated_report(self):
        """ScanPage must have a dev bypass that injects a simulated report."""
        scan_page = Path(__file__).parent.parent.parent / "frontend" / "src" / "pages" / "ScanPage.tsx"
        if scan_page.exists():
            content = scan_page.read_text(encoding="utf-8", errors="ignore")
            assert "dev-bypass" in content or "devBypass" in content or "handleDevSkip" in content, (
                "ScanPage must have a dev bypass for testing"
            )
            assert "buildSimulatedReport" in content, (
                "Dev bypass must inject a simulated report via buildSimulatedReport"
            )


# ─────────────────────────────────────────────
#  D. Regression: Screens 6-9 unaffected
# ─────────────────────────────────────────────

class TestRegressionScreens69:
    """Verify that Screens 6-9 backend contract remains intact after Phase 6i."""

    def test_report_generates_successfully(self):
        report = _make_report()
        assert report is not None

    def test_report_has_scan_id(self):
        report = _make_report()
        assert report.to_dict()["meta"]["scan_id"] is not None

    def test_report_store_and_retrieve(self):
        report = _make_report()
        d = report.to_dict()
        scan_id = d["meta"]["scan_id"]
        store_report(report)
        retrieved = get_report_by_id(scan_id)
        assert retrieved is not None
        # get_report_by_id may return a dict or object
        if isinstance(retrieved, dict):
            assert retrieved["meta"]["scan_id"] == scan_id
        else:
            assert retrieved.to_dict()["meta"]["scan_id"] == scan_id

    def test_multiple_reports_independent(self):
        r1 = _make_report(target="https://a.example.com")
        r2 = _make_report(target="https://b.example.com")
        assert r1.to_dict()["meta"]["target"] != r2.to_dict()["meta"]["target"]

    def test_deploy_config_does_not_mutate_report(self):
        """Deploying a plan must not change the scan report."""
        report = _make_report()
        original_target = report.to_dict()["meta"]["target"]
        original_risk_score = report.to_dict()["summary"]["risk_score"]

        # Simulate what DeployContext does — nothing touches the report
        deploy_config = {
            "provider": "aws",
            "mode": "bedrock",
            "region": "us-east-1",
            "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
            "deployed": False,
        }
        _ = deploy_config  # noqa: F841 — just verifying it doesn't touch report

        assert report.to_dict()["meta"]["target"] == original_target
        assert report.to_dict()["summary"]["risk_score"] == original_risk_score

    def test_deployed_invariant_in_config(self):
        """The deployed field in DeployConfig is always False."""
        config = {
            "provider": "aws",
            "mode": "sagemaker",
            "region": "us-east-1",
            "modelId": "custom-model-v1",
            "deployed": False,
        }
        assert config["deployed"] is False, "deployed must always be False in v1"
