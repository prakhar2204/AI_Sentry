'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { BackendCommands } = require('../electron/backend-commands.cjs');
const root = path.resolve(__dirname, '../../..');
const worker = new BackendCommands(() => ({
  executable: path.join(root, '.venv/Scripts/python.exe'), args: ['-m', 'ipc_server'],
  options: { cwd: path.join(root, 'app/backend'), env: { ...process.env, PYTHONIOENCODING: 'utf-8' } },
}), () => { throw new Error('Unexpected browser authentication during local tests'); });
const output = path.join(root, 'scan_artifacts', 'command-verification');
const command = (name, payload = {}) => worker.run({ command: `deploy:${name}`, provider: 'private',
  credentials: { output_dir: output }, payload });

(async () => {
  try {
    const scanPlan = await worker.run({ command: 'scan:estimate', engine: 'auto', scan_depth: 'quick', mode: 'local',
      categories: ['prompt_injection', 'jailbreak', 'data_leak', 'harmful_output', 'encoding_injection', 'malware_generation', 'toxicity'] });
    assert.equal(scanPlan.total_probes, 6);
    assert.equal(scanPlan.engine, 'garak');
    assert.ok(Object.values(scanPlan.per_category).every(count => count > 0));
    await assert.rejects(worker.run({ command: 'scan:estimate', categories: ['invalid'] }), /invalid/);
    const [credentials, plan] = await Promise.all([
      command('validate_credentials'),
      command('generate_plan', { config: { stack: 'docker_compose', domain: 'verify.local', model_name: 'test-model' } }),
    ]);
    assert.equal(credentials.status, 'valid');
    assert.equal(plan.raw_config.domain, 'verify.local');
    assert.equal((await command('dry_run', { plan })).success, true);
    await assert.rejects(command('execute', { plan, confirmed: false }), /not confirmed/);
    const deployed = await command('execute', { plan, confirmed: true });
    assert.equal(deployed.status, 'complete');
    assert.ok(deployed.resources.length >= 2);
    assert.equal((await command('status', { deployment_id: plan.deployment_id })).status, 'complete');
    const evidenceFile = ['scan_artifacts/desktop-verification/report.json', 'scan_artifacts/verified-scan.json']
      .map(file => path.join(root, file)).find(file => fs.existsSync(file));
    assert.ok(evidenceFile, 'Run desktop scan verification first to create a real report');
    const report = JSON.parse(fs.readFileSync(evidenceFile, 'utf8')).report;
    for (const format of ['json', 'html', 'txt']) {
      const result = await worker.run({ command: 'report:export', report, format, output_path: path.join(output, `report.${format}`) });
      assert.equal(result.success, true, result.error);
      assert.ok(fs.statSync(result.path).size > 0);
    }
    const rollback = await command('rollback', { deployment_id: plan.deployment_id });
    assert.equal(rollback.success, true);
    assert.ok(fs.existsSync(path.join(output, 'report.json')), 'Rollback must preserve unrelated exports');
    assert.equal((await command('status', { deployment_id: plan.deployment_id })).status, 'unknown');
    console.log('PASS: real scan plan, command queue, credentials, plan settings, dry run, confirmation, private artifacts, status, scoped rollback, JSON/HTML/text export');
  } finally { worker.stop(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
