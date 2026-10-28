/**
 * Sentryɸ — Electron API Type Declarations
 * src/electron.d.ts
 *
 * Provides TypeScript types for window.electronAPI exposed by preload.cjs.
 * When running in browser-only mode (npm run dev), window.electronAPI
 * will be undefined — all callers must check isElectron() first.
 */

/** Shape of the electronAPI exposed via contextBridge */
interface ElectronAPI {
  // Scan lifecycle
  startScan: (config: unknown) => Promise<{ started: boolean; error?: string }>;
  cancelScan: () => Promise<{ cancelled: boolean }>;
  onScanProgress: (callback: (data: unknown) => void) => () => void;
  onScanComplete: (callback: (data: unknown) => void) => () => void;
  onScanError: (callback: (data: unknown) => void) => () => void;

  // Export operations (Python-backed, native save dialog)
  exportReport: (
    reportData: unknown,
    format: string
  ) => Promise<{
    saved: boolean;
    filePath?: string;
    size_bytes?: number;
    fallback?: string | null;
    error?: string;
  }>;
  openFilePath:   (filePath: string) => Promise<{ success: boolean; error: string | null }>;
  openFileFolder: (filePath: string) => Promise<{ success: boolean }>;

  // File operations (legacy)
  saveReport: (
    data: unknown,
    format: string
  ) => Promise<{ saved: boolean; filePath?: string; error?: string }>;
  showSaveDialog: (options: unknown) => Promise<string | null>;

  // System info
  getPythonVersion: () => Promise<string>;
  getAppVersion: () => Promise<string>;

  // Platform detection
  isElectron: true;
  platform: string;
}

declare global {
  interface Window {
    /**
     * Available only when running inside Electron.
     * Check `isElectron()` from src/utils/platform.ts before using.
     */
    electronAPI?: ElectronAPI;
  }
}

export {};
