import { pageMetadata } from '@/lib/metadata';
import s from '@/styles/pages.module.css';

export const metadata = pageMetadata(
  '/docs/',
  "SentryPhi Documentation and Getting Started Guide",
  "Find installation instructions, scan configuration guidance and resources for interpreting LLM security reports.",
);

const SECTIONS = [
  {
    title: 'Getting Started',
    items: [
      { title: 'Installation Guide', desc: 'Find the Windows installer and check which release assets are available.', href: '/download/' },
      { title: 'Your First Scan', desc: 'Connect to an API endpoint, configure scan depth, and run your first vulnerability scan with a defined scope.', href: '/blog/scan-llm-security-vulnerabilities/#scan-workflow' },
      { title: 'Understanding Results', desc: 'How to read the risk score, severity levels, confidence ratings, and remediation recommendations.', href: '/blog/scan-llm-security-vulnerabilities/#scan-results' },
    ],
  },
  {
    title: 'Configuration',
    items: [
      { title: 'Scan Depth Profiles', desc: 'Quick, Standard, and Deep scans: what each covers, estimated time, and API cost.', href: '/blog/scan-llm-security-vulnerabilities/#scan-workflow' },
      { title: 'Manifest Files', desc: 'Explore the example JSON manifest before preparing your own scan configuration.', href: 'https://github.com/prakhar2204/AI_Sentry/blob/prakhar/app/backend/example_manifest.json' },
      { title: 'Probe Categories', desc: 'Prompt injection, jailbreak resistance, data leakage, harmful output — what each category tests.', href: '/blog/owasp-llm-top-10-guide/' },
    ],
  },
  {
    title: 'Security Analysis',
    items: [
      { title: 'Multi-Layer Architecture', desc: 'How three independent analysis layers — probing, adversarial simulation, behavioral evaluation — work together.', href: '/#features' },
      { title: 'Confidence Scoring', desc: 'The weighted formula behind confidence scores: cross-engine corroboration, attack success rate, probe diversity.', href: '/blog/scan-llm-security-vulnerabilities/#scan-results' },
      { title: 'OWASP LLM Top 10', desc: 'Coverage mapping: which OWASP categories Sentryɸ tests, which are partial, and which are advisory-only.', href: '/blog/owasp-llm-top-10-guide/' },
    ],
  },
  {
    title: 'Deployment & Reports',
    items: [
      { title: 'Report Formats', desc: 'PDF for stakeholders, HTML for sharing, JSON for CI/CD integration. All include full findings and remediation.', href: '/blog/scan-llm-security-vulnerabilities/#scan-results' },
      { title: 'Cloud Sign-In', desc: 'Read the project guide to connecting a cloud account for deployment.', href: 'https://github.com/prakhar2204/AI_Sentry/blob/prakhar/docs/CLOUD_SIGN_IN.md' },
      { title: 'Backend Reference', desc: 'Read the setup and usage notes in the backend documentation.', href: 'https://github.com/prakhar2204/AI_Sentry/blob/prakhar/app/backend/README.md' },
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
