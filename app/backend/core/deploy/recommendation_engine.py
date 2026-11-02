"""
Sentryɸ — Deployment Recommendation Engine
core/deploy/recommendation_engine.py

Analyses a completed ScanReport and automatically generates recommended
deployment settings for AWS, Azure, GCP, and Private (self-hosted) targets.

The recommendation logic is intentionally rule-based (no LLM calls) so that:
  1. It works offline and in air-gapped environments
  2. Recommendations are fully explainable and auditable
  3. No secondary API cost is incurred

Design:
    Input:  ScanReport (risk_score, findings, normalization coverage map)
    Output: DeploymentRecommendation
              ├─ recommended_provider: "aws" | "azure" | "gcp" | "private"
              ├─ rationale: str
              ├─ aws_config: AwsRecommendedConfig
              ├─ azure_config: AzureRecommendedConfig
              ├─ gcp_config: GcpRecommendedConfig
              ├─ private_config: PrivateRecommendedConfig
              └─ cost_estimate: CostRangeEstimate (per provider)
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────
#  Data classes
# ─────────────────────────────────────────────

@dataclass
class CostRange:
    """Monthly cost range estimate (USD)."""
    low_usd: float
    high_usd: float
    currency: str = "USD"
    basis: str = ""          # Explanation of the estimate basis

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class AwsRecommendedConfig:
    region: str = "us-east-1"
    deployment_mode: str = "bedrock"   # bedrock | sagemaker | lambda
    instance_type: str = ""            # only relevant for sagemaker
    enable_guardrails: bool = True
    enable_vpc: bool = True
    enable_cloudwatch: bool = True
    enable_budget_alert: bool = True
    budget_alert_usd: float = 500.0
    endpoint_scope: str = "private"    # private | public
    rationale: list[str] = field(default_factory=list)
    monthly_cost: CostRange = field(default_factory=lambda: CostRange(0, 0))

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["monthly_cost"] = self.monthly_cost.to_dict()
        return d


@dataclass
class AzureRecommendedConfig:
    region: str = "eastus"
    deployment_mode: str = "ai_services"  # ai_services | container | app_service
    enable_content_safety: bool = True
    enable_vnet: bool = True
    enable_monitoring: bool = True
    endpoint_scope: str = "private"
    rationale: list[str] = field(default_factory=list)
    monthly_cost: CostRange = field(default_factory=lambda: CostRange(0, 0))

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["monthly_cost"] = self.monthly_cost.to_dict()
        return d


@dataclass
class GcpRecommendedConfig:
    region: str = "us-central1"
    deployment_mode: str = "vertex_ai"  # vertex_ai | cloud_run | cloud_functions
    enable_model_monitoring: bool = True
    enable_vpc_sc: bool = True
    enable_cloud_armor: bool = False    # Only for high-risk public endpoints
    endpoint_scope: str = "private"
    rationale: list[str] = field(default_factory=list)
    monthly_cost: CostRange = field(default_factory=lambda: CostRange(0, 0))

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["monthly_cost"] = self.monthly_cost.to_dict()
        return d


@dataclass
class PrivateRecommendedConfig:
    stack: str = "docker_compose"     # docker_compose | kubernetes | bare_metal
    enable_nginx_proxy: bool = True
    enable_tls: bool = True
    enable_rate_limiting: bool = True
    monthly_cost: CostRange = field(default_factory=lambda: CostRange(0, 0))
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["monthly_cost"] = self.monthly_cost.to_dict()
        return d


@dataclass
class DeploymentRecommendation:
    """
    Full deployment recommendation produced from a ScanReport.
    All fields are populated regardless of the recommended_provider —
    the UI can display all 4 options for comparison.
    """
    recommended_provider: str          # aws | azure | gcp | private
    rationale: str                     # Human-readable reason for the recommendation
    risk_level: str                    # low | medium | high (from scan)
    risk_score: int                    # 0-100

    aws_config:     AwsRecommendedConfig     = field(default_factory=AwsRecommendedConfig)
    azure_config:   AzureRecommendedConfig   = field(default_factory=AzureRecommendedConfig)
    gcp_config:     GcpRecommendedConfig     = field(default_factory=GcpRecommendedConfig)
    private_config: PrivateRecommendedConfig = field(default_factory=PrivateRecommendedConfig)

    # Security warnings specific to this scan (from findings)
    security_warnings: list[str] = field(default_factory=list)
    # Required security controls before deployment
    required_controls: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended_provider": self.recommended_provider,
            "rationale":            self.rationale,
            "risk_level":           self.risk_level,
            "risk_score":           self.risk_score,
            "aws_config":           self.aws_config.to_dict(),
            "azure_config":         self.azure_config.to_dict(),
            "gcp_config":           self.gcp_config.to_dict(),
            "private_config":       self.private_config.to_dict(),
            "security_warnings":    self.security_warnings,
            "required_controls":    self.required_controls,
        }


# ─────────────────────────────────────────────
#  Rule tables
# ─────────────────────────────────────────────

# Risk score → deployment tightening rules
_RISK_RULES = {
    # For HIGH risk (score > 70): restrict everything
    "high": {
        "endpoint_scope":    "private",
        "enable_guardrails": True,
        "enable_vpc":        True,
        "enable_monitoring": True,
        "budget_alert":      250.0,
        "cloud_armor":       True,     # GCP: enable Cloud Armor
    },
    # For MEDIUM risk (31-70): standard security
    "medium": {
        "endpoint_scope":    "private",
        "enable_guardrails": True,
        "enable_vpc":        True,
        "enable_monitoring": True,
        "budget_alert":      500.0,
        "cloud_armor":       False,
    },
    # For LOW risk (0-30): relaxed, can allow public endpoint
    "low": {
        "endpoint_scope":    "public",
        "enable_guardrails": True,
        "enable_vpc":        False,
        "enable_monitoring": True,
        "budget_alert":      1000.0,
        "cloud_armor":       False,
    },
}

# Category → required control mapping
_CATEGORY_CONTROLS = {
    "prompt_injection":  "Input validation / system prompt hardening",
    "jailbreak":         "Content moderation guardrails (Bedrock / Azure AI Safety)",
    "data_leakage":      "Output scanning and PII redaction layer",
    "encoding_injection": "Request sanitization for encoded payloads",
    "malware_generation": "Strict output content filtering + human review loop",
    "toxicity":          "Toxicity classifier on model output",
}

# Category → security warning
_CATEGORY_WARNINGS = {
    "prompt_injection":  "⚠ Prompt injection detected — do not expose system prompt to users",
    "jailbreak":         "⚠ Jailbreak vulnerability — enforce guardrails before public deployment",
    "data_leakage":      "⚠ Data leakage risk — add output scanning layer",
    "encoding_injection": "⚠ Encoding injection — sanitize and decode all inputs server-side",
    "malware_generation": "🔴 Malware generation capability — DO NOT deploy publicly without controls",
    "toxicity":          "⚠ Toxic output detected — mandatory content moderation required",
}

# Cost range estimates by provider and mode (USD/month, approximate)
_COST_ESTIMATES = {
    "aws": {
        "bedrock":   CostRange(80,  300,  basis="Bedrock inference + CloudWatch"),
        "sagemaker": CostRange(200, 800,  basis="SageMaker ml.g4dn.xlarge instance + storage"),
        "lambda":    CostRange(20,  120,  basis="API Gateway + Lambda invocations"),
    },
    "azure": {
        "ai_services":  CostRange(100, 400, basis="Azure OpenAI Service + App Service"),
        "container":    CostRange(80,  300, basis="Container Instance + Networking"),
        "app_service":  CostRange(60,  250, basis="App Service B2 + AI Services"),
    },
    "gcp": {
        "vertex_ai":       CostRange(120, 500, basis="Vertex AI endpoints + Cloud Storage"),
        "cloud_run":       CostRange(40,  200, basis="Cloud Run + Artifact Registry"),
        "cloud_functions": CostRange(15,  80,  basis="Cloud Functions invocations"),
    },
    "private": {
        "docker_compose": CostRange(10,  50,  basis="Server cost only — no cloud provider fees"),
        "kubernetes":     CostRange(30,  150, basis="K8s cluster cost — no cloud provider fees"),
        "bare_metal":     CostRange(0,   30,  basis="Hardware already owned — ops cost only"),
    },
}


# ─────────────────────────────────────────────
#  Core recommendation logic
# ─────────────────────────────────────────────

def _determine_risk_level(risk_score: int) -> str:
    if risk_score > 70:
        return "high"
    if risk_score > 30:
        return "medium"
    return "low"


def _get_affected_categories(findings: list[dict]) -> set[str]:
    """Extract categories that have at least one finding."""
    return {f.get("category", "") for f in findings if f.get("category")}


def _choose_provider(risk_level: str, affected_categories: set[str]) -> tuple[str, str]:
    """
    Choose the recommended provider and generate rationale.
    Returns: (provider_id, rationale_text)
    """
    has_malware = "malware_generation" in affected_categories

    if has_malware or risk_level == "high":
        return (
            "private",
            "High-risk findings (including malware generation) detected. Private deployment "
            "recommended to maintain full control over the model and eliminate public attack surface. "
            "Consider AWS SageMaker with private VPC endpoint as a managed alternative."
        )

    if risk_level == "medium":
        return (
            "aws",
            "Medium-risk findings detected. AWS Bedrock with Guardrails provides the most mature "
            "built-in content moderation for LLMs, making it the recommended choice for models "
            "with moderate security findings."
        )

    # Low risk
    return (
        "aws",
        "Low-risk scan results. AWS Bedrock is recommended for its managed infrastructure, "
        "automatic scaling, and built-in compliance features. Public endpoint is acceptable "
        "given the low risk profile, but monitoring is still required."
    )


def generate_deployment_recommendation(scan_report: dict) -> DeploymentRecommendation:
    """
    Main public API.

    Args:
        scan_report: The ScanReport.to_dict() dictionary from the backend pipeline.

    Returns:
        DeploymentRecommendation with fully populated per-provider configs.
    """
    # Extract scan metadata
    risk_score: int = int(scan_report.get("risk_score", 0))
    findings:   list[dict] = scan_report.get("findings", [])

    risk_level = _determine_risk_level(risk_score)
    affected   = _get_affected_categories(findings)
    rules      = _RISK_RULES[risk_level]

    recommended_provider, rationale = _choose_provider(risk_level, affected)

    # Build security warnings from affected categories
    warnings = [
        _CATEGORY_WARNINGS[cat]
        for cat in sorted(affected)
        if cat in _CATEGORY_WARNINGS
    ]

    # Build required controls from affected categories
    controls = [
        _CATEGORY_CONTROLS[cat]
        for cat in sorted(affected)
        if cat in _CATEGORY_CONTROLS
    ]

    # ── AWS config ──
    aws_mode = "bedrock" if risk_level != "high" else "sagemaker"
    aws_rationale = [
        f"Risk level {risk_level}: endpoint access set to {rules['endpoint_scope']}",
        "Bedrock Guardrails enabled for content moderation" if rules["enable_guardrails"] else "",
        f"Budget alert set at ${rules['budget_alert']}/month",
    ]
    aws_cfg = AwsRecommendedConfig(
        deployment_mode    = aws_mode,
        enable_guardrails  = rules["enable_guardrails"],
        enable_vpc         = rules["enable_vpc"],
        enable_cloudwatch  = rules["enable_monitoring"],
        enable_budget_alert= True,
        budget_alert_usd   = rules["budget_alert"],
        endpoint_scope     = rules["endpoint_scope"],
        rationale          = [r for r in aws_rationale if r],
        monthly_cost       = _COST_ESTIMATES["aws"][aws_mode],
    )

    # ── Azure config ──
    azure_mode = "ai_services"
    azure_cfg = AzureRecommendedConfig(
        deployment_mode      = azure_mode,
        enable_content_safety= rules["enable_guardrails"],
        enable_vnet          = rules["enable_vpc"],
        enable_monitoring    = rules["enable_monitoring"],
        endpoint_scope       = rules["endpoint_scope"],
        rationale            = [
            f"Azure AI Content Safety enabled: {rules['enable_guardrails']}",
            f"VNet isolation: {rules['enable_vpc']}",
        ],
        monthly_cost = _COST_ESTIMATES["azure"][azure_mode],
    )

    # ── GCP config ──
    gcp_mode = "vertex_ai"
    gcp_cfg = GcpRecommendedConfig(
        deployment_mode      = gcp_mode,
        enable_model_monitoring = rules["enable_monitoring"],
        enable_vpc_sc        = rules["enable_vpc"],
        enable_cloud_armor   = rules["cloud_armor"],
        endpoint_scope       = rules["endpoint_scope"],
        rationale            = [
            "Vertex AI Model Monitoring enabled for drift detection",
            f"VPC Service Controls: {rules['enable_vpc']}",
            "Cloud Armor: enabled (high-risk)" if rules["cloud_armor"] else "Cloud Armor: disabled (low/medium risk)",
        ],
        monthly_cost = _COST_ESTIMATES["gcp"][gcp_mode],
    )

    # ── Private config ──
    priv_stack = "kubernetes" if risk_level == "high" else "docker_compose"
    priv_cfg = PrivateRecommendedConfig(
        stack             = priv_stack,
        enable_nginx_proxy= True,
        enable_tls        = True,
        enable_rate_limiting= risk_level in ("medium", "high"),
        monthly_cost      = _COST_ESTIMATES["private"][priv_stack],
        rationale         = [
            "Full control over model and data — no third-party provider",
            "TLS termination via Nginx reverse proxy",
            "Rate limiting enabled for medium/high risk models",
        ],
    )

    return DeploymentRecommendation(
        recommended_provider = recommended_provider,
        rationale            = rationale,
        risk_level           = risk_level,
        risk_score           = risk_score,
        aws_config           = aws_cfg,
        azure_config         = azure_cfg,
        gcp_config           = gcp_cfg,
        private_config       = priv_cfg,
        security_warnings    = warnings,
        required_controls    = controls,
    )
