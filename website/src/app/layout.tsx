import type { Metadata } from 'next';
import '@/styles/globals.css';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Sentryɸ — Pre-Deployment LLM Security Platform',
  description:
    'Sentryɸ scans your LLMs for vulnerabilities before deployment. Multi-layer security analysis, adaptive vulnerability detection, and actionable remediation. Free, open source.',
  keywords: [
    'LLM security scanner',
    'AI red teaming',
    'LLM vulnerability assessment',
    'jailbreak testing',
    'AI security platform',
    'OWASP LLM Top 10',
    'SentryPhi',
  ],
  applicationName: 'Sentryɸ',
  openGraph: {
    title: 'Sentryɸ — Pre-Deployment LLM Security Platform',
    description:
      'Scan your LLMs for vulnerabilities before deployment. Multi-layer security analysis, risk scoring, and actionable remediation.',
    siteName: 'Sentryɸ',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Sentryɸ — Pre-Deployment LLM Security Platform',
    description:
      'Scan your LLMs for vulnerabilities before deployment. Free and open source.',
  },
  robots: 'index, follow',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        {children}
        <Footer />
      </body>
    </html>
  );
}
