import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
const mocks = vi.hoisted(() => ({ start: vi.fn(), dispatch: vi.fn() }));
vi.mock('../store/ScanContext', () => ({ useScanContext: () => ({
  state: { target: 'http://localhost:11500', mode: 'local', scan_depth: 'quick',
    categories: ['prompt_injection'], engine: 'auto', scan_execution: null },
  dispatch: mocks.dispatch,
}) }));
vi.mock('../store/ReportContext', () => ({
  useReportContext: () => ({ dispatch: mocks.dispatch }), buildSimulatedReport: vi.fn(),
}));
vi.mock('../utils/platform', () => ({ isElectron: () => true }));
vi.mock('../services/ipcScanService', () => ({ startIpcScan: mocks.start }));
import { ScanPage } from '../pages/ScanPage';
describe('scan lifecycle', () => {
  it('starts a live scan after StrictMode effect cleanup and cancels on unmount', () => {
    const controllers: { cancel: ReturnType<typeof vi.fn>; cancelled: boolean }[] = [];
    mocks.start.mockImplementation(() => {
      const controller = { cancel: vi.fn(), cancelled: false };
      controllers.push(controller);
      return controller;
    });
    window.electronAPI = {} as any;
    const page = render(<React.StrictMode><ScanPage onComplete={() => {}} onCancel={() => {}} /></React.StrictMode>);
    expect(controllers).toHaveLength(2);
    expect(controllers[0].cancel).toHaveBeenCalledTimes(1);
    expect(controllers[1].cancel).not.toHaveBeenCalled();
    page.unmount();
    expect(controllers[1].cancel).toHaveBeenCalledTimes(1);
  });
});
