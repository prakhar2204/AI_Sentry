import type { Metadata } from 'next';
import { Logo } from '@/components/Logo';
import s from '@/styles/pages.module.css';

export const metadata: Metadata = {
  title: 'About — The Team Behind Sentryɸ',
  description:
    'Learn about Sentryɸ, the open-source LLM security platform. Our mission: make pre-deployment AI security testing accessible to every development team, not just security specialists.',
  alternates: { canonical: 'https://sentryphi.dev/about' },
};

const STATS = [
  { value: '100+', label: 'Security Probes' },
  { value: '10/10', label: 'OWASP LLM Coverage' },
  { value: '3', label: 'Analysis Layers' },
  { value: '0', label: 'Telemetry Collected' },
];

const VALUES = [
  {
    title: 'Security as a Standard',
    body: 'Every AI model deployed in production should pass adversarial security testing. We believe security scanning should be as routine as unit testing — not a luxury reserved for large enterprises.',
  },
  {
    title: 'Transparency Over Trust',
    body: "Black-box risk scores create false confidence. Every score in Sentryɸ is explainable: you can trace any finding back to the probe that triggered it, the evidence it produced, and the formula that scored it.",
  },
  {
    title: 'Privacy by Architecture',
    body: "We don't collect telemetry. We don't require accounts. We don't phone home. Scan data stays on your machine. API keys live in your OS keychain. Period.",
  },
  {
    title: 'Open Source, Always',
    body: 'Sentryɸ is MIT licensed. The scanning engine, scoring algorithm, and deployment advisor are all open source. Security tools should be auditable by the people who use them.',
  },
];

export default function AboutPage() {
  return (
    <main className={s.pageContainer}>
      <div className={s.pageInner}>
        {/* Hero */}
        <div style={{ marginBottom: '80px', textAlign: 'center' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '24px' }}>
            <Logo size={64} />
          </div>
          <h1 style={{
            fontSize: 'clamp(30px, 4vw, 48px)', fontWeight: 700,
            letterSpacing: '-1.5px', lineHeight: 1.1,
            color: 'var(--text-primary)', marginBottom: '20px',
          }}>
            Making LLM security<br />accessible to everyone.
          </h1>
          <p style={{
            fontSize: '18px', lineHeight: 1.7,
            color: 'var(--text-secondary)', maxWidth: '640px',
            margin: '0 auto',
          }}>
            Sentryɸ exists because pre-deployment security testing shouldn&apos;t require a dedicated
            security team, a six-figure budget, or weeks of manual configuration. We&apos;re building
            the security gate that every AI deployment deserves.
          </p>
        </div>

        {/* Stats */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1px', backgroundColor: 'var(--border-subtle)',
          borderRadius: 'var(--radius-lg)', overflow: 'hidden',
          marginBottom: '80px',
        }}>
          {STATS.map((stat) => (
            <div key={stat.label} style={{
              padding: '32px 24px', textAlign: 'center',
              backgroundColor: 'var(--bg-surface)',
            }}>
              <div style={{
                fontSize: '28px', fontWeight: 700,
                color: 'var(--accent)', marginBottom: '8px',
                letterSpacing: '-1px',
              }}>{stat.value}</div>
              <div style={{
                fontSize: '13px', fontWeight: 500,
                color: 'var(--text-secondary)',
                textTransform: 'uppercase', letterSpacing: '0.5px',
              }}>{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Values */}
        <div style={{ marginBottom: '80px' }}>
          <h2 style={{
            fontSize: '24px', fontWeight: 700, letterSpacing: '-0.5px',
            color: 'var(--text-primary)', marginBottom: '40px',
            textAlign: 'center',
          }}>What we believe</h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '24px',
          }}>
            {VALUES.map((v) => (
              <div key={v.title} style={{
                padding: '28px', backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
              }}>
                <h3 style={{
                  fontSize: '16px', fontWeight: 600,
                  color: 'var(--text-primary)', marginBottom: '12px',
                }}>{v.title}</h3>
                <p style={{
                  fontSize: '14px', lineHeight: 1.65,
                  color: 'var(--text-secondary)', margin: 0,
                }}>{v.body}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Open Source CTA */}
        <div style={{
          textAlign: 'center', padding: '48px 32px',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-xl)',
        }}>
          <h2 style={{
            fontSize: '22px', fontWeight: 700, letterSpacing: '-0.5px',
            color: 'var(--text-primary)', marginBottom: '12px',
          }}>Built in the open</h2>
          <p style={{
            fontSize: '15px', lineHeight: 1.6,
            color: 'var(--text-secondary)',
            maxWidth: '480px', margin: '0 auto 24px',
          }}>
            Sentryɸ is open source under the MIT license.
            Contributions, issues, and security audits are welcome.
          </p>
          <a
            href="#"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              padding: '12px 24px', fontSize: '14px', fontWeight: 600,
              color: '#fff', backgroundColor: 'var(--accent)',
              borderRadius: 'var(--radius-md)', textDecoration: 'none',
            }}
          >
            View on GitHub →
          </a>
        </div>
      </div>
    </main>
  );
}
