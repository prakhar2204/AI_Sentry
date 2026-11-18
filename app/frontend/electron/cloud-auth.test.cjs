'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { AwsCloudAuth, ProviderCloudAuth, CloudAuthStub, isolatedEnvironment } = require('./cloud-auth.cjs');

const identity = { Account: '123456789012', Arn: 'arn:aws:iam::123456789012:user/test', UserId: 'test' };
function fixture(handler = () => undefined, options = {}) {
  const calls = [], events = [];
  const spawn = (exe, args, opts) => {
    calls.push({ exe, args, opts });
    const child = new EventEmitter();
    child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
    child.exitCode = null; child.pid = 123;
    child.kill = () => { child.exitCode = -1; child.emit('close', -1); };
    queueMicrotask(() => {
      const result = handler(exe, args) || {};
      if (result.hang) return;
      if (result.missing) { child.emit('error', new Error('ENOENT')); return; }
      const output = result.output ?? (args[0] === '--version' ? 'aws-cli/2.32.0 Python/3.13' :
        args[0] === 'sts' ? JSON.stringify(identity) : '');
      child.stdout.emit('data', Buffer.from(output));
      if (result.stderr) child.stderr.emit('data', Buffer.from(result.stderr));
      child.exitCode = result.code || 0; child.emit('close', child.exitCode);
    });
    return child;
  };
  const opts = { spawn, mkdir: () => {}, platform: 'linux', onProgress: e => events.push(e), ...options };
  const auth = options.provider ? new ProviderCloudAuth(options.provider, 'isolated-cloud', opts) : new AwsCloudAuth('isolated-cloud', opts);
  return { auth, calls, events };
}

for (const provider of ['azure', 'gcp']) {
  test(`${provider}: official login, isolated environment, scope verification and logout`, async () => {
    let changed = false;
    const account = provider === 'azure' ? '12345678-1234-1234-1234-123456789abc' : 'example-project';
    const user = 'person@example.test';
    const { auth, calls, events } = fixture((_exe, args) => {
      if (args[0] === 'account' && args[1] === 'show') return { output: JSON.stringify({ id: account, state: 'Enabled', user: { name: changed ? 'other' : user } }) };
      if (args[0] === 'auth' && args[1] === 'list') return { output: JSON.stringify([{ account: changed ? 'other' : user, status: 'ACTIVE' }]) };
      if (args[0] === 'config' && args[1] === 'list') return { output: JSON.stringify({ core: { project: account } }) };
      return { output: args.includes('login') ? 'TOKEN_SENTINEL' : '{}' };
    }, { provider });
    assert.equal((await auth.check_cli()).available, true);
    const signedIn = await auth.login();
    assert.equal(signedIn.identity, user);
    assert.equal(signedIn.account, account);
    await assert.rejects(auth.require_confirmed_scope(signedIn.region), { code: 'SCOPE_UNCONFIRMED' });
    await auth.select_scope(signedIn);
    assert.equal((await auth.require_confirmed_scope(signedIn.region)).account, account);
    assert.ok(calls.every(c => c.opts.shell === false));
    assert.ok(calls.every(c => c.opts.env[provider === 'azure' ? 'AZURE_CONFIG_DIR' : 'CLOUDSDK_CONFIG'].endsWith(provider)));
    assert.ok(!JSON.stringify(events).includes('TOKEN_SENTINEL'));
    if (provider === 'gcp') assert.ok(calls.some(c => c.args.slice(0, 4).join(' ') === `auth application-default login ${user}`));
    changed = true;
    await assert.rejects(auth.require_confirmed_scope(signedIn.region), { code: 'IDENTITY_CHANGED' });
    await auth.logout();
  });

  test(`${provider}: timeout, cancellation and expired sessions are sanitized`, async () => {
    const timed = fixture((_exe, args) => args.includes('login') ? { hang: true } : { output: '{}' }, { provider, timeoutMs: 5 });
    await assert.rejects(timed.auth.login(), { code: 'TIMEOUT' });
    assert.equal(timed.auth.active, null);
    const cancelled = fixture(() => ({ hang: true }), { provider });
    const promise = cancelled.auth.login();
    const rejection = assert.rejects(promise, { code: 'CANCELLED' });
    cancelled.auth.cancel(); await rejection;
    const expired = fixture(() => ({ code: 1, stderr: 'invalid_grant SENTINEL' }), { provider });
    await assert.rejects(expired.auth.whoami(), e => e.code === 'EXPIRED_SESSION' && !e.message.includes('SENTINEL'));
  });
}

test('CLI minimum version, missing executable and upgrade guidance', async () => {
  for (const [version, available] of [['2.31.9', false], ['1.99.0', false], ['2.32.0', true], ['2.40.1', true], ['3.0.0', true]]) {
    const { auth } = fixture(() => ({ output: `aws-cli/${version}` }));
    assert.equal((await auth.check_cli()).available, available);
  }
  const status = await fixture(() => ({ missing: true })).auth.check_cli();
  assert.equal(status.code, 'CLI_MISSING'); assert.match(status.install_url, /^https:\/\/docs.aws.amazon.com\//);
});
test('login completes only after STS verification; login output never forwarded', async () => {
  const { auth, calls, events } = fixture((exe, args) => args[0] === 'login' ? { output: 'TOKEN_SENTINEL' } : undefined);
  const result = await auth.login({ region: 'us-east-1' });
  assert.equal(result.account, identity.Account);
  assert.deepEqual(calls.map(c => c.args[0]), ['--version', 'configure', 'login', 'sts']);
  assert.ok(calls.every(c => c.opts.shell === false && c.opts.env.AWS_PROFILE === 'sentryphi-console'));
  assert.ok(!JSON.stringify(events).includes('TOKEN_SENTINEL'));
  await assert.rejects(auth.require_confirmed_scope('us-east-1'), { code: 'SCOPE_UNCONFIRMED' });
  await auth.select_scope(result);
  assert.equal((await auth.require_confirmed_scope('us-east-1')).account, identity.Account);
  await assert.rejects(auth.require_confirmed_scope('us-west-2'), { code: 'SCOPE_UNCONFIRMED' });
});
test('identity changes and expired sessions stop deployment', async () => {
  let changed = false;
  const { auth } = fixture((exe, args) => args[0] === 'sts' && changed ?
    { output: JSON.stringify({ ...identity, Arn: 'arn:aws:iam::123456789012:user/other' }) } : undefined);
  await auth.select_scope(await auth.login({ region: 'us-east-1' }));
  changed = true;
  await assert.rejects(auth.require_confirmed_scope('us-east-1'), { code: 'IDENTITY_CHANGED' });
  assert.equal(auth.scope, null);
  await assert.rejects(fixture((exe, args) => args[0] === 'sts' ?
    { code: 1, stderr: 'ExpiredToken TOKEN_SENTINEL' } : undefined).auth.whoami(), { code: 'EXPIRED_SESSION' });
});
test('missing policy and closed browser yield actionable, sanitized failures', async () => {
  for (const [stderr, code] of [['SignInLocalDevelopmentAccess TOKEN_SENTINEL', 'MISSING_POLICY'], ['Browser closed TOKEN_SENTINEL', 'LOGIN_FAILED']]) {
    const { auth } = fixture((exe, args) => args[0] === 'login' ? { code: 1, stderr } : undefined);
    await assert.rejects(auth.login({ region: 'us-east-1' }), e => e.code === code && !e.message.includes('TOKEN_SENTINEL'));
  }
});
test('timeout kills the subprocess and releases the attempt', async () => {
  const { auth } = fixture((exe, args) => args[0] === 'login' ? { hang: true } : undefined, { timeoutMs: 5 });
  await assert.rejects(auth.login({ region: 'us-east-1' }), { code: 'TIMEOUT' });
  assert.equal(auth.active, null);
});
test('cancel login kills the subprocess; concurrent login/logout are rejected', async () => {
  const { auth, calls } = fixture((exe, args) => args[0] === 'login' ? { hang: true } : undefined);
  const pending = auth.login({ region: 'us-east-1' });
  const rejected = assert.rejects(pending, { code: 'CANCELLED' });
  await new Promise(resolve => setImmediate(resolve));
  await assert.rejects(auth.login({ region: 'us-east-1' }), { code: 'LOGIN_BUSY' });
  await assert.rejects(auth.logout(), { code: 'LOGIN_BUSY' });
  auth.cancel(); await rejected;
  assert.equal(auth.active, null); assert.equal(calls.at(-1).args[0], 'login');
});
test('Identity Center configuration and logout remain in dedicated home/profile', async () => {
  const { auth, calls } = fixture();
  await auth.login({ region: 'us-east-1', mode: 'sso', start_url: 'https://test.awsapps.com/start',
    account: identity.Account, role: 'Developer' });
  assert.ok(calls.some(c => c.args[0] === 'sso' && c.args[1] === 'login'));
  await auth.logout();
  assert.deepEqual(calls.at(-1).args.slice(0, 2), ['sso', 'logout']);
  assert.equal(calls.at(-1).opts.env.AWS_PROFILE, 'sentryphi-sso');
  assert.match(calls.at(-1).opts.env.USERPROFILE, /isolated-cloud.*aws.*home$/);
});
test('remote login hands interaction to official CLI in its own terminal', async () => {
  const { auth, calls } = fixture(undefined, { platform: 'win32' });
  await auth.login({ region: 'us-east-1', remote: true });
  const remote = calls.find(c => c.exe === 'powershell.exe');
  assert.match(remote.args.at(-1), /'login','--remote'/);
  assert.match(remote.args.at(-1), /-WindowStyle Normal -Wait/);
  assert.equal(remote.opts.stdio[0], 'ignore');
});
test('isolation strips ambient credentials and endpoints without changing parent environment', () => {
  const parent = { AWS_ACCESS_KEY_ID: 'SENTINEL', aws_secret_access_key: 'SENTINEL', AWS_ENDPOINT_URL: 'https://invalid', USERPROFILE: 'original', PATH: 'keep' };
  const env = isolatedEnvironment('aws', 'cloud', parent);
  assert.equal(env.AWS_ACCESS_KEY_ID, undefined); assert.equal(env.AWS_ENDPOINT_URL, undefined);
  assert.equal(env.aws_secret_access_key, undefined);
  assert.equal(parent.USERPROFILE, 'original'); assert.equal(env.PATH, 'keep');
  assert.match(isolatedEnvironment('azure', 'cloud', {}).AZURE_CONFIG_DIR, /azure$/);
  assert.match(isolatedEnvironment('gcp', 'cloud', {}).CLOUDSDK_CONFIG, /gcp$/);
});
test('Azure and GCP explicitly report stubs and reject mutations', async () => {
  for (const provider of ['azure', 'gcp']) {
    const auth = new CloudAuthStub(provider, 'cloud');
    assert.equal((await auth.check_cli()).implemented, false);
    await assert.rejects(auth.login(), { code: 'NOT_IMPLEMENTED' });
    await assert.rejects(auth.require_confirmed_scope(), { code: 'NOT_IMPLEMENTED' });
  }
});
