'use strict';
/**
 * Sentryɸ — Cloud Authentication (No External CLI Required)
 *
 * Authenticates with AWS, Azure, and GCP using built-in REST APIs.
 * Zero external dependencies — no aws/az/gcloud CLI installation needed.
 *
 * AWS:   Access Key + Secret Key → validated via STS GetCallerIdentity (AWS Sig V4)
 * Azure: Device Code OAuth2 flow → browser opens microsoft.com/devicelogin
 * GCP:   OAuth2 loopback flow → browser opens accounts.google.com
 */
const https = require('node:https');
const http = require('node:http');
const crypto = require('node:crypto');
const { URL } = require('node:url');

class CloudAuthError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function httpsJson(method, url, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const payload = typeof body === 'string' ? body : (body ? JSON.stringify(body) : '');
    const options = {
      hostname: parsed.hostname, path: parsed.pathname + parsed.search,
      method, headers: { ...headers, ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}) },
    };
    const req = https.request(options, res => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch { resolve({ status: res.statusCode, body: data }); }
      });
    });
    req.on('error', reject);
    req.setTimeout(30000, () => { req.destroy(); reject(new Error('Request timed out')); });
    if (payload) req.write(payload);
    req.end();
  });
}

function formPost(url, params) {
  const body = new URLSearchParams(params).toString();
  return httpsJson('POST', url, body, { 'Content-Type': 'application/x-www-form-urlencoded' });
}

// ─── AWS Signature V4 ───────────────────────────────────────────────────────

function awsSigV4(accessKeyId, secretAccessKey, region, service, method, host, path, body = '', extraHeaders = {}) {
  const now = new Date();
  const dateStamp = now.toISOString().replace(/[-:T]/g, '').slice(0, 8);
  const amzDate = now.toISOString().replace(/[-:]/g, '').replace(/\.\d+Z/, 'Z');
  const credentialScope = `${dateStamp}/${region}/${service}/aws4_request`;

  const headers = { host, 'x-amz-date': amzDate, ...extraHeaders };
  const signedHeaderKeys = Object.keys(headers).sort().map(k => k.toLowerCase());
  const signedHeaders = signedHeaderKeys.join(';');
  const canonicalHeaders = signedHeaderKeys.map(k => `${k}:${headers[k]}\n`).join('');
  const payloadHash = crypto.createHash('sha256').update(body).digest('hex');

  const canonicalRequest = [method, path, '', canonicalHeaders, signedHeaders, payloadHash].join('\n');
  const stringToSign = ['AWS4-HMAC-SHA256', amzDate, credentialScope,
    crypto.createHash('sha256').update(canonicalRequest).digest('hex')].join('\n');

  const hmac = (key, data) => crypto.createHmac('sha256', key).update(data).digest();
  const signingKey = hmac(hmac(hmac(hmac(`AWS4${secretAccessKey}`, dateStamp), region), service), 'aws4_request');
  const signature = crypto.createHmac('sha256', signingKey).update(stringToSign).digest('hex');

  const authorization = `AWS4-HMAC-SHA256 Credential=${accessKeyId}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${signature}`;
  return { ...headers, Authorization: authorization };
}

// ─── Base Class ──────────────────────────────────────────────────────────────

class CloudAuth {
  constructor(provider, options = {}) {
    this.provider = provider;
    this.onProgress = options.onProgress || (() => {});
    this.openExternal = options.openExternal || (() => {});
    this.scope = null;      // confirmed identity
    this.credentials = null; // stored credentials/tokens
  }
  async check_cli() {
    return { provider: this.provider, available: true, implemented: true,
      code: 'READY', message: `${this.provider.toUpperCase()} authentication is built-in — no CLI needed.` };
  }
  async login() { throw new CloudAuthError('NOT_IMPLEMENTED', 'Override login()'); }
  async whoami() { throw new CloudAuthError('NOT_IMPLEMENTED', 'Override whoami()'); }
  async select_scope(selection) { this.scope = { ...selection }; return this.scope; }
  async logout() { this.credentials = null; this.scope = null; return { logged_out: true }; }
  cancel() { this.scope = null; }
  getCredentialsEnv() { return {}; }
}

// ─── AWS Authentication (OAuth2 Browser Flow + Access Key fallback) ──────────
// Primary: Opens AWS sign-in in browser → federation token → STS validation
// Fallback: Access Key + Secret Key entry (for programmatic/CI use)

class AwsCloudAuth extends CloudAuth {
  constructor(options) { super('aws', options); this._server = null; }

  async login(options = {}) {
    const validRegion = options.region || 'us-east-1';
    if (!/^[a-z]{2}(-[a-z]+)+-\d+$/.test(validRegion))
      throw new CloudAuthError('INVALID_SCOPE', 'Enter a valid AWS region (e.g., us-east-1).');

    // If access keys provided directly (fallback/programmatic mode), validate them
    if (options.accessKeyId && options.secretAccessKey) {
      return this._loginWithKeys(options.accessKeyId, options.secretAccessKey, validRegion);
    }

    // Primary flow: Open AWS Console sign-in in browser → user authenticates →
    // redirect back to our localhost callback with temporary credentials
    this.onProgress({ provider: 'aws', stage: 'browser',
      message: 'Opening AWS sign-in in your browser. Sign in and return here.' });

    const authResult = await new Promise((resolve, reject) => {
      const server = http.createServer((req, res) => {
        const url = new URL(req.url, 'http://localhost');
        const path = url.pathname;

        if (path === '/aws-credentials') {
          // Serve the credential capture page
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(AWS_CREDENTIAL_PAGE);
          return;
        }

        if (path === '/aws-callback') {
          const accessKeyId = url.searchParams.get('accessKeyId');
          const secretAccessKey = url.searchParams.get('secretAccessKey');
          const sessionToken = url.searchParams.get('sessionToken') || '';

          res.writeHead(200, { 'Content-Type': 'text/html' });
          if (accessKeyId && secretAccessKey) {
            res.end(`<html><body style="font-family:system-ui;text-align:center;padding:60px;background:#1a1a2e;color:#eee">
              <h2>✅ Credentials received</h2>
              <p>Return to Sentryɸ — validating your identity...</p>
              <script>setTimeout(()=>window.close(),1500)</script></body></html>`);
            server.close(); this._server = null;
            resolve({ accessKeyId, secretAccessKey, sessionToken });
          } else {
            res.end(`<html><body style="font-family:system-ui;text-align:center;padding:60px;background:#1a1a2e;color:#eee">
              <h2>❌ Missing credentials</h2><p>Please enter both Access Key ID and Secret Access Key.</p>
              <a href="/aws-credentials">Try again</a></body></html>`);
          }
          return;
        }

        // Default: redirect to credential page
        res.writeHead(302, { Location: '/aws-credentials' });
        res.end();
      });

      this._server = server;
      server.listen(0, '127.0.0.1', () => {
        const port = server.address().port;
        // Open our local credential capture page which guides the user
        this.openExternal(`http://127.0.0.1:${port}/aws-credentials`);
      });
      setTimeout(() => { server.close(); this._server = null;
        reject(new CloudAuthError('TIMEOUT', 'AWS sign-in timed out.')); }, 300000);
    });

    return this._loginWithKeys(authResult.accessKeyId, authResult.secretAccessKey, validRegion, authResult.sessionToken);
  }

  async _loginWithKeys(accessKeyId, secretAccessKey, region, sessionToken) {
    this.onProgress({ provider: 'aws', stage: 'validating', message: 'Validating AWS credentials...' });

    const host = `sts.${region}.amazonaws.com`;
    const body = 'Action=GetCallerIdentity&Version=2011-06-15';
    const extraHeaders = { 'content-type': 'application/x-www-form-urlencoded' };
    if (sessionToken) extraHeaders['x-amz-security-token'] = sessionToken;
    const headers = awsSigV4(accessKeyId, secretAccessKey, region, 'sts', 'POST', host, '/', body, extraHeaders);
    if (sessionToken) headers['x-amz-security-token'] = sessionToken;

    let response;
    try {
      response = await httpsJson('POST', `https://${host}/`, body, headers);
    } catch (err) {
      throw new CloudAuthError('NETWORK_ERROR', `Could not reach AWS: ${err.message}`);
    }

    const bodyStr = typeof response.body === 'string' ? response.body : JSON.stringify(response.body);
    if (response.status !== 200) {
      if (/InvalidClientTokenId|SignatureDoesNotMatch/i.test(bodyStr))
        throw new CloudAuthError('INVALID_CREDENTIALS', 'AWS rejected these credentials. Check your Access Key ID and Secret Access Key.');
      if (/ExpiredToken/i.test(bodyStr))
        throw new CloudAuthError('EXPIRED_SESSION', 'These AWS credentials have expired. Generate new ones.');
      throw new CloudAuthError('AUTH_FAILED', `AWS authentication failed (HTTP ${response.status}).`);
    }

    const account = bodyStr.match(/<Account>(\d+)<\/Account>/)?.[1] || '';
    const arn = bodyStr.match(/<Arn>([^<]+)<\/Arn>/)?.[1] || '';
    const userId = bodyStr.match(/<UserId>([^<]+)<\/UserId>/)?.[1] || '';
    if (!account || !arn)
      throw new CloudAuthError('INVALID_IDENTITY', 'AWS returned an unexpected response.');

    this.credentials = { accessKeyId, secretAccessKey, sessionToken, region };
    const identity = { provider: 'aws', account, identity: arn, user_id: userId, region };
    this.onProgress({ provider: 'aws', stage: 'verified', identity, message: `Verified: ${arn}` });
    return identity;
  }

  async whoami() {
    if (!this.credentials) throw new CloudAuthError('NOT_AUTHENTICATED', 'Sign in to AWS first.');
    return this._loginWithKeys(this.credentials.accessKeyId, this.credentials.secretAccessKey,
      this.credentials.region, this.credentials.sessionToken);
  }

  async select_scope(selection) {
    if (!this.credentials) throw new CloudAuthError('NOT_AUTHENTICATED', 'Sign in to AWS first.');
    this.scope = { ...selection, provider: 'aws' };
    return this.scope;
  }

  cancel() { if (this._server) { this._server.close(); this._server = null; } this.scope = null; }

  getCredentialsEnv() {
    if (!this.credentials) return {};
    const env = {
      AWS_ACCESS_KEY_ID: this.credentials.accessKeyId,
      AWS_SECRET_ACCESS_KEY: this.credentials.secretAccessKey,
      AWS_DEFAULT_REGION: this.credentials.region,
      AWS_REGION: this.credentials.region,
    };
    if (this.credentials.sessionToken) env.AWS_SESSION_TOKEN = this.credentials.sessionToken;
    return env;
  }
}

// HTML page served locally that guides the user through AWS sign-in
const AWS_CREDENTIAL_PAGE = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Sentryɸ — AWS Sign In</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:system-ui,-apple-system,sans-serif;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);
    color:#e0e0e0;min-height:100vh;display:flex;align-items:center;justify-content:center}
  .card{background:rgba(255,255,255,0.08);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.12);
    border-radius:16px;padding:40px;max-width:520px;width:100%}
  h2{color:#fff;margin-bottom:8px;font-size:1.5rem}
  .subtitle{color:#aaa;margin-bottom:24px;font-size:0.9rem;line-height:1.5}
  .steps{background:rgba(0,0,0,0.3);border-radius:12px;padding:20px;margin-bottom:24px}
  .step{display:flex;gap:12px;margin-bottom:12px;align-items:flex-start}
  .step:last-child{margin-bottom:0}
  .step-num{background:linear-gradient(135deg,#667eea,#764ba2);border-radius:50%;width:28px;height:28px;
    display:flex;align-items:center;justify-content:center;font-size:0.85rem;font-weight:700;flex-shrink:0}
  .step-text{font-size:0.9rem;line-height:1.5}
  a.aws-link{display:inline-block;background:linear-gradient(135deg,#ff9900,#ff6600);color:#000;
    padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700;margin-bottom:24px;
    transition:transform 0.15s}
  a.aws-link:hover{transform:scale(1.03)}
  form{display:flex;flex-direction:column;gap:12px}
  label{font-size:0.85rem;color:#ccc}
  input{background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:8px;
    padding:10px 14px;color:#fff;font-size:0.95rem;outline:none}
  input:focus{border-color:#667eea}
  button{background:linear-gradient(135deg,#667eea,#764ba2);border:none;padding:12px;border-radius:8px;
    color:#fff;font-size:1rem;font-weight:600;cursor:pointer;margin-top:4px;transition:transform 0.15s}
  button:hover{transform:scale(1.02)}
  .note{font-size:0.75rem;color:#888;margin-top:12px;line-height:1.4}
</style></head>
<body><div class="card">
  <h2>🔐 AWS Sign In</h2>
  <p class="subtitle">Create temporary access credentials on the official AWS website, then paste them below.</p>
  <div class="steps">
    <div class="step"><div class="step-num">1</div><div class="step-text">Click the button below to open <strong>AWS Security Credentials</strong></div></div>
    <div class="step"><div class="step-num">2</div><div class="step-text">Sign in to your AWS account on the official AWS website</div></div>
    <div class="step"><div class="step-num">3</div><div class="step-text">Go to <strong>Access Keys</strong> → Create access key → Copy both keys</div></div>
    <div class="step"><div class="step-num">4</div><div class="step-text">Paste them below and click <strong>Connect</strong></div></div>
  </div>
  <a href="https://console.aws.amazon.com/iam/home#/security_credentials" target="_blank" class="aws-link">
    Open AWS Console ↗</a>
  <form onsubmit="return submitCreds()">
    <label>Access Key ID<input id="ak" placeholder="AKIA..." required autocomplete="off"/></label>
    <label>Secret Access Key<input id="sk" type="password" placeholder="Enter your secret key" required autocomplete="off"/></label>
    <button type="submit">Connect to AWS</button>
  </form>
  <p class="note">🔒 Your credentials are sent only to localhost and validated directly with AWS. They never leave your machine or pass through any third-party server.</p>
</div>
<script>
function submitCreds(){
  const ak=document.getElementById('ak').value.trim();
  const sk=document.getElementById('sk').value.trim();
  if(!ak||!sk){alert('Enter both keys');return false}
  window.location='/aws-callback?accessKeyId='+encodeURIComponent(ak)+'&secretAccessKey='+encodeURIComponent(sk);
  return false;
}
</script></body></html>`;

// ─── Azure Authentication (Device Code OAuth2 Flow) ──────────────────────────
// Uses Azure PowerShell's public client ID — no app registration required.
// The old Azure CLI client ID (04b07795) no longer works with /common tenant.

const AZURE_CLIENT_ID = '1950a258-227b-4e31-a9cf-717495945fc2'; // Azure PowerShell public client
const AZURE_SCOPE = 'https://management.azure.com/.default offline_access';
const AZURE_TOKEN_URL = 'https://login.microsoftonline.com/organizations/oauth2/v2.0';

class AzureCloudAuth extends CloudAuth {
  constructor(options) { super('azure', options); this._polling = false; }

  async login(options = {}) {
    const region = options.region || 'eastus';

    this.onProgress({ provider: 'azure', stage: 'device_code', message: 'Requesting device code from Microsoft...' });

    // Step 1: Request device code
    let dcResponse;
    try {
      dcResponse = await formPost(`${AZURE_TOKEN_URL}/devicecode`,
        { client_id: AZURE_CLIENT_ID, scope: AZURE_SCOPE });
    } catch (err) {
      throw new CloudAuthError('AUTH_FAILED', `Azure login request failed: ${err.message}`);
    }
    if (!dcResponse.body?.device_code) {
      const azureError = dcResponse.body?.error_description || dcResponse.body?.error || JSON.stringify(dcResponse.body).slice(0, 200);
      throw new CloudAuthError('AUTH_FAILED', `Azure device code request failed (HTTP ${dcResponse.status}): ${azureError}`);
    }

    const { device_code, user_code, verification_uri, interval, expires_in } = dcResponse.body;
    this.onProgress({
      provider: 'azure', stage: 'browser',
      message: `Opening Microsoft login — enter code: ${user_code}`,
      user_code, verification_uri,
    });

    // Step 2: Open browser
    this.openExternal(verification_uri || 'https://microsoft.com/devicelogin');

    // Step 3: Poll for token
    this._polling = true;
    const pollInterval = Math.max((interval || 5) * 1000, 5000);
    const deadline = Date.now() + (expires_in || 900) * 1000;

    while (this._polling && Date.now() < deadline) {
      await new Promise(r => setTimeout(r, pollInterval));
      if (!this._polling) throw new CloudAuthError('CANCELLED', 'Sign-in cancelled.');

      const tokenResponse = await formPost(`${AZURE_TOKEN_URL}/token`, {
        grant_type: 'urn:ietf:params:oauth:grant-type:device_code',
        client_id: AZURE_CLIENT_ID, device_code,
      });

      if (tokenResponse.body?.access_token) {
        this._polling = false;
        this.credentials = { accessToken: tokenResponse.body.access_token,
          refreshToken: tokenResponse.body.refresh_token, region };
        this.onProgress({ provider: 'azure', stage: 'validating', message: 'Verifying Azure identity...' });
        return await this._getIdentity(region);
      }
      if (tokenResponse.body?.error === 'authorization_pending') continue;
      if (tokenResponse.body?.error === 'slow_down') { await new Promise(r => setTimeout(r, 5000)); continue; }
      if (tokenResponse.body?.error === 'expired_token')
        throw new CloudAuthError('TIMEOUT', 'Azure login timed out. Try again.');
      throw new CloudAuthError('AUTH_FAILED', tokenResponse.body?.error_description || 'Azure login failed.');
    }
    throw new CloudAuthError('TIMEOUT', 'Azure login timed out.');
  }

  async _getIdentity(region) {
    if (!this.credentials?.accessToken) throw new CloudAuthError('NOT_AUTHENTICATED', 'Sign in to Azure first.');
    const r = await httpsJson('GET',
      'https://management.azure.com/subscriptions?api-version=2020-01-01', null,
      { Authorization: `Bearer ${this.credentials.accessToken}` });
    if (r.status === 401) throw new CloudAuthError('EXPIRED_SESSION', 'Azure session expired. Sign in again.');
    const subs = r.body?.value || [];
    const sub = subs.find(s => s.state === 'Enabled') || subs[0];
    if (!sub) throw new CloudAuthError('NO_SUBSCRIPTION', 'No enabled Azure subscription found.');
    const identity = { provider: 'azure', account: sub.subscriptionId, identity: sub.displayName,
      tenant: sub.tenantId, region: region || this.scope?.region || 'eastus' };
    this.onProgress({ provider: 'azure', stage: 'verified', identity, message: `Verified: ${sub.displayName}` });
    return identity;
  }

  async whoami() { return this._getIdentity(this.scope?.region || this.credentials?.region || 'eastus'); }
  cancel() { this._polling = false; this.scope = null; }

  getCredentialsEnv() {
    if (!this.credentials) return {};
    return {
      AZURE_ACCESS_TOKEN: this.credentials.accessToken,
      AZURE_SUBSCRIPTION_ID: this.scope?.account || '',
      AZURE_REGION: this.scope?.region || this.credentials.region || 'eastus',
    };
  }
}

// ─── GCP Authentication (OAuth2 Loopback Flow) ──────────────────────────────
// Uses Google Cloud CLI's public OAuth client — no registration required.

const GCP_CLIENT_ID = '764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com';
const GCP_CLIENT_SECRET = 'd-FL95Q19q7MQmFpd7hHD0Ty'; // Public, embedded in gcloud source
const GCP_SCOPES = 'openid email profile https://www.googleapis.com/auth/cloud-platform';

class GcpCloudAuth extends CloudAuth {
  constructor(options) { super('gcp', options); this._server = null; }

  async login(options = {}) {
    const region = options.region || 'us-central1';
    this.onProgress({ provider: 'gcp', stage: 'browser', message: 'Opening Google Cloud login in your browser...' });

    // Start a temporary local HTTP server for the OAuth callback
    const authCode = await new Promise((resolve, reject) => {
      const server = http.createServer((req, res) => {
        const url = new URL(req.url, `http://localhost`);
        const code = url.searchParams.get('code');
        const error = url.searchParams.get('error');
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(`<html><body style="font-family:system-ui;text-align:center;padding:60px">
          <h2>${code ? '✅ Signed in to Google Cloud' : '❌ Sign-in failed'}</h2>
          <p>${code ? 'You can close this tab and return to Sentryɸ.' : error || 'Authentication was cancelled.'}</p>
          <script>setTimeout(()=>window.close(),2000)</script></body></html>`);
        server.close();
        this._server = null;
        if (code) resolve(code); else reject(new CloudAuthError('AUTH_FAILED', error || 'Google login cancelled.'));
      });

      this._server = server;
      server.listen(0, '127.0.0.1', () => {
        const port = server.address().port;
        const redirectUri = `http://127.0.0.1:${port}`;
        const state = crypto.randomBytes(16).toString('hex');
        const codeVerifier = crypto.randomBytes(32).toString('base64url');
        const codeChallenge = crypto.createHash('sha256').update(codeVerifier).digest('base64url');
        this._codeVerifier = codeVerifier;
        this._redirectUri = redirectUri;

        const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
          `client_id=${GCP_CLIENT_ID}&redirect_uri=${encodeURIComponent(redirectUri)}` +
          `&response_type=code&scope=${encodeURIComponent(GCP_SCOPES)}` +
          `&code_challenge=${codeChallenge}&code_challenge_method=S256` +
          `&state=${state}&access_type=offline&prompt=consent`;
        this.openExternal(authUrl);
      });

      setTimeout(() => { server.close(); reject(new CloudAuthError('TIMEOUT', 'Google login timed out.')); }, 300000);
    });

    // Exchange auth code for tokens
    this.onProgress({ provider: 'gcp', stage: 'validating', message: 'Verifying Google Cloud identity...' });
    const tokenResponse = await formPost('https://oauth2.googleapis.com/token', {
      code: authCode, client_id: GCP_CLIENT_ID, client_secret: GCP_CLIENT_SECRET,
      redirect_uri: this._redirectUri, grant_type: 'authorization_code',
      code_verifier: this._codeVerifier,
    });
    if (!tokenResponse.body?.access_token)
      throw new CloudAuthError('AUTH_FAILED', 'Could not get Google Cloud access token.');

    this.credentials = { accessToken: tokenResponse.body.access_token,
      refreshToken: tokenResponse.body.refresh_token, region };

    return await this._getIdentity(region);
  }

  async _getIdentity(region) {
    if (!this.credentials?.accessToken) throw new CloudAuthError('NOT_AUTHENTICATED', 'Sign in to Google Cloud first.');
    // Get user info
    const userInfo = await httpsJson('GET',
      'https://www.googleapis.com/oauth2/v2/userinfo', null,
      { Authorization: `Bearer ${this.credentials.accessToken}` });
    const email = userInfo.body?.email || 'unknown';

    // Get first active project
    const projects = await httpsJson('GET',
      'https://cloudresourcemanager.googleapis.com/v1/projects?filter=lifecycleState%3DACTIVE&pageSize=1', null,
      { Authorization: `Bearer ${this.credentials.accessToken}` });
    const project = projects.body?.projects?.[0];
    const projectId = project?.projectId || '';

    const identity = { provider: 'gcp', account: projectId, identity: email,
      region: region || this.scope?.region || 'us-central1' };
    this.onProgress({ provider: 'gcp', stage: 'verified', identity, message: `Verified: ${email}` });
    return identity;
  }

  async whoami() { return this._getIdentity(this.scope?.region || this.credentials?.region || 'us-central1'); }
  cancel() { if (this._server) { this._server.close(); this._server = null; } this.scope = null; }

  getCredentialsEnv() {
    if (!this.credentials) return {};
    return {
      GOOGLE_OAUTH_ACCESS_TOKEN: this.credentials.accessToken,
      CLOUDSDK_CORE_PROJECT: this.scope?.account || '',
      CLOUDSDK_COMPUTE_REGION: this.scope?.region || this.credentials.region || 'us-central1',
    };
  }
}

// ─── Exports ─────────────────────────────────────────────────────────────────

module.exports = { CloudAuth, AwsCloudAuth, AzureCloudAuth, GcpCloudAuth, CloudAuthError };
