# SentryPhi backend

Python orchestration for the Electron desktop application's scan, report, and deployment workflows.

Use Python 3.12 and install `requirements-scan.txt` for the validated Garak runtime.
From the repository root, `start-sentryphi.cmd` launches the desktop app using `.venv`.
The IPC server accepts JSON through stdin; local GGUF targets are loaded by llama.cpp
before Garak receives an HTTP chat-completions endpoint.

Run `python -m pytest` from this directory.
`verify_engine_contract.py` tests probe compatibility using a deterministic local endpoint;
it does not assess a real model. `verify_local_scan.py` exercises a real GGUF model.

See `../../docs/SCAN_REPAIR.md` for verification evidence and current limitations.
