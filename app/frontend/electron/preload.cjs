/**
 * Sentryɸ — Electron Preload Script
 * electron/preload.cjs
 *
 * Exposes a safe, typed API surface from the main process to the
 * renderer (React app) via contextBridge. Renderer code accesses
 * this as `window.electronAPI`.
 *
 * Security:
 *   - contextIsolation: true (no direct Node access from renderer)
 *   - nodeIntegration: false
 *   - All IPC calls go through this controlled bridge only
 */

'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // ── Scan lifecycle ──────────────────────────────────────
  /** Start a scan with the given config. Returns { started: boolean, error?: string } */
  startScan: (config) => ipcRenderer.invoke('scan:start', config),

  /** Cancel the currently running scan */
  cancelScan: () => ipcRenderer.invoke('scan:cancel'),

  /**
   * Subscribe to scan progress events (progress, finding, activity, stage).
   * Returns an unsubscribe function — call it on cleanup.
   */
  onScanProgress: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('scan:progress', handler);
    return () => ipcRenderer.removeListener('scan:progress', handler);
  },

  /**
   * Subscribe to scan complete event.
   * Returns an unsubscribe function.
   */
  onScanComplete: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('scan:complete', handler);
    return () => ipcRenderer.removeListener('scan:complete', handler);
  },

  /**
   * Subscribe to scan error events.
   * Returns an unsubscribe function.
   */
  onScanError: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('scan:error', handler);
    return () => ipcRenderer.removeListener('scan:error', handler);
  },

  // ── Export operations ───────────────────────────────────
  /**
   * Full Python-backed export: opens native save dialog, invokes Python,
   * writes the file. Returns { saved, filePath?, size_bytes?, fallback?, error? }
   */
  exportReport: (reportData, format) =>
    ipcRenderer.invoke('report:export', reportData, format),

  /**
   * Open a saved file with the OS default application.
   * Returns { success: boolean, error: string | null }
   */
  openFilePath: (filePath) =>
    ipcRenderer.invoke('shell:openPath', filePath),

  /**
   * Reveal a file in the OS file explorer (Windows Explorer / Finder).
   * Returns { success: true }
   */
  openFileFolder: (filePath) =>
    ipcRenderer.invoke('shell:openFolder', filePath),

  // ── File operations ─────────────────────────────────────
  /**
   * Save a report to disk. Opens native save dialog.
   * Returns { saved: boolean, filePath?: string, error?: string }
   */
  saveReport: (data, format) => ipcRenderer.invoke('report:save', data, format),

  /**
   * Open a native save file dialog.
   * Returns the chosen file path string, or null if cancelled.
   */
  showSaveDialog: (options) => ipcRenderer.invoke('dialog:save', options),

  // ── System info ─────────────────────────────────────────
  /** Get the Python version string (e.g. "Python 3.11.2") */
  getPythonVersion: () => ipcRenderer.invoke('system:python-version'),

  /** Get the Electron app version (from package.json) */
  getAppVersion: () => ipcRenderer.invoke('system:app-version'),

  // ── Platform detection ──────────────────────────────────
  /** Always true when running inside Electron */
  isElectron: true,

  /** OS platform: 'win32', 'darwin', 'linux' */
  platform: process.platform,
});
