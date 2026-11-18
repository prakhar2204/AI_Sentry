import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import DeployFlowPage from '../pages/DeployFlowPage';
import { DeployFlowProvider } from '../store/DeployFlowContext';

vi.mock('../store/ReportContext', () => ({ useReportContext: () => ({ state: { report: null } }) }));
afterEach(() => vi.useRealTimers());

it('signs in, confirms scope, reviews the plan, explicitly deploys, and polls readiness', async () => {
  const identity = { provider: 'aws', account: '123456789012', identity: 'arn:aws:iam::123456789012:user/test', region: 'us-east-1', profile: 'sentryphi-console' };
  const auth = vi.fn(async ({ action }) => ({ ok: true, result: action === 'check_cli'
    ? { available: true, implemented: true, message: 'AWS CLI is ready' } : identity }));
  const result = { deployment_id: 'sp-test', endpoint_url: '', resources: [], errors: [], message: 'Waiting for stack', status: 'running' };
  const backend = vi.fn(async ({ command, payload }) => {
    if (command === 'deploy:generate_plan') return { deployment_id: 'sp-test', provider: 'aws', region: payload.config.region,
      resources: [{ resource_type: 'AWS::Lambda::Function' }], estimated_cost: { basis: 'not_estimated' }, security_notes: [], raw_config: payload.config };
    if (command === 'deploy:dry_run') return { success: true, warnings: [], errors: [], message: 'Template validated' };
    if (command === 'deploy:execute') return result;
    if (command === 'deploy:status') return { ...result, status: 'complete', endpoint_url: 'https://example.test/invoke' };
    throw new Error('Unexpected test command');
  });
  window.electronAPI = { cloudAuth: auth, runBackendCommand: backend, onCloudAuthProgress: () => () => {} } as any;
  render(<DeployFlowProvider><DeployFlowPage /></DeployFlowProvider>);
  fireEvent.click(screen.getByRole('button', { name: /Amazon Web Services/ }));
  fireEvent.click(await screen.findByRole('button', { name: 'Sign in with AWS' }));
  await screen.findByText(identity.identity);
  fireEvent.click(screen.getByLabelText('Use this account and region for deployment'));
  fireEvent.click(screen.getByRole('button', { name: 'Confirm account and continue' }));
  await screen.findByLabelText('Existing execution role ARN');
  fireEvent.change(screen.getByLabelText('Existing execution role ARN'), { target: { value: 'arn:aws:iam::123456789012:role/Inference' } });
  fireEvent.change(screen.getByLabelText('Bedrock model / inference profile ID'), { target: { value: 'test.model' } });
  fireEvent.change(screen.getByLabelText('Endpoint Access'), { target: { value: 'public' } });
  fireEvent.click(screen.getByRole('button', { name: /Generate Deployment Plan/ }));
  await screen.findByText('Not estimated');
  fireEvent.click(screen.getByRole('button', { name: /Validate Plan/ }));
  await screen.findByText('Confirm Deployment');
  expect(screen.getByRole('button', { name: /Deploy Now/ })).toBeDisabled();
  expect(backend.mock.calls.some(([c]) => c.command === 'deploy:execute')).toBe(false);
  fireEvent.click(screen.getByLabelText(/I confirm I want to deploy/));
  fireEvent.click(screen.getByRole('button', { name: /Deploy Now/ }));
  await waitFor(() => expect(backend.mock.calls.some(([c]) => c.command === 'deploy:execute')).toBe(true));
  expect(auth.mock.calls.filter(([c]) => c.action === 'select_scope')).toHaveLength(2);
  expect(screen.queryByText('Deployment Complete!')).toBeNull();
  await screen.findByText('Deployment Complete!', {}, { timeout: 7000 });
  expect(screen.getByText('https://example.test/invoke')).toBeInTheDocument();
}, 15000);
