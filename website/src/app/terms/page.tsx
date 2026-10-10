import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms of Service',
  description:
    'Sentryɸ terms of service. Authorized use only. MIT licensed. No warranty.',
  alternates: { canonical: 'https://sentryphi.dev/terms' },
};

export default function TermsPage() {
  const sectionStyle = { marginBottom: '48px' };
  const h2Style = {
    fontSize: '20px', fontWeight: 700 as const, letterSpacing: '-0.3px',
    color: 'var(--text-primary)', marginBottom: '16px',
  };
  const pStyle = {
    fontSize: '15px', lineHeight: 1.7,
    color: 'var(--text-secondary)', marginBottom: '12px',
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
        }}>Terms of Service</h1>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '48px' }}>
          Last updated: October 2026
        </p>

        <div style={sectionStyle}>
          <h2 style={h2Style}>1. Acceptance of Terms</h2>
          <p style={pStyle}>By downloading, installing, or using Sentryɸ (&quot;the Software&quot;), you agree to these Terms of Service. If you do not agree, do not use the Software.</p>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>2. Authorized Use Only</h2>
          <p style={pStyle}>Sentryɸ is designed for defensive security testing. You must have explicit authorization from the owner of any AI system you scan. Unauthorized security testing may violate applicable laws in your jurisdiction.</p>
          <p style={pStyle}>You agree not to use Sentryɸ for:</p>
          <p style={pStyle}>• Unauthorized penetration testing or scanning of systems you do not own or have permission to test</p>
          <p style={pStyle}>• Denial-of-service attacks against any system</p>
          <p style={pStyle}>• Unauthorized data extraction or exfiltration</p>
          <p style={pStyle}>• Any activity that violates applicable local, state, national, or international laws</p>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>3. License</h2>
          <p style={pStyle}>Sentryɸ is open source software licensed under the MIT License. The full license text is included with every distribution and available in the source repository.</p>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>4. No Warranty</h2>
          <p style={pStyle}>THE SOFTWARE IS PROVIDED &quot;AS IS&quot; WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. The developers are not liable for any damages resulting from the use of this software. Scan results are advisory and do not constitute a guarantee of security or compliance.</p>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>5. Limitation of Liability</h2>
          <p style={pStyle}>In no event shall the creators or contributors of Sentryɸ be liable for any direct, indirect, incidental, special, exemplary, or consequential damages arising from the use or inability to use the Software.</p>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>6. API Cost Responsibility</h2>
          <p style={pStyle}>Running security scans against remote API endpoints incurs API usage costs charged by the model provider. You are solely responsible for all API costs incurred during scanning. Sentryɸ provides cost estimates, but these are advisory and may differ from actual charges.</p>
        </div>

        <div style={sectionStyle}>
          <h2 style={h2Style}>7. Contact</h2>
          <p style={pStyle}>For questions about these terms, contact legal@sentryphi.dev or open an issue on our GitHub repository.</p>
        </div>
      </div>
    </main>
  );
}
