import { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowRight,
  ExternalLink,
  Clock,
  Copy,
  Check,
} from 'lucide-react';
import { submitVerification } from '../../lib/api';
import { useHistory } from '../../lib/historyContext';
import { VerificationResponse, ClaimCategory } from '../../types';

interface Preset {
  title: string;
  category: ClaimCategory;
  text: string;
  expectedVerdict: 'supported' | 'contradicted' | 'unclear';
  description: string;
}

const PRESETS: Preset[] = [
  {
    title: 'Pricing Verification',
    category: 'pricing',
    text: 'ChatGPT Plus costs $20 per month and includes access to GPT-4.',
    expectedVerdict: 'supported',
    description: 'Validates subscription price against active official documentation.',
  },
  {
    title: 'Software Version Verification',
    category: 'software_version',
    text: 'Python 3.12 is the latest major release series of the Python programming language.',
    expectedVerdict: 'supported',
    description: 'Validates stable runtime release against official release schedules.',
  },
  {
    title: 'Company Leadership Verification',
    category: 'leadership',
    text: 'Sam Altman is the Chief Executive Officer of OpenAI.',
    expectedVerdict: 'supported',
    description: 'Validates executive governance changes in real time.',
  },
  {
    title: 'Contradicted Claim (Stale Cache Candidate)',
    category: 'pricing',
    text: 'The OpenAI GPT-4 API is completely free of charge for all commercial applications.',
    expectedVerdict: 'contradicted',
    description: 'Catches hallucinated or outdated free tier claims and triggers cache eviction.',
  },
];

export function VerifyPage() {
  const [inputText, setInputText] = useState(PRESETS[0].text);
  const [selectedCategory, setSelectedCategory] = useState<string>('pricing');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState(false);

  const { addVerification } = useHistory();

  const handleVerify = async (textToVerify = inputText) => {
    if (!textToVerify.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const resp = await submitVerification({
        request_id: `ws-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
        text: textToVerify,
        categories: [selectedCategory],
      });

      setResult(resp);
      addVerification(resp);
    } catch (err: any) {
      setError(err.message || 'Verification failed. Ensure the verification service is running on :8000.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (preset: Preset) => {
    setInputText(preset.text);
    setSelectedCategory(preset.category);
    handleVerify(preset.text);
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  // Inspect claims
  const claimsList = result?.claims || result?.results || [];

  return (
    <div className="space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-3">
          <span>Verification Workspace</span>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800 font-mono font-bold">
            Live Engine
          </span>
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Submit candidate LLM responses for real-time claim extraction, Tavily evidence retrieval, and cache eviction analysis.
        </p>
      </div>

      {/* Preset Quick-Buttons */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
          Select Test Claim Preset
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {PRESETS.map((p) => (
            <button
              key={p.title}
              onClick={() => handleSelectPreset(p)}
              disabled={loading}
              className={`p-3.5 text-left rounded-xl border transition-all text-xs flex flex-col justify-between ${
                inputText === p.text
                  ? 'bg-primary-950/40 border-primary-500 text-white shadow-md shadow-primary-500/10'
                  : 'bg-slate-900/80 hover:bg-slate-800 border-slate-800 text-slate-300'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-bold text-slate-200">{p.title}</span>
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      p.expectedVerdict === 'supported'
                        ? 'bg-emerald-950 text-emerald-400'
                        : 'bg-rose-950 text-rose-400'
                    }`}
                  >
                    {p.expectedVerdict.toUpperCase()}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2">{p.description}</p>
              </div>
              <span className="mt-3 text-[10px] font-mono text-cyan-400 flex items-center gap-1">
                <span>Run Preset</span>
                <ArrowRight className="h-3 w-3" />
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Interactive Input Form */}
      <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl">
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              LLM Response Content to Verify
            </label>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Target Category:</span>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1 focus:ring-1 focus:ring-primary-500 outline-none"
              >
                <option value="pricing">Pricing & Subscription</option>
                <option value="software_version">Software Version</option>
                <option value="leadership">Company Leadership</option>
              </select>
            </div>
          </div>

          <textarea
            rows={4}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Type or paste model response here (e.g. OpenAI GPT-4 pricing is $20 per month)..."
            className="w-full p-4 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent font-sans leading-relaxed"
          />

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
            <p className="text-xs text-slate-500">
              ⚡ Evaluates against real-time web grounding before delivery or semantic cache reuse
            </p>
            <button
              onClick={() => handleVerify()}
              disabled={loading || !inputText.trim()}
              className="w-full sm:w-auto px-6 py-2.5 bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 hover:opacity-95 disabled:opacity-50 text-white font-bold text-sm rounded-xl shadow-lg shadow-primary-500/25 flex items-center justify-center gap-2 transition-all"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Evaluating Response...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Run Verification</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-300 text-sm flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold">Verification Request Failed</p>
            <p className="text-xs text-rose-200">{error}</p>
          </div>
        </div>
      )}

      {/* Result Display Card */}
      {result && (
        <div className="space-y-6">
          {/* Top Telemetry Summary Pill Bar */}
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Verification ID</span>
                <div className="flex items-center gap-1.5 font-mono text-cyan-300 font-bold">
                  <span>{result.verification_id || 'N/A'}</span>
                  {result.verification_id && (
                    <button
                      onClick={() => handleCopyId(result.verification_id!)}
                      className="text-slate-500 hover:text-slate-300"
                      title="Copy ID"
                    >
                      {copiedId ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                    </button>
                  )}
                </div>
              </div>

              <div className="h-6 w-px bg-slate-800 hidden sm:block" />

              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Freshness Status</span>
                <span
                  className={`font-mono font-bold px-2 py-0.5 rounded text-xs inline-block mt-0.5 ${
                    result.freshness_status === 'FRESH'
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : result.freshness_status === 'STALE'
                      ? 'bg-rose-950 text-rose-300 border border-rose-800'
                      : 'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}
                >
                  {result.freshness_status || 'UNCERTAIN'}
                </span>
              </div>

              <div className="h-6 w-px bg-slate-800 hidden sm:block" />

              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Cache Action</span>
                <span
                  className={`font-semibold inline-block mt-0.5 ${
                    result.requires_refresh || result.cache_evicted
                      ? 'text-rose-400 font-bold'
                      : 'text-emerald-400'
                  }`}
                >
                  {result.requires_refresh || result.cache_evicted
                    ? '⚠️ Evict Stale Entry'
                    : '✓ Safe to Cache'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span className="flex items-center gap-1 font-mono">
                <Clock className="h-3.5 w-3.5 text-amber-400" />
                <span>{result.processing_time_ms ? `${result.processing_time_ms} ms` : '< 30 ms'}</span>
              </span>
              <span className="font-mono text-[11px] text-slate-500">
                {result.checked_at ? new Date(result.checked_at).toLocaleTimeString() : 'Just now'}
              </span>
            </div>
          </div>

          {/* Claims List */}
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white uppercase tracking-wider flex items-center justify-between">
              <span>Extracted Claims ({claimsList.length})</span>
              <span className="text-xs text-slate-400 font-normal">
                Structured entities validated against evidence
              </span>
            </h2>

            {claimsList.length === 0 ? (
              <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-2xl text-slate-400 text-sm">
                No time-sensitive claims detected in this response text. The response is safe for standard caching.
              </div>
            ) : (
              claimsList.map((claim, idx) => {
                const verdict = (claim.verdict || 'unclear').toLowerCase();
                const isSupported = verdict === 'supported';
                const isContradicted = verdict === 'contradicted';

                return (
                  <div
                    key={claim.claim_id || idx}
                    className={`p-5 rounded-2xl border transition-all ${
                      isSupported
                        ? 'bg-slate-900/90 border-emerald-800/60 shadow-emerald-950/20 shadow-md'
                        : isContradicted
                        ? 'bg-slate-900/90 border-rose-800/60 shadow-rose-950/20 shadow-md'
                        : 'bg-slate-900/90 border-amber-800/60 shadow-amber-950/20 shadow-md'
                    }`}
                  >
                    {/* Header Row */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${
                            isSupported
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : isContradicted
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : 'bg-amber-950 text-amber-300 border border-amber-800'
                          }`}
                        >
                          {isSupported ? (
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                          ) : isContradicted ? (
                            <XCircle className="h-3.5 w-3.5 text-rose-400" />
                          ) : (
                            <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
                          )}
                          <span>{verdict.toUpperCase()}</span>
                        </span>

                        <span className="text-xs font-semibold text-slate-300">
                          {claim.entity} • <span className="text-slate-400 capitalize">{claim.attribute}</span>
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-slate-400">Confidence:</span>
                        <span className="font-mono font-bold text-white">
                          {claim.confidence !== undefined ? `${Math.round(claim.confidence * 100)}%` : '—'}
                        </span>
                      </div>
                    </div>

                    {/* Claim original text */}
                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-sm text-slate-200 mb-3 font-mono text-xs">
                      "{claim.original_text || claim.text}"
                    </div>

                    {/* Reason / Explanation */}
                    {claim.reason && (
                      <p className="text-xs text-slate-300 mb-3 leading-relaxed">
                        <span className="font-semibold text-slate-400">Analysis: </span>
                        {claim.reason}
                      </p>
                    )}

                    {/* Corrected value if contradicted */}
                    {claim.corrected_value && (
                      <div className="mb-3 p-2.5 bg-rose-950/40 border border-rose-900 rounded-lg text-xs text-rose-300">
                        <span className="font-bold">Corrected Value: </span>
                        {claim.corrected_value}
                      </div>
                    )}

                    {/* Grounding Evidence References */}
                    {claim.evidence && claim.evidence.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-800 space-y-2">
                        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                          Grounding Evidence References ({claim.evidence.length})
                        </span>
                        {claim.evidence.map((ev, evIdx) => (
                          <div
                            key={ev.evidence_id || evIdx}
                            className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs space-y-1"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-cyan-300">
                                {ev.title || ev.source_title || 'Documentation Source'}
                              </span>
                              {(ev.url || ev.source_url) && (
                                <a
                                  href={ev.url || ev.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-primary-400 hover:text-primary-300 flex items-center gap-1 text-[11px]"
                                >
                                  <span>View Source</span>
                                  <ExternalLink className="h-3 w-3" />
                                </a>
                              )}
                            </div>
                            <p className="text-slate-400 text-[11px] italic">
                              "{ev.snippet || ev.content || 'Evidence verified by engine.'}"
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
