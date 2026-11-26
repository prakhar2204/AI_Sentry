# Desktop milestones

| Phase | Deliverable | Evidence for completion |
| --- | --- | --- |
| 1. Scan evidence | Identify which engine actually ran. Compare finished Garak and PyRIT reports for the same model and scope, retain provenance and surface disagreement. | Two completed reports, a partial result, and a mismatched target produce distinguishable outcomes. |
| 2. Capacity | Explain weight storage, attention cache, context length and host/device memory budgets. Display measured capacity alongside estimates. | A local file shows model-specific assumptions. Endpoint scans identify where inference runs. |
| 3. Workspace | Bring the website’s spacing, typography and blue accents to the desktop workflow. Keep the current task and navigation visible on wide and narrow screens. | Agreement, input, estimates and results remain usable by keyboard in both themes. |
| 4. Updates | Check GitHub Releases at startup, persist automatic/manual preference, download in the background and restart safely. | An installed release can consume a newer installer and update manifest. In-progress work survives download and is never interrupted for installation. |
| 5. Cloud review | Document the existing AWS authentication and deployment path and review provider-supported options for future work. | A proposal can be reviewed separately before changing any provider implementation. |

## Implementation status, 25 November 2026

* Auto selects one installed engine, preferring Garak. The inspected development environment contains Garak 0.17.1. PyRIT is absent, and the verified scan requirements file omits it. Simultaneous attack execution is outside this implementation.
* The estimate view identifies available packages and the selected engine. Results can compare two completed SentryPhi JSON reports with matching scope and model identity, show the highest observed severity per category and export both engines’ evidence with deduplicated actions. Findings retain their original confidence. Historical endpoint reports may identify only the endpoint address.
* Local estimates follow the 4096-token, single-request runtime. For safetensors the estimator reads shard headers and accounts for the CPU runtime loading floating weights in FP32. For GGUF it shows artifact size, attention cache, CPU capacity and full-offload budget. Actual allocator peaks require measurement during inference.
* The shared desktop shell, agreement, model selection, estimate, scan activity and results now use the revised workspace layout. The startup updater and preferences are implemented. Distribution verification still requires a release-to-release installation test.

## Desktop release procedure

The Windows build uses NSIS and electron-updater. Increment the desktop package version (including its lockfile) before building an update. From app/frontend, use the backend build environment and run `npm run release:windows` with the release publisher's GitHub credentials and Windows signing certificate configured in the build environment. Review the draft, installer, blockmap and latest.yml together before publishing a stable release. The installed application reads the public release feed without a publishing token. Users of an older build that predates the updater need one installation of an updater-enabled build. macOS requires a signed app and the ZIP update artifact. Linux support targets AppImage.

The app checks on launch. With automatic updates off, a release is advertised and downloading requires a click. Downloads can proceed during work. Installation can restart an untouched startup session, or run on normal quit once the user has started working. Before distributing, install a signed build on a disposable machine, publish a higher version to a staging feed, cover automatic and manual settings, and confirm the version after restart.

## Cloud design review

The current Electron AWS login serves a loopback credential form. It validates credentials and passes them to the backend, which uses boto3 in token mode. For customers using IAM Identity Center, prefer short-lived role credentials from the AWS SDK SSO provider. This requires an Identity Center instance, an assigned account and role, and a region. Record these prerequisites during onboarding. Evaluate consumer account support separately before replacing a working AWS flow.

For Azure, register a desktop public client and use MSAL interactive sign-in with the system browser, then select a tenant and subscription. For GCP, use a Desktop OAuth client and the Google Auth library's loopback flow, then select a project. Bind the deployment confirmation to the selected identity and scope and check both again before provisioning. Provider and tenant setup, API permissions, refresh handling and account switching require separate integration tests before rollout.

References: [AWS SDK IAM Identity Center](https://docs.aws.amazon.com/sdkref/latest/guide/feature-sso-credentials.html), [Microsoft desktop interactive authentication](https://learn.microsoft.com/en-us/entra/identity-platform/scenario-desktop-acquire-token-interactive), [Google desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app), [electron-builder updates](https://www.electron.build/auto-update.html).
