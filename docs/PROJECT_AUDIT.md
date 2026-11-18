# Project understanding and repair status — 2026-11-15

> **2026-11-16 update:** AWS-first official CLI sign-in and CloudFormation deployment implementation supersede the historical cloud-authentication findings below. See [CLOUD_SIGN_IN.md](CLOUD_SIGN_IN.md) and [DEPLOYMENT_WORKLOG.md](DEPLOYMENT_WORKLOG.md). Custom OAuth is disabled; the app handles public identity metadata only. Azure/GCP are explicitly disabled stubs under the latest user instruction. Live login/deployment and the remaining release backlog are not claimed complete.

## What the project is

Sentryɸ is a desktop LLM security assessment application. It accepts a local GGUF model or an HTTP model endpoint, runs adversarial probes through existing engines, normalizes their findings, computes risk/confidence, and produces reports and deployment guidance. The core approach remains “wrap existing engines, normalize their results.” This repair preserves the application's workflow, visual design, supported categories, and scoring formula.

The repository contains a React/Vite/Electron desktop UI in `app/frontend`, a Python orchestration/CLI backend in `app/backend`, and a separate Next.js marketing website in `website`. `context/` and `docs/` contain multiple generations of plans. Some older documents describe Tauri, DeepTeam, AWS-only deployment, or completed features that do not match the current implementation. Treat their completion labels as historical planning records, not runtime proof.

This audit follows the live desktop scan and command paths, their adapters, state, process lifecycle, reports, and deployment interfaces, with targeted source review and automated verification. It is not a claim that every line of the repository or every historical document has been exhaustively reviewed. Website lint/build passed; browser behavior, cloud APIs, and every combination of model/provider/depth remain outside the demonstrated coverage.

## How the running app works

1. `ScanContext.tsx` holds consent, target, local model path, selected categories/depth/engine, API settings, and report state.
2. Agreement, Input, Config, and Estimate pages prepare the scan. `ScanPage.tsx` subscribes to progress through `ipcScanService.ts`.
3. Electron's preload exposes an IPC bridge. `electron/main.cjs` chooses the Python runtime, owns the scan subprocess, forwards JSON-line events, and handles cancellation and exit.
4. `ipc_server.py` builds the manifest and orchestrates the scan. For GGUF input, `local_model_server.py` starts llama.cpp and supplies its HTTP endpoint.
5. `engine_runner.py` selects an adapter. Auto currently selects Garak if installed, otherwise PyRIT; it does not run both in parallel. Explicit Mock remains a development option.
6. `garak_engine.py` invokes Garak in separate subprocesses per probe specification and parses its reports. The adapter converts evaluations into findings and excludes passing evaluations.
7. Normalization, scoring, recommendations, and report generation produce the shared report consumed by Results, Actions, Export, and deployment screens.
8. A separate persistent `backend-commands.cjs` worker handles deployment and export commands. Its sequential JSON-line protocol preserves plan/deployment state across commands without interfering with a scan.

Seven UI categories map to six Garak families: prompt injection, jailbreak, data leakage, encoding injection, malware generation, and toxicity. Harmful output and toxicity share the toxicity family. Quick selects one specification per family, Standard two, and Deep all 21 configured specifications. A specification can issue many model requests; these are different units of work.

## What is now demonstrated

| Area | Evidence and current status |
|---|---|
| Local GGUF scan | Actual desktop wizard completes all seven categories against Dolphin Phi; 58 model requests and rendered results |
| Engine compatibility | All 21 Garak specifications execute against a deterministic HTTP fixture; authenticated requests verified separately |
| Errors and cancellation | Regression coverage for missing model/engine, invalid endpoint, effect cleanup, and no silent mock fallback; process handling hardened |
| Inputs | Real reducer/file selection integration, editable HTTP URL, parsed manifest categories/depth, API key and model-name forwarding |
| Desktop scan estimates | Counts come from the selected engine's actual probe tables; shared families count once; unavailable engines fail before model startup |
| Results | Failed evaluations only, corrected unique-engine confidence corroboration, consistent gauge/report risk classification |
| Reports | JSON, HTML, and TXT exports verified through the persistent worker |
| Private deployment | Plan settings survive serialization; artifacts are isolated per deployment; status and scoped rollback verified in the same worker session |
| Cloud command plumbing | Persistent result transport; official AWS CLI sign-in with identity/account/region confirmation; CLI-backed CloudFormation deployment and durable ownership/status/removal. Azure/GCP routes are disabled pending CLI adapters. Live provisioning remains unverified. |
| Build/package metadata | Frontend build succeeds; Python editable install succeeds; source launcher uses the validated runtime |
| CLI health check | Checks actual package availability, Python, cached model server, and disk space; installed CLI and IPC module work from the repository root |

Detailed commands, environment, test results, and artifacts are in [SCAN_REPAIR.md](SCAN_REPAIR.md).

## Additional defects repaired during the audit

- Deployment UI previously reused the scan-start API and treated `{started: true}` as a deployment result. Dedicated commands now return the actual typed backend result.
- The old browser sign-in advanced without verified authentication. AWS now waits for official CLI completion and STS identity verification before account confirmation. The official CLI owns credential persistence; the app does not process tokens.
- Custom Azure/GCP token exchange was removed. Those providers remain disabled until their official CLI adapters replace the legacy provisioning paths.
- Deployment loading cleanup could erase an error immediately after showing it. Error state now survives the loading transition.
- Serialized plans lost `raw_config`; private deployment UI sent the wrong stack key. These contracts now agree.
- Recommendations read a nonexistent risk-score location and could treat every report as zero risk. They now use the report summary and current data-leak category name.
- Private artifact generation shared a directory with other output. Each deployment now owns its own directory and rollback is scoped to that owned directory.
- GCP rollback filtering matched all SentryPhi resources. Newly labeled Cloud Run/Function resources carry a deployment ID, and selection requires that exact ID. A mocked regression verifies unrelated resources are excluded; this is not proof of live GCP deletion behavior.
- Desktop estimates used unrelated four-category constants. A `scan:estimate` command now reads the selected engine's probe tables, recognizes all categories, and avoids double-counting shared families. The scan bridge waits for this plan before model startup and respects cancellation during planning. Unmeasured duration, API pricing, and VRAM requirements are displayed as dependent on the model/provider instead of invented fixed values.
- The CLI failed at import because engine type annotations referenced missing names, and Windows redirected output could not encode the product name. Engine imports and UTF-8 output are repaired. Package discovery now includes the report service and top-level IPC/export modules, so the installed entry point works outside the backend directory.
- The health-check command returned success without checking anything. It now reports required and optional dependencies and returns failure when a real scan engine or HTTP client is absent. This is a local prerequisite check, not a GPU benchmark or cloud credential validation.

## Remaining work, ordered by release impact

1. **Package and verify the repaired Windows release.** The existing installer still contains older code. PyInstaller must include Garak's dynamic plugins/data and a usable model server; test on a machine without the development environment. Until then use `start-sentryphi.cmd`.
2. **Calibrate duration/cost and migrate legacy CLI estimates.** Desktop probe counts now come from the selected engine. Probe specifications are not individual inference requests. Duration/cost prediction still needs measured throughput, token usage, and provider pricing. The separate legacy CLI estimator still uses its earlier baseline constants; it is not used by the repaired desktop estimate.
3. **Validate PyRIT independently.** Its adapter wiring was corrected and unit coverage exists, but the package was not installed or run in this environment. Parallel dual-engine orchestration is not implemented; the Auto description has been corrected to match current selection behavior.
4. **Finish and live-verify cloud deployment.** AWS CLI authentication and CloudFormation paths have offline coverage for Bedrock gateway/guardrails, SageMaker artifacts and Lambda images. Actual account permissions, regional quotas and inference still require explicit live-test approval. AWS private networking, account-specific pricing and automatic budget provisioning are unfinished. Azure/GCP CLI adapters and replacement provisioning remain deferred under the latest AWS-first instruction. No real cloud resources were created.
5. **Persist remaining ownership and scan recovery.** AWS journals now survive app restarts and bind removal to exact stack/account/region/tags. Private deployment tracking still lives in worker memory. Scan checkpoint/resume is not implemented. AWS session storage belongs to the official CLI, not an application keychain.
6. **Verify native PDF export.** Existing fallback behavior can produce HTML where a native PDF renderer is unavailable. JSON/HTML/TXT have integration evidence; native PDF output does not.
7. **Extend health diagnostics.** Local prerequisite checks are implemented. Driver compatibility, usable model capacity, engine dependency imports, and provider connectivity still require runtime checks; package discovery alone cannot prove these.
8. **Broaden hardware and model testing.** The demonstrated configuration is one Windows NVIDIA/Vulkan GGUF setup. CPU-only, other GPUs/operating systems, larger models, real remote providers, and full Deep inference against the user's model still need coverage. First-time detector dependencies may download data and take longer.
9. **Reconcile historical documentation and website claims.** The context status files now point to this audit, but old phase completion claims remain archived below that notice. The website passed lint and production build; its content and browser behavior were not exhaustively reviewed or changed. Next.js reports a nonfatal workspace-root warning because there are multiple lockfiles.

The scan's core failure is reproduced, corrected, and verified through the actual desktop workflow. The evidence does not support calling the entire multi-cloud product complete or free of all possible errors.
