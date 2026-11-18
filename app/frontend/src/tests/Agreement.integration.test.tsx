import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../App';

afterEach(() => vi.unstubAllGlobals());

it('advances from first-use consent with one acceptance click', async () => {
  const storage = new Map<string, string>();
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
    clear: () => storage.clear(),
  });
  render(<App />);
  fireEvent.click(document.querySelector('#consent-checkbox')!);
  fireEvent.click(document.querySelector('#agree-continue-button')!);
  expect(await screen.findByText('Select Target')).toBeInTheDocument();
});
