'use client';

import { useEffect, useState, useSyncExternalStore } from 'react';

const buildId = process.env.NEXT_PUBLIC_GA4_MEASUREMENT_ID;
const validId = (value?: string) => Boolean(value && /^G-[A-Z0-9]+$/.test(value));
const key = 'sentryphi-analytics';
type Choice = 'allow' | 'decline';

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

function startAnalytics(measurementId: string) {
  if (window.gtag) return;
  window.dataLayer = window.dataLayer || [];
  window.gtag = function () {
    // The Google tag expects arguments objects in its command queue.
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer!.push(arguments);
  };
  window.gtag('js', new Date());
  window.gtag('config', measurementId, { allow_google_signals: false, allow_ad_personalization_signals: false });
  const script = document.createElement('script');
  script.async = true;
  script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(measurementId);
  document.head.appendChild(script);
}

let temporaryChoice: Choice | null = null;
function preference(): Choice | null {
  try {
    const value = localStorage.getItem(key);
    return value === 'allow' || value === 'decline' ? value : temporaryChoice;
  } catch { return temporaryChoice; }
}

function subscribe(notify: () => void) {
  window.addEventListener('storage', notify);
  window.addEventListener(key, notify);
  return () => {
    window.removeEventListener('storage', notify);
    window.removeEventListener(key, notify);
  };
}

export function Analytics() {
  const choice = useSyncExternalStore(subscribe, preference, () => null);
  const [id, setId] = useState(buildId);
  const enabled = validId(id);
  useEffect(() => {
    if (validId(buildId)) return;
    const controller = new AbortController();
    fetch('/analytics-id.txt', { signal: controller.signal })
      .then(async response => response.ok ? (await response.text()).trim() : '')
      .then(value => { if (!controller.signal.aborted && validId(value)) setId(value); })
      .catch(() => { /* Downloads and navigation also work without analytics. */ });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!enabled || !id) return;
    if (choice !== 'allow') {
      if (window.gtag) window.location.reload();
      return;
    }
    startAnalytics(id);
    const onClick = (event: MouseEvent) => {
      const link = event.target instanceof Element && event.target.closest<HTMLElement>('[data-download-platform]');
      if (link) window.gtag?.('event', 'download_click', { platform: link.dataset.downloadPlatform });
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [enabled, choice, id]);

  function select(value: Choice) {
    try { localStorage.setItem(key, value); } catch { /* preference lasts for this visit */ }
    temporaryChoice = value;
    window.dispatchEvent(new Event(key));
  }

  if (!enabled) return null;
  return <section aria-label="Website analytics preference" className="analytics-preference">
    <span>{choice ? 'Website analytics ' + (choice === 'allow' ? 'enabled' : 'disabled') : 'Allow Google Analytics to measure visits and download clicks?'}</span>
    {choice !== 'allow' && <button onClick={() => select('allow')}>Allow analytics</button>}
    {choice !== 'decline' && <button onClick={() => select('decline')}>Decline analytics</button>}
    <a href="/privacy/">Privacy policy</a>
  </section>;
}
