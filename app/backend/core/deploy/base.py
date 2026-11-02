"""
Sentryɸ — Base Deploy Engine Interface
core/deploy/base.py

Abstract base class that every cloud/private deploy engine must implement.
All engines follow the same lifecycle: validate → plan → estimate → dry_run → deploy → rollback.

Security invariants (enforced by this base class):
  - Credentials are NEVER stored to disk. They live in process memory only for the duration
    of the deployment session (passed in via deploy() call from IPC).
  - dry_run is called by default before any real deploy; callers must explicitly pass
    confirmed=True to execute live provisioning.
  - Every deploy tags all created resources with SentryPhi=true for clean rollback.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─────────────────────────────────────────────
#  Status enumerations
# ─────────────────────────────────────────────

class CredentialStatus(str, Enum):
    VALID      = "valid"
    INVALID    = "invalid"
    EXPIRED    = "expired"
    MISSING    = "missing"
    UNKNOWN    = "unknown"


class DeployStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETE   = "complete"
    FAILED     = "failed"
    ROLLED_BACK = "rolled_back"


# ─────────────────────────────────────────────
#  Result data classes
# ─────────────────────────────────────────────

@dataclass
class CredentialResult:
    status:  CredentialStatus
    account: str = ""          # Account ID / email displayed in UI
    message: str = ""          # Human-readable status detail

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status.value, "account": self.account, "message": self.message}


@dataclass
class DeployResource:
    """A single cloud resource that will be / was created."""
    resource_type: str         # e.g. "IAM Role", "API Gateway", "VPC"
    resource_id:   str = ""    # Filled in after provisioning
    region:        str = ""
    arn_or_id:     str = ""    # ARN (AWS), resource ID (Azure/GCP), or path (private)
    status:        str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "resource_id":   self.resource_id,
            "region":        self.region,
            "arn_or_id":     self.arn_or_id,
            "status":        self.status,
        }


@dataclass
class DeployPlan:
    """
    Complete deployment plan produced by generate_plan().
    Shown to the user for review BEFORE any provisioning.
    """
    deployment_id:  str = field(default_factory=lambda: f"sp-{uuid.uuid4().hex[:8]}")
    provider:       str = ""
    region:         str = ""
    resources:      list[DeployResource] = field(default_factory=list)
    estimated_cost: dict[str, Any] = field(default_factory=dict)   # monthly range
    security_notes: list[str] = field(default_factory=list)
    raw_config:     dict[str, Any] = field(default_factory=dict)   # provider-specific config

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_id":  self.deployment_id,
            "provider":       self.provider,
            "region":         self.region,
            "resources":      [r.to_dict() for r in self.resources],
            "estimated_cost": self.estimated_cost,
            "security_notes": self.security_notes,
        }


@dataclass
class DryRunResult:
    success: bool
    errors:  list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success":  self.success,
            "errors":   self.errors,
            "warnings": self.warnings,
            "message":  self.message,
        }


@dataclass
class DeployResult:
    """Result of a live deployment execution."""
    status:        DeployStatus
    deployment_id: str = ""
    endpoint_url:  str = ""              # Live endpoint after deploy
    resources:     list[DeployResource] = field(default_factory=list)
    errors:        list[str] = field(default_factory=list)
    message:       str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status":        self.status.value,
            "deployment_id": self.deployment_id,
            "endpoint_url":  self.endpoint_url,
            "resources":     [r.to_dict() for r in self.resources],
            "errors":        self.errors,
            "message":       self.message,
        }


@dataclass
class RollbackResult:
    success:   bool
    deleted:   list[str] = field(default_factory=list)
    errors:    list[str] = field(default_factory=list)
    message:   str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "deleted": self.deleted,
            "errors":  self.errors,
            "message": self.message,
        }


# ─────────────────────────────────────────────
#  Abstract base engine
# ─────────────────────────────────────────────

class BaseDeployEngine(ABC):
    """
    All deploy engines must implement this interface.

    Credential handling contract:
      - credentials dict is passed per-call, never stored as instance state
      - Never write credentials to disk or log them
      - Clear from local variables immediately after SDK session is established
    """

    PROVIDER_ID: str = ""   # "aws" | "azure" | "gcp" | "private"

    @abstractmethod
    def get_auth_url(self, redirect_port: int = 9876) -> str:
        """
        Return a URL the user should open in their browser to authenticate.
        For OAuth flows: returns the provider login page URL.
        For API key flows: returns an empty string (no browser flow needed).
        """

    @abstractmethod
    def exchange_auth_code(self, code: str, state: str) -> CredentialResult:
        """
        Exchange an OAuth authorization code for session credentials.
        Credentials are returned in the CredentialResult — caller stores them
        in process memory only.
        """

    @abstractmethod
    def validate_credentials(self, credentials: dict[str, str]) -> CredentialResult:
        """
        Validate that credentials are active and have sufficient permissions
        for deployment. Must not cache or store the credentials.
        """

    @abstractmethod
    def generate_plan(
        self,
        config: dict[str, Any],
        credentials: dict[str, str],
        scan_report: dict[str, Any],
    ) -> DeployPlan:
        """
        Generate a deployment plan from the UI config and scan report.
        No cloud API calls that modify state — read-only queries only.
        """

    @abstractmethod
    def estimate_cost(self, plan: DeployPlan, credentials: dict[str, str]) -> dict[str, Any]:
        """
        Query the provider's pricing API and return a cost estimate.
        Returns a dict with: low_usd, high_usd, currency, breakdown, basis.
        """

    @abstractmethod
    def dry_run(self, plan: DeployPlan, credentials: dict[str, str]) -> DryRunResult:
        """
        Validate the plan against the provider's APIs without creating resources.
        AWS: CloudFormation change set.
        Azure: resource group deployment in validate mode.
        GCP: plan preview.
        """

    @abstractmethod
    def deploy(
        self,
        plan: DeployPlan,
        credentials: dict[str, str],
        confirmed: bool = False,
    ) -> DeployResult:
        """
        Provision resources according to the plan.
        MUST check confirmed=True before making any state-modifying API calls.
        If confirmed=False, must raise RuntimeError("Deploy not confirmed by user").
        """

    @abstractmethod
    def get_deployment_status(
        self,
        deployment_id: str,
        credentials: dict[str, str],
    ) -> DeployResult:
        """Poll the status of a running or completed deployment."""

    @abstractmethod
    def rollback(
        self,
        deployment_id: str,
        credentials: dict[str, str],
    ) -> RollbackResult:
        """
        Tear down all resources created for this deployment_id.
        Uses resource tags (SentryPhi=true) to identify resources.
        """

    def _require_confirmed(self, confirmed: bool) -> None:
        """Safety guard — call at top of deploy() before any API calls."""
        if not confirmed:
            raise RuntimeError(
                "Live deployment requires explicit user confirmation. "
                "Pass confirmed=True only after the user has reviewed and approved the plan."
            )
