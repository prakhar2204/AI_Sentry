import React, { useEffect, useMemo, useRef, useState } from 'react';
import { cloudAuth, type CloudIdentity, type CloudProvider } from '../../services/cloudAuthService';

const PROVIDER_LABEL: Record<CloudProvider, string> = { aws: 'AWS', azure: 'Azure', gcp: 'Google Cloud' };

export function CloudLoginPanel({ provider, initialRegion, onConfirmed, onBack }: {
  provider: CloudProvider;
  initialRegion?: string;
  onConfirmed: (identity: CloudIdentity) => void;
  onBack: () => void;
}) {
  const auth = useMemo(() => cloudAuth(provider), [provider]);
  const [identity, setIdentity] = useState<CloudIdentity | null>(null);
  const [region, setRegion] = useState(initialRegion || (provider === 'azure' ? 'eastus' : provider === 'gcp' ? 'us-central1' : 'us-east-1'));
  const [account, setAccount] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('Ready to sign in — no CLI installation needed.');
  const [error, setError] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const mounted = useRef(true);
  const pendingLogin = useRef(false);

  useEffect(() => {
    mounted.current = true;
    const unsubscribe = window.electronAPI?.onCloudAuthProgress?.(event => {
      if (event.provider === provider && mounted.current) setMessage(event.message);
    });
    return () => { mounted.current = false; unsubscribe?.(); if (pendingLogin.current) void auth.cancel().catch(() => {}); };
  }, [auth, provider]);

  async function login() {
    setBusy(true); setError(''); setIdentity(null); setConfirmed(false); pendingLogin.current = true;
    try {
      // All providers now use browser-based login — just pass the region
      const result = await auth.login({ region });
      if (mounted.current) { setIdentity(result); setAccount(result.account); }
    } catch (e: any) { if (mounted.current) setError(e.message || String(e)); }
    finally { pendingLogin.current = false; if (mounted.current) setBusy(false); }
  }

  async function confirmScope() {
    if (!identity || !confirmed) return;
    setBusy(true); setError('');
    try { onConfirmed(await auth.select_scope({ ...identity, account, region })); }
    catch (e: any) { setError(e.message || String(e)); }
    finally { if (mounted.current) setBusy(false); }
  }

  async function signOut() {
    setBusy(true); setError('');
    try { await auth.logout(); setIdentity(null); setConfirmed(false); setMessage('Signed out.'); }
    catch (e: any) { setError(e.message || String(e)); }
    finally { setBusy(false); }
  }

  const label = PROVIDER_LABEL[provider];

  return <div className="deploy-flow__panel">
    <h2 className="deploy-flow__panel-title">Sign in to {label}</h2>
    <p className="deploy-flow__panel-desc">
      {provider === 'aws'
        ? 'Your browser will open the official AWS sign-in page. Create or copy your credentials and connect.'
        : provider === 'azure'
        ? 'Your browser will open the official Microsoft login page. Sign in and return here.'
        : 'Your browser will open the official Google login page. Sign in and return here.'}
    </p>
    <p role="status" className="deploy-flow__status">{message}</p>
    {error && <p role="alert" className="deploy-error__message">{error}</p>}

    {!identity && <>
      {/* Region field (all providers) */}
      <div className="deploy-auth__field">
        <label htmlFor="cloud-region">{label} region</label>
        <input id="cloud-region" className="deploy-auth__input" value={region} disabled={busy}
          onChange={e => { setRegion(e.target.value); setConfirmed(false); }}
          placeholder={provider === 'aws' ? 'us-east-1' : provider === 'azure' ? 'eastus' : 'us-central1'} />
      </div>

      <div className="deploy-flow__actions">
        <button id="cloud-login" className="deploy-flow__btn deploy-flow__btn--primary" disabled={busy} onClick={login}>
          {busy ? 'Waiting for sign-in…' : `Sign in with ${label} (opens browser)`}
        </button>
        {busy && <button id="cloud-login-cancel" className="deploy-flow__btn deploy-flow__btn--ghost"
          onClick={() => void auth.cancel().catch(e => setError(String(e)))}>Cancel</button>}
      </div>
    </>}

    {identity && <>
      {provider !== 'aws' && <div className="deploy-auth__field">
        <label>{provider === 'azure' ? 'Azure subscription ID' : 'Google Cloud project ID'}</label>
        <input className="deploy-auth__input" value={account} disabled={busy}
          onChange={e => { setAccount(e.target.value); setConfirmed(false); }} />
      </div>}
      <h3>Confirm deployment account</h3>
      <dl>
        <dt>Identity</dt><dd><code>{identity.identity}</code></dd>
        <dt>Account</dt><dd>{identity.account}</dd>
        <dt>Region</dt><dd>{region}</dd>
      </dl>
      <label><input id="cloud-scope-confirm" type="checkbox" checked={confirmed} disabled={busy}
        onChange={e => setConfirmed(e.target.checked)} /> Use this account and region for deployment</label>
      <div className="deploy-flow__actions">
        <button id="cloud-scope-continue" className="deploy-flow__btn deploy-flow__btn--primary"
          disabled={!confirmed || busy} onClick={confirmScope}>Confirm account and continue</button>
        <button className="deploy-flow__btn deploy-flow__btn--ghost" disabled={busy} onClick={signOut}>Sign out</button>
        <button className="deploy-flow__btn deploy-flow__btn--ghost" disabled={busy} onClick={login}>Sign in again</button>
      </div>
    </>}

    <button className="deploy-flow__btn deploy-flow__btn--ghost" disabled={busy} onClick={onBack}>Back to providers</button>
  </div>;
}
