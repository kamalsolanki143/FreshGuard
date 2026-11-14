import { Navbar } from '../components/layout/Navbar';
import { Hero } from '../components/Hero';
import { ProblemStatement } from '../components/ProblemStatement';
import { ProposedSolution } from '../components/ProposedSolution';
import { HowItWorks } from '../components/HowItWorks';
import { Features } from '../components/Features';
import { Benefits } from '../components/Benefits';
import { ArchitectureSection } from '../components/ArchitectureSection';
import { FAQ } from '../components/FAQ';
import { CTA } from '../components/CTA';
import { Footer } from '../components/Footer';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 flex flex-col">
        <Hero />
        <section id="problem">
          <ProblemStatement />
        </section>
        <section id="solution">
          <ProposedSolution />
        </section>
        <section id="how-it-works">
          <HowItWorks />
        </section>
        <section id="features">
          <Features />
        </section>
        <Benefits />
        <ArchitectureSection />
        <section id="faq">
          <FAQ />
        </section>
        <CTA />
      </main>

      <Footer />
    </div>
  );
}

