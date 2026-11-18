'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function fixture() {
  const handlers = {}, calls = [], focus = [];
  const identity = { account: '123456789012', identity: 'arn:aws:iam::123456789012:user/test', profile: 'sentryphi-console', region: 'us-east-1' };
  class Auth {
    constructor() { this.scope = null; }
    async login() { calls.push('login'); return identity; }
    async select_scope() { this.scope = identity; return identity; }
    async require_confirmed_scope(region) { calls.push(['reverify', region]); return identity; }
  }
  class Backend { run(config) { calls.push(config); return Promise.resolve({ status: 'running' }); } }
  const context = vm.createContext({
    require: name => name === 'electron' ? {
      app: { isPackaged: false, getPath: () => 'test-app-data', whenReady: () => ({ then() {} }), on() {} },
      ipcMain: { handle: (name, handler) => { handlers[name] = handler; } },
    } : name === './cloud-auth.cjs' ? { AwsCloudAuth: Auth, CloudAuthStub: Auth }
      : name === './backend-commands.cjs' ? { BackendCommands: Backend } : require(name),
    process, console, __dirname, setTimeout, clearTimeout,
    testWindow: { isDestroyed: () => false, isMinimized: () => true,
      restore: () => focus.push('restore'), show: () => focus.push('show'), focus: () => focus.push('focus') },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, 'main.cjs'), 'utf8'), context);
  vm.runInContext('mainWindow = testWindow', context);
  return { handlers, calls, focus, identity };
}

test('successful CLI sign-in foregrounds the app after verified identity returns', async () => {
  const { handlers, focus, identity } = fixture();
  const result = await handlers['cloud-auth:command']({}, { provider: 'aws', action: 'login' });
  assert.equal(result.ok, true); assert.deepEqual(result.result, identity);
  assert.deepEqual(focus, ['restore', 'show', 'focus']);
});
test('deployment requires confirmed scope and replaces renderer credentials with verified public metadata', async () => {
  const { handlers, calls, identity } = fixture();
  const command = { command: 'deploy:execute', provider: 'aws', credentials: { access_token: 'SENTINEL' }, payload: { plan: { region: 'us-east-1' }, confirmed: true } };
  await assert.rejects(handlers['backend:command']({}, command), /confirm your cloud account/);
  await handlers['cloud-auth:command']({}, { provider: 'aws', action: 'select_scope', options: identity });
  await handlers['backend:command']({}, command);
  assert.equal(calls.at(-2)[0], 'reverify');
  const forwarded = calls.at(-1);
  assert.equal(forwarded.credentials.account_id, identity.account);
  assert.equal(forwarded.credentials.profile, identity.profile);
  assert.equal(forwarded.credentials.access_token, undefined);
});
test('legacy OAuth is blocked and malformed auth commands return an error', async () => {
  const { handlers } = fixture();
  await assert.rejects(handlers['backend:command']({}, { command: 'deploy:auth_url', provider: 'aws' }), /official CLI/);
  const result = await handlers['cloud-auth:command']({}, { provider: 'unsupported', action: 'login' });
  assert.equal(result.ok, false);
});
