import type { Metadata } from 'next';
import s from '@/styles/pages.module.css';

export const metadata: Metadata = {
  title: 'Documentation — Getting Started & Reference',
  description:
    'Complete documentation for Sentryɸ. Learn how to install, configure, and run LLM security scans. Covers scan depth profiles, manifest configuration, report interpretation, and cloud deployment.',
  alternates: { canonical: 'https://sentryphi.dev/docs' },
};

const SECTIONS = [
  {
    title: 'Getting Started',
    items: [
      { title: 'Installation Guide', desc: 'Download and install Sentryɸ on Windows or Linux. No terminal, no dependencies.', href: '#install' },
      { title: 'Your First Scan', desc: 'Connect to an API endpoint, configure scan depth, and run your first vulnerability scan in under 5 minutes.', href: '#first-scan' },
      { title: 'Understanding Results', desc: 'How to read the risk score, severity levels, confidence ratings, and remediation recommendations.', href: '#results' },
    ],
  },
  {
    title: 'Configuration',
    items: [
      { title: 'Scan Depth Profiles', desc: 'Quick, Standard, and Deep scans: what each covers, estimated time, and API cost.', href: '#depth' },
      { title: 'Manifest Files', desc: 'Define reusable scan configurations in JSON. Pin categories, set API keys, specify output directories.', href: '#manifest' },
      { title: 'Probe Categories', desc: 'Prompt injection, jailbreak resistance, data leakage, harmful output — what each category tests.', href: '#categories' },
    ],
  },
  {
    title: 'Security Analysis',
    items: [
      { title: 'Multi-Layer Architecture', desc: 'How three independent analysis layers — probing, adversarial simulation, behavioral evaluation — work together.', href: '#layers' },
      { title: 'Confidence Scoring', desc: 'The weighted formula behind confidence scores: cross-engine corroboration, attack success rate, probe diversity.', href: '#scoring' },
      { title: 'OWASP LLM Top 10', desc: 'Coverage mapping: which OWASP categories Sentryɸ tests, which are partial, and which are advisory-only.', href: '#owasp' },
    ],
  },
  {
    title: 'Deployment & Reports',
    items: [
      { title: 'Report Formats', desc: 'PDF for stakeholders, HTML for sharing, JSON for CI/CD integration. All include full findings and remediation.', href: '#reports' },
      { title: 'AWS Deployment', desc: 'One-click deployment advisory: IAM policies, Bedrock guardrails, CloudWatch alarms, cost estimation.', href: '#aws' },
      { title: 'CLI Reference', desc: 'Full CLI command reference for terminal-first workflows. sentryphi scan, healthcheck, version.', href: '#cli' },
    ],
  },
];

export default function DocsPage() {
  return (
    <main className={s.pageContainer}>
      <div className={s.pageInner}>
        <div className={s.pageHeader}>
          <span className={s.pageLabel}>Documentation</span>
          <h1 className={s.pageTitle}>Learn Sentryɸ</h1>
          <p className={s.pageSubtitle}>
            Everything you need to install, configure, and run LLM security scans —
            from first download to cloud deployment.
          </p>
        </div>

        <div className={s.sectionGroup}>
          {SECTIONS.map((section) => (
            <div key={section.title}>
              <h2 className={s.sectionTitle}>{section.title}</h2>
              <div className={s.cardGrid}>
                {section.items.map((item) => (
                  <a key={item.title} href={item.href} className={s.hoverCard}>
                    <h3 style={{
                      fontSize: '15px', fontWeight: 600,
                      color: 'var(--text-primary)', marginBottom: '8px',
                    }}>
                      {item.title}
                      <span style={{ marginLeft: '8px', color: 'var(--accent)', fontSize: '13px' }}>→</span>
                    </h3>
                    <p style={{
                      fontSize: '14px', lineHeight: 1.6,
                      color: 'var(--text-secondary)', margin: 0,
                    }}>
                      {item.desc}
                    </p>
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
