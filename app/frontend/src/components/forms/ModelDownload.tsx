import React, { useEffect, useRef, useState } from 'react';

interface Download { download_id: string; status: string; downloaded_bytes: number; total_bytes?: number; path?: string; name?: string; error?: string; }

export function ModelDownload({ onComplete, onBusy }: { onComplete: (path: string, name: string) => void; onBusy: (busy: boolean) => void }) {
  const [url, setUrl] = useState('');
  const [job, setJob] = useState<Download | null>(null);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);
  const current = useRef<string | null>(null);
  const alive = useRef(true);
  const busy = starting || job?.status === 'running';
  useEffect(() => { onBusy(busy); }, [busy, onBusy]);
  useEffect(() => { alive.current = true; return () => {
    alive.current = false;
    onBusy(false);
    if (current.current) void window.electronAPI?.runBackendCommand({ command: 'model:download_cancel', download_id: current.current }).catch(() => {});
  }; }, []);
  useEffect(() => {
    if (job?.status !== 'running') return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const update = await window.electronAPI!.runBackendCommand({ command: 'model:download_status', download_id: job.download_id }) as Download;
        if (cancelled) return;
        setJob(update);
        if (update.status !== 'running') current.current = null;
        if (update.status === 'complete' && update.path) onComplete(update.path, update.name || 'Downloaded model.gguf');
        if (update.error) setError(update.error);
      } catch (e) { if (!cancelled) {
        setError(String(e)); setJob({ ...job, status: 'failed' });
        void window.electronAPI?.runBackendCommand({ command: 'model:download_cancel', download_id: job.download_id }).catch(() => {});
      } }
    }, 700);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [job, onComplete]);
  async function start() {
    setStarting(true); setError('');
    try {
      if (!window.electronAPI) throw new Error('Model downloads require the desktop app');
      const result = await window.electronAPI.runBackendCommand({ command: 'model:download', url }) as Download;
      if (!alive.current) {
        await window.electronAPI.runBackendCommand({ command: 'model:download_cancel', download_id: result.download_id });
        return;
      }
      current.current = result.download_id; setJob(result);
    } catch (e) { if (alive.current) setError(String(e)); }
    finally { if (alive.current) setStarting(false); }
  }
  async function cancel() {
    try { await window.electronAPI?.runBackendCommand({ command: 'model:download_cancel', download_id: job?.download_id }); }
    catch (e) { setError(String(e)); }
  }
  return <div className="input-page__native-picker">
    <label htmlFor="model-download-url">Public model download link</label>
    <input id="model-download-url" className="text-input" type="url" disabled={busy} value={url}
      onChange={e => setUrl(e.target.value)} placeholder="https://…/model.gguf" />
    <p>Direct HTTPS GGUF links are downloaded to this app’s model folder before scanning. For private repositories or Transformers packages, download the complete package and browse to it.</p>
    <button type="button" className="button button--secondary" disabled={busy || !url.trim()} onClick={start}>Download model</button>
    {busy && <button type="button" className="button button--secondary" disabled={!job} onClick={cancel}>Cancel download</button>}
    {job && <p role="status">{job.status} · {(job.downloaded_bytes / 1024 ** 2).toFixed(1)} MiB{job.total_bytes ? ` / ${(job.total_bytes / 1024 ** 2).toFixed(1)} MiB` : ''}</p>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
