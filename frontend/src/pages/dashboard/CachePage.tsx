import { useState } from 'react';
import {
  RefreshCw,
  Info,
} from 'lucide-react';

export function CachePage() {
  const [simulatedCacheAge, setSimulatedCacheAge] = useState<number>(30); // in hours
  const [simulatedCategory, setSimulatedCategory] = useState<'pricing' | 'software_version' | 'leadership'>('pricing');

  // Policy TTL rules (matching Go plugin and Python policy defaults)
  const categoryTTLs: Record<string, number> = {
    pricing: 6, // 6 hours
    software_version: 24, // 24 hours
    leadership: 24, // 24 hours
  };

  const currentTTL = categoryTTLs[simulatedCategory];
  const isExpired = simulatedCacheAge > currentTTL;
  const decision = isExpired
    ? {
        verdict: 'EXPIRED',
        shouldEvict: true,
        reverify: true,
        action: 'DELETE /api/cache/clear/{cacheId}',
        badgeColor: 'rose',
        explanation: `Cached verification expired (${simulatedCacheAge}h > ${currentTTL}h policy TTL). Bifrost cache entry must be evicted; cache hit cannot silently inherit expired Supported verdict.`,
      }
    : {
        verdict: 'FRESH',
        shouldEvict: false,
        reverify: false,
        action: 'Serve from semantic cache directly',
        badgeColor: 'emerald',
        explanation: `Cache entry is verified fresh (age ${simulatedCacheAge}h is within the ${currentTTL}h policy TTL window).`,
      };

  return (
    <div className="space-y-8">
      {/* Title */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-3">
          <span>Bifrost Semantic Cache Protection</span>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800 font-mono font-bold">
            Bifrost v2.5.1
          </span>
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Guarding semantic LLM caching against poisoned, stale, or contradicted time-sensitive claims
        </p>
      </div>

      {/* Distinction Banner: Telemetry vs Architecture */}
      <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
        <Info className="h-5 w-5 text-cyan-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-bold text-white">Live Integration & Architectural Boundaries</p>
          <p className="text-slate-400 leading-relaxed">
            FreshGuard integrates with Bifrost via native Go hooks (<code className="text-cyan-300 font-mono">PreLLMHook</code> and <code className="text-cyan-300 font-mono">PostLLMHook</code>). Cache invalidation commands invoke Bifrost's verified management endpoints (<code className="text-cyan-300 font-mono">DELETE /api/cache/clear/&#123;cacheId&#125;</code>) with virtual key (<code className="text-cyan-300 font-mono">x-bf-vk</code>) and setup token headers.
          </p>
        </div>
      </div>

      {/* Core Cache Protection Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl space-y-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-400 flex items-center justify-center font-bold text-xs">
            01
          </div>
          <h3 className="font-bold text-sm text-white">Missing Metadata is Never Fresh</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            If a semantic cache hit occurs and no prior FreshGuard verification record is located in the ledger, the response is rejected as unverified and evicted.
          </p>
        </div>

        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl space-y-2">
          <div className="w-8 h-8 rounded-lg bg-primary-950 border border-primary-800 text-primary-400 flex items-center justify-center font-bold text-xs">
            02
          </div>
          <h3 className="font-bold text-sm text-white">Minimum Volatility TTL Binding</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Cache entry validity is strictly determined by the shortest TTL among verified claims (<code className="text-primary-300 font-mono">min(TTL_claims)</code>). Fast-changing pricing claims supersede longer software version TTLs.
          </p>
        </div>

        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl space-y-2">
          <div className="w-8 h-8 rounded-lg bg-rose-950 border border-rose-800 text-rose-400 flex items-center justify-center font-bold text-xs">
            03
          </div>
          <h3 className="font-bold text-sm text-white">No Silent Verdict Inheritance</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Expired cache hits cannot silently pass through with stale <span className="text-emerald-400 font-semibold">SUPPORTED</span> badges. FreshGuard forces cache purging and triggers live re-verification.
          </p>
        </div>
      </div>

      {/* Interactive Cache Freshness Evaluator Simulator */}
      <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl space-y-6">
        <div>
          <h2 className="text-base font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-cyan-400" />
            <span>Interactive Cache Evaluator Simulator</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Simulate how FreshGuard's Go Evaluator (<code className="text-cyan-300 font-mono">plugin/cache/evaluator.go</code>) decides whether to serve or purge cached responses.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Controls */}
          <div className="space-y-4 p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs">
            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">
                Claim Category
              </label>
              <select
                value={simulatedCategory}
                onChange={(e) => setSimulatedCategory(e.target.value as any)}
                className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded-lg p-2 text-xs outline-none"
              >
                <option value="pricing">Pricing (Policy TTL: 6 hours)</option>
                <option value="software_version">Software Version (Policy TTL: 24 hours)</option>
                <option value="leadership">Company Leadership (Policy TTL: 24 hours)</option>
              </select>
            </div>

            <div>
              <div className="flex justify-between text-slate-300 font-semibold mb-1.5">
                <span>Cached Response Age:</span>
                <span className="font-mono text-cyan-400">{simulatedCacheAge} hours ago</span>
              </div>
              <input
                type="range"
                min={1}
                max={72}
                value={simulatedCacheAge}
                onChange={(e) => setSimulatedCacheAge(Number(e.target.value))}
                className="w-full accent-cyan-500 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 mt-1">
                <span>1 hour</span>
                <span>Policy TTL: {currentTTL}h</span>
                <span>72 hours</span>
              </div>
            </div>
          </div>

          {/* Decision Outcome */}
          <div
            className={`p-5 rounded-xl border flex flex-col justify-between ${
              decision.badgeColor === 'emerald'
                ? 'bg-emerald-950/20 border-emerald-800/80 text-emerald-200'
                : 'bg-rose-950/20 border-rose-800/80 text-rose-200'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono uppercase font-bold tracking-wider text-slate-400">
                  Evaluator Decision
                </span>
                <span
                  className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
                    decision.badgeColor === 'emerald'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : 'bg-rose-950 text-rose-400 border border-rose-800'
                  }`}
                >
                  VERDICT: {decision.verdict}
                </span>
              </div>

              <p className="text-xs text-slate-200 leading-relaxed mb-4">
                {decision.explanation}
              </p>
            </div>

            <div className="pt-3 border-t border-slate-800/80 space-y-1.5 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Bifrost Action:</span>
                <span className={decision.shouldEvict ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
                  {decision.action}
                </span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Re-verification:</span>
                <span className="text-slate-200">
                  {decision.reverify ? 'Mandatory (Triggered)' : 'Bypassed (Within TTL)'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Lifecyle Sequence Visualizer */}
      <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">
          Bifrost Request Lifecycle Hook Execution
        </h3>
        <div className="space-y-3 font-mono text-xs">
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between">
            <span className="text-cyan-400 font-semibold">1. PreLLMHook</span>
            <span className="text-slate-400 text-[11px]">Injects x-bifrost-request-id correlation tracking</span>
          </div>
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between">
            <span className="text-purple-400 font-semibold">2. Semantic Cache Check</span>
            <span className="text-slate-400 text-[11px]">Checks embedding similarity against cached queries</span>
          </div>
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between">
            <span className="text-primary-400 font-semibold">3. PostLLMHook (Reverse LIFO)</span>
            <span className="text-slate-400 text-[11px]">Evaluates metadata hash, checks TTL, triggers eviction on stale hits</span>
          </div>
        </div>
      </div>
    </div>
  );
}
