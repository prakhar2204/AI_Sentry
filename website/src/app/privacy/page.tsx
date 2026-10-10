import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description:
    'Sentryɸ privacy policy. We collect zero telemetry, require no accounts, and process all scan data locally on your machine.',
  alternates: { canonical: 'https://sentryphi.dev/privacy' },
};

export default function PrivacyPage() {
  const sectionStyle = { marginBottom: '48px' };
  const h2Style = {
    fontSize: '20px', fontWeight: 700 as const, letterSpacing: '-0.3px',
    color: 'var(--text-primary)', marginBottom: '16px',
  };
  const pStyle = {
    fontSize: '15px', lineHeight: 1.7,
    color: 'var(--text-secondary)', marginBottom: '12px',
  };
  const liStyle = {
    fontSize: '15px', lineHeight: 1.7,
    color: 'var(--text-secondary)', marginBottom: '8px',
    paddingLeft: '16px',
  };

  return (
    <main style={{ paddingTop: 'calc(var(--nav-height) + 48px)', paddingBottom: '96px', minHeight: '100vh' }}>
      <div style={{ maxWidth: '720px', margin: '0 auto', padding: '0 var(--space-lg)' }}>
        <span style={{
          display: 'inline-block', fontSize: '11px', fontWeight: 600,
          letterSpacing: '1.5px', textTransform: 'uppercase',
          color: 'var(--accent)', marginBottom: '16px',
        }}>Legal</span>
        <h1 style={{
          fontSize: 'clamp(28px, 3vw, 36px)', fontWeight: 700,
          letterSpacing: '-1px', lineHeight: 1.15,
          color: 'var(--text-primary)', marginBottom: '8px',
        }}>Privacy Policy</h1>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '48px' }}>
          Last updated: October 2026
        </p>

        <div style={sectionStyle}>
          <h2 style={h2Style}>1. Data We Collect</h2>
          <p style={pStyle}>
            <strong style={{ color: 'var(--text-primary)' }}>None.</strong> Sentryɸ does not collect personal information, usage analytics, telemetry data, or any other user data. The application runs entirely on your local machine.
          </p>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>2. Local Processing</h2>
          <p style={pStyle}>All scan data — including target URLs, API keys, scan results, vulnerability findings, and generated reports — is processed and stored locally on your machine. No data is transmitted to Sentryɸ servers or any third party.</p>
          <div style={{ ...liStyle }}>• API keys are stored in your operating system&apos;s native keychain (Windows Credential Manager or Linux Secret Service)</div>
          <div style={{ ...liStyle }}>• Scan reports are saved to the output directory you specify</div>
          <div style={{ ...liStyle }}>• No cookies are set by the desktop application</div>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>3. Website Analytics</h2>
          <p style={pStyle}>The Sentryɸ website (sentryphi.dev) uses privacy-respecting analytics that set no cookies and store no personal data. We collect only aggregate page view counts and referrer information — no individual tracking.</p>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>4. Third-Party API Interactions</h2>
          <p style={pStyle}>When you run a scan against a remote API endpoint, Sentryɸ sends adversarial probes directly to the target model&apos;s API. These requests may be logged by the model provider (e.g., OpenAI, Anthropic, Azure) according to their own privacy policies. You are responsible for ensuring this is acceptable under your agreements with those providers.</p>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>5. Open Source Transparency</h2>
          <p style={pStyle}>Sentryɸ is open source under the MIT license. You can audit the complete source code to verify these privacy claims independently.</p>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>6. Contact</h2>
          <p style={pStyle}>For privacy-related questions, open an issue on our GitHub repository or email privacy@sentryphi.dev.</p>
        </div>
      </div>
    </main>
  );
}
