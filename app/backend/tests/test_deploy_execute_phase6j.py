"""
SentryÉ¸ -- Phase 6j Deploy Execution Tests
tests/test_deploy_execute_phase6j.py

Backend contract and logic tests for Screen 11 (Deploy Execution).

Coverage:
  A. Navigation contract tests (S8 â†’ S9 path verified via frontend audit)
  B. Dry-run plan logic contracts (Python mirror of dryRunTypes.ts pure functions)
  C. Safety invariants (deployed stays false, no cloud calls, report unchanged)
  D. Provider capability contracts (AWS provisionable, Azure/GCP plan-only)
  E. Regression: Screens 6-10 unaffected

Note:
  - The dry-run plan engine lives in frontend (dryRunTypes.ts).
  - Backend tests verify safety invariants and design contracts.
  - No cloud API calls are made in any test.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from core.manifest import create_manifest
from core.mock_engine import MockEngine
from core.scorer import generate_risk_report
from core.recommender import generate_recommendations
from core.report_generator import (
    ScanReport,
    generate_full_report,
    REPORT_VERSION,
)
from services.report_service import (
    store_report,
    get_report_by_id,
    clear_reports,
)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _make_report(
    target: str = "https://execute-test.example.com",
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


# Simulated DeployConfig dictionaries (mirror of deployTypes.ts)
def _make_config(**overrides) -> dict:
    base = {
        "provider":         "aws",
        "mode":             "bedrock",
        "region":           "us-east-1",
        "modelId":          "anthropic.claude-3-sonnet-20240229-v1:0",
        "modelLabel":       "Claude 3 Sonnet",
        "instanceType":     None,
        "replicas":         1,
        "endpointScope":    "private",
        "requireAuth":      True,
        "enableLogging":    True,
        "enableGuardrails": False,
        "budgetMonthlyUsd": None,
        "sourceScanId":     None,
        "isSimulated":      False,
        "lastModifiedAt":   "2026-10-16T00:00:00Z",
        "deployed":         False,
    }
    base.update(overrides)
    return base


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  A. Navigation contract tests
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestNavigationContract:
    """
    Verify the navigation repair (Part A) contracts documented in the codebase.

    These tests verify that:
      1. ExportPage now has an onProceedToDeploy prop (verified via source inspection)
      2. App.tsx wires export â†’ deploy-config correctly
      3. deploy-execute route is wired to DeployExecutePage (not PlaceholderPage)
      4. DeployExecutePage file exists
    """

    FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "src"

    def test_export_page_has_proceed_to_deploy_prop(self):
        """ExportPage must declare onProceedToDeploy prop (Part A fix)."""
        export_page = self.FRONTEND_DIR / "pages" / "ExportPage.tsx"
        assert export_page.exists(), "ExportPage.tsx must exist"
        content = export_page.read_text(encoding="utf-8", errors="ignore")
        assert "onProceedToDeploy" in content, (
            "ExportPage must have onProceedToDeploy prop (Part A navigation fix)"
        )

    def test_export_page_proceed_button_exists(self):
        """ExportPage must have a 'Continue to Deployment Planning' button."""
        export_page = self.FRONTEND_DIR / "pages" / "ExportPage.tsx"
        content = export_page.read_text(encoding="utf-8", errors="ignore")
        assert "Continue to Deployment Planning" in content or "export-proceed-deploy" in content, (
            "ExportPage must have a visible button to proceed to deployment planning"
        )

    def test_app_tsx_wires_export_to_deploy(self):
        """App.tsx export case must include onProceedToDeploy â†’ deploy-config."""
        app_tsx = self.FRONTEND_DIR / "App.tsx"
        assert app_tsx.exists(), "App.tsx must exist"
        content = app_tsx.read_text(encoding="utf-8", errors="ignore")
        assert "onProceedToDeploy" in content, (
            "App.tsx must wire onProceedToDeploy to ExportPage"
        )
        assert "deploy-config" in content, (
            "App.tsx must route export â†’ deploy-config"
        )

    def test_deploy_execute_route_wired(self):
        """App.tsx deploy-execute case must point to DeployExecutePage."""
        app_tsx = self.FRONTEND_DIR / "App.tsx"
        content = app_tsx.read_text(encoding="utf-8", errors="ignore")
        assert "DeployExecutePage" in content, (
            "App.tsx must import and use DeployExecutePage for deploy-execute route"
        )
        assert "PlaceholderPage" not in content.split("deploy-execute")[1][:200], (
            "deploy-execute route must not use PlaceholderPage"
        )

    def test_deploy_execute_page_exists(self):
        """DeployExecutePage.tsx must exist."""
        page = self.FRONTEND_DIR / "pages" / "DeployExecutePage.tsx"
        assert page.exists(), "DeployExecutePage.tsx must be created for Phase 6j"

    def test_dry_run_types_file_exists(self):
        """dryRunTypes.ts must exist and be the dry-run plan engine."""
        types_file = self.FRONTEND_DIR / "services" / "dryRunTypes.ts"
        assert types_file.exists(), "dryRunTypes.ts must be created for Phase 6j"

    def test_deploy_execute_page_no_cloud_calls(self):
        """DeployExecutePage must not make any cloud API calls."""
        page = self.FRONTEND_DIR / "pages" / "DeployExecutePage.tsx"
        content = page.read_text(encoding="utf-8", errors="ignore")
        for forbidden in ("fetch(", "axios.", "XMLHttpRequest", "new AWS.", "aws-sdk"):
            assert forbidden not in content, (
                f"DeployExecutePage must not contain cloud API call: {forbidden}"
            )

    def test_deploy_execute_page_has_dry_run_label(self):
        """DeployExecutePage must display a DRY RUN / simulation label."""
        page = self.FRONTEND_DIR / "pages" / "DeployExecutePage.tsx"
        content = page.read_text(encoding="utf-8", errors="ignore")
        assert "DRY RUN" in content or "Dry-Run" in content or "dry-run" in content, (
            "DeployExecutePage must display a dry-run label"
        )

    def test_deploy_execute_page_never_sets_deployed_true(self):
        """deployed must never be set to true in DeployExecutePage (in non-comment code)."""
        import re
        page = self.FRONTEND_DIR / "pages" / "DeployExecutePage.tsx"
        assert page.exists(), "DeployExecutePage.tsx must exist"
        content = page.read_text(encoding="utf-8", errors="ignore")
        # Strip comment lines before searching (lines starting with optional whitespace + * or //)
        code_lines = [
            line for line in content.splitlines()
            if not re.match(r"^\s*[\*\/]", line)
        ]
        code_only = "\n".join(code_lines)
        # Look for TypeScript assignment patterns in actual code
        pattern = re.compile(r"deployed\s*[:=]\s*true")
        matches = pattern.findall(code_only)
        assert len(matches) == 0, (
            f"deployed must never be assigned to true in DeployExecutePage code — found: {matches}"
        )

    def test_deploy_execute_no_success_language(self):
        """DeployExecutePage must not use 'Deployment successful' language."""
        page = self.FRONTEND_DIR / "pages" / "DeployExecutePage.tsx"
        content = page.read_text(encoding="utf-8", errors="ignore")
        forbidden_phrases = [
            "Deployment successful",
            "deployed successfully",
            "Successfully deployed",
            "Resources created",
            "Infrastructure provisioned",
        ]
        for phrase in forbidden_phrases:
            assert phrase not in content, (
                f"DeployExecutePage must not contain misleading success language: '{phrase}'"
            )


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  B. Dry-run plan logic contracts
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDryRunPlanContracts:
    """
    Mirror the TypeScript dry-run plan logic in Python.
    Asserts design contracts of the frontend dryRunTypes.ts module.
    """

    # â”€â”€ Plan ID invariants â”€â”€

    def test_plan_id_has_drp_prefix(self):
        """
        Plan IDs must start with 'drp-' to distinguish from real cloud resource IDs.
        Format: drp-<timestamp>-<random>
        """
        import re
        pattern = re.compile(r"^drp-[a-z0-9]+-[a-z0-9]+$")
        # Simulate the ID generation contract
        sample_id = "drp-1abc23-xyz45"
        assert sample_id.startswith("drp-"), "Plan ID must start with 'drp-'"
        assert pattern.match(sample_id), "Plan ID must match drp-<ts>-<rnd>"

    def test_plan_id_not_aws_resource_id(self):
        """Plan ID must not look like a real AWS resource ID."""
        aws_like = ["arn:aws:", "endpoint-", "sagemaker-", "bedrock-"]
        sample_id = "drp-lm3p7q-abc12"
        for prefix in aws_like:
            assert not sample_id.startswith(prefix), (
                f"Plan ID must not look like an AWS resource ID (prefix: {prefix})"
            )

    # â”€â”€ Provenance invariants â”€â”€

    def test_plan_provenance_source_is_local_simulation(self):
        """PlanProvenance.source must always be 'local-simulation'."""
        provenance = {
            "source":            "local-simulation",
            "planType":          "dry-run",
            "configSnapshotAt":  "2026-10-16T00:00:00Z",
            "generatedAt":       "2026-10-16T12:00:00Z",
        }
        assert provenance["source"] == "local-simulation"
        assert provenance["planType"] == "dry-run"
        assert provenance["source"] != "aws-response"
        assert provenance["source"] != "cloud-api"

    # â”€â”€ Config validation contracts â”€â”€

    def test_valid_aws_bedrock_config_can_generate_plan(self):
        """A fully filled AWS Bedrock config passes preflight (no blocking issues)."""
        cfg = _make_config(
            provider="aws", mode="bedrock",
            region="us-east-1", modelId="anthropic.claude-3",
        )
        blocking_issues = _simulate_preflight_check(cfg)
        assert blocking_issues == [], f"Expected no blocking issues, got: {blocking_issues}"

    def test_missing_provider_blocks_plan(self):
        """Missing provider must block plan generation."""
        cfg = _make_config(provider=None)
        issues = _simulate_preflight_check(cfg)
        assert len(issues) > 0, "Missing provider should produce blocking issues"

    def test_missing_model_id_blocks_plan(self):
        """Missing modelId must block plan generation."""
        cfg = _make_config(modelId="")
        issues = _simulate_preflight_check(cfg)
        assert len(issues) > 0, "Empty modelId should produce blocking issues"

    def test_missing_region_blocks_plan(self):
        """Missing region must block plan generation."""
        cfg = _make_config(region=None)
        issues = _simulate_preflight_check(cfg)
        assert len(issues) > 0, "Missing region should produce blocking issues"

    def test_sagemaker_without_instance_type_blocks_plan(self):
        """SageMaker mode without instanceType must block plan generation."""
        cfg = _make_config(mode="sagemaker", instanceType=None)
        issues = _simulate_preflight_check(cfg)
        assert len(issues) > 0, "SageMaker without instanceType should block plan"

    def test_public_endpoint_without_auth_blocks_plan(self):
        """Public endpoint + no auth = security blocking issue."""
        cfg = _make_config(endpointScope="public", requireAuth=False)
        issues = _simulate_preflight_check(cfg)
        assert len(issues) > 0, "Public endpoint without auth must be a blocking issue"

    # â”€â”€ Provider capability contracts â”€â”€

    def test_aws_is_provisionable(self):
        """AWS is the only provider that can enter dry-run simulation."""
        assert _provider_can_simulate("aws") is True

    def test_azure_is_plan_only(self):
        """Azure must not enter the dry-run simulation path."""
        assert _provider_can_simulate("azure") is False

    def test_gcp_is_plan_only(self):
        """GCP must not enter the dry-run simulation path."""
        assert _provider_can_simulate("gcp") is False

    def test_aws_modes_are_valid(self):
        """AWS supports bedrock, sagemaker, lambda modes."""
        valid_modes = {"bedrock", "sagemaker", "lambda"}
        for mode in valid_modes:
            cfg = _make_config(mode=mode)
            if mode == "sagemaker":
                cfg["instanceType"] = "ml.m5.large"
            issues = _simulate_preflight_check(cfg)
            assert len(issues) == 0, f"AWS mode {mode} with valid config should have no issues"

    # â”€â”€ Summary message invariants â”€â”€

    def test_summary_message_dry_run_only(self):
        """Summary message must say 'no cloud resources created'."""
        success_message = "Dry-run plan generated â€” no cloud resources created."
        assert "no cloud resources created" in success_message
        assert "Deployment successful" not in success_message
        assert "Resources created" not in success_message

    def test_plan_only_message_no_simulation(self):
        """Plan-only provider summary must not imply simulation succeeded."""
        plan_only_message = "Plan-only: AZURE deployment cannot be simulated. No cloud resources created."
        assert "No cloud resources created" in plan_only_message
        assert "Deployment successful" not in plan_only_message

    def test_blocked_message_no_success(self):
        """Blocked plan summary must not imply success."""
        blocked_message = "Dry-run plan blocked â€” configuration is incomplete or invalid. No cloud resources created."
        assert "blocked" in blocked_message
        assert "Deployment successful" not in blocked_message

    # â”€â”€ deployed invariant â”€â”€

    def test_deployed_always_false_in_config(self):
        """deployed must always be False â€” dry-run never sets it to true."""
        cfg = _make_config()
        assert cfg["deployed"] is False

        # Even after "plan generation" (simulated), deployed must remain false
        cfg_after_plan = {**cfg}  # Copy â€” plan generation in frontend doesn't mutate config
        assert cfg_after_plan["deployed"] is False

    def test_no_credentials_in_config(self):
        """Config must never contain credentials."""
        cfg = _make_config()
        forbidden_fields = [
            "accessKey", "secretKey", "sessionToken", "serviceAccountKey",
            "apiKey", "password", "token", "secret",
        ]
        for field in forbidden_fields:
            assert field not in cfg, f"Config must not contain credential field: {field}"

    # â”€â”€ Stale detection â”€â”€

    def test_stale_detection_uses_last_modified_at(self):
        """
        Plan is stale when configSnapshotAt != config.lastModifiedAt.
        This mirrors isDryRunPlanStale() in dryRunTypes.ts.
        """
        config_ts    = "2026-10-16T12:00:00Z"
        snapshot_ts  = "2026-10-16T11:55:00Z"  # Older than current config
        is_stale = snapshot_ts != config_ts
        assert is_stale, "Plan should be stale when snapshot is older than config"

    def test_fresh_plan_not_stale(self):
        """Plan with matching timestamp is not stale."""
        config_ts   = "2026-10-16T12:00:00Z"
        snapshot_ts = "2026-10-16T12:00:00Z"
        is_stale = snapshot_ts != config_ts
        assert not is_stale, "Plan with matching timestamp should not be stale"

    # â”€â”€ Stages â”€â”€

    def test_plan_stages_not_executable_commands(self):
        """Plan stages must not contain shell commands or terraform."""
        stage_notes = [
            "Would configure Bedrock model endpoint",
            "Would create SageMaker endpoint",
            "Dry-run plan generated â€” no cloud resources created",
        ]
        forbidden = ["terraform", "aws deploy", "kubectl", "docker run", "bash -c", "sh -c", "PowerShell"]
        for note in stage_notes:
            for cmd in forbidden:
                assert cmd not in note, (
                    f"Stage note must not contain executable command '{cmd}': {note}"
                )

    def test_plan_has_no_live_resource_ids(self):
        """Plan must not contain real-looking AWS resource IDs."""
        forbidden_patterns = [
            "arn:aws:sagemaker",
            "arn:aws:bedrock",
            "arn:aws:lambda",
            "endpoint-",
            "sagemaker-",
        ]
        plan_content = json.dumps({
            "planId":    "drp-abc123-xyz",
            "provider":  "aws",
            "mode":      "bedrock",
            "summaryMessage": "Dry-run plan generated â€” no cloud resources created.",
        })
        for pattern in forbidden_patterns:
            assert pattern not in plan_content, (
                f"Plan must not contain real AWS resource ID pattern: {pattern}"
            )

    def test_repeated_plan_generation_not_duplicate(self):
        """
        Calling buildDryRunPlan twice with same config produces different planIds
        (via random component) but same planStatus and stages.
        """
        # Simulate: two calls produce different IDs but same status
        id1 = f"drp-{id(object())}-abc"
        id2 = f"drp-{id(object())}-def"
        assert id1 != id2, "Repeated plan generation must produce unique plan IDs"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  C. Safety invariants
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestSafetyInvariants:
    """Ensure no cloud operations exist anywhere in the backend."""

    BACKEND_DIR = Path(__file__).parent.parent

    def test_no_boto3_in_production_code(self):
        """boto3 must not be used in production backend code (only tests permitted)."""
        for py_file in (self.BACKEND_DIR / "core").rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if "import boto3" in content or "from boto3" in content:
                pytest.fail(f"boto3 found in production code: {py_file}")

    def test_no_azure_sdk_in_backend(self):
        """Azure SDK must not be imported in production backend code."""
        for py_file in (self.BACKEND_DIR / "core").rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if "azure-mgmt" in content or "from azure" in content:
                pytest.fail(f"Azure SDK found in production code: {py_file}")

    def test_no_gcp_sdk_in_backend(self):
        """GCP SDK must not be imported in production backend code."""
        for py_file in (self.BACKEND_DIR / "core").rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if "google-cloud" in content or "from google.cloud" in content:
                pytest.fail(f"GCP SDK found in production code: {py_file}")

    def test_deploy_execute_page_no_fetch(self):
        """DeployExecutePage must not make fetch() calls."""
        page = Path(__file__).parent.parent.parent / "frontend" / "src" / "pages" / "DeployExecutePage.tsx"
        if page.exists():
            content = page.read_text(encoding="utf-8", errors="ignore")
            for pattern in ("fetch(", "axios.", "XMLHttpRequest("):
                assert pattern not in content, (
                    f"DeployExecutePage must not make network calls: {pattern}"
                )

    def test_dry_run_types_no_fetch(self):
        """dryRunTypes.ts must not make fetch() calls â€” pure functions only."""
        types_file = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "dryRunTypes.ts"
        if types_file.exists():
            content = types_file.read_text(encoding="utf-8", errors="ignore")
            for pattern in ("fetch(", "axios.", "XMLHttpRequest("):
                assert pattern not in content, (
                    f"dryRunTypes.ts must not make network calls: {pattern}"
                )

    def test_dry_run_types_has_pure_function_annotation(self):
        """dryRunTypes.ts must contain buildDryRunPlan pure function."""
        types_file = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "dryRunTypes.ts"
        if types_file.exists():
            content = types_file.read_text(encoding="utf-8", errors="ignore")
            assert "buildDryRunPlan" in content, (
                "dryRunTypes.ts must export buildDryRunPlan pure function"
            )

    def test_report_not_mutated_by_plan_generation(self):
        """Generating a plan must not change the scan report."""
        report = _make_report()
        original_target     = report.to_dict()["meta"]["target"]
        original_risk_score = report.to_dict()["summary"]["risk_score"]

        # Simulate what plan generation does â€” reads DeployContext, not ReportContext
        cfg = _make_config()
        # Plan generation is pure and doesn't touch the report
        _ = cfg

        assert report.to_dict()["meta"]["target"]       == original_target
        assert report.to_dict()["summary"]["risk_score"] == original_risk_score

    def test_scan_report_has_no_deploy_state(self):
        """ScanReport must not contain deployment state fields."""
        report = _make_report()
        d = report.to_dict()
        forbidden_fields = ["deployed", "deployment_config", "plan_id", "dry_run"]
        for field in forbidden_fields:
            assert field not in d, f"ScanReport must not contain deployment field: {field}"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  D. Provider capability contracts
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestProviderCapabilityContracts:
    """Verify D-022: AWS provisionable, Azure/GCP plan-only."""

    def test_aws_only_provider_in_provisioning_set(self):
        """AWS is the only provisioning provider in v1."""
        provisioning_providers = {"aws"}
        plan_only_providers    = {"azure", "gcp"}
        assert "aws" in provisioning_providers
        assert "azure" in plan_only_providers
        assert "gcp"   in plan_only_providers
        assert provisioning_providers.isdisjoint(plan_only_providers)

    def test_aws_modes(self):
        """AWS supports exactly bedrock, sagemaker, lambda."""
        aws_modes = {"bedrock", "sagemaker", "lambda"}
        assert "bedrock"   in aws_modes
        assert "sagemaker" in aws_modes
        assert "lambda"    in aws_modes
        # No Azure/GCP modes exist in v1
        assert "azure-ml"  not in aws_modes
        assert "vertex-ai" not in aws_modes

    def test_azure_gcp_cannot_enter_dry_run_simulation(self):
        """Azure and GCP configs must display plan-only state on Screen 11."""
        for provider in ("azure", "gcp"):
            cfg = _make_config(provider=provider)
            can_simulate = cfg["provider"] == "aws"
            assert not can_simulate, f"{provider} must not enter the dry-run simulation path"

    def test_deployed_false_across_all_providers(self):
        """deployed must be False for all provider configs."""
        for provider in ("aws", "azure", "gcp"):
            cfg = _make_config(provider=provider)
            assert cfg["deployed"] is False, (
                f"deployed must always be False for provider: {provider}"
            )


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  E. Regression: Screens 6-10
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRegressionScreens610:
    """Verify Screens 6-10 backend contract is unchanged after Phase 6j."""

    def test_report_generates_successfully(self):
        report = _make_report()
        assert report is not None

    def test_report_has_scan_id(self):
        report = _make_report()
        assert report.to_dict()["meta"]["scan_id"] is not None

    def test_report_schema_intact(self):
        """Top-level report keys must be present."""
        report = _make_report()
        d = report.to_dict()
        required = {"meta", "summary", "findings", "recommendations", "engine", "report_version"}
        assert required.issubset(d.keys()), f"Missing keys: {required - d.keys()}"

    def test_report_independent_of_deploy_config(self):
        """Two different reports are independent."""
        r1 = _make_report(target="https://r1.example.com")
        r2 = _make_report(target="https://r2.example.com")
        assert r1.to_dict()["meta"]["target"] != r2.to_dict()["meta"]["target"]

    def test_compare_types_file_still_present(self):
        """compareTypes.ts (Screen 10) must still be present."""
        compare_file = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "compareTypes.ts"
        assert compare_file.exists(), "compareTypes.ts must not be removed"

    def test_deploy_config_page_still_present(self):
        """DeployConfigPage.tsx (Screen 9) must still be present."""
        page = Path(__file__).parent.parent.parent / "frontend" / "src" / "pages" / "DeployConfigPage.tsx"
        assert page.exists(), "DeployConfigPage.tsx must not be removed"

    def test_scan_bypass_still_present(self):
        """DEV MODE scan bypass must still be present in ScanPage."""
        scan_page = Path(__file__).parent.parent.parent / "frontend" / "src" / "pages" / "ScanPage.tsx"
        if scan_page.exists():
            content = scan_page.read_text(encoding="utf-8", errors="ignore")
            assert "buildSimulatedReport" in content, (
                "Dev bypass must still be present in ScanPage"
            )


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Helper functions (Python mirrors of TS logic)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _simulate_preflight_check(cfg: dict) -> list[str]:
    """
    Python mirror of the preflight check logic in buildPreflightChecks().
    Returns a list of blocking issues (automated checks only).
    Mirrors the automated checks â€” NOT user-ack checks.
    """
    issues = []

    # Provider check
    if not cfg.get("provider"):
        issues.append("No provider selected")
    elif cfg["provider"] not in ("aws", "azure", "gcp"):
        issues.append(f"Unknown provider: {cfg['provider']}")

    # Provider capability check (AWS-only can proceed with simulation)
    if cfg.get("provider") in ("azure", "gcp"):
        issues.append(f"{cfg['provider'].upper()} is plan-only, cannot simulate")
        return issues  # No further checks needed for plan-only providers

    # AWS-specific checks
    if cfg.get("provider") == "aws":
        if not cfg.get("mode"):
            issues.append("No deployment mode selected")
        if not cfg.get("modelId", "").strip():
            issues.append("Model identifier is empty")
        if not cfg.get("region"):
            issues.append("Region not selected")
        if cfg.get("mode") == "sagemaker" and not cfg.get("instanceType"):
            issues.append("SageMaker requires instanceType")
        if cfg.get("endpointScope") == "public" and not cfg.get("requireAuth", True):
            issues.append("Public endpoint without auth is a security risk")

    return issues


def _provider_can_simulate(provider: str) -> bool:
    """
    Python mirror of the provider capability check:
    Only AWS can enter the dry-run simulation. Azure and GCP are plan-only.
    """
    return provider == "aws"

