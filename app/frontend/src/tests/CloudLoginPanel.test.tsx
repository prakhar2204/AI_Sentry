import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CloudLoginPanel } from '../components/deploy/CloudLoginPanel';

const identity = { provider: 'aws', account: '123456789012', identity: 'arn:aws:iam::123456789012:user/test', region: 'us-east-1', profile: 'sentryphi-console' };
const ready = { provider: 'aws', available: true, implemented: true, code: 'READY', message: 'AWS CLI is ready' };
let command: ReturnType<typeof vi.fn>;
beforeEach(() => {
  command = vi.fn(async ({ action }) => ({ ok: true, result: action === 'check_cli' ? ready : identity }));
  window.electronAPI = { cloudAuth: command, onCloudAuthProgress: vi.fn(() => () => {}), openExternal: vi.fn() } as any;
});

describe('official CLI cloud sign-in', () => {
  it('does not automatically log in and requires identity/account/region confirmation', async () => {
    const confirmed = vi.fn();
    render(<CloudLoginPanel provider="aws" onConfirmed={confirmed} onBack={() => {}} />);
    await screen.findByText('AWS CLI is ready');
    expect(command.mock.calls.map(([c]) => c.action)).toEqual(['check_cli']);
    fireEvent.click(screen.getByRole('button', { name: 'Sign in with AWS' }));
    await screen.findByText(identity.identity);
    expect(screen.getByText(identity.account)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm account and continue' })).toBeDisabled();
    expect(confirmed).not.toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText('Use this account and region for deployment'));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm account and continue' }));
    await waitFor(() => expect(confirmed).toHaveBeenCalledWith(identity));
    expect(command.mock.calls[command.mock.calls.length - 1]?.[0]).toMatchObject({ action: 'select_scope', options: identity });
    expect(document.querySelector('input[type="password"]')).toBeNull();
  });

  it('cancel invokes the adapter and shows the cancellation result', async () => {
    let finish: (result: any) => void = () => {};
    command.mockImplementation(({ action }) => {
      if (action === 'login') return new Promise(resolve => { finish = resolve; });
      if (action === 'cancel') finish({ ok: false, message: 'Sign-in cancelled' });
      return Promise.resolve({ ok: true, result: ready });
    });
    render(<CloudLoginPanel provider="aws" onConfirmed={() => {}} onBack={() => {}} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Sign in with AWS' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel sign-in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Sign-in cancelled');
    expect(screen.getByRole('button', { name: 'Sign in with AWS' })).toBeEnabled();
  });

  it('missing/old CLI gives guidance and cannot start login', async () => {
    command.mockResolvedValue({ ok: true, result: { ...ready, available: false, code: 'CLI_OLD',
      message: 'Upgrade to AWS CLI 2.32.0', install_url: 'https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html' } });
    render(<CloudLoginPanel provider="aws" onConfirmed={() => {}} onBack={() => {}} />);
    await screen.findByText('Upgrade to AWS CLI 2.32.0');
    expect(screen.queryByRole('button', { name: 'Sign in with AWS' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Installation / upgrade instructions' }));
    expect(window.electronAPI?.openExternal).toHaveBeenCalled();
  });

  it('does not continue when the identity expires during confirmation', async () => {
    const confirmed = vi.fn();
    command.mockImplementation(async ({ action }) => action === 'select_scope'
      ? { ok: false, message: 'Session expired; sign in again' }
      : { ok: true, result: action === 'check_cli' ? ready : identity });
    render(<CloudLoginPanel provider="aws" onConfirmed={confirmed} onBack={() => {}} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Sign in with AWS' }));
    await screen.findByText(identity.identity);
    fireEvent.click(screen.getByLabelText('Use this account and region for deployment'));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm account and continue' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Session expired');
    expect(confirmed).not.toHaveBeenCalled();
  });

  it('unmounting an active sign-in cancels it', async () => {
    command.mockImplementation(({ action }) => action === 'login' ? new Promise(() => {}) : Promise.resolve({ ok: true, result: ready }));
    const view = render(<CloudLoginPanel provider="aws" onConfirmed={() => {}} onBack={() => {}} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Sign in with AWS' }));
    view.unmount();
    expect(command).toHaveBeenLastCalledWith({ provider: 'aws', action: 'cancel', options: {} });
  });
});
