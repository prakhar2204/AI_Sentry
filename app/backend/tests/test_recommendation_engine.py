"""
Tests for W1.3: Deployment Recommendation Engine
tests/test_recommendation_engine.py
"""
from __future__ import annotations

import pytest
from core.deploy.recommendation_engine import (
    generate_deployment_recommendation,
    DeploymentRecommendation,
    _determine_risk_level,
    _get_affected_categories,
    _choose_provider,
)


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

def _make_report(risk_score: int = 0, findings: list[dict] | None = None) -> dict:
    return {
        "risk_score": risk_score,
        "findings": findings or [],
    }


def _finding(cat: str, severity: str = "medium") -> dict:
    return {"category": cat, "severity": severity, "title": f"{cat} finding"}


# ─────────────────────────────────────────────
#  _determine_risk_level
# ─────────────────────────────────────────────

class TestDetermineRiskLevel:
    def test_zero_is_low(self):
        assert _determine_risk_level(0) == "low"

    def test_30_is_low(self):
        assert _determine_risk_level(30) == "low"

    def test_31_is_medium(self):
        assert _determine_risk_level(31) == "medium"

    def test_70_is_medium(self):
        assert _determine_risk_level(70) == "medium"

    def test_71_is_high(self):
        assert _determine_risk_level(71) == "high"

    def test_100_is_high(self):
        assert _determine_risk_level(100) == "high"


# ─────────────────────────────────────────────
#  _get_affected_categories
# ─────────────────────────────────────────────

class TestGetAffectedCategories:
    def test_empty_findings(self):
        assert _get_affected_categories([]) == set()

    def test_single_category(self):
        findings = [_finding("prompt_injection")]
        assert _get_affected_categories(findings) == {"prompt_injection"}

    def test_multiple_categories(self):
        findings = [_finding("prompt_injection"), _finding("jailbreak"), _finding("toxicity")]
        cats = _get_affected_categories(findings)
        assert cats == {"prompt_injection", "jailbreak", "toxicity"}

    def test_deduplicated(self):
        findings = [_finding("prompt_injection")] * 3
        assert _get_affected_categories(findings) == {"prompt_injection"}

    def test_missing_category_key(self):
        findings = [{"severity": "high", "title": "no category"}]
        # findings without a 'category' key are filtered out entirely
        assert _get_affected_categories(findings) == set()



# ─────────────────────────────────────────────
#  _choose_provider
# ─────────────────────────────────────────────

class TestChooseProvider:
    def test_malware_always_private(self):
        provider, _ = _choose_provider("low", {"malware_generation"})
        assert provider == "private"

    def test_high_risk_private(self):
        provider, _ = _choose_provider("high", {"prompt_injection"})
        assert provider == "private"

    def test_medium_risk_aws(self):
        provider, _ = _choose_provider("medium", {"jailbreak"})
        assert provider == "aws"

    def test_low_risk_aws(self):
        provider, _ = _choose_provider("low", {"toxicity"})
        assert provider == "aws"

    def test_rationale_is_non_empty(self):
        _, rationale = _choose_provider("medium", {"jailbreak"})
        assert len(rationale) > 20


# ─────────────────────────────────────────────
#  Full generate_deployment_recommendation
# ─────────────────────────────────────────────

class TestGenerateDeploymentRecommendation:

    def test_returns_recommendation_object(self):
        report = _make_report(risk_score=10)
        rec = generate_deployment_recommendation(report)
        assert isinstance(rec, DeploymentRecommendation)

    def test_low_risk_recommended_aws(self):
        report = _make_report(risk_score=20)
        rec = generate_deployment_recommendation(report)
        assert rec.recommended_provider == "aws"
        assert rec.risk_level == "low"

    def test_medium_risk_recommended_aws(self):
        report = _make_report(risk_score=50, findings=[_finding("jailbreak")])
        rec = generate_deployment_recommendation(report)
        assert rec.recommended_provider == "aws"
        assert rec.risk_level == "medium"

    def test_high_risk_recommended_private(self):
        report = _make_report(risk_score=80, findings=[_finding("prompt_injection")])
        rec = generate_deployment_recommendation(report)
        assert rec.recommended_provider == "private"
        assert rec.risk_level == "high"

    def test_malware_finding_forces_private(self):
        report = _make_report(risk_score=30, findings=[_finding("malware_generation")])
        rec = generate_deployment_recommendation(report)
        assert rec.recommended_provider == "private"

    def test_all_four_configs_populated(self):
        report = _make_report(risk_score=40)
        rec = generate_deployment_recommendation(report)
        assert rec.aws_config is not None
        assert rec.azure_config is not None
        assert rec.gcp_config is not None
        assert rec.private_config is not None

    def test_security_warnings_match_categories(self):
        findings = [_finding("malware_generation"), _finding("toxicity")]
        report = _make_report(risk_score=50, findings=findings)
        rec = generate_deployment_recommendation(report)
        warning_text = " ".join(rec.security_warnings)
        assert "Malware" in warning_text or "malware" in warning_text

    def test_required_controls_non_empty_with_findings(self):
        findings = [_finding("prompt_injection")]
        report = _make_report(risk_score=40, findings=findings)
        rec = generate_deployment_recommendation(report)
        assert len(rec.required_controls) >= 1

    def test_to_dict_structure(self):
        report = _make_report(risk_score=50)
        rec = generate_deployment_recommendation(report)
        d = rec.to_dict()
        assert "recommended_provider" in d
        assert "rationale" in d
        assert "aws_config" in d
        assert "azure_config" in d
        assert "gcp_config" in d
        assert "private_config" in d
        assert "security_warnings" in d
        assert "required_controls" in d
        assert "risk_score" in d
        assert "risk_level" in d

    def test_to_dict_aws_has_cost(self):
        rec = generate_deployment_recommendation(_make_report(risk_score=30))
        d = rec.to_dict()
        assert "monthly_cost" in d["aws_config"]
        assert "low_usd" in d["aws_config"]["monthly_cost"]
        assert "high_usd" in d["aws_config"]["monthly_cost"]

    def test_high_risk_endpoint_scope_private(self):
        report = _make_report(risk_score=85, findings=[_finding("jailbreak")])
        rec = generate_deployment_recommendation(report)
        assert rec.aws_config.endpoint_scope == "private"
        assert rec.azure_config.endpoint_scope == "private"
        assert rec.gcp_config.endpoint_scope == "private"

    def test_low_risk_endpoint_scope_public_allowed(self):
        report = _make_report(risk_score=10)
        rec = generate_deployment_recommendation(report)
        assert rec.aws_config.endpoint_scope == "public"

    def test_high_risk_guardrails_enabled(self):
        report = _make_report(risk_score=90, findings=[_finding("prompt_injection")])
        rec = generate_deployment_recommendation(report)
        assert rec.aws_config.enable_guardrails is True
        assert rec.azure_config.enable_content_safety is True

    def test_high_risk_gcp_cloud_armor(self):
        report = _make_report(risk_score=90)
        rec = generate_deployment_recommendation(report)
        assert rec.gcp_config.enable_cloud_armor is True

    def test_low_risk_gcp_no_cloud_armor(self):
        report = _make_report(risk_score=10)
        rec = generate_deployment_recommendation(report)
        assert rec.gcp_config.enable_cloud_armor is False

    def test_empty_report(self):
        """Should not raise — handle gracefully with zero risk."""
        rec = generate_deployment_recommendation({})
        assert rec is not None
        assert rec.risk_score == 0
        assert rec.risk_level == "low"

    def test_risk_score_roundtrip(self):
        for score in [0, 30, 31, 70, 71, 100]:
            rec = generate_deployment_recommendation(_make_report(risk_score=score))
            assert rec.risk_score == score

    def test_private_config_tls_always_enabled(self):
        rec = generate_deployment_recommendation(_make_report(risk_score=80))
        assert rec.private_config.enable_tls is True

    def test_private_high_risk_uses_kubernetes(self):
        rec = generate_deployment_recommendation(_make_report(risk_score=80))
        assert rec.private_config.stack == "kubernetes"

    def test_private_low_risk_uses_docker_compose(self):
        rec = generate_deployment_recommendation(_make_report(risk_score=10))
        assert rec.private_config.stack == "docker_compose"
