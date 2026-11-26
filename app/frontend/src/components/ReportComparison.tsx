import React, { useState } from 'react';
import { compareEvidence } from '../services/compareEvidence';
import type { ScanReport } from '../services/reportTypes';

export function ReportComparison({report}: {report: ScanReport}) {
  const [combined, setCombined] = useState<ReturnType<typeof compareEvidence>>();
  const [error, setError] = useState('');
  async function compare(file?: File) {
    if (!file) return;
    setCombined(undefined);
    setError('');
    try {
      if (file.size > 32 * 1024 * 1024) throw new Error('Choose a report smaller than 32 MiB.');
      setCombined(compareEvidence(report, JSON.parse(await file.text())));
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not read the report.'); }
  }
  function save() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(combined, null, 2)], {type:'application/json'}));
    const link = document.createElement('a');
    link.href = url; link.download = 'sentryphi-combined-evidence.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
  return <details className="results-page__section"><summary>Compare evidence from another engine</summary>
    <p>Choose the other engine’s exported SentryPhi JSON report for this model and scan scope.</p>
    <input aria-label="Second engine report" type="file" accept=".json" onChange={e => void compare(e.target.files?.[0])}/>
    {error && <p role="alert">{error}</p>}
    {combined && <><p>{combined.identity_basis}. Categories are ordered by highest observed severity. Each finding retains its original confidence.</p>
      {combined.categories.map(row => <details key={row.category}><summary>{row.category} · {row.severity} · {row.enginesReporting}/2 engines reported findings</summary>
        {row.sources.map(src => <p key={src.engine}>{src.engine}: {src.findings.length} findings</p>)}
        <ul>{row.actions.map(action => <li key={action}>{action}</li>)}</ul></details>)}
      <button className="button button--secondary" onClick={save}>Save combined report</button></>}
  </details>;
}
