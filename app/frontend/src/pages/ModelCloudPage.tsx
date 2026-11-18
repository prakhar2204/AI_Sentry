import React, { useEffect, useState } from 'react';
import '../styles/model-cloud.css';
import { useReportContext } from '../store/ReportContext';
import { useScanContext } from '../store/ScanContext';
import type { DeployProvider, ManagedModelConfig } from '../services/deployIpcTypes';

interface ModelProfile { source: string; name: string; format: string; fingerprint: string; weights_gib: number; required_ram_gib: number; recommended_vram_gib: number; }
interface Offer {
  provider: DeployProvider; service: string; config: ManagedModelConfig; fits: boolean; reason: string;
  model: ModelProfile; instances: { id: string; ram_gib: number; vcpus: number; vram_gib: number }[];
  estimate: { monthly_usd: number; hourly_usd: number; source: string; as_of: string; warnings: string[] };
}
interface Comparison { model: ModelProfile; offers: Offer[]; }
const NAMES = { aws: 'AWS', azure: 'Azure', gcp: 'Google Cloud', private: 'Personal / private cloud' };

export function ModelCloudPage({ onBack, onSelect }: {
  onBack: () => void; onSelect: (provider: DeployProvider, config: ManagedModelConfig) => void;
}) {
  const { state: reportState } = useReportContext();
  const { state: scanState } = useScanContext();
  const report = reportState.report as unknown as { model_profile?: ModelProfile; meta?: { scan_id?: string }; engine?: { error?: string } } | null;
  const source = report?.model_profile?.source || scanState.local_model_path;
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [edits, setEdits] = useState<Record<string, Record<string, string | number>>>({});
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function calculate(reset = false) {
    if (!source || !report?.model_profile?.fingerprint) return;
    setBusy(true); setError('');
    try {
      if (!window.electronAPI) throw new Error('Model inspection requires the desktop application');
      const result = await window.electronAPI.runBackendCommand({ command: 'cloud:recommend', source,
        scanned_fingerprint: report.model_profile.fingerprint, edits: reset ? {} : edits }) as Comparison;
      setComparison(result); setDirty(false);
      if (reset) setEdits({});
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }
  useEffect(() => { void calculate(true); }, [source, report?.model_profile?.fingerprint]);
  function edit(provider: string, field: string, value: string | number) {
    setEdits(previous => ({ ...previous, [provider]: { ...previous[provider], [field]: value } }));
    setDirty(true);
  }
  return <div className="deploy-flow">
    <h1>Deploy the scanned model</h1>
    <p>Compare configurations for your model, edit them if needed, then select a provider and sign in. Report download is optional.</p>
    {!report?.model_profile && <p role="alert">A completed artifact scan is required to recommend hosting for your own model. An API URL alone does not provide model weights to deploy; scan a local model package first.</p>}
    {report?.model_profile && <p><strong>{report.model_profile.name}</strong> · {report.model_profile.format} · {report.model_profile.weights_gib} GiB weights · Scan {report.meta?.scan_id}</p>}
    {error && <p role="alert" className="deploy-error__message">{error}</p>}
    {busy && <p role="status">Inspecting model and calculating configurations…</p>}
    <div className="deploy-flow__actions">
      <button className="button button--secondary" onClick={onBack}>Back to results</button>
      <button className="button button--primary" disabled={busy || !report?.model_profile} onClick={() => calculate(true)}>Recommend settings</button>
      <button className="button button--secondary" disabled={busy || !dirty} onClick={() => calculate()}>Recalculate edited costs</button>
    </div>
    {dirty && <p role="status">Settings changed. Recalculate before selecting a deployment.</p>}
    <div className="model-cloud-grid">
      {comparison?.offers.map(offer => {
        const changed = edits[offer.provider] || {};
        const value = (key: string, fallback: string | number) => changed[key] ?? fallback;
        const numeric = (key: string, label: string, fallback: number, min: number, max: number) => <label className="deploy-cfg__field" key={key}>
          {label}<input className="deploy-cfg__input" type="number" min={min} max={max} disabled={busy}
            value={value(key, fallback)} onChange={e => edit(offer.provider, key, e.target.value)} />
        </label>;
        return <section className="deploy-flow__panel" key={offer.provider} aria-label={NAMES[offer.provider]}>
          <h2>{NAMES[offer.provider]}</h2><p>{offer.service}</p>
          <p><strong>${offer.estimate.monthly_usd.toFixed(2)} / month</strong> reference estimate</p>
          <p>{offer.reason}</p>
          <p>Region: {offer.config.region} · {offer.provider === 'private' ? 'Local loopback endpoint' : 'Identity-authenticated endpoint'}</p>
          {offer.provider !== 'private' && <label className="deploy-cfg__field">Instance
            <select className="deploy-cfg__select" value={value('instance_type', offer.config.instance_type)} disabled={busy}
              onChange={e => edit(offer.provider, 'instance_type', e.target.value)}>
              {offer.instances.map(instance => <option key={instance.id} value={instance.id}>
                {instance.id} · {instance.ram_gib} GiB RAM{instance.vram_gib ? ` · ${instance.vram_gib} GiB GPU` : ' · CPU'}
              </option>)}
            </select>
          </label>}
          {numeric('context_length', 'Context tokens', offer.config.context_length, 256, 131072)}
          {numeric('concurrency', 'Concurrent requests', offer.config.concurrency, 1, 32)}
          {numeric('hours_per_month', 'Deployed hours per month', offer.config.hours_per_month, 1, 744)}
          {offer.provider !== 'private' ? numeric('replicas', 'Replicas', offer.config.replicas, 1, 10) : <>
            {numeric('power_watts', 'Average hardware watts', 200, 0, 10000)}
            {numeric('electricity_usd_kwh', 'Electricity USD/kWh', .15, 0, 100)}
            {numeric('hardware_monthly_usd', 'Monthly hardware cost (USD)', 0, 0, 100000)}
          </>}
          {!offer.fits && <p role="alert">This instance does not meet the estimated model memory requirement. Choose a larger instance or reduce context/concurrency.</p>}
          <p>Price reference: {offer.estimate.as_of}</p>
          <ul>{offer.estimate.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul>
          {offer.estimate.source.startsWith('https://') && <button className="deploy-flow__btn deploy-flow__btn--ghost"
            onClick={() => window.electronAPI?.openExternal?.(offer.estimate.source)}>View pricing source</button>}
          <button className="button button--primary" disabled={busy || dirty || !offer.fits || !!error}
            onClick={() => onSelect(offer.provider, { ...offer.config, scan_id: report?.meta?.scan_id || '' })}>
            {offer.provider === 'private' ? 'Prepare private deployment' : `Select ${NAMES[offer.provider]} and sign in`}
          </button>
        </section>;
      })}
    </div>
  </div>;
}
