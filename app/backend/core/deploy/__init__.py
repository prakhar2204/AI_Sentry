"""core/deploy package — W2 multi-cloud deployment engines"""
from .recommendation_engine import (
    generate_deployment_recommendation,
    DeploymentRecommendation,
    AwsRecommendedConfig,
    AzureRecommendedConfig,
    GcpRecommendedConfig,
    PrivateRecommendedConfig,
    CostRange,
)
from .base import (
    BaseDeployEngine,
    CredentialResult,
    CredentialStatus,
    DeployPlan,
    DeployResource,
    DeployResult,
    DeployStatus,
    DryRunResult,
    RollbackResult,
)
from .aws_engine     import AwsDeployEngine
from .azure_engine   import AzureDeployEngine
from .gcp_engine     import GcpDeployEngine
from .private_engine import PrivateDeployEngine
from .oauth_server   import OAuthCallbackServer, get_callback_server, PROVIDER_PORTS

# Registry — keyed by provider ID
DEPLOY_ENGINES: dict[str, BaseDeployEngine] = {
    "aws":     AwsDeployEngine(),
    "azure":   AzureDeployEngine(),
    "gcp":     GcpDeployEngine(),
    "private": PrivateDeployEngine(),
}

__all__ = [
    "generate_deployment_recommendation",
    "DeploymentRecommendation",
    "AwsRecommendedConfig",
    "AzureRecommendedConfig",
    "GcpRecommendedConfig",
    "PrivateRecommendedConfig",
    "CostRange",
    "BaseDeployEngine",
    "CredentialResult",
    "CredentialStatus",
    "DeployPlan",
    "DeployResource",
    "DeployResult",
    "DeployStatus",
    "DryRunResult",
    "RollbackResult",
    "AwsDeployEngine",
    "AzureDeployEngine",
    "GcpDeployEngine",
    "PrivateDeployEngine",
    "OAuthCallbackServer",
    "get_callback_server",
    "PROVIDER_PORTS",
    "DEPLOY_ENGINES",
]
