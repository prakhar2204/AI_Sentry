# Sentryɸ — Build & Distribution Guide

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Node.js | ≥ 18 | [nodejs.org](https://nodejs.org) |
| Python | ≥ 3.10 | System-installed or virtualenv |
| npm | ≥ 9 | Bundled with Node.js |
| garak | ≥ 0.16.0 | `pip install garak` |
| pyrit | = 1.1.0 | `pip install pyrit==1.1.0` |

---

## Development (no build step)

```bash
# 1. Install Node dependencies
cd app/frontend
npm install

# 2. Install Python dependencies
cd ../backend
pip install -e ".[dev]"

# 3. Start Vite dev server + Electron (in one command)
cd ../frontend
npm run dev:electron
```

> The app loads at `http://localhost:5173` (Vite) while Electron opens a window pointing to it.  
> Backend Python is launched on-demand by Electron via `python -m ipc_server`.

---

## Production Build

### Step 1 — Bundle Python backend

```bash
cd app/frontend
python scripts/build-python.py
```

This runs PyInstaller on `app/backend/ipc_server.py` and produces a standalone executable at `app/frontend/dist_python/ipc_server[.exe]`, then copies it to `resources/backend/`.

**Engine availability in the bundle:**
- `MockEngine` — always included (no external deps)
- `GarakAdapter` — included if `garak` is installed at build time
- `PyRITAdapter` — included if `pyrit` is installed at build time

To check which engines will be bundled before building:
```bash
python scripts/build-python.py --check
```

### Step 2 — Build Electron app + installer

```bash
npm run build:electron
```

Output: `app/frontend/release/`

| Platform | Output |
|----------|--------|
| Windows  | `release/Sentryphi Setup 1.0.0.exe` (NSIS installer) |
| macOS    | `release/Sentryphi-1.0.0.dmg` |
| Linux    | `release/Sentryphi-1.0.0.AppImage` |

### One-command full build

```bash
npm run build:all
```

This runs `build:python` then `build:electron`.

---

## Installer Contents

The NSIS installer (Windows) installs:
- `%LOCALAPPDATA%\Sentryphi\` — Electron app
- `resources\backend\ipc_server.exe` — bundled Python runtime (all engines)
- `resources\backend_src\` — Python source fallback
- Desktop shortcut: **Sentryphi**
- Start menu: **Sentryphi**
- Uninstaller registered in Add/Remove Programs

---

## First-launch experience

On first launch, the app checks:
1. ✓ Python backend (bundled exe or system Python)
2. ✓ Garak engine (if bundled)
3. ✓ PyRIT engine (if bundled)
4. Shows dependency status before allowing the user to start scanning

If an engine is missing, the app falls back gracefully to **MockEngine** and warns the user.

---

## Build scripts reference

| Script | Description |
|--------|-------------|
| `npm run dev` | Vite dev server only |
| `npm run dev:electron` | Vite + Electron (full dev mode) |
| `npm run build` | TypeScript check + Vite build |
| `npm run build:python` | PyInstaller bundle |
| `npm run build:electron` | Electron app + installer |
| `npm run build:all` | Python bundle + Electron |
| `npm run dist` | Alias for `build:all` |
| `npm run preview` | Preview the Vite production build |

---

## Troubleshooting

### `wait-on` times out
Vite must start before Electron. If `dev:electron` fails, ensure port 5173 is free:
```bash
netstat -ano | findstr 5173
```

### PyInstaller fails
Ensure all Python deps are installed and PyInstaller is available:
```bash
pip install pyinstaller>=6.0
python scripts/build-python.py --check
```

### Garak/PyRIT not available in bundled app
These engines must be installed in the **same Python environment** that runs `build:python`.
```bash
pip install garak>=0.16.0 pyrit==1.1.0
npm run build:python
```

### App shows "Python not found" in production
Verify the PyInstaller bundle was copied:
```bash
ls app/frontend/resources/backend/
# Should show: ipc_server.exe (Windows) or ipc_server (Linux/Mac)
```

---

## Engine roadmap

| Engine | Status | Notes |
|--------|--------|-------|
| MockEngine | ✅ Always bundled | Deterministic test data |
| GarakAdapter | ✅ Bundled when installed | NVIDIA garak 0.16+ |
| PyRITAdapter | ✅ Bundled when installed | Microsoft PyRIT 1.1.0 |
| AgentGuardian | 🔜 Future | After garak + pyrit stable |

---

*Last updated: November 2026*
