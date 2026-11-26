import type { ScanReport } from './reportTypes';

type EvidenceReport = Pick<ScanReport, 'meta' | 'engine' | 'findings' | 'recommendations'> & {
  model_profile?: { content_sha256?: string };
};

function validate(report: EvidenceReport) {
  if (typeof report?.meta?.target !== 'string' || !report.meta.target || typeof report.meta.scan_id !== 'string' ||
      !['garak', 'pyrit'].includes(report.engine?.name?.toLowerCase()) ||
      !Array.isArray(report.meta.categories) || !report.meta.categories.every(c => typeof c === 'string') ||
      !Array.isArray(report.findings) || !report.findings.every(f =>
        typeof f?.category === 'string' && typeof f.evidence === 'string' &&
        ['high','medium','low'].includes(f.severity) && Number.isFinite(f.confidence) && f.confidence >= 0 && f.confidence <= 1) ||
      !Array.isArray(report.recommendations) || !report.recommendations.every(r =>
        typeof r?.category === 'string' && Array.isArray(r.actions) && r.actions.every(a => typeof a === 'string'))) {
    throw new Error('Choose a SentryPhi JSON report from Garak or PyRIT.');
  }
  if (report.engine.error || report.meta.scan_id.startsWith('sim-') || !(report.engine.total_probes > 0))
    throw new Error('Both reports must contain completed, non-simulated work.');
}

export function compareEvidence(first: EvidenceReport, second: EvidenceReport) {
  validate(first);
  validate(second);
  if (first.engine.name.toLowerCase() === second.engine.name.toLowerCase())
    throw new Error('Choose a report from the other engine.');
  const scope = (r: EvidenceReport) => JSON.stringify([...new Set(r.meta.categories)].sort());
  const digest = first.model_profile?.content_sha256;
  if (digest !== second.model_profile?.content_sha256 || (!digest && (first.meta.target !== second.meta.target || first.meta.model_name !== second.meta.model_name)) ||
      first.meta.scan_depth !== second.meta.scan_depth || first.meta.mode !== second.meta.mode || scope(first) !== scope(second))
    throw new Error('The target or model digest, depth, mode and selected categories must match.');
  const reports = [first, second];
  const endpointIdentity = first.meta.model_name ? 'Endpoint and reported model ID: ' + first.meta.model_name : 'Reported endpoint address only';
  const categories = [...new Set(reports.flatMap(r => [...r.meta.categories, ...r.findings.map(f => f.category)]))];
  const rows = categories.map(category => {
    const sources = reports.map(r => {
      const findings = r.findings.filter(f => f.category === category);
      return { engine: r.engine.name, findings };
    });
    const observations = sources.flatMap(src => src.findings);
    const severity = (['high','medium','low'] as const).find(level => observations.some(f => f.severity === level));
    const actions = [...new Set(reports.flatMap(r => r.recommendations.filter(rec => rec.category === category).flatMap(rec => rec.actions)))];
    return {category, severity: severity ?? 'none', sources, actions,
      enginesReporting: sources.filter(src => src.findings.length > 0).length};
  });
  const rank = ['high','medium','low','none'];
  rows.sort((a,b) => rank.indexOf(a.severity) - rank.indexOf(b.severity) || b.enginesReporting - a.enginesReporting);
  return {target: first.meta.target, model_sha256: digest, scope: first.meta.categories, depth: first.meta.scan_depth,
    identity_basis: digest ? 'Model file digest' : endpointIdentity,
    runs: reports.map(r => ({engine: r.engine.name, id: r.meta.scan_id, timestamp: r.meta.timestamp, probes: r.engine.total_probes})), categories: rows};
}
