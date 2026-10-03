'use client';

import { useScrollReveal } from '@/lib/useScrollReveal';
import {
  HeroSection,
  TrustBar,
  ProblemSolution,
  FeaturesSection,
  HowItWorksSection,
  CapabilitiesSection,
  CloudSection,
  ProductPreview,
  OwaspSection,
  FutureSection,
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
      <CapabilitiesSection />
      <CloudSection />
      <ProductPreview />
      <OwaspSection />
      <FutureSection />
      <FinalCTA />
    </main>
  );
}
