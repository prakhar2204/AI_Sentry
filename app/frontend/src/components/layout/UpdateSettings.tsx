import type { DesktopUpdate } from '../../electron';
import React, { useEffect, useRef, useState } from 'react';

export function UpdateSettings({ startup }: { startup: boolean }) {
  const [state, setState] = useState<DesktopUpdate | null>(null);
  const [error, setError] = useState('');
  const idle = useRef(true);
  const manual = useRef(false);
  const api = window.electronAPI;
  useEffect(() => {
    let live = true;
    let received = false;
    const off = api?.onUpdate?.(data => { received = true; if (live) setState(data); });
    api?.updateCommand?.('state').then(data => {
      if (live && !received) {
        setState(data);
        if (!data) setError('Restart the desktop app to load update settings.');
      }
    }).catch(() => { if (live) setError('Update settings could not be loaded. Restart the desktop app.'); });
    const markBusy = (event: Event) => {
      if (!(event.target instanceof Element && event.target.closest('.update-settings'))) idle.current = false;
    };
    window.addEventListener('pointerdown', markBusy, true);
    window.addEventListener('keydown', markBusy, true);
    return () => {
      live = false; off?.();
      window.removeEventListener('pointerdown', markBusy, true);
      window.removeEventListener('keydown', markBusy, true);
    };
  }, [api]);
  useEffect(() => {
    if (state?.stage === 'ready' && (state.automatic || manual.current) && startup && idle.current) {
      void api?.updateCommand?.('install').catch(() => setError('Restart to finish installing.'));
    }
  }, [state, startup, api]);
  async function command(action: 'auto' | 'download' | 'retry' | 'queue', value?: boolean) {
    setError('');
    if (action === 'download' || action === 'queue') manual.current = true;
    if (action === 'auto') manual.current = false;
    try {
      const result = await api?.updateCommand?.(action, value);
      if (result) setState(result);
    }
    catch { setError('Update settings could not be saved. Try again.'); }
  }
  if (!state) return <details className="update-settings"><summary>Updates</summary>
    <div className="update-settings__panel" role="status">
      {error || (api ? 'Loading update settings…' : 'Open the desktop app to manage automatic updates.')}
    </div>
  </details>;
  const labels = {checking:'Checking for updates…', current:'Up to date', available:'Update available',
    development:'Development mode',
    downloading:'Downloading ' + state.percent + '%', ready:'Update ready', error:'Could not check or download the release'};
  return <details className="update-settings"><summary>{['available','ready','downloading'].includes(state.stage) ? labels[state.stage] : 'Updates'}</summary>
    <div className="update-settings__panel">
      <p>SentryPhi {state.currentVersion}</p>
      <label><input type="checkbox" checked={state.automatic} onChange={e => void command('auto', e.target.checked)}/> Automatic updates</label>
      <p role="status">{error || labels[state.stage]} {state.version}</p>
      {state.stage === 'development' && <p>Your preference is saved. GitHub release downloads and installation are available in an installed build. This development session receives source changes live.</p>}
      {state.stage === 'available' && <button onClick={() => void command('download')}>Download update</button>}
      {state.stage === 'ready' && (state.installOnExit ? <small>Ready to install when you quit.</small> : <button onClick={() => void command('queue')}>Install update on exit</button>)}
      {state.stage === 'error' && <button onClick={() => void command('retry')}>Retry</button>}
      {state.stage === 'current' && <button onClick={() => void command('retry')}>Check for updates</button>}
    </div></details>;
}
