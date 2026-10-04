import type { Metadata } from 'next';
import '@/styles/globals.css';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
  title: 'AI Sentry — Pre-Deployment Security Platform for LLMs',
  description:
    'AI Sentry scans your LLMs for vulnerabilities before deployment. Multi-layer security analysis, adaptive vulnerability detection, and actionable remediation. Free, open source.',
  keywords: [
    'LLM security scanner',
    'AI red teaming',
    'LLM vulnerability assessment',
    'jailbreak testing',
    'AI security platform',
    'OWASP LLM Top 10',
  ],
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
