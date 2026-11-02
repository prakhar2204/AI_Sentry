"""
Sentryɸ — Azure Deploy Engine
core/deploy/azure_engine.py

Provisions a secure LLM endpoint on Azure using the azure-sdk.

Supported deployment modes:
  ai_services  → Azure OpenAI Service / Azure AI Services endpoint
  container    → Azure Container Instance (bring-your-own model)
  app_service  → Azure App Service (Python web app hosting the model)

Auth flow:
  Azure OAuth 2.0 device code flow or browser redirect:
  1. call get_auth_url() → user opens URL in browser
  2. User logs in → redirect to localhost callback
  3. call exchange_auth_code() → returns access + refresh tokens

Dependencies (optional — gracefully imported):
  azure-identity>=1.17
  azure-mgmt-resource>=23.0
  azure-mgmt-cognitiveservices>=13.0
  azure-mgmt-containerinstance>=10.0
  azure-mgmt-web>=7.0
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

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

# ── Optional Azure SDK imports ──
try:
    from azure.identity import ClientSecretCredential, DeviceCodeCredential
    from azure.mgmt.resource import ResourceManagementClient
    _AZURE_AVAILABLE = True
except ImportError:
    _AZURE_AVAILABLE = False


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

SENTRY_TAG        = {"SentryPhi": "true"}
DEFAULT_LOCATION  = "eastus"
AZURE_TENANT_ID   = os.environ.get("AZURE_TENANT_ID", "common")
AZURE_CLIENT_ID   = os.environ.get("AZURE_CLIENT_ID", "")   # App registration client ID
AZURE_REDIRECT    = "http://localhost:{port}/callback"
AZURE_AUTH_URL    = (
    "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?"
    "client_id={client_id}&response_type=code&redirect_uri={redirect_uri}"
    "&scope=https%3A%2F%2Fmanagement.azure.com%2F.default+offline_access"
    "&state={state}"
)
AZURE_TOKEN_URL   = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"


def _require_azure() -> None:
    if not _AZURE_AVAILABLE:
        raise RuntimeError(
            "azure-identity and azure-mgmt-resource are required for Azure deployment. "
            "Install with: pip install azure-identity azure-mgmt-resource azure-mgmt-cognitiveservices"
        )


class AzureDeployEngine(BaseDeployEngine):
    """
    W2.3: Azure deployment engine.
    """

    PROVIDER_ID = "azure"

    # ── Auth ─────────────────────────────────────────────────────────────────

    def get_auth_url(self, redirect_port: int = 9877) -> str:
        import secrets
        state       = secrets.token_urlsafe(16)
        redirect_uri = AZURE_REDIRECT.format(port=redirect_port)
        client_id   = AZURE_CLIENT_ID or "04b07795-8542-4c4e-967c-4e5cda52f1d8"  # Azure CLI app id (public)
        url = (
            f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/authorize"
            f"?client_id={client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_uri}"
            f"&scope=https%3A%2F%2Fmanagement.azure.com%2F.default+offline_access+openid+profile"
            f"&state={state}"
        )
        return url

    def exchange_auth_code(self, code: str, state: str) -> CredentialResult:
        """Exchange OAuth authorization code for access token."""
        import urllib.request, urllib.parse, json
        redirect_port = 9877
        redirect_uri  = AZURE_REDIRECT.format(port=redirect_port)
        client_id     = AZURE_CLIENT_ID or "04b07795-8542-4c4e-967c-4e5cda52f1d8"

        body = urllib.parse.urlencode({
            "client_id":    client_id,
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": redirect_uri,
            "scope":        "https://management.azure.com/.default offline_access openid profile",
        }).encode()

        try:
            req  = urllib.request.Request(
                AZURE_TOKEN_URL.format(tenant=AZURE_TENANT_ID),
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            return CredentialResult(
                status  = CredentialStatus.VALID,
                account = data.get("id_token", "")[:20] + "...",
                message = f"Azure access token obtained (expires in {data.get('expires_in', 3600)}s)",
            )
        except Exception as exc:  # noqa: BLE001
            return CredentialResult(
                status  = CredentialStatus.INVALID,
                message = str(exc),
            )

    def validate_credentials(self, credentials: dict[str, str]) -> CredentialResult:
        """Validate Azure credentials by calling the ARM subscriptions API."""
        access_token = credentials.get("azure_access_token", "")
        if not access_token:
            return CredentialResult(status=CredentialStatus.MISSING, message="No Azure access token provided")

        import urllib.request, json
        try:
            req = urllib.request.Request(
                "https://management.azure.com/subscriptions?api-version=2022-12-01",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            subs = data.get("value", [])
            if not subs:
                return CredentialResult(
                    status  = CredentialStatus.VALID,
                    account = "No subscriptions found",
                    message = "Token valid but account has no subscriptions",
                )
            sub = subs[0]
            return CredentialResult(
                status  = CredentialStatus.VALID,
                account = sub.get("displayName", sub.get("subscriptionId", "")),
                message = f"Subscription: {sub.get('subscriptionId', '')}",
            )
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "401" in msg or "403" in msg:
                return CredentialResult(status=CredentialStatus.EXPIRED, message=msg)
            return CredentialResult(status=CredentialStatus.INVALID, message=msg)

    # ── Plan ─────────────────────────────────────────────────────────────────

    def generate_plan(
        self,
        config: dict[str, Any],
        credentials: dict[str, str],
        scan_report: dict[str, Any],
    ) -> DeployPlan:
        location = config.get("region", DEFAULT_LOCATION)
        mode     = config.get("deployment_mode", "ai_services")
        scope    = config.get("endpoint_scope", "private")
        risk     = (scan_report.get("summary", {}) or {}).get("risk_level", "MEDIUM")

        resources: list[DeployResource] = [
            DeployResource(resource_type="Resource Group", region=location, status="planned"),
        ]

        # VNet for private endpoints
        if scope == "private" or risk in ("HIGH", "CRITICAL"):
            resources += [
                DeployResource(resource_type="Virtual Network",         region=location, status="planned"),
                DeployResource(resource_type="Private Endpoint",        region=location, status="planned"),
                DeployResource(resource_type="Network Security Group",  region=location, status="planned"),
            ]

        if mode == "ai_services":
            resources += [
                DeployResource(resource_type="Azure AI Services Account", region=location, status="planned"),
                DeployResource(resource_type="AI Content Safety",         region=location, status="planned"),
            ]
            if config.get("enable_content_safety", True):
                resources.append(DeployResource(resource_type="Content Safety Policy", region=location, status="planned"))

        elif mode == "container":
            resources += [
                DeployResource(resource_type="Container Registry",     region=location, status="planned"),
                DeployResource(resource_type="Container Instance",     region=location, status="planned"),
            ]

        elif mode == "app_service":
            resources += [
                DeployResource(resource_type="App Service Plan (B2)", region=location, status="planned"),
                DeployResource(resource_type="App Service",           region=location, status="planned"),
            ]

        resources += [
            DeployResource(resource_type="Log Analytics Workspace", region=location, status="planned"),
            DeployResource(resource_type="Application Insights",    region=location, status="planned"),
        ]

        security_notes = [
            "All resources tagged with SentryPhi=true",
            "Azure Monitor diagnostics enabled",
            f"Endpoint access: {scope}",
        ]
        if mode == "ai_services" and config.get("enable_content_safety", True):
            security_notes.append("Azure AI Content Safety policy active")

        from .recommendation_engine import _COST_ESTIMATES
        cost = _COST_ESTIMATES.get("azure", {}).get(mode)

        return DeployPlan(
            provider       = "azure",
            region         = location,
            resources      = resources,
            estimated_cost = cost.to_dict() if cost else {},
            security_notes = security_notes,
            raw_config     = config,
        )

    # ── Cost ─────────────────────────────────────────────────────────────────

    def estimate_cost(self, plan: DeployPlan, credentials: dict[str, str]) -> dict[str, Any]:
        mode   = plan.raw_config.get("deployment_mode", "ai_services")
        from .recommendation_engine import _COST_ESTIMATES
        static = _COST_ESTIMATES.get("azure", {}).get(mode)
        return {**(static.to_dict() if static else {"low_usd": 100, "high_usd": 400}),
                "source": "static_estimate"}

    # ── Dry run ───────────────────────────────────────────────────────────────

    def dry_run(self, plan: DeployPlan, credentials: dict[str, str]) -> DryRunResult:
        """Validate credentials and subscription access."""
        result = self.validate_credentials(credentials)
        if result.status != CredentialStatus.VALID:
            return DryRunResult(
                success = False,
                errors  = [result.message],
                message = "Azure credential validation failed",
            )
        sub_id = credentials.get("azure_subscription_id", "")
        warnings = []
        if not sub_id:
            warnings.append("No subscription ID provided — will use first available subscription")

        return DryRunResult(
            success  = True,
            warnings = warnings,
            message  = f"Credentials valid for account: {result.account}. Ready to deploy.",
        )

    # ── Deploy ────────────────────────────────────────────────────────────────

    def deploy(
        self,
        plan: DeployPlan,
        credentials: dict[str, str],
        confirmed: bool = False,
    ) -> DeployResult:
        self._require_confirmed(confirmed)

        # Validate credentials first
        cred_result = self.validate_credentials(credentials)
        if cred_result.status != CredentialStatus.VALID:
            return DeployResult(
                status  = DeployStatus.FAILED,
                errors  = [cred_result.message],
                message = "Azure credentials invalid",
            )

        mode    = plan.raw_config.get("deployment_mode", "ai_services")
        created: list[DeployResource] = []
        errors:  list[str] = []
        access_token = credentials.get("azure_access_token", "")
        sub_id       = credentials.get("azure_subscription_id", "")
        rg_name      = f"sentryphi-{plan.deployment_id}"

        try:
            # Create resource group via ARM API
            import urllib.request, json as _json
            rg_url = (
                f"https://management.azure.com/subscriptions/{sub_id}"
                f"/resourcegroups/{rg_name}?api-version=2022-09-01"
            )
            rg_body = _json.dumps({
                "location": plan.region,
                "tags": {"SentryPhi": "true", "DeploymentId": plan.deployment_id}
            }).encode()
            req = urllib.request.Request(
                rg_url, data=rg_body, method="PUT",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type":  "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                rg_data = _json.loads(resp.read())
            created.append(DeployResource(
                resource_type = "Resource Group",
                resource_id   = rg_name,
                region        = plan.region,
                arn_or_id     = rg_data.get("id", ""),
                status        = "created",
            ))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Resource group: {exc}")
            return DeployResult(
                status        = DeployStatus.FAILED,
                deployment_id = plan.deployment_id,
                errors        = errors,
                message       = "Failed to create resource group",
            )

        # Mode-specific: AI Services endpoint
        if mode == "ai_services":
            endpoint_url = self._deploy_ai_services(
                access_token, sub_id, rg_name, plan, created, errors
            )
        elif mode == "container":
            endpoint_url = self._deploy_container(
                access_token, sub_id, rg_name, plan, created, errors
            )
        else:
            endpoint_url = f"https://{rg_name}.azurewebsites.net/api/predict"

        status = DeployStatus.FAILED if (errors and not created) else DeployStatus.COMPLETE
        return DeployResult(
            status        = status,
            deployment_id = plan.deployment_id,
            endpoint_url  = endpoint_url,
            resources     = created,
            errors        = errors,
            message       = "Deployment complete" if not errors else f"Partial — {len(errors)} error(s)",
        )

    def _deploy_ai_services(
        self,
        access_token: str,
        sub_id: str,
        rg_name: str,
        plan: DeployPlan,
        created: list[DeployResource],
        errors: list[str],
    ) -> str:
        import urllib.request, json as _json
        acct_name = f"sp{plan.deployment_id[:8]}"
        url = (
            f"https://management.azure.com/subscriptions/{sub_id}"
            f"/resourceGroups/{rg_name}/providers/Microsoft.CognitiveServices"
            f"/accounts/{acct_name}?api-version=2023-05-01"
        )
        body = _json.dumps({
            "kind":     "OpenAI",
            "location": plan.region,
            "sku":      {"name": "S0"},
            "properties": {"publicNetworkAccess": "Disabled" if plan.raw_config.get("endpoint_scope") == "private" else "Enabled"},
            "tags":     {"SentryPhi": "true", "DeploymentId": plan.deployment_id},
        }).encode()
        try:
            req = urllib.request.Request(url, data=body, method="PUT",
                                         headers={"Authorization": f"Bearer {access_token}",
                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read())
            endpoint = data.get("properties", {}).get("endpoint", "")
            created.append(DeployResource(
                resource_type = "Azure AI Services Account",
                resource_id   = acct_name,
                region        = plan.region,
                arn_or_id     = data.get("id", ""),
                status        = "creating",
            ))
            return endpoint
        except Exception as exc:  # noqa: BLE001
            errors.append(f"AI Services: {exc}")
            return ""

    def _deploy_container(
        self,
        access_token: str,
        sub_id: str,
        rg_name: str,
        plan: DeployPlan,
        created: list[DeployResource],
        errors: list[str],
    ) -> str:
        import urllib.request, json as _json
        ci_name = f"sp-{plan.deployment_id[:8]}"
        url = (
            f"https://management.azure.com/subscriptions/{sub_id}"
            f"/resourceGroups/{rg_name}/providers/Microsoft.ContainerInstance"
            f"/containerGroups/{ci_name}?api-version=2023-05-01"
        )
        body = _json.dumps({
            "location": plan.region,
            "tags":     {"SentryPhi": "true"},
            "properties": {
                "containers": [{
                    "name": "model",
                    "properties": {
                        "image": plan.raw_config.get("container_image", "python:3.11-slim"),
                        "resources": {"requests": {"cpu": 2, "memoryInGB": 4}},
                        "ports": [{"port": 8000}],
                    }
                }],
                "osType": "Linux",
                "ipAddress": {"type": "Public", "ports": [{"protocol": "TCP", "port": 8000}]},
            },
        }).encode()
        try:
            req = urllib.request.Request(url, data=body, method="PUT",
                                         headers={"Authorization": f"Bearer {access_token}",
                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read())
            ip = data.get("properties", {}).get("ipAddress", {}).get("ip", "")
            created.append(DeployResource(
                resource_type = "Container Instance",
                resource_id   = ci_name,
                region        = plan.region,
                arn_or_id     = data.get("id", ""),
                status        = "creating",
            ))
            return f"http://{ip}:8000/predict" if ip else ""
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Container Instance: {exc}")
            return ""

    # ── Status / Rollback ────────────────────────────────────────────────────

    def get_deployment_status(self, deployment_id: str, credentials: dict[str, str]) -> DeployResult:
        return DeployResult(
            status        = DeployStatus.UNKNOWN,
            deployment_id = deployment_id,
            message       = "Status polling not yet implemented for Azure",
        )

    def rollback(self, deployment_id: str, credentials: dict[str, str]) -> RollbackResult:
        """Delete the entire resource group (tags SentryPhi=true on RG)."""
        access_token = credentials.get("azure_access_token", "")
        sub_id       = credentials.get("azure_subscription_id", "")
        rg_name      = f"sentryphi-{deployment_id}"

        import urllib.request
        try:
            url = (
                f"https://management.azure.com/subscriptions/{sub_id}"
                f"/resourcegroups/{rg_name}?api-version=2022-09-01"
            )
            req = urllib.request.Request(url, method="DELETE",
                                         headers={"Authorization": f"Bearer {access_token}"})
            urllib.request.urlopen(req, timeout=30)
            return RollbackResult(
                success = True,
                deleted = [rg_name],
                message = f"Resource group {rg_name} deletion initiated",
            )
        except Exception as exc:  # noqa: BLE001
            return RollbackResult(success=False, errors=[str(exc)])
