'use client';

import { useState } from 'react';
import s from './download.module.css';

const WIN_CHECKSUM = 'a3b7c9d1e4f5681234567890abcdef0123456789abcdef0123456789abcdef01';
const LINUX_CHECKSUM = '9f8e7d6c5b4a3210fedcba9876543210fedcba9876543210fedcba9876543210';

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard API not available */
    }
  };

  return (
    <button className={s.copyBtn} onClick={handleCopy}>
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

export default function DownloadPage() {
  return (
    <div className={s.downloadPage}>
      <div className={s.inner}>
        {/* ── Header ── */}
        <div className={s.header}>
          <h1 className={s.title}>Download AI-SENTRY</h1>
          <p className={s.subtitle}>
            Free. Open Source. No setup required.
          </p>
          <p className={s.version}>
            Current version: v1.0.0 — Released October 2026
          </p>
        </div>

        {/* ── Platform Cards ── */}
        <div className={s.platforms}>
          {/* Windows */}
          <div className={s.platformCard}>
            <h2 className={s.platformName}>AI-SENTRY for Windows</h2>
            <div className={s.platformMeta}>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Version</span>
                <span>1.0.0</span>
              </div>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Filename</span>
                <span>AI-Sentry-Setup-1.0.0.exe</span>
              </div>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Size</span>
                <span>~12 MB</span>
              </div>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Requires</span>
                <span>Windows 10 64-bit or later</span>
              </div>
            </div>

            <a href="#" className={s.downloadBtn}>
              ↓ &nbsp;Download for Windows
            </a>

            <div>
              <div className={s.checksumLabel}>SHA256 Checksum</div>
              <div className={s.checksumBlock}>
                <span className={s.checksumValue}>{WIN_CHECKSUM}</span>
                <CopyButton text={WIN_CHECKSUM} />
              </div>
            </div>

            <div className={s.mirrorLink}>
              <a href="#">Mirror download ↗</a>
            </div>
          </div>

          {/* Linux */}
          <div className={s.platformCard}>
            <h2 className={s.platformName}>AI-SENTRY for Linux</h2>
            <div className={s.platformMeta}>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Version</span>
                <span>1.0.0</span>
              </div>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Filename</span>
                <span>AI-Sentry-1.0.0.AppImage</span>
              </div>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Size</span>
                <span>~18 MB</span>
              </div>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Requires</span>
                <span>Ubuntu 20.04+ or equivalent glibc</span>
              </div>
            </div>

            <a href="#" className={s.downloadBtn}>
              ↓ &nbsp;Download for Linux
            </a>

            <div>
              <div className={s.checksumLabel}>SHA256 Checksum</div>
              <div className={s.checksumBlock}>
                <span className={s.checksumValue}>{LINUX_CHECKSUM}</span>
                <CopyButton text={LINUX_CHECKSUM} />
              </div>
            </div>

            <div className={s.mirrorLink}>
              Also available: <a href="#">.deb (Ubuntu/Debian)</a> &nbsp;·&nbsp; <a href="#">Mirror ↗</a>
            </div>
          </div>
        </div>

        {/* ── System Requirements ── */}
        <div className={s.reqSection}>
          <h2 className={s.reqTitle}>System Requirements</h2>
          <div className={s.reqGrid}>
            <div className={s.reqCard}>
              <h3 className={s.reqCardTitle}>Minimum Requirements</h3>
              <table className={s.reqTable}>
                <tbody>
                  <tr>
                    <td>OS</td>
                    <td>Windows 10 64-bit or Ubuntu 20.04+</td>
                  </tr>
                  <tr>
                    <td>RAM</td>
                    <td>8 GB minimum (16 GB recommended)</td>
                  </tr>
                  <tr>
                    <td>Disk</td>
                    <td>500 MB free</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className={s.reqCard}>
              <h3 className={s.reqCardTitle}>Local GGUF Model Scanning</h3>
              <table className={s.reqTable}>
                <tbody>
                  <tr>
                    <td>Up to 7B</td>
                    <td>8 GB RAM — no GPU required</td>
                  </tr>
                  <tr>
                    <td>Up to 13B</td>
                    <td>16 GB RAM recommended</td>
                  </tr>
                  <tr>
                    <td>Up to 30B</td>
                    <td>32 GB RAM or dedicated GPU</td>
                  </tr>
                  <tr>
                    <td>Over 30B</td>
                    <td>Use API mode (local not recommended)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ── Trust Verification ── */}
        <div className={s.trustBlock}>
          <h3 className={s.trustTitle}>Trust &amp; Verification</h3>
          <div className={s.trustList}>
            <div className={s.trustItem}>
              <span className={s.trustCheck}>✓</span>
              SHA256 checksums published on this page
            </div>
            <div className={s.trustItem}>
              <span className={s.trustCheck}>✓</span>
              Code-signed (Windows Authenticode certificate)
            </div>
            <div className={s.trustItem}>
              <span className={s.trustCheck}>✓</span>
              GPG-signed (Linux releases)
            </div>
            <div className={s.trustItem}>
              <span className={s.trustCheck}>✓</span>
              Full source code available on GitHub
            </div>
          </div>
          <div className={s.engineVersions}>
            Bundled engine versions (v1.0.0): &nbsp;
            Garak v0.9.0.14 &nbsp;·&nbsp; PyRIT v0.5.0 &nbsp;·&nbsp; DeepTeam v1.4.0
          </div>
        </div>

        {/* ── Post Download ── */}
        <div className={s.postDownload}>
          <h2 className={s.postTitle}>After Downloading</h2>
          <div className={s.postSteps}>
            <div className={s.postStep}>
              <span className={s.postStepNum}>1.</span>
              Run the installer (no terminal required)
            </div>
            <div className={s.postStep}>
              <span className={s.postStepNum}>2.</span>
              Launch AI-SENTRY from your desktop shortcut
            </div>
            <div className={s.postStep}>
              <span className={s.postStepNum}>3.</span>
              Follow the 4-screen guided setup
            </div>
          </div>
          <div className={s.postLinks}>
            <a href="#">Getting Started Guide →</a>
            <a href="#">Open an Issue on GitHub →</a>
          </div>
        </div>
      </div>
    </div>
  );
}
