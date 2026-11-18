import React, { useState } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { ModelCloudPage } from '../pages/ModelCloudPage';
import DeployFlowPage from '../pages/DeployFlowPage';
import { DeployFlowProvider, useDeployFlow } from '../store/DeployFlowContext';

const profile = { source: 'D:/models/scanned.gguf', name: 'scanned.gguf', format: 'gguf', fingerprint: 'scan-fingerprint', weights_gib: 2 };
vi.mock('../store/ReportContext', () => ({ useReportContext: () => ({ state: { report: {
  model_profile: { source: 'D:/models/scanned.gguf', name: 'scanned.gguf', format: 'gguf', fingerprint: 'scan-fingerprint', weights_gib: 2 }, meta: { scan_id: 'scan-test' },
} } }) }));
vi.mock('../store/ScanContext', () => ({ useScanContext: () => ({ state: { local_model_path: 'D:/models/scanned.gguf' } }) }));

function Harness() {
  const [selected, setSelected] = useState(false);
  const { dispatch } = useDeployFlow();
  return selected ? <DeployFlowPage onEdit={() => setSelected(false)} /> : <ModelCloudPage onBack={() => {}} onSelect={(provider, config) => {
    dispatch({ type: 'SET_PROVIDER', provider }); dispatch({ type: 'SET_CONFIG', config }); setSelected(true);
  }} />;
}

it.each(['aws', 'azure', 'gcp'] as const)('%s: model comparison → edit costs → official sign-in → reviewed model plan → confirmed deploy', async provider => {
  const names = { aws: 'AWS', azure: 'Azure', gcp: 'Google Cloud' };
  const identity = { provider, account: provider === 'gcp' ? 'test-project' : '12345678-1234-1234-1234-123456789abc', identity: 'person@example.test', region: 'test-region' };
  const auth = vi.fn(async ({ action }) => ({ ok: true, result: action === 'check_cli'
    ? { available: true, implemented: true, message: 'Official CLI ready' } : identity }));
  const backend = vi.fn(async ({ command, payload, edits }) => {
    if (command === 'cloud:recommend') return { model: profile, offers: ['aws', 'azure', 'gcp'].map(p => ({
      provider: p, service: 'Managed model endpoint', model: profile, fits: true, reason: 'Model capacity estimate',
      instances: [{ id: 'cpu-16gb', ram_gib: 16, vcpus: 4, vram_gib: 0 }],
      config: { deployment_mode: 'managed_model', region: 'test-region', instance_type: 'cpu-16gb',
        context_length: 2048, concurrency: 1, replicas: Number(edits?.[p]?.replicas || 1), hours_per_month: 730,
        model_source: profile.source, model_fingerprint: profile.fingerprint, model_format: 'gguf', accelerator: 'cpu', endpoint_scope: 'authenticated' },
      estimate: { monthly_usd: Number(edits?.[p]?.replicas || 1) * 100, as_of: '2026-11-17', source: 'reference', warnings: ['Reference estimate'] },
    })) };
    if (command === 'deploy:generate_plan') return { deployment_id: 'sp-model-test', provider, region: payload.config.region,
      resources: [{ resource_type: 'Scanned model endpoint' }], security_notes: ['Upload the scanned model'],
      estimated_cost: { low_usd: 200, high_usd: 200 }, raw_config: payload.config };
    if (command === 'deploy:dry_run') return { success: true, errors: [], warnings: [], message: 'Model and identity verified' };
    if (command === 'deploy:execute') return { deployment_id: 'sp-model-test', status: 'running', resources: [], errors: [], endpoint_url: '', message: 'Uploading the model' };
    throw new Error('Unexpected command: ' + command);
  });
  window.electronAPI = { cloudAuth: auth, runBackendCommand: backend, onCloudAuthProgress: () => () => {} } as any;
  const view = render(<DeployFlowProvider><Harness /></DeployFlowProvider>);
  const card = await screen.findByRole('region', { name: names[provider] });
  expect(auth).not.toHaveBeenCalled(); // Choosing settings/cost does not start auth.
  fireEvent.change(within(card).getByLabelText('Replicas'), { target: { value: '2' } });
  expect(within(card).getByRole('button', { name: /Select .* and sign in/ })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Recalculate edited costs' }));
  await within(card).findByText('$200.00 / month');
  fireEvent.click(within(card).getByRole('button', { name: /Select .* and sign in/ }));
  fireEvent.click(await screen.findByRole('button', { name: /Sign in with/ }));
  await screen.findByText(identity.identity);
  fireEvent.click(screen.getByLabelText('Use this account and region for deployment'));
  fireEvent.click(screen.getByRole('button', { name: 'Confirm account and continue' }));
  await screen.findByText('Deployment Plan');
  expect(backend.mock.calls.find(([c]) => c.command === 'deploy:generate_plan')?.[0].payload.config).toMatchObject({
    model_source: profile.source, model_fingerprint: profile.fingerprint, replicas: 2, scan_id: 'scan-test', deployment_mode: 'managed_model',
  });
  expect(screen.queryByLabelText('Existing execution role ARN')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: /Validate Plan/ }));
  await screen.findByText('Confirm Deployment');
  expect(screen.getByRole('button', { name: /Deploy Now/ })).toBeDisabled();
  expect(backend.mock.calls.some(([c]) => c.command === 'deploy:execute')).toBe(false);
  fireEvent.click(screen.getByLabelText(/I confirm I want to deploy/));
  fireEvent.click(screen.getByRole('button', { name: /Deploy Now/ }));
  await waitFor(() => expect(backend.mock.calls.some(([c]) => c.command === 'deploy:execute')).toBe(true));
  expect(auth.mock.calls.filter(([c]) => c.action === 'select_scope')).toHaveLength(2);
  expect(screen.queryByText('Deployment Complete!')).toBeNull();
  view.unmount();
});
