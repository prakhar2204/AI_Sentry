const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;
const output = path.resolve(__dirname, '../../../scan_artifacts/desktop-verification');
fs.mkdirSync(output, { recursive: true });
const log = fs.createWriteStream(path.join(output, 'run.log'));
const child = spawn(require('electron'), [path.join(__dirname, 'verify-desktop-scan.cjs'), ...process.argv.slice(2)],
  { env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
child.stdout.on('data', data => { process.stdout.write(data); log.write(data); });
child.stderr.on('data', data => { process.stderr.write(data); log.write(data); });
child.on('error', error => { console.error(error); process.exitCode = 1; log.end(); });
child.on('close', code => { process.exitCode = code ?? 1; log.end(); });
