const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { registerUpdates } = require('./updates.cjs');

test('development exposes and persists preferences without contacting an update feed', async t => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sentryphi-update-dev-'));
  t.after(() => fs.rmSync(dir, {recursive:true, force:true}));
  function launch() {
    let command;
    const win = {isDestroyed: () => false, webContents: {mainFrame: {}, send() {}}};
    registerUpdates({app: {getPath: () => dir, getVersion: () => '1.0.0'},
      ipcMain: {handle: (_channel, handler) => { command = handler; }},
      currentWindow: () => win, busy: () => false, enabled: false,
      updater: {checkForUpdates() { throw new Error('Development contacted update feed'); }}});
    return (action, value) => command({sender: win.webContents, senderFrame: win.webContents.mainFrame}, action, value);
  }
  const first = launch();
  assert.equal((await first('state')).stage, 'development');
  await first('auto', false);
  const second = launch();
  assert.equal((await second('state')).automatic, false);
  assert.equal((await second('state')).currentVersion, '1.0.0');
  assert.equal((await second('download')).stage, 'development');
  assert.equal((await second('install')).stage, 'development');
});

test('updates persist manual mode, announce, download once and defer installation during work', async t => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sentryphi-update-'));
  t.after(() => fs.rmSync(dir, {recursive:true, force:true}));
  function launch() {
    let command, downloads = 0, installs = 0, busy = false;
    const updater = new EventEmitter();
    updater.checkForUpdates = async () => {};
    updater.downloadUpdate = async () => { downloads++; };
    updater.quitAndInstall = () => { installs++; };
    const win = {isDestroyed: () => false, webContents: {mainFrame: {}, send() {}}};
    registerUpdates({app:{getPath: () => dir, getVersion: () => '1.0.0'}, ipcMain:{handle: (key, fn) => { command = fn; }},
      currentWindow: () => win, busy: () => busy, updater});
    return { updater, cmd: (a, v) => command({sender:win.webContents, senderFrame:win.webContents.mainFrame}, a, v),
      downloads: () => downloads, installs: () => installs, setBusy: v => { busy = v; } };
  }
  const first = launch();
  first.updater.emit('update-available', {version:'2.0.0'});
  assert.equal(first.downloads(), 1);
  await first.cmd('auto', false);
  first.updater.emit('update-downloaded');
  await first.cmd('install');
  assert.equal(first.installs(), 0);
  const next = launch();
  next.updater.emit('update-available', {version:'2.0.0'});
  assert.equal((await next.cmd('state')).automatic, false);
  assert.equal(next.downloads(), 0);
  await Promise.all([next.cmd('download'), next.cmd('download')]);
  assert.equal(next.downloads(), 1);
  next.updater.emit('update-downloaded');
  next.setBusy(true);
  await next.cmd('install');
  assert.equal(next.installs(), 0);
  next.setBusy(false);
  await next.cmd('install');
  assert.equal(next.installs(), 1);
});
