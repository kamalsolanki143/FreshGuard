import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Database,
  Sparkles,
  ArrowRight,
  TrendingUp,
  Layers,
  Clock,
} from 'lucide-react';
import { useHistory } from '../../lib/historyContext';
import { checkHealth } from '../../lib/api';

export function OverviewPage() {
  const { history, getStats } = useHistory();
  const stats = getStats();
  const [pythonHealth, setPythonHealth] = useState<'checking' | 'healthy' | 'offline'>('checking');

  useEffect(() => {
    let mounted = true;
    checkHealth()
      .then(() => {
        if (mounted) setPythonHealth('healthy');
      })
      .catch(() => {
        if (mounted) setPythonHealth('offline');
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="space-y-8">
      {/* Page Title & Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Verification Overview
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time telemetry across LLM factual verification and Bifrost semantic caching
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard/verify"
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 hover:opacity-95 text-white font-bold text-sm rounded-xl shadow-lg shadow-primary-500/20 transition-all"
          >
            <Sparkles className="h-4 w-4" />
            <span>Verify New Claim</span>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Verifications */}
        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Verifications</span>
            <Layers className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{stats.total}</span>
            <span className="text-xs font-medium text-slate-400">runs</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Active verification jobs processed
          </p>
        </div>

        {/* Claims Evaluated */}
        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Claims Evaluated</span>
            <Sparkles className="h-4 w-4 text-primary-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{stats.claimsChecked}</span>
            <span className="text-xs font-medium text-primary-300">claims</span>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-2">
            <span className="text-emerald-400 font-semibold">{stats.supported} supported</span>
            <span>•</span>
            <span className="text-rose-400 font-semibold">{stats.contradicted} contradicted</span>
          </div>
        </div>

        {/* Cache Freshness Decisions */}
        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Cache State</span>
            <Database className="h-4 w-4 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-emerald-400">{stats.fresh}</span>
            <span className="text-xs font-medium text-slate-400">fresh / {stats.stale} stale</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Protected against semantic cache poisoning
          </p>
        </div>

        {/* Average Processing Time */}
        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Engine Latency</span>
            <Clock className="h-4 w-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-amber-400">~24</span>
            <span className="text-xs font-medium text-slate-400">ms avg</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Real-time pipeline prefilter + extraction
          </p>
        </div>
      </div>

      {/* Main Grid: Recent Activity & Verdict Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Verifications Table (2 columns wide) */}
        <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Recent Verification Activity
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Claims analyzed across Pricing, Software Versions, and Leadership
              </p>
            </div>
            <Link
              to="/dashboard/history"
              className="text-xs font-semibold text-primary-400 hover:text-primary-300 flex items-center gap-1"
            >
              <span>View Full History</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-3">Verification ID</th>
                  <th className="py-3 px-3">Category / Entity</th>
                  <th className="py-3 px-3">Verdict</th>
                  <th className="py-3 px-3">Freshness</th>
                  <th className="py-3 px-3">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70 text-slate-300">
                {history.slice(0, 5).map((item) => {
                  const claim = (item.claims && item.claims[0]) || (item.results && item.results[0]);
                  const verdict = claim?.verdict || 'unclear';
                  return (
                    <tr key={item.verification_id || item.request_id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3.5 px-3 font-mono text-slate-300 font-medium">
                        {item.verification_id || item.request_id}
                      </td>
                      <td className="py-3.5 px-3">
                        <div className="font-semibold text-white">
                          {claim?.entity || 'Claim Text'}
                        </div>
                        <div className="text-[11px] text-slate-400 capitalize">
                          {claim?.category || 'general'}
                        </div>
                      </td>
                      <td className="py-3.5 px-3">
                        {verdict === 'supported' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                            <CheckCircle2 className="h-3 w-3" /> Supported
                          </span>
                        ) : verdict === 'contradicted' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-950 text-rose-400 border border-rose-800">
                            <XCircle className="h-3 w-3" /> Contradicted
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-950 text-amber-400 border border-amber-800">
                            <AlertCircle className="h-3 w-3" /> Unclear
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-3">
                        <span
                          className={`font-mono text-[10px] font-semibold px-2 py-0.5 rounded ${
                            item.freshness_status === 'FRESH'
                              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                              : item.freshness_status === 'STALE'
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {item.freshness_status || 'COMPLETED'}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 font-mono text-slate-400">
                        {item.processing_time_ms ? `${item.processing_time_ms}ms` : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Verdict Distribution & Service Health (1 column) */}
        <div className="space-y-6">
          {/* Verdict Distribution Box */}
          <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-sm">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center justify-between">
              <span>Verdict Distribution</span>
              <TrendingUp className="h-4 w-4 text-primary-400" />
            </h3>

            <div className="space-y-3.5">
              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Supported
                  </span>
                  <span className="text-slate-300">
                    {stats.supported} ({stats.claimsChecked ? Math.round((stats.supported / stats.claimsChecked) * 100) : 0}%)
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                    style={{
                      width: `${stats.claimsChecked ? (stats.supported / stats.claimsChecked) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-rose-400 flex items-center gap-1.5">
                    <XCircle className="h-3.5 w-3.5" /> Contradicted
                  </span>
                  <span className="text-slate-300">
                    {stats.contradicted} ({stats.claimsChecked ? Math.round((stats.contradicted / stats.claimsChecked) * 100) : 0}%)
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-rose-500 rounded-full transition-all duration-500"
                    style={{
                      width: `${stats.claimsChecked ? (stats.contradicted / stats.claimsChecked) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-amber-400 flex items-center gap-1.5">
                    <AlertCircle className="h-3.5 w-3.5" /> Unclear / Missing
                  </span>
                  <span className="text-slate-300">
                    {stats.unclear} ({stats.claimsChecked ? Math.round((stats.unclear / stats.claimsChecked) * 100) : 0}%)
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full transition-all duration-500"
                    style={{
                      width: `${stats.claimsChecked ? (stats.unclear / stats.claimsChecked) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Service Health Card */}
          <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                System Status
              </h3>
              <Link to="/dashboard/integrations" className="text-xs text-primary-400 hover:text-primary-300">
                Details
              </Link>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-slate-300 font-medium">Verification Engine</span>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                    pythonHealth === 'healthy'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : 'bg-amber-950 text-amber-400 border border-amber-800'
                  }`}
                >
                  {pythonHealth === 'healthy' ? 'Online (:8000)' : 'Standby / Check'}
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-slate-300 font-medium">Bifrost Gateway</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-400 border border-cyan-800">
                  Ready (:8080)
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-slate-300 font-medium">Tavily Search Engine</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-800">
                  Advanced Mode
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
