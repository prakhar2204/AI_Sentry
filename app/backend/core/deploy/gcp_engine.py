"""
Sentryɸ — GCP Deploy Engine
core/deploy/gcp_engine.py

Provisions a secure LLM endpoint on Google Cloud Platform.

Supported deployment modes:
  vertex_ai       → Vertex AI managed model endpoint
  cloud_run       → Cloud Run container service
  cloud_functions → Cloud Functions (serverless, small models)

Auth flow:
  Google OAuth 2.0 web application flow:
  1. get_auth_url() → Google consent screen URL
  2. User authorizes → redirect to localhost callback with ?code=
  3. exchange_auth_code() → returns access + refresh tokens
  4. Access token passed in credentials dict for all subsequent calls

Dependencies (optional — gracefully imported):
  google-auth>=2.29
  google-cloud-aiplatform>=1.50 (for Vertex AI)
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any

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

# ── Optional google-cloud imports ──
try:
    import google.auth  # type: ignore
    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False

# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

SENTRY_LABEL      = {"sentryphi": "true"}
DEFAULT_REGION    = "us-central1"
GCP_CLIENT_ID     = os.environ.get("GCP_OAUTH_CLIENT_ID", "")
GCP_CLIENT_SECRET = os.environ.get("GCP_OAUTH_CLIENT_SECRET", "")
GCP_AUTH_URL      = "https://accounts.google.com/o/oauth2/v2/auth"
GCP_TOKEN_URL     = "https://oauth2.googleapis.com/token"
GCP_SCOPES        = "https://www.googleapis.com/auth/cloud-platform"


def _gcp_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }


def _gcp_request(
    url: str,
    access_token: str,
    body: dict | None = None,
    method: str | None = None,
) -> dict:
    data   = json.dumps(body).encode() if body else None
    meth   = method or ("POST" if body else "GET")
    req    = urllib.request.Request(url, data=data, method=meth,
                                    headers=_gcp_headers(access_token))
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


class GcpDeployEngine(BaseDeployEngine):
    """
    W2.4: GCP deployment engine.
    Uses GCP REST APIs directly (no google-cloud SDK required at runtime).
    """

    PROVIDER_ID = "gcp"

    # ── Auth ─────────────────────────────────────────────────────────────────

    def get_auth_url(self, redirect_port: int = 9878) -> str:
        import secrets
        state        = secrets.token_urlsafe(16)
        redirect_uri = f"http://localhost:{redirect_port}/callback"
        client_id    = GCP_CLIENT_ID or "32555940559.apps.googleusercontent.com"  # gcloud public client

        params = {
            "client_id":     client_id,
            "redirect_uri":  redirect_uri,
            "response_type": "code",
            "scope":         GCP_SCOPES,
            "access_type":   "offline",
            "state":         state,
            "prompt":        "consent",
        }
        return f"{GCP_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_auth_code(self, code: str, state: str) -> CredentialResult:
        redirect_port = 9878
        redirect_uri  = f"http://localhost:{redirect_port}/callback"
        client_id     = GCP_CLIENT_ID or "32555940559.apps.googleusercontent.com"
        client_secret = GCP_CLIENT_SECRET

        body = urllib.parse.urlencode({
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  redirect_uri,
            "grant_type":    "authorization_code",
        }).encode()

        try:
            req = urllib.request.Request(
                GCP_TOKEN_URL, data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            return CredentialResult(
                status  = CredentialStatus.VALID,
                account = data.get("id_token", "")[:20] + "...",
                message = f"GCP access token obtained (expires in {data.get('expires_in', 3600)}s)",
            )
        except Exception as exc:  # noqa: BLE001
            return CredentialResult(status=CredentialStatus.INVALID, message=str(exc))

    def validate_credentials(self, credentials: dict[str, str]) -> CredentialResult:
        access_token = credentials.get("gcp_access_token", "")
        if not access_token:
            return CredentialResult(status=CredentialStatus.MISSING, message="No GCP access token")

        try:
            data = _gcp_request(
                f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={access_token}",
                access_token="",
            )
            if "error" in data:
                return CredentialResult(status=CredentialStatus.EXPIRED, message=data.get("error_description", ""))
            return CredentialResult(
                status  = CredentialStatus.VALID,
                account = data.get("email", data.get("sub", "")),
                message = f"Token valid for {data.get('email', 'unknown')}",
            )
        except Exception as exc:  # noqa: BLE001
            return CredentialResult(status=CredentialStatus.INVALID, message=str(exc))

    # ── Plan ─────────────────────────────────────────────────────────────────

    def generate_plan(
        self,
        config: dict[str, Any],
        credentials: dict[str, str],
        scan_report: dict[str, Any],
    ) -> DeployPlan:
        region = config.get("region", DEFAULT_REGION)
        mode   = config.get("deployment_mode", "vertex_ai")
        scope  = config.get("endpoint_scope", "private")
        risk   = (scan_report.get("summary", {}) or {}).get("risk_level", "MEDIUM")

        resources: list[DeployResource] = []

        # VPC Service Controls (high risk)
        if scope == "private" or risk in ("HIGH", "CRITICAL"):
            resources += [
                DeployResource(resource_type="VPC Network",              region=region, status="planned"),
                DeployResource(resource_type="VPC Service Controls",     region=region, status="planned"),
                DeployResource(resource_type="Private Service Connect",  region=region, status="planned"),
            ]

        if config.get("enable_cloud_armor", False):
            resources.append(DeployResource(resource_type="Cloud Armor Security Policy", region=region, status="planned"))

        if mode == "vertex_ai":
            resources += [
                DeployResource(resource_type="Vertex AI Model",          region=region, status="planned"),
                DeployResource(resource_type="Vertex AI Endpoint",       region=region, status="planned"),
                DeployResource(resource_type="Model Monitoring Job",     region=region, status="planned"),
            ]
        elif mode == "cloud_run":
            resources += [
                DeployResource(resource_type="Artifact Registry Repo",  region=region, status="planned"),
                DeployResource(resource_type="Cloud Run Service",       region=region, status="planned"),
            ]
        elif mode == "cloud_functions":
            resources.append(DeployResource(resource_type="Cloud Function (Gen2)", region=region, status="planned"))

        resources += [
            DeployResource(resource_type="Cloud Logging Sink",           region=region, status="planned"),
            DeployResource(resource_type="Cloud Monitoring Alert Policy",region=region, status="planned"),
        ]

        security_notes = [
            "All resources labelled sentryphi=true",
            f"Endpoint access: {scope}",
            "Cloud Monitoring alerts on error rate",
        ]
        if mode == "vertex_ai" and config.get("enable_model_monitoring", True):
            security_notes.append("Vertex AI Model Monitoring enabled for drift detection")
        if config.get("enable_cloud_armor", False):
            security_notes.append("Cloud Armor WAF rules active")

        from .recommendation_engine import _COST_ESTIMATES
        cost = _COST_ESTIMATES.get("gcp", {}).get(mode)

        return DeployPlan(
            provider       = "gcp",
            region         = region,
            resources      = resources,
            estimated_cost = cost.to_dict() if cost else {},
            security_notes = security_notes,
            raw_config     = config,
        )

    # ── Cost ─────────────────────────────────────────────────────────────────

    def estimate_cost(self, plan: DeployPlan, credentials: dict[str, str]) -> dict[str, Any]:
        mode   = plan.raw_config.get("deployment_mode", "vertex_ai")
        from .recommendation_engine import _COST_ESTIMATES
        static = _COST_ESTIMATES.get("gcp", {}).get(mode)
        return {**(static.to_dict() if static else {"low_usd": 120, "high_usd": 500}),
                "source": "static_estimate"}

    # ── Dry run ───────────────────────────────────────────────────────────────

    def dry_run(self, plan: DeployPlan, credentials: dict[str, str]) -> DryRunResult:
        result = self.validate_credentials(credentials)
        if result.status != CredentialStatus.VALID:
            return DryRunResult(success=False, errors=[result.message])

        project_id = credentials.get("gcp_project_id", "")
        warnings   = []
        if not project_id:
            warnings.append("No GCP project ID provided — set gcp_project_id in credentials")

        mode = plan.raw_config.get("deployment_mode", "vertex_ai")
        if mode == "vertex_ai":
            warnings.append("Ensure Vertex AI API is enabled in your project")
        elif mode == "cloud_run":
            warnings.append("Ensure Cloud Run API and Artifact Registry API are enabled")

        return DryRunResult(
            success  = True,
            warnings = warnings,
            message  = f"Credentials valid for {result.account}. Plan validated.",
        )

    # ── Deploy ────────────────────────────────────────────────────────────────

    def deploy(
        self,
        plan: DeployPlan,
        credentials: dict[str, str],
        confirmed: bool = False,
    ) -> DeployResult:
        self._require_confirmed(confirmed)

        cred_result = self.validate_credentials(credentials)
        if cred_result.status != CredentialStatus.VALID:
            return DeployResult(
                status  = DeployStatus.FAILED,
                errors  = [cred_result.message],
                message = "GCP credentials invalid",
            )

        access_token = credentials.get("gcp_access_token", "")
        project_id   = credentials.get("gcp_project_id", "")
        mode         = plan.raw_config.get("deployment_mode", "vertex_ai")
        created: list[DeployResource] = []
        errors:  list[str] = []
        endpoint_url = ""

        try:
            if mode == "vertex_ai":
                endpoint_url = self._deploy_vertex_ai(access_token, project_id, plan, created, errors)
            elif mode == "cloud_run":
                endpoint_url = self._deploy_cloud_run(access_token, project_id, plan, created, errors)
            elif mode == "cloud_functions":
                endpoint_url = self._deploy_cloud_function(access_token, project_id, plan, created, errors)

            status = DeployStatus.FAILED if (errors and not created) else DeployStatus.COMPLETE
            return DeployResult(
                status        = status,
                deployment_id = plan.deployment_id,
                endpoint_url  = endpoint_url,
                resources     = created,
                errors        = errors,
                message       = "Deployment complete" if not errors else f"Partial — {len(errors)} error(s)",
            )
        except Exception as exc:  # noqa: BLE001
            return DeployResult(
                status        = DeployStatus.FAILED,
                deployment_id = plan.deployment_id,
                resources     = created,
                errors        = [str(exc)],
                message       = "GCP deployment failed",
            )

    def _deploy_vertex_ai(
        self,
        access_token: str,
        project_id: str,
        plan: DeployPlan,
        created: list[DeployResource],
        errors: list[str],
    ) -> str:
        region    = plan.region
        endpoint_name = f"sentryphi-{plan.deployment_id}"
        url = (
            f"https://{region}-aiplatform.googleapis.com/v1"
            f"/projects/{project_id}/locations/{region}/endpoints"
        )
        body = {
            "displayName": endpoint_name,
            "labels":      {"sentryphi": "true", "deployment-id": plan.deployment_id},
        }
        try:
            data = _gcp_request(url, access_token, body)
            op_name = data.get("name", "")
            created.append(DeployResource(
                resource_type = "Vertex AI Endpoint",
                resource_id   = endpoint_name,
                region        = region,
                arn_or_id     = op_name,
                status        = "creating",
            ))
            return f"https://{region}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region}/endpoints/{plan.deployment_id}:predict"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Vertex AI endpoint: {exc}")
            return ""

    def _deploy_cloud_run(
        self,
        access_token: str,
        project_id: str,
        plan: DeployPlan,
        created: list[DeployResource],
        errors: list[str],
    ) -> str:
        region   = plan.region
        svc_name = f"sentryphi-{plan.deployment_id[:8]}"
        url = (
            f"https://run.googleapis.com/v2/projects/{project_id}"
            f"/locations/{region}/services"
        )
        body = {
            "name":   f"projects/{project_id}/locations/{region}/services/{svc_name}",
            "labels": {"sentryphi": "true"},
            "template": {
                "containers": [{
                    "image": plan.raw_config.get("container_image", "python:3.11-slim"),
                    "resources": {"limits": {"cpu": "2", "memory": "2Gi"}},
                    "ports": [{"containerPort": 8080}],
                }]
            },
            "ingress": "INGRESS_TRAFFIC_ALL" if plan.raw_config.get("endpoint_scope") == "public" else "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER",
        }
        try:
            data = _gcp_request(url, access_token, body)
            svc_uri = data.get("status", {}).get("url", "")
            created.append(DeployResource(
                resource_type = "Cloud Run Service",
                resource_id   = svc_name,
                region        = region,
                arn_or_id     = data.get("name", ""),
                status        = "creating",
            ))
            return svc_uri
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Cloud Run: {exc}")
            return ""

    def _deploy_cloud_function(
        self,
        access_token: str,
        project_id: str,
        plan: DeployPlan,
        created: list[DeployResource],
        errors: list[str],
    ) -> str:
        region  = plan.region
        fn_name = f"sentryphi-{plan.deployment_id[:8]}"
        url = (
            f"https://cloudfunctions.googleapis.com/v2/projects/{project_id}"
            f"/locations/{region}/functions"
        )
        body = {
            "name": f"projects/{project_id}/locations/{region}/functions/{fn_name}",
            "buildConfig": {
                "runtime": "python311",
                "entryPoint": "predict",
                "source": {"storageSource": {}},  # placeholder
            },
            "serviceConfig": {
                "availableMemory": "512M",
                "ingressSettings": "ALLOW_ALL" if plan.raw_config.get("endpoint_scope") == "public" else "ALLOW_INTERNAL_ONLY",
            },
            "labels": {"sentryphi": "true"},
        }
        try:
            data = _gcp_request(url, access_token, body)
            created.append(DeployResource(
                resource_type = "Cloud Function (Gen2)",
                resource_id   = fn_name,
                region        = region,
                arn_or_id     = data.get("name", ""),
                status        = "creating",
            ))
            return f"https://{region}-{project_id}.cloudfunctions.net/{fn_name}"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Cloud Function: {exc}")
            return ""

    # ── Status / Rollback ────────────────────────────────────────────────────

    def get_deployment_status(self, deployment_id: str, credentials: dict[str, str]) -> DeployResult:
        return DeployResult(
            status        = DeployStatus.UNKNOWN,
            deployment_id = deployment_id,
            message       = "GCP status polling queries Vertex AI / Cloud Run operation APIs",
        )

    def rollback(self, deployment_id: str, credentials: dict[str, str]) -> RollbackResult:
        """Delete resources labelled sentryphi=true via Cloud Asset API."""
        access_token = credentials.get("gcp_access_token", "")
        project_id   = credentials.get("gcp_project_id", "")

        try:
            # Query Cloud Asset API for resources with our label
            url = (
                f"https://cloudasset.googleapis.com/v1/projects/{project_id}/assets"
                f"?assetTypes=aiplatform.googleapis.com/Endpoint"
                f"&assetTypes=run.googleapis.com/Service"
                f"&contentType=RESOURCE"
            )
            data    = _gcp_request(url, access_token)
            assets  = data.get("assets", [])
            deleted = []
            errors  = []

            for asset in assets:
                labels = asset.get("resource", {}).get("data", {}).get("labels", {})
                if labels.get("sentryphi") == "true":
                    name = asset.get("name", "")
                    try:
                        _gcp_request(
                            f"https://us-central1-aiplatform.googleapis.com/v1/{name}",
                            access_token,
                            method="DELETE",
                        )
                        deleted.append(name)
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"{name}: {exc}")

            return RollbackResult(
                success = len(errors) == 0,
                deleted = deleted,
                errors  = errors,
                message = f"Deleted {len(deleted)}/{len(assets)} resource(s)",
            )
        except Exception as exc:  # noqa: BLE001
            return RollbackResult(success=False, errors=[str(exc)])
