import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { startIpcScan } from '../services/ipcScanService';
import type { ScanController, ScanExecutionConfig } from '../services/scanTypes';

const config: ScanExecutionConfig = {
  target: 'http://localhost:11500/v1/chat/completions', mode: 'local',
  scan_depth: 'quick', categories: ['encoding_injection'], engine: 'auto',
  total_probes: 99, per_category_probes: { encoding_injection: 0 },
};
const plan = { engine: 'garak', total_probes: 1, per_category: { encoding_injection: 1 } };
let controller: ScanController;

describe('real scan planning before launch', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { controller?.cancel(); delete window.electronAPI; vi.useRealTimers(); });

  function setup(runBackendCommand: ReturnType<typeof vi.fn>) {
    const startScan = vi.fn().mockResolvedValue({ started: true });
    const handlers = { onProgress: vi.fn(), onActivity: vi.fn(), onComplete: vi.fn(), onError: vi.fn() };
    window.electronAPI = { runBackendCommand, startScan,
      cancelScan: vi.fn().mockResolvedValue({ cancelled: true }),
      onScanProgress: vi.fn().mockReturnValue(vi.fn()),
      onScanComplete: vi.fn().mockReturnValue(vi.fn()),
      onScanError: vi.fn().mockReturnValue(vi.fn()),
    } as any;
    controller = startIpcScan(config, handlers);
    return { startScan, handlers };
  }

  it('uses the backend plan instead of legacy counts before starting the model', async () => {
    const command = vi.fn().mockResolvedValue(plan);
    const { startScan, handlers } = setup(command);
    await vi.waitFor(() => expect(startScan).toHaveBeenCalledOnce());
    expect(command).toHaveBeenCalledWith(expect.objectContaining({ command: 'scan:estimate', engine: 'auto' }));
    expect(handlers.onProgress).toHaveBeenLastCalledWith(expect.objectContaining({
      probes_total: 1, categories: [expect.objectContaining({ probes_total: 1 })],
    }));
    expect(handlers.onError).not.toHaveBeenCalled();
  });

  it('does not launch when cancelled while the plan is pending', async () => {
    let resolve!: (value: unknown) => void;
    const { startScan } = setup(vi.fn().mockReturnValue(new Promise(r => { resolve = r; })));
    controller.cancel();
    resolve(plan);
    await vi.advanceTimersByTimeAsync(10);
    expect(startScan).not.toHaveBeenCalled();
  });

  it('surfaces a missing engine without starting a model process', async () => {
    const { startScan, handlers } = setup(vi.fn().mockRejectedValue(new Error('pyrit is not installed')));
    await vi.waitFor(() => expect(handlers.onError).toHaveBeenCalledWith('pyrit is not installed', 'IPC_ERROR'));
    expect(startScan).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });
});
