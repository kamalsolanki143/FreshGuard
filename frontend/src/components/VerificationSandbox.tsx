import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  ExternalLink,
  Sparkles,
  RefreshCw,
  Clock,
  Layers,
  Database,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
} from 'lucide-react';

interface EvidenceItem {
  evidence_id?: string;
  source_title?: string;
  title?: string;
  source_url?: string;
  url?: string;
  snippet?: string;
  content?: string;
  retrieved_at?: string;
  source_type?: string;
}

interface ClaimResult {
  claim_id: string;
  category: string;
  entity: string;
  attribute: string;
  original_text?: string;
  text?: string;
  verdict: 'supported' | 'contradicted' | 'unclear';
  confidence: number;
  reason?: string;
  corrected_value?: string | null;
  checked_at?: string;
  evidence?: EvidenceItem[];
}

interface VerificationResponse {
  verification_id?: string;
  request_id: string;
  status: string;
  freshness_status?: 'FRESH' | 'STALE' | 'UNCERTAIN' | 'NOT_REQUIRED';
  requires_refresh?: boolean;
  claims_checked?: number;
  processing_time_ms?: number;
  checked_at?: string;
  claims?: ClaimResult[];
  results?: ClaimResult[];
  error?: {
    code: string;
    message: string;
  };
}

const SAMPLE_PRESETS = [
  {
    label: 'Pricing Claim',
    text: 'ChatGPT Plus pricing is $20 per month. Anthropic Claude 3.5 Sonnet costs $3 per million input tokens.',
    category: 'pricing',
  },
  {
    label: 'Software Version',
    text: 'Python 3.12 is the latest major release of the Python programming language.',
    category: 'software_version',
  },
  {
    label: 'Company Leadership',
    text: 'Sam Altman is the Chief Executive Officer of OpenAI, and Dario Amodei leads Anthropic.',
    category: 'leadership',
  },
  {
    label: 'Contradicted Claim',
    text: 'GPT-4 is completely free and OpenAI operates with zero paid subscription tiers.',
    category: 'pricing',
  },
];

export function VerificationSandbox() {
  const [inputText, setInputText] = useState(SAMPLE_PRESETS[0].text);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleVerify = async () => {
    if (!inputText.trim()) {
      setErrorMsg('Please enter or select LLM output text to verify.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setResult(null);

    try {
      const payload = {
        request_id: `ui-${Date.now()}`,
        text: inputText.trim(),
        mode: 'blocking',
        categories: ['pricing', 'software_version', 'leadership'],
      };

      // Call through Vite proxy (/api/v1/verifications) with fallback to direct localhost:8000
      let res = await fetch('/api/v1/verifications', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok && res.status === 404) {
        // Fallback for direct port or local production testing
        res = await fetch('http://localhost:8000/v1/verifications', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
          body: JSON.stringify(payload),
        });
      }

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.message || data.error || `HTTP error ${res.status}`);
      }

      setResult(data);
    } catch (err: any) {
      console.error('Verification error:', err);
      setErrorMsg(
        err.message || 'Failed to connect to FreshGuard verification service. Ensure backend is running on port 8000.'
      );
    } finally {
      setLoading(false);
    }
  };

  const claimsList = result?.claims || result?.results || [];

  return (
    <section className="py-20 bg-gradient-to-b from-white via-slate-50 to-slate-100 relative overflow-hidden" id="sandbox">
      {/* Background Decorative Blur */}
      <div className="absolute top-10 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-primary-200/20 blur-3xl rounded-full pointer-events-none" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10">
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-100 text-cyan-800 font-bold text-xs uppercase tracking-wider mb-3 border border-cyan-200">
            <Sparkles className="h-4 w-4 text-cyan-600" />
            <span>Interactive Live Verification</span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-slate-900 tracking-tight mb-4">
            Test FreshGuard in <span className="gradient-text">Real Time</span>
          </h2>
          <p className="text-base sm:text-lg text-slate-700 max-w-2xl mx-auto font-medium">
            Submit any LLM response text below to see live claim prefiltering, Tavily evidence retrieval, deterministic version checks, and Bifrost cache freshness decisions.
          </p>
        </motion.div>

        {/* Input Box Card */}
        <div className="bg-white rounded-3xl shadow-xl shadow-slate-200/70 border-2 border-slate-200/80 p-6 sm:p-8 mb-10 transition-all">
          {/* Presets Row */}
          <div className="mb-4">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2.5 flex items-center gap-1.5">
              <span>Choose Sample Preset:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_PRESETS.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setInputText(preset.text);
                    setResult(null);
                    setErrorMsg(null);
                  }}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${
                    inputText === preset.text
                      ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                      : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Text Area */}
          <div className="relative mb-5">
            <textarea
              rows={4}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Paste candidate LLM completion containing pricing, versions, or leadership claims..."
              className="w-full p-4 rounded-2xl bg-slate-50 border-2 border-slate-200 text-slate-900 text-sm sm:text-base font-normal focus:bg-white focus:border-primary-500 focus:outline-none focus:ring-4 focus:ring-primary-500/10 transition-all resize-y"
            />
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-xs text-slate-500 font-medium flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>Supported Categories: Pricing, Software Versions, Company Leadership</span>
            </div>
            <button
              onClick={handleVerify}
              disabled={loading}
              className="w-full sm:w-auto px-8 py-3.5 bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 text-white rounded-xl font-bold text-sm shadow-lg shadow-primary-500/25 hover:shadow-primary-500/40 hover:opacity-95 transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Verifying via Tavily...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Verify Answer Freshness</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error Alert */}
        <AnimatePresence>
          {errorMsg && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-8 p-4 rounded-2xl bg-rose-50 border-2 border-rose-200 text-rose-800 flex items-start gap-3"
            >
              <AlertCircle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="text-sm font-semibold leading-relaxed">
                <span className="font-bold">Verification Error:</span> {errorMsg}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Result Container */}
        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="space-y-6"
            >
              {/* Telemetry Dashboard Banner */}
              <div className="bg-slate-900 text-white rounded-3xl p-6 sm:p-8 shadow-2xl border border-slate-800">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-800">
                  <div>
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-widest mb-1.5">
                      <span>Bifrost Gateway Freshness Verdict</span>
                    </div>
                    <div className="flex items-center gap-3">
                      {result.freshness_status === 'FRESH' && (
                        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-black text-sm">
                          <CheckCircle2 className="h-4 w-4" />
                          <span>FRESH RESPONSE</span>
                        </div>
                      )}
                      {result.freshness_status === 'STALE' && (
                        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 font-black text-sm">
                          <XCircle className="h-4 w-4" />
                          <span>STALE / CONTRADICTED</span>
                        </div>
                      )}
                      {result.freshness_status === 'UNCERTAIN' && (
                        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 font-black text-sm">
                          <AlertTriangle className="h-4 w-4" />
                          <span>UNCERTAIN EVIDENCE</span>
                        </div>
                      )}
                      {(!result.freshness_status || result.freshness_status === 'NOT_REQUIRED') && (
                        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-700 text-slate-300 font-black text-sm">
                          <span>NO TEMPORAL CLAIMS</span>
                        </div>
                      )}

                      <span className="text-xs text-slate-400 font-mono">
                        Job: {result.verification_id?.substring(0, 8) || 'N/A'}
                      </span>
                    </div>
                  </div>

                  {/* Cache Policy Indicator */}
                  <div className="flex items-center gap-3 bg-slate-800/80 px-4 py-3 rounded-2xl border border-slate-700/80">
                    <Database className="h-5 w-5 text-cyan-400 shrink-0" />
                    <div>
                      <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                        Bifrost Cache Action
                      </div>
                      <div className="text-sm font-bold text-white flex items-center gap-1.5">
                        {result.requires_refresh ? (
                          <span className="text-rose-400">Evict &amp; Invalidate Cache</span>
                        ) : (
                          <span className="text-emerald-400">Safe for Semantic Cache</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Telemetry Stats Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6">
                  <div>
                    <div className="text-[11px] text-slate-400 font-bold uppercase tracking-wider">Claims Checked</div>
                    <div className="text-xl sm:text-2xl font-black text-white mt-1">
                      {result.claims_checked ?? claimsList.length}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-400 font-bold uppercase tracking-wider">Latency</div>
                    <div className="text-xl sm:text-2xl font-black text-cyan-400 mt-1 flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      <span>{result.processing_time_ms ?? 0} ms</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-400 font-bold uppercase tracking-wider">Lifecycle Status</div>
                    <div className="text-xl sm:text-2xl font-black text-emerald-400 mt-1 uppercase">
                      {result.status}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-400 font-bold uppercase tracking-wider">Validated At</div>
                    <div className="text-xs sm:text-sm font-mono text-slate-300 mt-1">
                      {result.checked_at ? new Date(result.checked_at).toLocaleTimeString() : 'Just now'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Extracted Claims Section */}
              {claimsList.length === 0 ? (
                <div className="bg-white rounded-3xl p-8 border-2 border-slate-200 text-center">
                  <Layers className="h-8 w-8 text-slate-400 mx-auto mb-2" />
                  <h3 className="text-lg font-bold text-slate-800">No time-sensitive factual claims detected</h3>
                  <p className="text-slate-600 text-sm mt-1">
                    The provided text does not contain assertions regarding pricing, software versions, or leadership.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                    <span>Evaluated Claims</span>
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-200 text-slate-700 font-black">
                      {claimsList.length}
                    </span>
                  </h3>

                  <div className="grid gap-4">
                    {claimsList.map((claim, idx) => {
                      const verdict = claim.verdict?.toLowerCase();
                      const isSupported = verdict === 'supported';
                      const isContradicted = verdict === 'contradicted';

                      return (
                        <div
                          key={claim.claim_id || idx}
                          className={`bg-white rounded-2xl p-6 border-2 transition-all ${
                            isSupported
                              ? 'border-emerald-200 shadow-sm'
                              : isContradicted
                              ? 'border-rose-300 shadow-sm'
                              : 'border-amber-200 shadow-sm'
                          }`}
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                            <div className="flex items-center gap-2">
                              {isSupported && (
                                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 font-black text-xs">
                                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                                  SUPPORTED
                                </span>
                              )}
                              {isContradicted && (
                                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-100 text-rose-800 font-black text-xs">
                                  <XCircle className="h-3.5 w-3.5 text-rose-600" />
                                  CONTRADICTED
                                </span>
                              )}
                              {!isSupported && !isContradicted && (
                                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100 text-amber-800 font-black text-xs">
                                  <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                                  UNCLEAR
                                </span>
                              )}

                              <span className="text-xs font-bold px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-600 uppercase">
                                {claim.category}
                              </span>
                            </div>

                            <div className="text-xs font-semibold text-slate-500">
                              Confidence: <span className="font-bold text-slate-800">{(claim.confidence * 100).toFixed(1)}%</span>
                            </div>
                          </div>

                          <div className="text-base font-bold text-slate-900 mb-2">
                            "{claim.original_text || claim.text}"
                          </div>

                          <div className="grid sm:grid-cols-2 gap-2 text-xs text-slate-600 mb-4 bg-slate-50 p-3 rounded-xl">
                            <div>
                              <span className="font-bold text-slate-700">Entity:</span> {claim.entity}
                            </div>
                            <div>
                              <span className="font-bold text-slate-700">Attribute:</span> {claim.attribute}
                            </div>
                            {claim.corrected_value && (
                              <div className="sm:col-span-2 text-rose-700 font-semibold">
                                <span className="font-bold">Correct Value:</span> {claim.corrected_value}
                              </div>
                            )}
                            {claim.reason && (
                              <div className="sm:col-span-2 text-slate-700">
                                <span className="font-bold">Grounding Rationale:</span> {claim.reason}
                              </div>
                            )}
                          </div>

                          {/* Evidence Items */}
                          {claim.evidence && claim.evidence.length > 0 && (
                            <div className="border-t border-slate-100 pt-3">
                              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                                Retrieved Tavily Evidence ({claim.evidence.length} sources)
                              </div>
                              <div className="space-y-2">
                                {claim.evidence.map((ev, evIdx) => {
                                  const url = ev.source_url || ev.url || '#';
                                  const title = ev.source_title || ev.title || 'Authoritative Source';
                                  const snippet = ev.snippet || ev.content || '';

                                  return (
                                    <div
                                      key={ev.evidence_id || evIdx}
                                      className="p-3 rounded-xl bg-slate-50/80 border border-slate-200/80 text-xs text-slate-700"
                                    >
                                      <div className="flex items-center justify-between gap-2 mb-1">
                                        <a
                                          href={url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="font-bold text-primary-600 hover:text-primary-800 flex items-center gap-1 hover:underline truncate"
                                        >
                                          <span>{title}</span>
                                          <ExternalLink className="h-3 w-3 shrink-0" />
                                        </a>
                                        {ev.retrieved_at && (
                                          <span className="text-[10px] text-slate-400 shrink-0 font-mono">
                                            {new Date(ev.retrieved_at).toLocaleDateString()}
                                          </span>
                                        )}
                                      </div>
                                      {snippet && (
                                        <p className="text-slate-600 line-clamp-2 leading-relaxed">
                                          "{snippet}"
                                        </p>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
