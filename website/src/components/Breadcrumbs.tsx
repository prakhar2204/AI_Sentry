'use client';

import { usePathname } from 'next/navigation';

const names: Record<string, string> = {
  about: 'About', docs: 'Documentation', blog: 'Blog', download: 'Download',
  privacy: 'Privacy', terms: 'Terms',
  'owasp-llm-top-10-guide': 'OWASP LLM Top 10',
  'scan-llm-security-vulnerabilities': 'Scanning an LLM',
};

export function Breadcrumbs() {
  const segments = usePathname().split('/').filter(Boolean);
  if (!segments.length || segments.some(segment => !names[segment])) return null;
  const items = [{ name: 'Home', path: '/' }, ...segments.map((part, i) => ({
    name: names[part], path: '/' + segments.slice(0, i + 1).join('/') + '/',
  }))];
  const data = {
    '@context': 'https://schema.org', '@type': 'BreadcrumbList',
    itemListElement: items.map(({ name, path }, i) => ({
      '@type': 'ListItem', position: i + 1, name, item: 'https://sentryphi.me' + path,
    })),
  };
  return <nav aria-label="Breadcrumb" className="breadcrumbs">
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
    {items.map(({ name, path }, i) => i === items.length - 1
      ? <span key={path} aria-current="page">{name}</span>
      : <span key={path}><a href={path}>{name}</a> / </span>)}
  </nav>;
}
