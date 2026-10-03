import type { Metadata } from 'next';
import '@/styles/globals.css';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
  title: 'AI-SENTRY — LLM Security Scanner | Scan Before You Ship',
  description:
    'AI-SENTRY runs Garak, PyRIT, and DeepTeam to find LLM vulnerabilities before you deploy. Free, open source. Download for Windows and Linux.',
  keywords: [
    'LLM security scanner',
    'AI red teaming',
    'LLM vulnerability assessment',
    'jailbreak testing',
    'Garak PyRIT scanner',
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
