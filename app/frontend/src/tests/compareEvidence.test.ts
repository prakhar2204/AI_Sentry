import { describe, it, expect } from 'vitest';
import { compareEvidence } from '../services/compareEvidence';
import type { ScanReport } from '../services/reportTypes';
function report(engine: string): ScanReport {
  return {meta:{target:'local', scan_depth:'quick', categories:['alpha'], scan_id:engine, mode:'local'},
    engine:{name:engine, total_probes:2, error:null},
    recommendations:[{category:'alpha',severity:'low',actions:['Review configuration']}],
    findings: [{category:'alpha', confidence:.8, severity:'low', evidence:'Observed behavior'}]} as ScanReport;
}
describe('cross-engine evidence', () => {
  it('retains source confidence and recommends each action once', () => {
    const combined = compareEvidence(report('garak'), report('pyrit'));
    expect(combined.categories[0].enginesReporting).toBe(2);
    expect(combined.categories[0].sources.every(s => s.findings[0].confidence === .8)).toBe(true);
    expect(combined.categories[0].actions).toEqual(['Review configuration']);
  });
  it('rejects mismatched targets and incomplete runs', () => {
    const other = report('pyrit');
    other.meta.target = 'other';
    expect(() => compareEvidence(report('garak'), other)).toThrow(/target/);
    other.engine.error = 'interrupted';
    expect(() => compareEvidence(report('garak'), other)).toThrow(/completed/);
  });
});
