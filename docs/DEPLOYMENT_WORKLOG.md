# Deployment completion worklog

Started 2026-11-15 after the verified local scan repair. User authorizes completing final deployment, AWS/Azure/GCP, the audit backlog, and wider defect checks while preserving core workflows.

## Execution sequence

1. Trace both deployment UI routes and all provider contracts. Replace dry-run-only final navigation with the existing live provider wizard, retaining review/confirmation.
2. Implement durable, credential-free deployment records; exact account/resource ownership; asynchronous provisioning/status/rollback; truthful terminal states.
3. Implement Azure AI model deployments, Container Instances, and container App Service with required artifacts and actual resource polling.
4. Implement GCP Vertex model attachment, Cloud Run, and source-based Functions with operations, authentic returned endpoints, and exact resource deletion.
5. Complete AWS model/container/function deployment, readiness, status and rollback; use official CLI sign-in per the accepted correction below.
6. Wire required configuration, authentication, progress, retry/recovery, and rollback into the desktop UI. Add provider protocol tests and real desktop tests with local/mock provider boundaries.
7. Address audit backlog: private execution/persistence, PyRIT verification, checkpoint recovery, PDF, legacy CLI estimation, runtime diagnostics, packaging, documentation/website discrepancies.
8. Run regression suites, static checks and builds; prepare concrete live-test plan once account identifiers and budget are supplied. No live cloud mutation has been authorized or performed by this worklog.

## Findings driving implementation

- App.tsx routes Export → deploy-config → deploy-compare → dry-run DeployExecutePage. DeployFlowPage is implemented but not connected to that path.
- Azure creates a resource group/account without deploying an OpenAI model; App Service fabricates a URL; partial errors may still be marked complete. Private networking is advertised without being provisioned.
- GCP Vertex creates an endpoint but attaches no model; Run reads a v1-style URL from an operation response; Functions has an empty source; status is a stub; rollback uses the wrong API for some resource types.
- AWS Lambda deploys stub code; SageMaker model creation/readiness and provider status require review.
- Original authentication borrowed third-party CLI OAuth client IDs and AWS sign-in was a placeholder. Replaced with official CLI subprocess authentication; custom OAuth/token exchange is disabled.
- Current provider plans list controls/resources that execution never creates. Plans must match actual actions.
- Existing backend tests do not exercise the actual cloud provider engines comprehensively.

## Verification boundaries

Local protocol tests can prove request shape, state transitions, failure behavior and rollback scope. They cannot prove cloud account permissions, quotas, billing, available model versions or regional capacity. Actual provisioning requires a reviewed plan and account-specific approval after implementation is concrete.

## Primary API references

- [Cloud Run v2 service creation](https://docs.cloud.google.com/run/docs/reference/rest/v2/projects.locations.services/create)
- [Cloud Run v2 service resource](https://docs.cloud.google.com/run/docs/reference/rest/v2/projects.locations.services)
- [Azure asynchronous operations](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/async-operations)

Status: investigation complete for the main deployment blockers; implementation in progress.

## Accepted authentication correction

User explicitly requires official CLI authentication only: AWS CLI >=2.32.0 (`aws login`, Identity Center option `aws sso login`), with Azure/GCP adapters behind CloudAuth (`check_cli`, `login`, `whoami`, `select_scope`, `logout`). Use system browser, isolated provider configuration, timeout/cancellation, display verified identity and account/region confirmation, and reverify before deploy. Never read/log/store/display tokens or credential files. No live login or deployment without explicit user approval. Custom OAuth implementation is prohibited; the newly drafted OAuth helper was removed before use. Existing provider OAuth entry points will be disabled/replaced.

Authentication does not need an application-owned redirect server: the official CLI owns browser authentication; successful subprocess completion triggers identity verification and foregrounds the app.

## Implemented on 2026-11-16

- Added `CloudAuth` and AWS adapter with CLI >=2.32.0 checking, console/Identity Center modes, system-browser authentication, remote terminal option, cancellation, timeout, sanitized diagnostics, verified identity, scope confirmation and official logout. Azure/GCP are disabled stubs with isolated configuration environments.
- Wired `CloudLoginPanel` into the live wizard; removed manual secret/token inputs and custom OAuth entry points. Electron restores/focuses the window after verified sign-in. The existing planning flow now links to sign-in and carries provider/region/mode/model choices forward.
- Deployment IPC ignores renderer credential payloads and uses verified public scope metadata. The Python AWS CLI transport duplicates the same isolation rules and independently reverifies STS identity immediately before provisioning.
- Replaced AWS placeholder resource creation with CloudFormation templates: real Bedrock Converse gateway plus enforced versioned guardrail, SageMaker model/artifact/endpoint, and Lambda image plus IAM-authenticated API Gateway. Required model/image/role inputs are exposed in the wizard. No stub inference handler or invented endpoint remains in the AWS path.
- Added atomic credential-free AWS journals; readiness polling, exact ownership checks, scoped stack deletion and restart recovery by deployment ID. Submission timeouts preserve intent and do not automatically create duplicate stacks.
- Explicitly reject unimplemented AWS private networking. Pricing is shown as unestimated; budget alerts are not falsely advertised as created. Azure/GCP backend routes are blocked until official CLI transport replaces legacy implementations. Earlier unconnected token-based HTTP workflow drafts were removed.

The AWS-first implementation is locally testable; live account/inference verification remains pending explicit approval. The earlier Azure/GCP and broader audit/release work is still outstanding, not silently marked complete.

See [CLOUD_SIGN_IN.md](CLOUD_SIGN_IN.md) for the concrete workflow, inputs, limitations and official references.

## Verification on 2026-11-16

- Full backend suite: **1255 passed, 4 skipped** (1259 collected). The first run caught a historical deployment-file allowlist test; the allowlist now includes the new CLI/template/journal modules and the full rerun passes.
- Frontend suite: **97 passed** across 11 files, including the real reducer/components from sign-in through account confirmation, plan review, deployment confirmation and status polling with mocked IPC.
- Electron/CLI subprocess tests: **13 passed**, including window foreground, renderer credential replacement, official-CLI invocation, missing/old CLI, policy failures, expiration, changed identity, timeout/cancel, remote terminal and SSO isolation.
- Frontend production build and Ruff undefined-name checks pass. Model artifacts and cloud responses in deployment tests are fixtures; these are not live cloud tests.
- Independently generated Bedrock/SageMaker/Lambda templates pass **cfn-lint 1.60.1** with exit code 0 and no diagnostics. Validator dependencies are isolated in ignored `.tools/cloud-validation`, not installed into the application runtime. `verify_cloud_templates.py` reproduces the examples without calling AWS.
