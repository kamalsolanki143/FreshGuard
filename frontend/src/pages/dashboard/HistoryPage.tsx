import { useState } from 'react';
import {
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Eye,
  X,
  Database,
  ExternalLink,
  Info,
} from 'lucide-react';
import { useHistory } from '../../lib/historyContext';
import { getVerification } from '../../lib/api';
import { VerificationResponse } from '../../types';

export function HistoryPage() {
  const { history, addVerification } = useHistory();
  const [searchTerm, setSearchTerm] = useState('');
  const [filterVerdict, setFilterVerdict] = useState<string>('all');
  const [filterFreshness, setFilterFreshness] = useState<string>('all');
  const [selectedRecord, setSelectedRecord] = useState<VerificationResponse | null>(null);

  // Direct ID Lookup state
  const [lookupId, setLookupId] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupId.trim()) return;

    setLookupLoading(true);
    setLookupError(null);

    try {
      const record = await getVerification(lookupId.trim());
      addVerification(record);
      setSelectedRecord(record);
    } catch (err: any) {
      setLookupError(err.message || `Verification ID "${lookupId}" not found in database.`);
    } finally {
      setLookupLoading(false);
    }
  };

  // Filter history
  const filteredHistory = history.filter((item) => {
    const idMatches =
      (item.verification_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.request_id || '').toLowerCase().includes(searchTerm.toLowerCase());

    const claim = (item.claims && item.claims[0]) || (item.results && item.results[0]);
    const textMatches =
      idMatches ||
      (claim?.entity || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (claim?.text || '').toLowerCase().includes(searchTerm.toLowerCase());

    if (!textMatches) return false;

    if (filterVerdict !== 'all') {
      const verd = (claim?.verdict || '').toLowerCase();
      if (verd !== filterVerdict.toLowerCase()) return false;
    }

    if (filterFreshness !== 'all') {
      if ((item.freshness_status || '').toUpperCase() !== filterFreshness.toUpperCase()) {
        return false;
      }
    }

    return true;
  });

  return (
    <div className="space-y-8">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Verification History
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Audit trail of verified LLM outputs, retrieved evidence citations, and freshness verdicts
          </p>
        </div>
      </div>

      {/* API Capability Notice */}
      <div className="p-4 rounded-2xl bg-cyan-950/40 border border-cyan-800/60 text-xs text-cyan-200 flex items-start gap-3">
        <Info className="h-5 w-5 text-cyan-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-bold text-white">Supported Database API Contract</p>
          <p className="text-slate-300 leading-relaxed">
            The verification service persists all sessions in SQLite with strict audit tracking. Direct lookups invoke{' '}
            <code className="bg-slate-900 px-1.5 py-0.5 rounded text-cyan-300 font-mono">
              GET /v1/verifications/&#123;verification_id&#125;
            </code>
            . You can search session history below or look up any historical verification record directly by ID.
          </p>
        </div>
      </div>

      {/* Direct ID Lookup Box */}
      <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
        <form onSubmit={handleLookup} className="space-y-2">
          <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
            Direct Database Record Lookup by Verification ID
          </label>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <input
                type="text"
                value={lookupId}
                onChange={(e) => setLookupId(e.target.value)}
                placeholder="Enter verification_id (e.g. verif_live-test-req-1_3fa23ed0)..."
                className="w-full pl-3 pr-4 py-2 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
            <button
              type="submit"
              disabled={lookupLoading || !lookupId.trim()}
              className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs rounded-xl border border-slate-700 transition-colors flex items-center justify-center gap-2"
            >
              {lookupLoading ? (
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <Search className="h-3.5 w-3.5" />
                  <span>Fetch Record</span>
                </>
              )}
            </button>
          </div>
          {lookupError && (
            <p className="text-xs text-rose-400 mt-1.5 flex items-center gap-1">
              <AlertCircle className="h-3.5 w-3.5" />
              <span>{lookupError}</span>
            </p>
          )}
        </form>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-2xl flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by ID, entity, or claim text..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded-xl text-slate-200 placeholder-slate-500 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="h-3.5 w-3.5" />
            <span>Verdict:</span>
            <select
              value={filterVerdict}
              onChange={(e) => setFilterVerdict(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1 outline-none"
            >
              <option value="all">All Verdicts</option>
              <option value="supported">Supported</option>
              <option value="contradicted">Contradicted</option>
              <option value="unclear">Unclear</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Freshness:</span>
            <select
              value={filterFreshness}
              onChange={(e) => setFilterFreshness(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1 outline-none"
            >
              <option value="all">All States</option>
              <option value="FRESH">Fresh</option>
              <option value="STALE">Stale</option>
              <option value="UNCERTAIN">Uncertain</option>
            </select>
          </div>
        </div>
      </div>

      {/* History Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px] bg-slate-950/60">
                <th className="py-3 px-4">Verification ID</th>
                <th className="py-3 px-4">Entity / Category</th>
                <th className="py-3 px-4">Verdict</th>
                <th className="py-3 px-4">Freshness State</th>
                <th className="py-3 px-4">Checked At</th>
                <th className="py-3 px-4">Cache Action</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-500">
                    No matching verification records found.
                  </td>
                </tr>
              ) : (
                filteredHistory.map((item) => {
                  const claim = (item.claims && item.claims[0]) || (item.results && item.results[0]);
                  const verdict = (claim?.verdict || 'unclear').toLowerCase();
                  return (
                    <tr
                      key={item.verification_id || item.request_id}
                      className="hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-3.5 px-4 font-mono font-medium text-slate-200">
                        {item.verification_id || item.request_id}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-white">
                          {claim?.entity || 'Multiple claims'}
                        </div>
                        <div className="text-[11px] text-slate-400 capitalize">
                          {claim?.category || 'general'}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
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
                      <td className="py-3.5 px-4">
                        <span
                          className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded ${
                            item.freshness_status === 'FRESH'
                              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                              : item.freshness_status === 'STALE'
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : 'bg-amber-950 text-amber-300 border border-amber-800'
                          }`}
                        >
                          {item.freshness_status || 'UNCERTAIN'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                        {item.checked_at ? new Date(item.checked_at).toLocaleDateString() : 'Recent'}
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`text-[11px] font-semibold ${
                            item.requires_refresh || item.cache_evicted
                              ? 'text-rose-400'
                              : 'text-emerald-400'
                          }`}
                        >
                          {item.requires_refresh || item.cache_evicted
                            ? 'Evicted / Stale'
                            : 'Cached Fresh'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => setSelectedRecord(item)}
                          className="px-2.5 py-1 text-xs font-semibold text-primary-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors inline-flex items-center gap-1"
                        >
                          <Eye className="h-3 w-3" />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Record Inspector Drawer / Modal */}
      {selectedRecord && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Database className="h-4 w-4 text-primary-400" />
                  <span>Verification Audit Inspector</span>
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  ID: {selectedRecord.verification_id || selectedRecord.request_id}
                </p>
              </div>
              <button
                onClick={() => setSelectedRecord(null)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Status overview */}
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Lifecycle</span>
                <span className="font-bold text-emerald-400 capitalize">{selectedRecord.status}</span>
              </div>
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Freshness</span>
                <span className="font-bold text-cyan-300 font-mono">{selectedRecord.freshness_status || 'UNCERTAIN'}</span>
              </div>
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Cache Evicted</span>
                <span className={`font-bold ${selectedRecord.cache_evicted ? 'text-rose-400' : 'text-slate-300'}`}>
                  {selectedRecord.cache_evicted ? 'Yes (Evicted)' : 'No'}
                </span>
              </div>
            </div>

            {/* Claims and Evidence */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Extracted Claims & Grounding
              </h4>
              {((selectedRecord.claims || selectedRecord.results) || []).map((claim, idx) => (
                <div key={idx} className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">{claim.entity}</span>
                    <span className="font-bold text-cyan-400 uppercase">{claim.verdict}</span>
                  </div>
                  <p className="text-slate-300 italic font-mono text-[11px]">
                    "{claim.original_text || claim.text}"
                  </p>
                  {claim.reason && (
                    <p className="text-slate-400 text-[11px]">{claim.reason}</p>
                  )}
                  {claim.evidence && claim.evidence.length > 0 && (
                    <div className="pt-2 border-t border-slate-800 space-y-1">
                      <span className="text-[10px] font-bold text-slate-500 uppercase">Citations:</span>
                      {claim.evidence.map((ev, eIdx) => (
                        <div key={eIdx} className="text-[11px] text-slate-400 flex items-center justify-between">
                          <span>• {ev.title || ev.source_title || 'Documentation reference'}</span>
                          {(ev.url || ev.source_url) && (
                            <a
                              href={ev.url || ev.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary-400 hover:underline flex items-center gap-1"
                            >
                              <span>Link</span>
                              <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Raw JSON View */}
            <div>
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                Raw JSON Record Payload
              </h4>
              <pre className="p-3 bg-slate-950 rounded-xl border border-slate-800 font-mono text-[10px] text-slate-300 overflow-x-auto max-h-40">
                {JSON.stringify(selectedRecord, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
