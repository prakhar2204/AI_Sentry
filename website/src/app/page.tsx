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
