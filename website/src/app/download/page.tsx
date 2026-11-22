import s from './download.module.css';

const VERSION = '1.0.0';
const GITHUB_REPO = 'https://github.com/prakhar2204/AI_Sentry';
const WIN_DOWNLOAD = `${GITHUB_REPO}/releases/download/v${VERSION}/Sentryphi-Setup-${VERSION}.exe`;


export default function DownloadPage() {
  return (
    <main className={s.downloadPage}>
      <div className={s.inner}>
        {/* ── Header ── */}
        <div className={s.header}>
          <h1 className={s.title}>Download Sentryɸ</h1>
          <p className={s.subtitle}>
            Free. Open Source. No setup required.
          </p>
          <p className={s.version}>
            Current version: v{VERSION} — Released November 2026
          </p>
        </div>

        {/* ── Platform Cards ── */}
        <div className={s.platforms}>
          {/* Windows */}
          <div className={s.platformCard}>
            <h2 className={s.platformName}>Sentryɸ for Windows</h2>
            <div className={s.platformMeta}>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Version</span>
                <span>{VERSION}</span>
              </div>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Filename</span>
                <span>Sentryphi-Setup-{VERSION}.exe</span>
              </div>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Requires</span>
                <span>Windows 10 64-bit or later</span>
              </div>
            </div>

            <a href={WIN_DOWNLOAD} data-download-platform="windows" className={s.downloadBtn}>
              ↓ &nbsp;Download for Windows
            </a>

            <div className={s.mirrorLink}>
              <a href={`${GITHUB_REPO}/releases/tag/v${VERSION}`}>All releases on GitHub ↗</a>
            </div>
          </div>

          {/* Linux */}
          <div className={s.platformCard}>
            <h2 className={s.platformName}>Sentryɸ for Linux</h2>
            <div className={s.platformMeta}>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Version</span>
                <span>{VERSION}</span>
              </div>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Filename</span>
                <span>Linux installer pending</span>
              </div>
              <div className={s.platformMetaRow}>
                <span className={s.platformMetaLabel}>Requires</span>
                <span>Ubuntu 20.04+ or equivalent glibc</span>
              </div>
            </div>

            <a href={`${GITHUB_REPO}/releases/tag/v${VERSION}`} className={s.downloadBtn}>
              View available release assets
            </a>

            <div className={s.mirrorLink}>
              <a href={`${GITHUB_REPO}/releases/tag/v${VERSION}`}>All releases on GitHub ↗</a>
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

        {/* ── What's Included ── */}
        <div className={s.trustBlock}>
          <h3 className={s.trustTitle}>What the download includes</h3>
          <div className={s.trustList}>
            <div className={s.trustItem}>
              <span className={s.trustCheck}>✓</span>
              AI security scanning engine with multi-layer probing
            </div>
            <div className={s.trustItem}>
              <span className={s.trustCheck}>✓</span>
              Cloud account sign-in through provider tools
            </div>
            <div className={s.trustItem}>
              <span className={s.trustCheck}>✓</span>
              One-click cloud deployment with infrastructure-as-code
            </div>
            <div className={s.trustItem}>
              <span className={s.trustCheck}>✓</span>
              Full source code available on GitHub
            </div>
          </div>
          <div className={s.engineVersions}>
            Analysis engine v{VERSION} — includes multi-layer probing, adversarial simulation, and behavioral evaluation
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
              Launch Sentryɸ from your desktop shortcut
            </div>
            <div className={s.postStep}>
              <span className={s.postStepNum}>3.</span>
              Point it at your AI model and start scanning
            </div>
          </div>
          <div className={s.postLinks}>
            <a href="/docs/">Getting Started Guide →</a>
            <a href={`${GITHUB_REPO}/issues`}>Open an Issue on GitHub →</a>
          </div>
        </div>
      </div>
    </main>
  );
}
