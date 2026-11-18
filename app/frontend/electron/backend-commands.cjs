'use strict';
const { spawn } = require('child_process');
const readline = require('readline');

// A separate, sequential worker retains deployment state across plan/execute/status.
// It never replaces or cancels the active scan process.
class BackendCommands {
  constructor(launch, openAuthUrl) {
    this.launch = launch;
    this.openAuthUrl = openAuthUrl;
    this.child = null;
    this.pending = null;
    this.queue = Promise.resolve();
  }

  run(config) {
    const task = this.queue.then(() => this.request(config));
    this.queue = task.catch(() => {});
    return task;
  }

  request(config) {
    if (!this.child) {
      const { executable, args, options } = this.launch();
      const child = spawn(executable, [...args, '--commands'], {
        ...options, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'],
      });
      this.child = child;
      readline.createInterface({ input: child.stdout }).on('line', line => {
        if (this.child !== child || !this.pending) return;
        let event;
        try { event = JSON.parse(line); } catch { return; }
        if (event.type === 'deploy_auth_url') {
          Promise.resolve().then(() => this.openAuthUrl(event.url)).catch(error => this.stop(error));
        } else if (event.type === 'error' || event.type === 'deploy_error') {
          this.pending.error = new Error(event.message || 'Backend command failed');
        } else if (event.type === 'command_done') {
          this.finish(this.pending.error || (this.pending.result === undefined ? new Error('Backend returned no result') : null), this.pending.result);
        } else if (event.type?.startsWith('deploy_') || event.type === 'export_result' || event.type === 'estimate_result') {
          this.pending.result = event.plan ?? event.result ?? event;
        }
      });
      // Drain stderr, but do not expose provider tokens or credential payloads.
      child.stderr.on('data', () => {});
      child.stdin.on('error', error => { if (this.child === child) this.stop(error); });
      child.on('error', error => { if (this.child === child) this.stop(error); });
      child.on('close', code => {
        if (this.child === child) {
          this.child = null;
          this.finish(new Error(`Backend command worker exited (${code})`));
        }
      });
    }
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => this.stop(new Error('Backend command timed out')), 360000);
      this.pending = { resolve, reject, timer };
      this.child.stdin.write(JSON.stringify(config) + '\n', 'utf8');
    });
  }

  finish(error, value) {
    const pending = this.pending;
    if (!pending) return;
    this.pending = null;
    clearTimeout(pending.timer);
    if (error) pending.reject(error); else pending.resolve(value);
  }

  stop(error = new Error('Backend command worker stopped')) {
    const child = this.child;
    this.child = null;
    this.finish(error);
    if (child) child.kill();
  }
}
module.exports = { BackendCommands };
