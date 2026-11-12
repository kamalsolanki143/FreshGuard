import { useEffect, useState } from 'react';
import { Hero } from '@components/Hero';
import { ProblemStatement } from '@components/ProblemStatement';
import { ProposedSolution } from '@components/ProposedSolution';
import { Features } from '@components/Features';
import { HowItWorks } from '@components/HowItWorks';
import { Benefits } from '@components/Benefits';
import { FAQ } from '@components/FAQ';
import { CTA } from '@components/CTA';
import { Footer } from '@components/Footer';
import { Navigation } from '@components/Navigation';
import { FloatingCTA } from '@components/FloatingCTA';

export function App() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 100);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Navigation scrolled={scrolled} />

      <main className="flex flex-col">
        <Hero />
        <ProblemStatement />
        <ProposedSolution />
        <Features />
        <HowItWorks />
        <Benefits />
        <FAQ />
        <CTA />
      </main>

      <FloatingCTA />
      <Footer />
    </div>
  );
}

export default App;