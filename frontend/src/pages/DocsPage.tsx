import { useState } from 'react';
import {
  BookOpen,
  Layers,
  Shield,
  Database,
  Search,
  Code2,
  Terminal,
  ChevronRight,
} from 'lucide-react';
import { Navbar } from '../components/layout/Navbar';
import { Footer } from '../components/Footer';

interface DocSection {
  id: string;
  title: string;
  icon: any;
  content: React.ReactNode;
}

export function DocsPage() {
  const [activeSection, setActiveSection] = useState('getting-started');

  const SECTIONS: DocSection[] = [
    {
      id: 'getting-started',
      title: '1. Getting Started',
      icon: BookOpen,
      content: (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">Getting Started with FreshGuard</h2>
          <p className="text-slate-300 leading-relaxed text-sm">
            FreshGuard detects time-sensitive claims in LLM responses, verifies them against live web evidence using Tavily, and prevents stale verification metadata from silently poisoning Bifrost semantic caching.
          </p>
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-2">
            <span className="text-cyan-400 font-bold block">Quick Launch:</span>
            <pre className="font-mono text-slate-200">python scripts/run_dev.py</pre>
            <p className="text-slate-400">
              Starts Python Verification Service on <code className="text-cyan-300">http://127.0.0.1:8000</code> and the React Frontend on <code className="text-cyan-300">http://localhost:3000</code>.
            </p>
          </div>
        </div>
      ),
    },
    {
      id: 'architecture',
      title: '2. System Architecture',
      icon: Layers,
      content: (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">System Architecture & Boundaries</h2>
          <p className="text-slate-300 leading-relaxed text-sm">
            FreshGuard employs a decoupled three-tier architecture ensuring gateway latency is strictly bounded and verification compute remains isolated.
          </p>
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-2">
            <div className="font-mono text-slate-300 space-y-1">
              <p><span className="text-cyan-400 font-bold">Tier 1:</span> Bifrost LLM Gateway (:8080) with FreshGuard Go Plugin</p>
              <p><span className="text-primary-400 font-bold">Tier 2:</span> FastAPI Verification Service (:8000) with SQLite Audit DB</p>
              <p><span className="text-purple-400 font-bold">Tier 3:</span> React 18 + Vite Web Application & Evaluator Workspace (:3000)</p>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'verification-pipeline',
      title: '3. Verification Pipeline',
      icon: Shield,
      content: (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">The Six-Stage Verification Pipeline</h2>
          <div className="space-y-3 text-sm text-slate-300">
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="font-bold text-cyan-400">Stage 1 — Prompt Interception:</span> Injects correlation IDs via Bifrost <code className="text-cyan-300 font-mono">PreLLMHook</code>.
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="font-bold text-primary-400">Stage 2 — Time-Sensitivity Prefilter:</span> Fast-path regex and heuristic evaluation skips static general knowledge.
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="font-bold text-purple-400">Stage 3 — Claim Extraction:</span> Isolates discrete verifiable facts (entity, attribute, claimed value).
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="font-bold text-amber-400">Stage 4 — Tavily Evidence Retrieval:</span> Executes advanced search queries targeting authoritative documentation.
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="font-bold text-emerald-400">Stage 5 — Verdict & Confidence Engine:</span> Calibrates evidence to produce Supported, Contradicted, or Unclear verdicts.
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="font-bold text-rose-400">Stage 6 — Semantic Cache Invalidation:</span> Purges stale or contradicted cache entries via <code className="text-rose-300 font-mono">DELETE /api/cache/clear/&#123;id&#125;</code>.
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'claim-extraction',
      title: '4. Claim Extraction',
      icon: Code2,
      content: (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">Target Claim Categories</h2>
          <p className="text-slate-300 leading-relaxed text-sm">
            FreshGuard focuses on three high-volatility claim categories where LLM hallucinations cause high financial and technical risk:
          </p>
          <ul className="list-disc list-inside text-sm text-slate-300 space-y-1.5 ml-2">
            <li><strong className="text-white">Pricing:</strong> Model subscription costs, API token rates, tier limits.</li>
            <li><strong className="text-white">Software Versions:</strong> Stable release numbers, deprecation warnings, LTS status.</li>
            <li><strong className="text-white">Company Leadership:</strong> Executive officers, CEOs, founders, board members.</li>
          </ul>
        </div>
      ),
    },
    {
      id: 'tavily-retrieval',
      title: '5. Tavily Evidence Retrieval',
      icon: Search,
      content: (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">Real-Time Search Grounding with Tavily</h2>
          <p className="text-slate-300 leading-relaxed text-sm">
            Tavily Search queries are dynamically generated based on the normalized entity and attribute of each extracted claim. The engine filters for official documentation, release notes, and authoritative announcements.
          </p>
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs">
            <p className="text-slate-400">
              Fallback behavior: If <code className="text-cyan-300 font-mono">TAVILY_API_KEY</code> is unconfigured, the verification service records a graceful <code className="text-amber-300 font-mono">unclear</code> verdict without crashing.
            </p>
          </div>
        </div>
      ),
    },
    {
      id: 'bifrost-plugin',
      title: '6. Bifrost Plugin & Semantic Cache',
      icon: Database,
      content: (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">Go Plugin & Cache Protection Rules</h2>
          <p className="text-slate-300 leading-relaxed text-sm">
            The Go integration plugin intercepts responses during Bifrost's <code className="text-cyan-300 font-mono">PostLLMHook</code> phase (which executes in reverse LIFO order on both cache misses and cache hits).
          </p>
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-2 font-mono">
            <p className="text-white font-bold font-sans">Strict Cache Guardrails:</p>
            <p className="text-slate-300">1. Missing metadata is never treated as fresh.</p>
            <p className="text-slate-300">2. Cache hit cannot silently inherit an expired verdict.</p>
            <p className="text-slate-300">3. Contradicted claims trigger immediate cache eviction.</p>
          </div>
        </div>
      ),
    },
    {
      id: 'api-reference',
      title: '7. API Reference',
      icon: Terminal,
      content: (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">REST API Specification</h2>
          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-emerald-400 font-bold">GET</span> /health
              <p className="text-slate-400 font-sans mt-1">Lightweight liveness check for container probes.</p>
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-emerald-400 font-bold">GET</span> /health/ready
              <p className="text-slate-400 font-sans mt-1">Readiness probe verifying async SQLite database connectivity.</p>
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-cyan-400 font-bold">POST</span> /v1/verifications
              <p className="text-slate-400 font-sans mt-1">Submits LLM text for time-sensitive claim verification.</p>
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-emerald-400 font-bold">GET</span> /v1/verifications/&#123;id&#125;
              <p className="text-slate-400 font-sans mt-1">Retrieves historical audit record and evidence references.</p>
            </div>
          </div>
        </div>
      ),
    },
  ];

  const currentDoc = SECTIONS.find((s) => s.id === activeSection) || SECTIONS[0];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full pt-28 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Docs Sidebar Navigation */}
          <aside className="w-full lg:w-64 flex-shrink-0">
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl sticky top-28 space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-3 mb-2 block">
                Technical Documentation
              </span>
              {SECTIONS.map((sec) => {
                const Icon = sec.icon;
                const isSelected = sec.id === activeSection;
                return (
                  <button
                    key={sec.id}
                    onClick={() => setActiveSection(sec.id)}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold text-left transition-all ${
                      isSelected
                        ? 'bg-primary-600/20 text-white border border-primary-500/40'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={`h-4 w-4 ${isSelected ? 'text-primary-400' : 'text-slate-500'}`} />
                      <span>{sec.title}</span>
                    </div>
                    {isSelected && <ChevronRight className="h-3 w-3 text-primary-400" />}
                  </button>
                );
              })}
            </div>
          </aside>

          {/* Docs Content Body */}
          <div className="flex-1 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 md:p-8 shadow-xl min-w-0">
            {currentDoc.content}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
