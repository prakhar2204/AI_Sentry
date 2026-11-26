'use strict';
const fs = require('node:fs');
const path = require('node:path');

function registerUpdates({ app, ipcMain, currentWindow, busy, updater, enabled = true }) {
  const autoUpdater = enabled ? updater || require('electron-updater').autoUpdater : null;
  const preference = path.join(app.getPath('userData'), 'updates.json');
  let automatic = true;
  try { automatic = JSON.parse(fs.readFileSync(preference, 'utf8')).automatic === true; }
  catch (error) { if (error.code !== 'ENOENT') automatic = false; }
  let state = { automatic, stage: enabled ? 'checking' : 'development',
    currentVersion: app.getVersion(), version: '', percent: 0, installOnExit: false };
  let authorizedDownload = false;
  function set(change) {
    state = { ...state, ...change };
    const win = currentWindow();
    if (win && !win.isDestroyed()) win.webContents.send('updates:changed', state);
  }
  if (autoUpdater) {
    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = false;
  }
  async function download() {
    if (!autoUpdater || state.stage !== 'available') return;
    authorizedDownload = true;
    set({stage: 'downloading', percent: 0});
    try { await autoUpdater.downloadUpdate(); }
    catch { set({stage: 'error'}); }
  }
  async function check() {
    if (!autoUpdater) return;
    set({stage: 'checking'});
    try { await autoUpdater.checkForUpdates(); }
    catch { set({stage: 'error'}); }
  }
  autoUpdater?.on('update-available', info => {
    set({stage: 'available', version: info.version});
    if (automatic) void download();
  });
  autoUpdater?.on('update-not-available', () => set({stage: 'current'}));
  autoUpdater?.on('download-progress', p => set({percent: Math.floor(p.percent)}));
  autoUpdater?.on('error', () => set({stage: 'error'}));
  autoUpdater?.on('update-downloaded', () => {
    // BaseUpdater registers its quit listener immediately after this event.
    // Keep the listener registered if the user changes the preference later.
    autoUpdater.autoInstallOnAppQuit = true;
    queueMicrotask(() => { autoUpdater.autoInstallOnAppQuit = authorizedDownload; });
    set({stage: 'ready', installOnExit: authorizedDownload});
  });
  ipcMain.handle('updates:command', async (event, action, value) => {
    const win = currentWindow();
    if (!win || event.sender !== win.webContents || event.senderFrame !== win.webContents.mainFrame)
      throw new Error('Unknown update caller');
    if (action === 'auto' && typeof value === 'boolean') {
      fs.writeFileSync(preference + '.tmp', JSON.stringify({automatic: value}));
      fs.renameSync(preference + '.tmp', preference);
      automatic = value;
      authorizedDownload = value;
      if (autoUpdater) autoUpdater.autoInstallOnAppQuit = value && state.stage === 'ready';
      set({automatic, installOnExit: autoUpdater?.autoInstallOnAppQuit ?? false});
      if (automatic) void download();
    } else if (action === 'download') {
      void download();
    } else if (action === 'queue' && state.stage === 'ready') {
      authorizedDownload = true;
      autoUpdater.autoInstallOnAppQuit = true;
      set({installOnExit: true});
    } else if (action === 'retry' && ['error', 'current'].includes(state.stage)) {
      void check();
    } else if (action === 'install' && state.stage === 'ready' && authorizedDownload && !busy()) {
      autoUpdater.quitAndInstall(true, true);
    }
    return state;
  });
  void check();
}
module.exports = { registerUpdates };
