import React, { useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ScanProvider, useScanContext } from '../store/ScanContext';
import { InputPage } from '../pages/InputPage';
import { ScanPage } from '../pages/ScanPage';

const mocks = vi.hoisted(() => ({ start: vi.fn(), reportDispatch: vi.fn() }));
vi.mock('../store/ReportContext', () => ({
  useReportContext: () => ({ dispatch: mocks.reportDispatch }), buildSimulatedReport: vi.fn(),
}));
vi.mock('../utils/platform', () => ({ isElectron: () => true }));
vi.mock('../services/ipcScanService', () => ({ startIpcScan: mocks.start }));

function Wizard() {
  const [scanning, setScanning] = useState(false);
  const { state, dispatch } = useScanContext();
  return <>
    <output data-testid="model-path">{state.local_model_path}</output>
    <button onClick={() => dispatch({ type: 'RESET_SCAN' })}>Reset test scan</button>
    {scanning ? <ScanPage onComplete={() => {}} onCancel={() => {}} /> :
      <InputPage onContinue={() => setScanning(true)} onBack={() => {}} />}
  </>;
}

describe('model selection to scan configuration with the real state reducer', () => {
  beforeEach(() => {
    mocks.start.mockReset().mockReturnValue({ cancel: vi.fn(), cancelled: false });
    window.electronAPI = { openModelFilePicker: vi.fn().mockResolvedValue({
      filePath: 'F:\\models\\dolphin-phi.gguf', fileName: 'dolphin-phi.gguf',
    }) } as any;
  });

  it('preserves the native model path and sends it separately from the HTTP target', async () => {
    render(<ScanProvider><Wizard /></ScanProvider>);
    fireEvent.click(screen.getByRole('button', { name: /Browse for Model/ }));
    await screen.findByText('dolphin-phi.gguf');
    fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    await waitFor(() => expect(mocks.start).toHaveBeenCalled());
    expect(screen.getByTestId('model-path').textContent).toBe('F:\\models\\dolphin-phi.gguf');
    expect(mocks.start.mock.calls[0][0]).toMatchObject({
      mode: 'local', local_model_path: 'F:\\models\\dolphin-phi.gguf',
      target: 'http://127.0.0.1:11500/v1/chat/completions', engine: 'auto',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Reset test scan' }));
    expect(screen.getByTestId('model-path').textContent).toBe('');
  });

  it('allows typing and clearing an existing local server URL', async () => {
    render(<ScanProvider><Wizard /></ScanProvider>);
    const input = screen.getByLabelText('Local Server URL (if already running)');
    await userEvent.type(input, 'http://localhost:11434');
    expect(input).toHaveValue('http://localhost:11434');
    await userEvent.clear(input);
    expect(input).toHaveValue('');
  });

  it('passes API credentials and model ID to the real scan bridge', async () => {
    render(<ScanProvider><Wizard /></ScanProvider>);
    fireEvent.click(screen.getByLabelText('API Endpoint'));
    fireEvent.change(screen.getByLabelText('API Endpoint URL'), { target: { value: 'https://example.test/v1' } });
    fireEvent.change(screen.getByLabelText('API key (if required)'), { target: { value: 'test-key' } });
    fireEvent.change(screen.getByLabelText('Model ID (if required)'), { target: { value: 'test-model' } });
    fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    await waitFor(() => expect(mocks.start).toHaveBeenCalled());
    expect(mocks.start.mock.calls[0][0]).toMatchObject({ api_key: 'test-key', model_name: 'test-model', mode: 'api' });
    expect(mocks.start.mock.calls[0][0].local_model_path).toBeUndefined();
  });
});
