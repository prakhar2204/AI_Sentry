# Cloud sign-in and AWS deployment

Updated 2026-11-16. The desktop application uses the official AWS CLI, not an application-owned OAuth implementation. Azure and GCP implement the same interface as disabled stubs for the accepted AWS-first stage.

## Sign-in workflow

1. Follow the existing Export → Deployment Configuration → Cloud Comparison → Plan workflow. Choose **Continue to Account Sign-In**. The selected provider, region, mode and model settings carry forward.
2. Install AWS CLI **2.32.0 or newer** if the app reports it missing or old. Restart the app after installation so its PATH includes the CLI.
3. Choose **AWS console account** (`aws login`) or **IAM Identity Center** (`aws sso login`). Identity Center also requires its official start URL, account ID, role and region.
4. Sign in on the official website in the system browser. The CLI owns the browser callback. After the CLI exits successfully, the app verifies `aws sts get-caller-identity`, restores/focuses its window, and shows the ARN, account ID and region.
5. Confirm that identity and region. Before provisioning, a second confirmation screen shows the account, region and resource plan. Electron and the backend independently reverify identity before deployment.

The CLI callback returns control to the app through subprocess completion; there is no custom application callback URL or embedded webview. Closing the browser does not necessarily terminate the CLI: use **Cancel sign-in**, or wait for the five-minute login timeout. The app reports missing permissions, expired sessions and CLI errors without forwarding raw authentication output.

On Windows, **Remote / another-device sign-in** opens the official CLI in its own terminal with `aws login --remote` (or the Identity Center device-code option). Complete its prompts there. Authorization codes never pass through the application. This terminal-based remote option is not implemented for macOS/Linux yet.

## Session isolation

- Profiles are `sentryphi-console` and `sentryphi-sso` in the app's own cloud directory under Electron `userData`.
- AWS config, shared-credential and login-cache paths point into that directory; a child-only HOME/USERPROFILE isolates the SSO cache too. The app does not open or parse those files.
- Ambient AWS credentials, role overrides and custom endpoints are removed from the CLI child environment. The backend deployment CLI uses the same directory/profile and isolation rules.
- Only public identity/scope metadata crosses IPC. Login output is discarded; credential files and tokens are never read, logged, displayed or persisted by application code. The official CLI manages its own session storage.
- Sign-out invokes the official CLI against the isolated configuration. It does not sign out the user's ordinary CLI profiles or browser session.
- Azure and GCP have reserved isolated `AZURE_CONFIG_DIR` and `CLOUDSDK_CONFIG` environments. Their login/deployment routes are disabled until the corresponding adapters are implemented.

## AWS deployment modes

Deployment uses CloudFormation through the official CLI. Templates list actual resources and status remains in progress until AWS reports `CREATE_COMPLETE` with an endpoint output.

| Mode | Required inputs | Resources/behavior |
| --- | --- | --- |
| Bedrock | Converse-compatible model/inference-profile ID; existing Lambda execution role | Versioned guardrail, Lambda gateway and IAM-authenticated HTTP API (`POST /invoke`). Every request uses the configured model and guardrail. Text-only Converse messages are supported. |
| SageMaker | Compatible ECR inference image, S3 model archive, instance type, existing SageMaker execution role | Model, endpoint configuration and real-time endpoint. Container network isolation is enabled; model dependencies must be bundled. Invocation requires SigV4. |
| Lambda | Lambda-compatible ECR image containing the actual inference handler; existing execution role | Container function, HTTP API integration/route/stage and scoped invocation permission. Invocation requires SigV4. |

The signed-in identity needs CloudFormation/service permissions and `iam:PassRole`. Existing execution roles must trust the appropriate service and grant artifact/model access and logging permissions. Bedrock execution requires model invocation and guardrail permissions. Provisioning validation cannot prove the supplied role policy or container's inference behavior.

AWS private VPC networking is explicitly rejected rather than silently creating a public endpoint. Choose the public IAM-authenticated option explicitly to use these templates. HTTP API has a 30-second integration timeout. AWS Budgets, custom domains, model access grants and automatic role creation are not provisioned. The plan reports pricing as **Not estimated**, not zero cost.

## Recovery and removal

Copy the deployment ID (`sp-...`) shown during provisioning. Credential-free journals are written atomically under `userData/deployments`. After restarting and signing in to the same AWS account, enter the ID in **Resume an existing deployment**. Status reads the recorded stack's actual state.

Removal requires a checkbox and **Confirm removal**. The backend verifies account, region, exact stack ARN/name and deployment tags before requesting stack deletion. Deletion is asynchronous; refresh/poll until AWS confirms it. Existing roles, images and S3 artifacts are not owned or removed by this stack. A submission timeout preserves the deployment ID so refresh can reconcile the outcome without creating another stack.

## Verification boundary

Tests use mocked subprocesses/provider responses, including a full React deployment-wizard path and Electron foreground/identity checks. No live login, cloud account or deployment was used. Live deployment still requires the user's explicit approval, selected account/region, actual model artifacts and a reviewed spending limit. Template validation and unit tests cannot establish regional availability, quotas or real inference success.

Local verification: 1255 backend tests passed (4 skipped), 97 frontend tests passed, 13 Electron/auth tests passed, production frontend build passed, and all three generated templates passed cfn-lint 1.60.1. Use `start-sentryphi.cmd` for the updated source build; the older installed release has not been rebuilt.

## Official references

- [AWS browser sign-in](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html) and [login command / remote mode](https://docs.aws.amazon.com/cli/latest/reference/login/).
- [IAM Identity Center CLI configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).
- [CloudFormation SageMaker model](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-sagemaker-model.html).
- [CloudFormation Bedrock guardrail version](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrock-guardrailversion.html) and [Converse guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-converse-api.html).
- [HTTP API route authorization](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-apigatewayv2-route.html).
