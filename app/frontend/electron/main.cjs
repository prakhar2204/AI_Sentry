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

const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const readline = require('readline');
const fs = require('fs');

// ─────────────────────────────────────────────
//  Environment
// ─────────────────────────────────────────────

const isDev = !app.isPackaged;
const DEV_URL = 'http://localhost:3000';

// ─────────────────────────────────────────────
//  Active scan process reference
// ─────────────────────────────────────────────

let scanProcess = null;
let mainWindow = null;

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

  if (isDev) {
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
  // In production, check for bundled Python first
  if (!isDev) {
    const bundledPy = path.join(process.resourcesPath, 'python', 'python');
    if (fs.existsSync(bundledPy)) return bundledPy;
    const bundledPyWin = path.join(process.resourcesPath, 'python', 'python.exe');
    if (fs.existsSync(bundledPyWin)) return bundledPyWin;
  }
  // Fall back to system Python
  return process.platform === 'win32' ? 'python' : 'python3';
}

function getBackendPath() {
  if (isDev) {
    // Development: backend is at ../../backend relative to electron/
    return path.join(__dirname, '../../backend');
  }
  // Production: backend is bundled in resources
  return path.join(process.resourcesPath, 'backend');
}

function killScanProcess() {
  if (scanProcess) {
    try {
      scanProcess.kill('SIGTERM');
    } catch (_) {}
    scanProcess = null;
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

  try {
    scanProcess = spawn(pythonPath, ['-m', 'ipc_server'], {
      cwd: backendPath,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    });

    // Write config to Python stdin
    scanProcess.stdin.write(JSON.stringify(config) + '\n');
    scanProcess.stdin.end();

    // Stream stdout line-by-line (JSON Lines protocol)
    const rl = readline.createInterface({ input: scanProcess.stdout });
    rl.on('line', (line) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      try {
        const evt = JSON.parse(trimmed);
        const win = BrowserWindow.getFocusedWindow() || mainWindow;
        if (!win) return;

        switch (evt.type) {
          case 'progress':
          case 'finding':
          case 'activity':
          case 'stage':
            win.webContents.send('scan:progress', evt);
            break;
          case 'complete':
            win.webContents.send('scan:complete', evt);
            scanProcess = null;
            break;
          case 'error':
            win.webContents.send('scan:error', evt);
            scanProcess = null;
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

    scanProcess.on('exit', (code) => {
      const win = BrowserWindow.getFocusedWindow() || mainWindow;
      if (code !== 0 && code !== null && win) {
        win.webContents.send('scan:error', {
          type: 'error',
          message: `Python process exited with code ${code}`,
          code: 'PROCESS_EXIT',
        });
      }
      scanProcess = null;
    });

    return { started: true };
  } catch (err) {
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

  // Invoke Python export_handler via subprocess
  const py = findPython();
  const backendDir = path.join(__dirname, '..', '..', 'backend');
  const exportScript = path.join(backendDir, 'export_handler.py');

  // Payload sent to Python via stdin
  const payload = JSON.stringify({
    action:      'export',
    format:      format,
    output_path: filePath,
    report:      reportData,
  });

  return new Promise((resolve) => {
    let stdout = '';
    let stderr = '';

    const proc = spawn(py, [exportScript], {
      cwd:   backendDir,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    proc.stdin.write(payload, 'utf-8');
    proc.stdin.end();

    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });

    proc.on('exit', (code) => {
      try {
        // export_handler.py prints a single JSON result line to stdout
        const trimmed = stdout.trim();
        if (trimmed) {
          const result = JSON.parse(trimmed);
          if (result.success) {
            resolve({
              saved:      true,
              filePath:   result.path,
              size_bytes: result.size_bytes || 0,
              fallback:   result.fallback || null,
            });
          } else {
            resolve({ saved: false, error: result.error || 'Export failed' });
          }
        } else {
          // Script printed nothing — use exit code
          if (code === 0) {
            const size = (() => {
              try { return fs.statSync(filePath).size; } catch (_) { return 0; }
            })();
            resolve({ saved: true, filePath, size_bytes: size });
          } else {
            resolve({ saved: false, error: stderr.trim() || `Python exited ${code}` });
          }
        }
      } catch (parseErr) {
        resolve({ saved: false, error: `Parse error: ${parseErr.message}. Stderr: ${stderr.trim()}` });
      }
    });

    proc.on('error', (err) => {
      resolve({ saved: false, error: `Spawn failed: ${err.message}` });
    });
  });
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

/** dialog:save — open native save dialog and return chosen path */
ipcMain.handle('dialog:save', async (event, options) => {
  const result = await dialog.showSaveDialog(mainWindow, options || {});
  return result.canceled ? null : result.filePath;
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
  killScanProcess();
});
