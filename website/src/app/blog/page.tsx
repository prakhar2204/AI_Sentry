import type { Metadata } from 'next';
import s from '@/styles/pages.module.css';

export const metadata: Metadata = {
  title: 'Blog — LLM Security Research & Tutorials',
  description:
    'Articles on LLM security research, prompt injection defense, jailbreak prevention, AI red teaming methodologies, and pre-deployment security best practices from the Sentryɸ team.',
  alternates: { canonical: 'https://sentryphi.dev/blog' },
};

const POSTS = [
  {
    title: 'Why Your LLM Needs a Security Scan Before Deployment',
    excerpt: 'Most teams ship AI models without meaningful adversarial testing. We break down the five vulnerability categories every production LLM should be scanned for — and what happens when you skip them.',
    date: 'October 2026',
    category: 'Security Fundamentals',
    readTime: '8 min read',
  },
  {
    title: 'Understanding the OWASP LLM Top 10: A Practical Guide',
    excerpt: 'The OWASP LLM Top 10 defines the most critical security risks for large language models. We map each category to real-world attack patterns and show how automated scanning catches them.',
    date: 'October 2026',
    category: 'OWASP',
    readTime: '12 min read',
  },
  {
    title: "Multi-Layer Security Analysis: Why One Scanner Isn't Enough",
    excerpt: "Probe-based testing finds different vulnerabilities than adversarial simulation or behavioral evaluation. Here's how running all three produces higher-confidence findings with lower false-positive rates.",
    date: 'October 2026',
    category: 'Architecture',
    readTime: '10 min read',
  },
  {
    title: 'Explainable AI Security: How Sentryɸ Computes Confidence Scores',
    excerpt: "Black-box risk scores create more confusion than clarity. We explain the weighted formula behind Sentryɸ's dual-axis scoring — and why separation of severity and confidence matters.",
    date: 'October 2026',
    category: 'Deep Dive',
    readTime: '15 min read',
  },
  {
    title: 'Prompt Injection in 2026: Attack Vectors and Defense Strategies',
    excerpt: 'From simple instruction overrides to multi-turn extraction attacks — the prompt injection landscape has evolved. We catalog current attack patterns and review effective defense layers.',
    date: 'October 2026',
    category: 'Research',
    readTime: '11 min read',
  },
  {
    title: 'From Scan to Deploy: Securing LLMs on AWS with Bedrock Guardrails',
    excerpt: "After scanning, what next? We walk through Sentryɸ's Deployment Advisor — from risk-based guardrail configuration to one-click IAM + CloudWatch + Bedrock provisioning on AWS.",
    date: 'October 2026',
    category: 'Deployment',
    readTime: '9 min read',
  },
];

export default function BlogPage() {
  return (
    <main className={s.pageContainer}>
      <div className={s.pageInner}>
        <div className={s.pageHeader}>
          <span className={s.pageLabel}>Blog</span>
          <h1 className={s.pageTitle}>LLM Security Research &amp; Tutorials</h1>
          <p className={s.pageSubtitle}>
            Deep dives into AI security, vulnerability research, and practical
            guides for securing language models in production.
          </p>
        </div>

        <div className={s.cardGridWide}>
          {POSTS.map((post) => (
            <a key={post.title} href="#" className={s.hoverCardLg} style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <span className={s.categoryTag}>{post.category}</span>
                <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{post.readTime}</span>
              </div>
              <h2 style={{
                fontSize: '17px', fontWeight: 600,
                color: 'var(--text-primary)', lineHeight: 1.35,
                marginBottom: '12px',
              }}>{post.title}</h2>
              <p style={{
                fontSize: '14px', lineHeight: 1.6,
                color: 'var(--text-secondary)', margin: 0, flex: 1,
              }}>{post.excerpt}</p>
              <div style={{
                marginTop: '20px', paddingTop: '16px',
                borderTop: '1px solid var(--border-subtle)',
                fontSize: '13px', color: 'var(--text-muted)',
              }}>
                {post.date}
              </div>
            </a>
          ))}
        </div>
      </div>
    </main>
  );
}
