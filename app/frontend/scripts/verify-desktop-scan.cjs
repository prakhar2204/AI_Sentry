// Real Electron + React + preload + Python + Garak + llama.cpp regression.
// Only the native file picker is substituted; all scan execution is real.
const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const artifactDir = path.resolve(__dirname, '../../../scan_artifacts/desktop-verification');
fs.mkdirSync(artifactDir, { recursive: true });
app.setPath('userData', fs.mkdtempSync(path.join(artifactDir, 'electron-profile-')));
process.env.SENTRYPHI_USE_BUILD = '1';
const model = process.argv[2] || 'F:\\models\\dolphin-phi.gguf';
const categories = process.argv[3]?.split(',') || ['prompt_injection'];
dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [model] });
BrowserWindow.prototype.show = function () {}; // Test window stays hidden.
let scanConfig;
let report;
let requests = 0;
let backendError;
let failed = false;
app.on('will-quit', () => { if (failed) app.exit(1); });
const handle = ipcMain.handle.bind(ipcMain);
ipcMain.handle = (name, callback) => handle(name, (...args) => {
  if (name === 'scan:start') scanConfig = args[1];
  return callback(...args);
});
const timeout = setTimeout(() => { console.error('Desktop test timed out'); failed = true; app.quit(); }, 720000);

app.on('browser-window-created', (_event, win) => {
  win.webContents.setBackgroundThrottling(false);
  const send = win.webContents.send.bind(win.webContents);
  win.webContents.send = (channel, event) => {
    if (channel === 'scan:complete') report = event.report;
    if (channel === 'scan:error') backendError = event.message;
    if (channel === 'scan:progress' && event.type === 'activity' && event.message.includes('processing task,')) requests++;
    return send(channel, event);
  };
  const evaluate = code => win.webContents.executeJavaScript(code);
  async function waitFor(code, limit = 30000) {
    const deadline = Date.now() + limit;
    while (Date.now() < deadline) {
      if (backendError) throw new Error(backendError);
      if (await evaluate(code)) return;
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    throw new Error(`UI condition timed out: ${code}`);
  }
  const click = async selector => {
    await waitFor(`document.querySelector(${JSON.stringify(selector)}) && !document.querySelector(${JSON.stringify(selector)}).disabled`);
    await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  };
  win.webContents.once('did-finish-load', async () => {
    try {
      await waitFor('document.querySelector("#consent-checkbox") || document.querySelector("#browse-model-button")');
      if (await evaluate('!!document.querySelector("#consent-checkbox")')) {
        await click('#consent-checkbox');
        await click('#agree-continue-button');
      }
      await click('#browse-model-button');
      await waitFor('!!document.querySelector("#selected-model-display")');
      await click('#input-continue-button');
      await click('input[name="scan-strategy"][value="manual"]');
      for (const category of categories) await click(`input[type="checkbox"][value="${category}"]`);
      await click('input[name="scan-depth"][value="quick"]');
      await click('#config-continue-button');
      await waitFor('document.querySelector("#stat-probes") && !document.querySelector("#estimate-continue-button").disabled');
      const estimatedProbes = Number(await evaluate('document.querySelector("#stat-probes").textContent'));
      const expectedFamilies = new Set(categories.map(c => c === 'harmful_output' ? 'toxicity' : c));
      assert.equal(estimatedProbes, expectedFamilies.size, 'Quick estimate must match actual engine families');
      await click('#estimate-continue-button');
      await waitFor('!!document.querySelector("#results-score-section")', 600000);
      assert.equal(scanConfig.local_model_path, model);
      assert.equal(scanConfig.engine, 'auto');
      assert.equal(report.engine.name, 'garak');
      assert.deepEqual(scanConfig.categories, categories);
      assert.ok(requests > 0);
      await new Promise(resolve => setTimeout(resolve, 1600));
      fs.writeFileSync(path.join(artifactDir, 'report.json'), JSON.stringify({ scanConfig, estimatedProbes, requests, report }, null, 2));
      fs.writeFileSync(path.join(artifactDir, 'results.txt'), await evaluate('document.body.innerText'));
      fs.writeFileSync(path.join(artifactDir, 'results.png'), (await win.webContents.capturePage(undefined, { stayHidden: true, stayAwake: true })).toPNG());
      console.log(`PASS: complete desktop wizard, real model, ${requests} inference requests, results rendered`);
      clearTimeout(timeout);
      app.quit();
    } catch (error) {
      console.error(error);
      fs.writeFileSync(path.join(artifactDir, 'failure.txt'), await evaluate('document.body.innerText'));
      clearTimeout(timeout);
      // Normal quit triggers the app's owned-process cleanup.
      failed = true;
      app.quit();
    }
  });
});
require('../electron/main.cjs');
