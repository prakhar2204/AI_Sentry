# Local scan repair — 2026-11-15

## Run the corrected application

Close the previous desktop window and run [start-sentryphi.cmd](../start-sentryphi.cmd) from the repository root. It builds the React UI, then opens Electron against the current backend source using the project's `.venv` Python 3.12 environment. It does not require a separate Vite server. The old installer has **not** been rebuilt and does not contain these fixes.

The current workspace has the required scanner dependencies installed. For a fresh checkout, create `.venv` with Python 3.12, install `app/backend/requirements-scan.txt`, and run `npm ci` in `app/frontend`. PyRIT is optional and was not installed or live-tested in this repair. Garak is pinned to 0.17.1.

## Why the scan failed

The file picker dispatched `SET_LOCAL_MODEL_PATH`, but the scan reducer did not handle it. The selected GGUF path therefore never reached the model loader as `local_model_path`. Garak received `F:\models\dolphin-phi.gguf` as an HTTP endpoint, producing the reported `No connection adapters were found` error. A subprocess return code of zero did not mean evaluations had actually run.

The UI action, reducer, scan configuration, and backend fallback now preserve and recognize local model paths. The backend starts llama.cpp, waits for its HTTP health endpoint, and passes its chat-completions URL to Garak. A file path passed directly to Garak is rejected clearly. API endpoints retain their query parameters when their completion path is normalized.

Additional failures repaired:

- React StrictMode cancelled the initial scan effect while a retained start flag prevented its replacement. Cleanup now resets that flag and controller.
- Electron could select system Python 3.15 without scanner packages. Development now discovers `.venv`, with `SENTRYPHI_PYTHON` available as an override.
- Missing engines and model startup errors could fall back to simulated results. Auto now requires a real installed engine; Mock must be explicitly selected.
- IPC now handles spawn/stdin errors, startup silence, process exit without completion, and stale events. Windows cancellation terminates the owned scan process tree.
- Model startup waits for readiness, detects early exit, drains logs continuously, and releases the owned server on completion or failure.
- Progress uses actual probe specifications and category aliases. Harmful output and toxicity share one underlying family, with progress sent to both selected UI rows.
- Passing evaluations are excluded from vulnerabilities. No-evaluation runs fail explicitly. Duplicate records from one engine no longer receive a cross-engine confidence boost.
- Quick jailbreak uses the cap-aware `DanInTheWild` probe. Some other probe implementations still exceed the soft prompt cap, so probe-specification counts are distinct from inference-request counts.
- Garak errors retain useful diagnostics without ANSI clutter. JSON-formatted YAML safely quotes configuration values. API keys reach Garak through its `REST_API_KEY` environment variable rather than temporary configuration files.
- First-use consent advances with one acceptance click. API URL editing, model/API-key forwarding, and manifest parsing are repaired.
- Results gauges use the report's risk classification. The underlying scoring formula is unchanged.
- Desktop estimates read the selected engine's probe tables. Shared categories count once; cancellation during planning prevents model startup. Fixed time, price, and VRAM guesses were removed, and the local-model notice now explains automatic server startup.
- CLI health checks now report actual prerequisites. Missing engine imports, Windows output encoding, and incomplete Python package discovery were corrected; the installed CLI and IPC module work outside the backend folder.

## Verification

Machine: Windows, RTX 4050 Laptop, Vulkan llama.cpp, `F:\models\dolphin-phi.gguf`.

| Check | Result |
|---|---|
| Actual desktop wizard, fresh profile, prompt injection | Consent → native model selection → configuration → real scan → results succeeded |
| Actual desktop wizard, all seven categories, Quick | Latest run: six estimated and executed probe specifications, 58 real model requests, 547 stdout events, two findings, no engine error, approximately 167 seconds of engine execution |
| All 21 configured Garak probe specifications, Deep | 274 requests to a deterministic local HTTP fixture, no errors |
| Authenticated HTTP fixture, three injection probes | Three requests, zero authentication failures, no errors |
| Frontend suite | 91 tests passed |
| Frontend production build | TypeScript and Vite passed |
| Website | ESLint and Next.js production build passed; nonfatal multiple-lockfile workspace-root warning |
| Backend suite | 1,232 passed, four skipped; includes scan-plan, health, and repair regressions |
| Python static checks | Ruff undefined-name/local/export checks passed across backend and frontend Python scripts; compilation checks passed |
| Backend command worker | Real scan plan, private plan, validation, confirmation gate, artifact creation, status, scoped rollback, JSON/HTML/TXT export passed |
| Python package installation | Editable installation succeeded after correcting the build backend and adding the missing README |

All repair regressions are under `app/backend/tests/` and included in default pytest discovery. The erroneous Git ignore entry for that directory was removed so new tests remain reviewable.

Desktop automation uses the actual Electron main process, preload, React pages, Python IPC, Garak, and llama.cpp. Only the native file-picker response is supplied automatically. Results navigation was asserted through the rendered DOM. A hidden-window screenshot can capture a stale paint; it is not the sole evidence of results navigation.

During real inference, the separate `llama-server.exe` process used approximately 2.4 GB working-set RAM and 3.1 GB GPU memory; GPU utilization reached 91%. Memory need not appear under Electron, and utilization naturally falls between requests.

Evidence (generated locally, ignored by Git):

- `scan_artifacts/desktop-verification/report.json`: configuration, request count, and real report.
- `scan_artifacts/desktop-verification/results.txt`: rendered results DOM text.
- `scan_artifacts/desktop-verification/run.log`: desktop verification output.
- `scan_artifacts/command-verification/`: command/export verification artifacts.
- `app/backend/scan_artifacts/contract/`: Garak reports from deterministic compatibility tests.

The deterministic fixture verifies engine integration, not model security. The desktop test uses the real model. Quick mode is a sample, not exhaustive coverage; the complete Deep probe set was exercised against the fixture, not this GGUF model.

## Reproduce

From the repository root:

```powershell
node app/frontend/scripts/run-desktop-verification.cjs F:\models\dolphin-phi.gguf prompt_injection,jailbreak,data_leak,harmful_output,encoding_injection,malware_generation,toxicity
node app/frontend/scripts/verify-backend-commands.cjs
```

Build the frontend before the desktop verification script when UI source changes. From `app/backend`:

```powershell
..\..\.venv\Scripts\python.exe -m pytest
..\..\.venv\Scripts\python.exe verify_engine_contract.py
..\..\.venv\Scripts\python.exe verify_engine_contract.py --categories prompt_injection --check-auth
```

See [PROJECT_AUDIT.md](PROJECT_AUDIT.md) for the architecture and remaining release work. Cloud provisioning, PyRIT, packaged installers, and other operating systems are not established as working by these checks.
