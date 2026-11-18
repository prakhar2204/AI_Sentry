// Exercise the actual Electron main-process scan handler and real Python/model
// subprocesses, without opening a window. Usage: node scripts/verify-scan-ipc.cjs MODEL.gguf
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { spawnSync } = require('child_process');
const handlers = new Map();
const electron = {
  app: { isPackaged: false, whenReady: () => ({ then() {} }), on() {} },
  ipcMain: { handle: (name, fn) => handlers.set(name, fn) },
};
const mainPath = path.resolve(__dirname, '../electron/main.cjs');
const mainRequire = require('module').createRequire(mainPath);
let progress = 0;
let modelRequests = 0;
const timer = setTimeout(() => {
  console.error('Scan verification timed out');
  handlers.get('scan:cancel')?.();
  process.exitCode = 1;
}, 720000);
const testWindow = { isDestroyed: () => false, webContents: { send(channel, event) {
  if (channel === 'scan:progress') {
    progress++;
    if (event.type === 'stage' || (event.type === 'progress' && event.stage === 'scanning'))
      console.log(event.message);
    if (event.type === 'activity' && event.message.includes('processing task,')) {
      modelRequests++;
      if (modelRequests === 1) console.log(spawnSync('nvidia-smi', [
        '--query-gpu=name,memory.used,utilization.gpu', '--format=csv'
      ], { encoding: 'utf8' }).stdout);
    }
  }
  if (channel === 'scan:error') {
    console.error(JSON.stringify(event));
    clearTimeout(timer);
    process.exitCode = 1;
  }
  if (channel === 'scan:complete') {
    clearTimeout(timer);
    console.log(JSON.stringify({ progressEvents: progress, modelRequests, report: event.report }));
    const artifactDir = path.resolve(__dirname, '../../../scan_artifacts');
    fs.mkdirSync(artifactDir, { recursive: true });
    fs.writeFileSync(path.join(artifactDir, 'verified-scan.json'), JSON.stringify({ progressEvents: progress, modelRequests, report: event.report }, null, 2));
    if (!modelRequests || !progress || event.report.engine.name === 'mock') process.exitCode = 1;
  }
} } };
vm.runInNewContext(fs.readFileSync(mainPath, 'utf8') + '\nmainWindow = testWindow;', {
  require: name => name === 'electron' ? electron : mainRequire(name),
  __dirname: path.dirname(mainPath), process, console, setTimeout, clearTimeout, testWindow,
});
handlers.get('scan:start')({}, {
  target: path.resolve(process.argv[2]), mode: 'local', scan_depth: 'quick',
  categories: process.argv[3] ? process.argv[3].split(',') : ['prompt_injection'], engine: 'auto',
}).then(result => {
  if (!result.started) { clearTimeout(timer); throw new Error(result.error); }
});
