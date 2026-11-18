/**
 * Sentryɸ — Electron Main Process
 * electron/main.cjs
 *
 * Entry point for the Electron desktop shell.
 *
 * Dual-mode:
 *   Development: loads http://localhost:5173 (Vite dev server)
 *   Production:  loads dist/index.html (built bundle)
 *
 * Mode detection:
 *   - ELECTRON_DEV env var set → development
 *   - app.isPackaged → production
 */

'use strict';

// ── Global crash protection ─────────────────────────────────────────
// Prevent Electron from showing fatal "A JavaScript error occurred in the
// main process" dialogs when spawn ENOENT or AbortSignal errors bubble up.
process.on('uncaughtException', (err) => {
  console.error('[main] Uncaught exception (handled gracefully):', err?.message || err);
});
process.on('unhandledRejection', (reason) => {
  console.error('[main] Unhandled rejection (handled gracefully):', reason?.message || reason);
});

const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const readline = require('readline');
const fs = require('fs');
const { BackendCommands } = require('./backend-commands.cjs');
const { AwsCloudAuth, AzureCloudAuth, GcpCloudAuth } = require('./cloud-auth.cjs');

// ─────────────────────────────────────────────
//  Environment
// ─────────────────────────────────────────────

const isDev = process.env.ELECTRON_DEV === '1' || !app.isPackaged;
const DEV_URL = 'http://localhost:5173';

// ─────────────────────────────────────────────
//  Active scan process reference
// ─────────────────────────────────────────────

let scanProcess = null;
let mainWindow = null;
const cloudAuthMap = new Map();
function getCloudAuth(provider) {
  if (!['aws', 'azure', 'gcp'].includes(provider)) throw new Error('Unsupported cloud provider');
  if (!cloudAuthMap.has(provider)) {
    const options = {
      onProgress: event => {
        if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('cloud-auth:progress', event);
      },
      openExternal: url => shell.openExternal(url),
    };
    const AuthClass = provider === 'aws' ? AwsCloudAuth : provider === 'azure' ? AzureCloudAuth : GcpCloudAuth;
    cloudAuthMap.set(provider, new AuthClass(options));
  }
  return cloudAuthMap.get(provider);
}
function focusApplication() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show(); mainWindow.focus();
  }
}
ipcMain.handle('cloud-auth:command', async (_event, config) => {
  try {
    const auth = getCloudAuth(config?.provider);
    if (!['check_cli', 'login', 'whoami', 'select_scope', 'logout', 'cancel'].includes(config?.action))
      throw new Error('Unsupported authentication action');
    const result = await auth[config.action](config.options || {});
    if (config.action === 'login') focusApplication();
    return { ok: true, result: result ?? { cancelled: true } };
  } catch (error) {
    return { ok: false, code: error.code || 'AUTH_FAILED', message: error.message };
  }
});
const backendCommands = new BackendCommands(() => {
  const executable = findPython();
  const bundled = /ipc_server(?:\.exe)?$/.test(executable);
  return { executable, args: bundled ? [] : ['-m', 'ipc_server'],
    options: { cwd: bundled ? path.dirname(executable) : getBackendPath(),
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1',
        SENTRYPHI_DATA_DIR: app.getPath('userData'), SENTRYPHI_CLOUD_AUTH_ROOT: path.join(app.getPath('userData'), 'cloud') } } };
}, async url => {
  if (typeof url !== 'string' || !url.startsWith('https://')) throw new Error('Invalid authentication URL');
  await shell.openExternal(url);
});

ipcMain.handle('backend:command', async (_event, config) => {
  if (!config || !(String(config.command).startsWith('deploy:') || ['scan:estimate', 'model:inspect', 'model:download', 'model:download_status', 'model:download_cancel', 'cloud:recommend'].includes(config.command))) throw new Error('Unsupported backend command');
  if (config.command.startsWith('deploy:') && config.provider !== 'private') {
    const auth = getCloudAuth(config.provider);
    if (!auth.scope) throw new Error('Sign in and confirm your cloud account first');
    // Pass credentials as env vars to the Python backend (no CLI needed)
    const credentialsEnv = auth.getCredentialsEnv();
    config = { ...config, credentials: {
      auth_mode: 'token',
      account_id: auth.scope.account,
      identity: auth.scope.identity,
      region: auth.scope.region,
      env: credentialsEnv,
    } };
  }
  return backendCommands.run(config);
});

// ─────────────────────────────────────────────
//  Window creation
// ─────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 700,
    title: 'Sentryɸ — LLM Security Platform',
    backgroundColor: '#0a0a0b',
    show: false, // Show after content loads to avoid white flash
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  // Remove native menu bar on Windows/Linux
  mainWindow.setMenu(null);

  if (isDev && process.env.SENTRYPHI_USE_BUILD !== '1') {
    // Load Vite dev server
    mainWindow.loadURL(DEV_URL);
    // Open DevTools in development
    // mainWindow.webContents.openDevTools();
  } else {
    // Load built bundle with Content-Security-Policy
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));

    mainWindow.webContents.session.webRequest.onHeadersReceived(
      (details, callback) => {
        callback({
          responseHeaders: {
            ...details.responseHeaders,
            'Content-Security-Policy': [
              "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com;"
            ],
          },
        });
      }
    );
  }

  // Show window once content is ready (no white flash)
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Clean up scan process on window close
  mainWindow.on('closed', () => {
    killScanProcess();
    mainWindow = null;
  });
}

// ─────────────────────────────────────────────
//  Python utilities
// ─────────────────────────────────────────────

/** Find the Python executable on the system */
function findPython() {
  if (process.env.SENTRYPHI_PYTHON) return process.env.SENTRYPHI_PYTHON;
  const projectPython = path.join(__dirname, '../../../.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  if (isDev && fs.existsSync(projectPython)) return projectPython;
  // In production, check for bundled PyInstaller executable first
  if (!isDev) {
    // PyInstaller single-file bundle
    const bundledExe = path.join(process.resourcesPath, 'backend', 'ipc_server.exe');
    if (fs.existsSync(bundledExe)) return bundledExe;
    const bundledBin = path.join(process.resourcesPath, 'backend', 'ipc_server');
    if (fs.existsSync(bundledBin)) return bundledBin;
    // Embedded Python
    const embeddedPy = path.join(process.resourcesPath, 'python', 'python.exe');
    if (fs.existsSync(embeddedPy)) return embeddedPy;
    const embeddedPy3 = path.join(process.resourcesPath, 'python', 'python');
    if (fs.existsSync(embeddedPy3)) return embeddedPy3;
  }
  // Development: use system Python
  return process.platform === 'win32' ? 'python' : 'python3';
}

function getBackendPath() {
  if (isDev) {
    // Development: backend source is at ../../backend relative to electron/
    return path.join(__dirname, '../../backend');
  }
  // Production: prefer raw backend_src (always bundled)
  const srcPath = path.join(process.resourcesPath, 'backend_src');
  if (fs.existsSync(srcPath)) return srcPath;
  // Fallback: old layout
  return path.join(process.resourcesPath, 'backend');
}

function killScanProcess() {
  if (scanProcess) {
    const child = scanProcess;
    scanProcess = null;
    try {
      if (process.platform === 'win32' && child.pid) {
        const killer = spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { windowsHide: true });
        killer.on('error', () => child.kill());
      } else {
        child.kill('SIGTERM');
      }
    } catch (_) {}
  }
}

// ─────────────────────────────────────────────
//  IPC Handlers
// ─────────────────────────────────────────────

/** scan:start — spawn Python IPC server and stream progress */
ipcMain.handle('scan:start', async (event, config) => {
  // Kill any existing scan
  killScanProcess();

  const pythonPath = findPython();
  const backendPath = getBackendPath();

  console.log('[scan:start] ========== SCAN STARTING ==========');
  console.log('[scan:start] pythonPath:', pythonPath);
  console.log('[scan:start] backendPath:', backendPath);
  console.log('[scan:start] mainWindow exists:', !!mainWindow);

  try {
    // Detect if pythonPath IS the bundled ipc_server executable (PyInstaller)
    const isBundledExe = pythonPath.endsWith('ipc_server.exe') || pythonPath.endsWith('ipc_server');
    const spawnArgs  = isBundledExe ? [] : ['-m', 'ipc_server'];
    const spawnCwd   = isBundledExe ? path.dirname(pythonPath) : backendPath;

    console.log('[scan:start] spawnArgs:', spawnArgs);
    console.log('[scan:start] spawnCwd:', spawnCwd);

    const child = spawn(pythonPath, spawnArgs, {
      cwd: spawnCwd,
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONUTF8: '1' },
    });
    scanProcess = child;
    let terminal = false;
    let stderrTail = '';
    const fail = (message) => {
      if (terminal || scanProcess !== child) return;
      terminal = true;
      mainWindow?.webContents.send('scan:error', {type: 'error', message, code: 'PROCESS_ERROR'});
    };
    child.on('error', (err) => fail(`Cannot start scan backend: ${err.message}`));
    child.stdin.on('error', (err) => fail(`Cannot send scan configuration: ${err.message}`));
    const startupTimer = setTimeout(() => {
      fail('Scan backend did not respond within 60 seconds. Check the Python environment.');
      if (scanProcess === child) killScanProcess();
    }, 60000);
    child.once('close', () => clearTimeout(startupTimer));
    child.stderr.on('data', (data) => { stderrTail = (stderrTail + data.toString()).slice(-4000); });

    console.log('[scan:start] Python spawned, PID:', scanProcess.pid);

    // Write config to Python stdin
    const configJson = JSON.stringify(config) + '\n';
    scanProcess.stdin.write(configJson);
    scanProcess.stdin.end();
    console.log('[scan:start] Config written to stdin:', configJson.length, 'bytes');

    // Stream stdout line-by-line (JSON Lines protocol)
    const rl = readline.createInterface({ input: scanProcess.stdout });
    let lineCount = 0;
    rl.on('line', (line) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      lineCount++;
      if (lineCount <= 5) {
        console.log('[scan:stdout line', lineCount, ']', trimmed.substring(0, 120));
      }
      try {
        const evt = JSON.parse(trimmed);
        if (scanProcess !== child) return;
        clearTimeout(startupTimer);
        // Always use mainWindow — getFocusedWindow() returns null when the user
        // has any other window focused (alt-tab, clicking elsewhere), which would
        // silently drop ALL scan events leaving the UI stuck at "Preparing... 0%".
        const win = mainWindow;
        if (!win || win.isDestroyed()) {
          console.warn('[scan:start] mainWindow gone, dropping event:', evt.type);
          return;
        }

        switch (evt.type) {
          case 'progress':
          case 'finding':
          case 'activity':
          case 'stage':
            win.webContents.send('scan:progress', evt);
            break;
          case 'complete':
            terminal = true;
            win.webContents.send('scan:complete', evt);
            break;
          case 'error':
            terminal = true;
            win.webContents.send('scan:error', evt);
            break;
        }
      } catch (_) {
        // Non-JSON line (e.g. Python warnings) — ignore
        console.warn('[IPC stdout non-JSON]', line);
      }
    });

    // Log Python stderr (useful for debugging)
    scanProcess.stderr.on('data', (data) => {
      console.error('[Python stderr]', data.toString());
    });

    child.on('close', (code) => {
      console.log('[scan:start] Python exited with code:', code, '| stdout lines received:', lineCount);
      const win = mainWindow;
      if (!terminal && scanProcess === child && win && !win.isDestroyed()) {
        win.webContents.send('scan:error', {
          type: 'error',
          message: `Scan backend exited before completing (code ${code}). ${stderrTail}`,
          code: 'PROCESS_EXIT',
        });
      }
      if (scanProcess === child) scanProcess = null;
    });

    console.log('[scan:start] Listeners attached, returning started=true');
    return { started: true };
  } catch (err) {
    console.error('[scan:start] SPAWN ERROR:', err);
    return { started: false, error: err.message };
  }
});

/** scan:cancel — send SIGTERM to the running Python process */
ipcMain.handle('scan:cancel', async () => {
  killScanProcess();
  return { cancelled: true };
});

/** report:save — write report data to file (legacy browser-compat path) */
ipcMain.handle('report:save', async (event, data, format) => {
  const ext = format === 'pdf' ? 'pdf' : format === 'html' ? 'html' : format === 'txt' ? 'txt' : 'json';
  const { filePath, canceled } = await dialog.showSaveDialog(mainWindow, {
    title: 'Save Scan Report',
    defaultPath: `sentryphi-report.${ext}`,
    filters: [{ name: `${format.toUpperCase()} File`, extensions: [ext] }],
  });

  if (canceled || !filePath) return { saved: false };

  try {
    const content = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    fs.writeFileSync(filePath, content, 'utf-8');
    return { saved: true, filePath };
  } catch (err) {
    return { saved: false, error: err.message };
  }
});

/**
 * report:export — Full Python-backed export.
 * 1. Opens native save dialog
 * 2. Spawns Python export_handler.py via subprocess
 * 3. Returns { saved: boolean, filePath?, size_bytes?, fallback?, error? }
 */
ipcMain.handle('report:export', async (event, reportData, format) => {
  const FORMAT_EXTS = { json: 'json', html: 'html', txt: 'txt', pdf: 'pdf' };
  const ext = FORMAT_EXTS[format] || 'json';
  const formatLabel = format.toUpperCase();

  const { filePath, canceled } = await dialog.showSaveDialog(mainWindow, {
    title: `Save Scan Report as ${formatLabel}`,
    defaultPath: `sentryphi-report.${ext}`,
    filters: [
      { name: `${formatLabel} Report`, extensions: [ext] },
      { name: 'All Files', extensions: ['*'] },
    ],
  });

  if (canceled || !filePath) return { saved: false };

  try {
    const result = await backendCommands.run({ command: 'report:export',
      format, output_path: filePath, report: reportData });
    return { saved: result.success, filePath: result.path, size_bytes: result.size_bytes,
      fallback: result.fallback || null, error: result.error || null };
  } catch (error) {
    return { saved: false, error: error.message };
  }
});

/** shell:openPath — open a file with the default OS application */
ipcMain.handle('shell:openPath', async (event, filePath) => {
  const error = await shell.openPath(filePath);
  return { success: !error, error: error || null };
});

/** shell:openFolder — reveal a file in the OS file explorer */
ipcMain.handle('shell:openFolder', async (event, filePath) => {
  shell.showItemInFolder(filePath);
  return { success: true };
});

/** shell:openExternal — open a URL in the system default browser (OAuth flows) */
ipcMain.handle('shell:openExternal', async (event, url) => {
  // Security: only allow https:// URLs to prevent protocol exploitation
  if (typeof url !== 'string' || !url.startsWith('https://')) {
    return { success: false, error: 'Only https:// URLs are permitted' };
  }
  try {
    await shell.openExternal(url);
    return { success: true };
  } catch (err) {
    return { success: false, error: String(err) };
  }
});

/** dialog:save — open native save dialog and return chosen path */
ipcMain.handle('dialog:save', async (event, options) => {
  const result = await dialog.showSaveDialog(mainWindow, options || {});
  return result.canceled ? null : result.filePath;
});

/**
 * dialog:open-model-file -- open native Windows file picker for .gguf model files.
 * Returns the REAL full disk path (e.g. D:\\models\\dolphin-phi.gguf).
 * The browser File API can only return the filename, not the full path --
 * this IPC call is required for the Python backend to actually load the file.
 *
 * Returns: { filePath, fileName } or null if cancelled.
 */
ipcMain.handle('dialog:open-model-file', async (_event, folder = false) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: folder === true ? 'Select Transformers Model Folder' : 'Select Model File',
    buttonLabel: 'Select Model',
    filters: [
      { name: 'Model Files', extensions: ['gguf', 'safetensors'] },
      { name: 'All Files', extensions: ['*'] },
    ],
    properties: [folder === true ? 'openDirectory' : 'openFile'],
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  const fullPath = result.filePaths[0];
  const fileName = require('path').basename(fullPath);
  return { filePath: fullPath, fileName };
});


/** system:python-version — get Python version string */
ipcMain.handle('system:python-version', async () => {
  return new Promise((resolve) => {
    const py = findPython();
    const proc = spawn(py, ['--version'], { stdio: ['pipe', 'pipe', 'pipe'] });
    let version = '';
    proc.stdout.on('data', (d) => { version += d.toString(); });
    proc.stderr.on('data', (d) => { version += d.toString(); }); // Python 2 prints to stderr
    proc.on('exit', () => resolve(version.trim() || 'unknown'));
    proc.on('error', () => resolve('not found'));
  });
});

/** system:app-version — get Electron app version */
ipcMain.handle('system:app-version', async () => {
  return app.getVersion();
});

/**
 * system:gpu-info — Query NVIDIA GPU info via nvidia-smi.
 * Returns { available, name, vram_total_mb, vram_free_mb, utilization_pct, driver_version }
 * Falls back to { available: false } if no NVIDIA GPU or nvidia-smi not found.
 */
ipcMain.handle('system:gpu-info', async () => {
  return new Promise((resolve) => {
    const args = [
      '--query-gpu=name,memory.total,memory.free,utilization.gpu,driver_version',
      '--format=csv,noheader,nounits',
    ];
    const proc = spawn('nvidia-smi', args, { stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });
    proc.on('exit', (code) => {
      if (code !== 0 || !stdout.trim()) {
        resolve({ available: false, error: stderr.trim() || 'No NVIDIA GPU detected' });
        return;
      }
      try {
        const parts = stdout.trim().split(',').map(s => s.trim());
        resolve({
          available:        true,
          name:             parts[0] || 'Unknown GPU',
          vram_total_mb:    parseInt(parts[1], 10) || 0,
          vram_free_mb:     parseInt(parts[2], 10) || 0,
          utilization_pct:  parseInt(parts[3], 10) || 0,
          driver_version:   parts[4] || 'unknown',
        });
      } catch (err) {
        resolve({ available: false, error: String(err) });
      }
    });
    proc.on('error', () => {
      resolve({ available: false, error: 'nvidia-smi not found — no NVIDIA GPU or driver not installed' });
    });
    setTimeout(() => {
      try { proc.kill(); } catch (_) {}
      resolve({ available: false, error: 'GPU query timed out' });
    }, 5000);
  });
});

/**
 * system:health-check — W6.3 First-Launch Health Check
 *
 * Returns a detailed status object for all backend components:
 *   - python:  version string or 'not found'
 *   - backend: 'available' | 'not found' (IPC server entry point)
 *   - engines: { mock, garak, pyrit } availability
 *   - bundled: true if running from PyInstaller .exe
 *   - paths:   { python, backend } resolved paths
 *
 * The frontend uses this on first launch to show a startup status screen.
 * If garak/pyrit unavailable → shows warning but allows scan with MockEngine.
 */
ipcMain.handle('system:health-check', async () => {
  const pythonPath  = findPython();
  const backendPath = getBackendPath();
  const isBundled   = pythonPath.endsWith('ipc_server.exe') || pythonPath.endsWith('ipc_server');

  // 1. Python version
  const pythonVersion = await new Promise((resolve) => {
    if (isBundled) { resolve('bundled'); return; }
    const proc = spawn(pythonPath, ['--version'], { stdio: ['pipe', 'pipe', 'pipe'] });
    let ver = '';
    proc.stdout.on('data', (d) => { ver += d.toString(); });
    proc.stderr.on('data', (d) => { ver += d.toString(); });
    proc.on('exit', () => resolve(ver.trim() || 'unknown'));
    proc.on('error', () => resolve('not found'));
  });

  // 2. Backend (IPC server) availability
  let backendAvailable = false;
  if (isBundled) {
    backendAvailable = true;
  } else {
    const ipcEntry = path.join(backendPath, 'ipc_server.py');
    backendAvailable = fs.existsSync(ipcEntry);
  }

  // 3. Engine availability — ask the backend via quick ping
  //    Use --check flag on the ipc_server to get engine status JSON.
  const engineStatus = await new Promise((resolve) => {
    const args = isBundled ? ['--check'] : ['-m', 'ipc_server', '--check'];
    const cwd  = isBundled ? path.dirname(pythonPath) : backendPath;
    const proc = spawn(pythonPath, args, {
      cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });
    proc.on('exit', (code) => {
      try {
        const parsed = JSON.parse(stdout.trim());
        resolve(parsed);
      } catch {
        // If --check not supported, assume mock only
        resolve({ mock: true, garak: false, pyrit: false, error: stderr.trim() });
      }
    });
    proc.on('error', (err) => {
      resolve({ mock: false, garak: false, pyrit: false, error: err.message });
    });

    // Timeout: 8 seconds max for health check
    setTimeout(() => {
      try { proc.kill(); } catch (_) {}
      resolve({ mock: true, garak: false, pyrit: false, error: 'timeout' });
    }, 8000);
  });

  return {
    python:  pythonVersion,
    backend: backendAvailable ? 'available' : 'not found',
    engines: engineStatus,
    bundled: isBundled,
    paths: {
      python:  pythonPath,
      backend: backendPath,
    },
    appVersion: app.getVersion(),
    platform:   process.platform,
    arch:       process.arch,
  };
});

// ─────────────────────────────────────────────
//  App lifecycle
// ─────────────────────────────────────────────

app.whenReady().then(() => {
  createWindow();

  // On macOS, re-create window when dock icon is clicked
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  killScanProcess();
  // On macOS, apps stay open until Cmd+Q
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  for (const auth of cloudAuth.values()) auth.cancel();
  killScanProcess();
  backendCommands.stop();
});
