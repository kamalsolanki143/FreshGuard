import { useState } from 'react';
import {
  Shield,
  Clock,
  Lock,
  Info,
} from 'lucide-react';

export function SettingsPage() {
  const [failOpen, setFailOpen] = useState(true);
  const [enableEviction, setEnableEviction] = useState(true);
  const [reverifyOnHit, setReverifyOnHit] = useState(true);

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Title */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
          System Policies & Settings
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Configure freshness policies, TTL durations, and gateway lifecycle behavior
        </p>
      </div>

      {/* Backend Synchronization Notice */}
      <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
        <Info className="h-5 w-5 text-cyan-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-bold text-white">Engine Configuration Transparency</p>
          <p className="text-slate-400 leading-relaxed">
            Values displayed below reflect the active FreshGuard Go plugin defaults and Python FastAPI backend configurations. In production, enterprise policies are managed via immutable configuration files (<code className="text-cyan-300 font-mono">bifrost.yaml</code> and environment variables) to maintain SOC 2 compliance.
          </p>
        </div>
      </div>

      {/* Freshness TTL Policies (Backend Supported) */}
      <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-sm space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="h-4 w-4 text-cyan-400" />
              <span>Category Freshness TTL Policies</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Maximum time a verified claim verdict can be trusted before mandatory re-verification
            </p>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
            Active Policies
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Pricing & Plans</span>
            <div className="text-lg font-black text-white">6 Hours</div>
            <p className="text-[11px] text-slate-500">21,600s TTL. High volatility; protects against price changes.</p>
          </div>

          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Software Versions</span>
            <div className="text-lg font-black text-white">24 Hours</div>
            <p className="text-[11px] text-slate-500">86,400s TTL. Medium volatility; tracks daily release updates.</p>
          </div>

          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Company Leadership</span>
            <div className="text-lg font-black text-white">24 Hours</div>
            <p className="text-[11px] text-slate-500">86,400s TTL. Medium volatility; captures executive turnover.</p>
          </div>
        </div>
      </div>

      {/* Gateway Lifecycle & Failure Modes */}
      <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-sm space-y-5">
        <div className="border-b border-slate-800 pb-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary-400" />
            <span>Gateway Fault Tolerance & Eviction Policies</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Controls how FreshGuard handles upstream service timeouts or missing search evidence
          </p>
        </div>

        <div className="space-y-4 text-xs">
          {/* Fail-Open Toggle */}
          <div className="flex items-center justify-between p-4 bg-slate-950 rounded-xl border border-slate-800">
            <div className="space-y-0.5">
              <span className="font-bold text-white text-sm">Fail-Open Delivery Mode</span>
              <p className="text-slate-400 text-xs">
                When enabled, if the verification engine is unreachable or times out, the original model response is delivered with a prominent <code className="text-amber-300">unverified</code> warning rather than returning an error to the user.
              </p>
            </div>
            <button
              onClick={() => setFailOpen(!failOpen)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                failOpen
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : 'bg-rose-950 text-rose-400 border border-rose-800'
              }`}
            >
              {failOpen ? 'Enabled (Default)' : 'Fail-Closed'}
            </button>
          </div>

          {/* Automatic Cache Eviction */}
          <div className="flex items-center justify-between p-4 bg-slate-950 rounded-xl border border-slate-800">
            <div className="space-y-0.5">
              <span className="font-bold text-white text-sm">Automatic Bifrost Cache Eviction</span>
              <p className="text-slate-400 text-xs">
                Immediately issues <code className="text-cyan-300">DELETE /api/cache/clear/&#123;cacheId&#125;</code> when a cached response is confirmed expired or contradicted.
              </p>
            </div>
            <button
              onClick={() => setEnableEviction(!enableEviction)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                enableEviction
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {enableEviction ? 'Active' : 'Disabled'}
            </button>
          </div>

          {/* Re-verify on Cache Hit */}
          <div className="flex items-center justify-between p-4 bg-slate-950 rounded-xl border border-slate-800">
            <div className="space-y-0.5">
              <span className="font-bold text-white text-sm">Re-verify Expired Hits Synchronously</span>
              <p className="text-slate-400 text-xs">
                When a cache hit has expired metadata, immediately query fresh web evidence and update the ledger.
              </p>
            </div>
            <button
              onClick={() => setReverifyOnHit(!reverifyOnHit)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                reverifyOnHit
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {reverifyOnHit ? 'Active' : 'Disabled'}
            </button>
          </div>
        </div>
      </div>

      {/* Secure Credential Management Guidance */}
      <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-sm space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Lock className="h-4 w-4 text-purple-400" />
          <span>Credential & Secret Configuration</span>
        </h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          Configure API credentials using the following environment variables before starting the stack:
        </p>

        <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 space-y-2">
          <div>
            <span className="text-cyan-400 font-bold">TAVILY_API_KEY</span>=tvly-...
            <span className="text-slate-500 text-[11px] block font-sans">Required for real-time web search grounding.</span>
          </div>
          <div>
            <span className="text-cyan-400 font-bold">VERIFICATION_SERVICE_API_KEY</span>=fg_sec_...
            <span className="text-slate-500 text-[11px] block font-sans">Used when API_AUTH_MODE=enforce for cross-service authentication.</span>
          </div>
          <div>
            <span className="text-cyan-400 font-bold">BIFROST_VIRTUAL_KEY</span>=vk_...
            <span className="text-slate-500 text-[11px] block font-sans">Propagated by Go plugin to Bifrost cache eviction headers.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
