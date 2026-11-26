import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { UpdateSettings } from '../components/layout/UpdateSettings';
import type { DesktopUpdate } from '../electron';

afterEach(() => { cleanup(); delete window.electronAPI; });

it('keeps Updates visible in browser preview', () => {
  delete window.electronAPI;
  render(<UpdateSettings startup />);
  fireEvent.click(screen.getByText('Updates'));
  expect(screen.getByText('Open the desktop app to manage automatic updates.')).toBeVisible();
});

it('shows development state and saves the toggle through IPC', async () => {
  let state: DesktopUpdate = {automatic: true, installOnExit: false, currentVersion: '1.0.0',
    stage: 'development', version: '', percent: 0};
  const command = vi.fn(async (action: string, value?: boolean) => {
    if (action === 'auto') state = {...state, automatic: value!};
    return state;
  });
  window.electronAPI = {updateCommand: command, onUpdate: () => () => {}} as unknown as NonNullable<Window['electronAPI']>;
  render(<UpdateSettings startup />);
  fireEvent.click(screen.getByText('Updates'));
  expect(await screen.findByText('Development mode')).toBeVisible();
  fireEvent.click(screen.getByRole('checkbox', {name: 'Automatic updates'}));
  expect(command).toHaveBeenCalledWith('auto', false);
  expect(await screen.findByText(/Your preference is saved/)).toBeVisible();
});
