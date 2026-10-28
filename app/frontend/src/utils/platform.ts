/**
 * Sentryɸ — Platform Detection Utility
 * src/utils/platform.ts
 *
 * Centralizes Electron vs. browser detection so components don't
 * need to check window.electronAPI directly.
 */

/**
 * Returns true when the React app is running inside an Electron window.
 * Returns false when running in a regular browser (dev or browser-only mode).
 */
export function isElectron(): boolean {
  return typeof window !== 'undefined' && window.electronAPI?.isElectron === true;
}

/**
 * Returns the OS platform string when in Electron ('win32', 'darwin', 'linux'),
 * or 'browser' when running outside Electron.
 */
export function getPlatform(): string {
  if (isElectron()) {
    return window.electronAPI!.platform;
  }
  return 'browser';
}

/**
 * Returns the Electron API if available, otherwise null.
 * Use this when you want to safely call Electron-specific features.
 *
 * @example
 * const api = getElectronAPI();
 * if (api) {
 *   const version = await api.getAppVersion();
 * }
 */
export function getElectronAPI(): NonNullable<Window['electronAPI']> | null {
  if (isElectron()) {
    return window.electronAPI!;
  }
  return null;
}
