import '@/styles/globals.css';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Breadcrumbs } from '@/components/Breadcrumbs';
import { Analytics } from '@/components/Analytics';
import { pageMetadata, site } from '@/lib/metadata';

export const metadata = {
  metadataBase: new URL(site),
  ...pageMetadata('/', 'SentryPhi | AI Red Teaming Tool for LLM Security',
    'Evaluate language model behavior before deployment with SentryPhi, an AI red teaming tool for local scans, evidence-backed findings and risk reports.'),
};

const orgJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Sentryɸ',
  url: site,
  logo: `${site}/brand-mark.svg`,
  description:
    'Open-source LLM security platform for pre-deployment vulnerability assessment.',
  foundingDate: '2026',
  sameAs: ['https://github.com/prakhar2204/AI_Sentry'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(orgJsonLd) }} />
        <Navbar />
        <Breadcrumbs />
        {children}
        <Footer />
        <Analytics />
      </body>
    </html>
  );
}
