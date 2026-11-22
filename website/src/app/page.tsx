'use client';

import { useScrollReveal } from '@/lib/useScrollReveal';
import {
  HeroSection,
  TrustBar,
  ProblemSolution,
  FeaturesSection,
  HowItWorksSection,
  CapabilitiesSection,
  StatsSection,
  CloudSection,
  ProductPreview,
  OwaspSection,
  FAQSection,
  FinalCTA,
} from '@/sections/LandingSections';

export default function HomePage() {
  useScrollReveal();

  return (
    <main>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
        '@context': 'https://schema.org', '@type': 'SoftwareApplication', name: 'SentryPhi',
        applicationCategory: 'SecurityApplication', operatingSystem: 'Windows',
        url: 'https://sentryphi.me/', offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
      }) }} />
      <HeroSection />
      <TrustBar />
      <ProblemSolution />
      <FeaturesSection />
      <HowItWorksSection />
      <StatsSection />
      <CapabilitiesSection />
      <CloudSection />
      <ProductPreview />
      <OwaspSection />
      <FAQSection />
      <FinalCTA />
    </main>
  );
}
