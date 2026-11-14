import { Server, Search, ArrowRight, Zap, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../lib/authContext';

export function ArchitectureSection() {
  const { user } = useAuth();
  return (
    <section id="architecture" className="py-24 bg-slate-900/90 text-white relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-96 h-96 bg-primary-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest px-3 py-1 bg-cyan-950/60 border border-cyan-800/80 rounded-full inline-block mb-3">
            System Architecture
          </span>
          <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-white">
            Engineered for <span className="gradient-text">Zero-Overhead Protection</span>
          </h2>
          <p className="mt-3 text-slate-400 text-sm sm:text-base leading-relaxed">
            FreshGuard decouples gateway latency from factual verification compute. The lightweight Go plugin intercepts model lifecycle events, while the Python verification engine runs independently.
          </p>
        </div>

        {/* 3-Tier Interactive Diagram Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          {/* Tier 1: Gateway */}
          <div className="p-6 rounded-2xl bg-slate-950/90 border border-slate-800 shadow-xl space-y-4 relative group hover:border-cyan-500/50 transition-all">
            <div className="w-12 h-12 rounded-xl bg-cyan-950 border border-cyan-800 flex items-center justify-center text-cyan-400 shadow-md">
              <Server className="h-6 w-6" />
            </div>
            <div>
              <span className="text-[10px] font-mono text-cyan-400 font-bold uppercase tracking-wider">
                Gateway Layer (:8080)
              </span>
              <h3 className="text-lg font-bold text-white mt-0.5">Bifrost LLM Gateway</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Receives client prompts, checks semantic cache similarity, and calls LLM providers. Runs FreshGuard's <code className="text-cyan-300 font-mono">PreLLMHook</code> and <code className="text-cyan-300 font-mono">PostLLMHook</code>.
            </p>
            <div className="pt-3 border-t border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
              <p>• Reverse LIFO Hook Execution</p>
              <p>• DELETE /api/cache/clear/&#123;id&#125;</p>
              <p>• Virtual Key Header Propagation</p>
            </div>
          </div>

          {/* Tier 2: Go Plugin & Evaluator */}
          <div className="p-6 rounded-2xl bg-slate-950/90 border border-slate-800 shadow-xl space-y-4 relative group hover:border-primary-500/50 transition-all">
            <div className="w-12 h-12 rounded-xl bg-primary-950 border border-primary-800 flex items-center justify-center text-primary-400 shadow-md">
              <Zap className="h-6 w-6" />
            </div>
            <div>
              <span className="text-[10px] font-mono text-primary-400 font-bold uppercase tracking-wider">
                Plugin Layer (Native Go)
              </span>
              <h3 className="text-lg font-bold text-white mt-0.5">FreshGuard Go Plugin</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Inspects model output, consults local file-backed freshness ledger, evaluates TTLs, and delegates claim verification to the Python service.
            </p>
            <div className="pt-3 border-t border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
              <p>• Bounded 3-Second Timeout</p>
              <p>• Exponential Backoff Retries</p>
              <p>• Atomic File-Backed Ledger</p>
            </div>
          </div>

          {/* Tier 3: Python Verification Engine */}
          <div className="p-6 rounded-2xl bg-slate-950/90 border border-slate-800 shadow-xl space-y-4 relative group hover:border-purple-500/50 transition-all">
            <div className="w-12 h-12 rounded-xl bg-purple-950 border border-purple-800 flex items-center justify-center text-purple-400 shadow-md">
              <Search className="h-6 w-6" />
            </div>
            <div>
              <span className="text-[10px] font-mono text-purple-400 font-bold uppercase tracking-wider">
                Verification Engine (:8000)
              </span>
              <h3 className="text-lg font-bold text-white mt-0.5">FastAPI + Tavily</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Extracts factual claims, retrieves authoritative citations via Tavily Search, calibrates confidence, and stores audit logs in SQLite.
            </p>
            <div className="pt-3 border-t border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
              <p>• Supported/Contradicted Engine</p>
              <p>• Asynchronous Non-blocking IO</p>
              <p>• Idempotent Deduplication</p>
            </div>
          </div>
        </div>

        {/* Live Demo Preview CTA Card */}
        <div className="p-8 rounded-3xl bg-gradient-to-r from-cyan-950/60 via-slate-900 to-purple-950/60 border border-slate-800 text-center max-w-4xl mx-auto shadow-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-800 text-emerald-400 text-xs font-bold mb-4">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>Interactive Verification Sandbox Ready</span>
          </div>
          <h3 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Ready to test live factual verification?
          </h3>
          <p className="mt-2 text-slate-300 text-sm max-w-xl mx-auto">
            Test model prompts across pricing, software versions, and leadership in the dedicated developer workspace.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-4">
            <Link
              to={user ? '/dashboard/verify' : '/login'}
              className="px-6 py-3 bg-gradient-to-r from-cyan-500 via-primary-600 to-purple-600 hover:opacity-95 text-white font-bold text-sm rounded-xl shadow-lg shadow-primary-500/25 flex items-center gap-2 transition-all"
            >
              <span>Open Verification Workspace</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to={user ? '/dashboard' : '/login'}
              className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white font-bold text-sm rounded-xl border border-slate-700 transition-colors"
            >
              <span>{user ? 'Open Dashboard' : 'Explore Dashboard'}</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
