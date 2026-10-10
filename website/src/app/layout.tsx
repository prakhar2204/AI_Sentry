import type { Metadata } from 'next';
import '@/styles/globals.css';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

const BASE_URL = 'https://sentryphi.dev';

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),
  title: {
    default: 'Sentryɸ — Pre-Deployment LLM Security Platform',
    template: '%s | Sentryɸ',
  },
  description:
    'Sentryɸ is a free, open-source LLM security platform that scans AI models for vulnerabilities before deployment. Multi-layer security analysis, adaptive vulnerability detection, explainable risk scoring, and actionable remediation — in a single desktop application.',
  keywords: [
    'LLM security scanner',
    'AI red teaming tool',
    'LLM vulnerability assessment',
    'jailbreak testing',
    'prompt injection detection',
    'AI security platform',
    'OWASP LLM Top 10',
    'pre-deployment AI validation',
    'LLM penetration testing',
    'AI model security audit',
    'open source AI security',
    'SentryPhi',
    'Sentryɸ',
  ],
  applicationName: 'Sentryɸ',
  authors: [{ name: 'Sentryɸ Team' }],
  creator: 'Sentryɸ',
  publisher: 'Sentryɸ',
  category: 'Technology',
  classification: 'AI Security Software',
  openGraph: {
    title: 'Sentryɸ — Pre-Deployment LLM Security Platform',
    description:
      'Scan your LLMs for vulnerabilities before deployment. Multi-layer security analysis, risk scoring, and actionable remediation. Free and open source.',
    siteName: 'Sentryɸ',
    type: 'website',
    url: BASE_URL,
    locale: 'en_US',
    images: [
      {
        url: `${BASE_URL}/og-image.png`,
        width: 1200,
        height: 630,
        alt: 'Sentryɸ — LLM Security Platform',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Sentryɸ — Pre-Deployment LLM Security Platform',
    description:
      'Scan your LLMs for vulnerabilities before deployment. Free and open source.',
    images: [`${BASE_URL}/og-image.png`],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  alternates: {
    canonical: BASE_URL,
  },
  verification: {
    // Add your verification codes here after setting up
    // google: 'your-google-verification-code',
    // yandex: 'your-yandex-verification-code',
  },
  other: {
    'msapplication-TileColor': '#08090D',
    'theme-color': '#08090D',
  },
};

/* JSON-LD Structured Data */
const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Sentryɸ',
  alternateName: 'SentryPhi',
  description:
    'A free, open-source LLM security platform that scans AI models for prompt injection, jailbreak, data leakage, and behavioral vulnerabilities before deployment.',
  url: BASE_URL,
  applicationCategory: 'SecurityApplication',
  operatingSystem: ['Windows 10+', 'Ubuntu 20.04+'],
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'USD',
  },
  featureList: [
    'Multi-layer security analysis',
    'Adaptive vulnerability detection',
    'Model behavior stress testing',
    'Explainable dual-axis risk scoring',
    'OWASP LLM Top 10 coverage mapping',
    'Actionable three-layer remediation',
    'Cloud deployment advisory',
    'PDF, HTML, JSON report export',
  ],
  softwareVersion: '1.0.0',
  license: 'https://opensource.org/licenses/MIT',
  isAccessibleForFree: true,
  creator: {
    '@type': 'Organization',
    name: 'Sentryɸ',
    url: BASE_URL,
  },
};

const orgJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Sentryɸ',
  url: BASE_URL,
  logo: `${BASE_URL}/logo.svg`,
  description:
    'Open-source LLM security platform for pre-deployment vulnerability assessment.',
  foundingDate: '2026',
  sameAs: [
    // Add social links here when available
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(orgJsonLd) }}
        />
      </head>
      <body>
        <Navbar />
        {children}
        <Footer />
      </body>
    </html>
  );
}
