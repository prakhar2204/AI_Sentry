import type { Metadata } from 'next';

export const site = 'https://sentryphi.me';

export function pageMetadata(path: string, title: string, description: string, article = false): Metadata {
  const url = site + path;
  const images = [{ url: site + '/social-card.webp', width: 1200, height: 630, alt: 'SentryPhi LLM security platform' }];
  return {
    title, description, alternates: { canonical: url },
    openGraph: { title, description, url, siteName: 'SentryPhi', type: article ? 'article' : 'website', images },
    twitter: { card: 'summary_large_image', title, description, images },
  };
}
