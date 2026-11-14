import { motion } from 'framer-motion';
import { Search, Database, Terminal, CheckCircle2 } from 'lucide-react';

export function ProposedSolution() {
  const steps = [
    {
      icon: Terminal,
      title: '1. Intelligent Claim Extraction',
      description: 'The FreshGuard engine scans LLM outputs in real time, detecting temporal claims around pricing tiers, API versions, and organizational moves.',
      color: 'from-blue-500 to-cyan-500',
      badge: 'Regex + Spacy NER',
      badgeColor: 'bg-blue-950/80 text-blue-300 border border-blue-800',
    },
    {
      icon: Search,
      title: '2. Live Tavily Evidence Retrieval',
      description: 'Dispatches targeted freshness verification queries via Tavily API to fetch authoritative web evidence with sub-second latency.',
      color: 'from-emerald-500 to-teal-500',
      badge: 'Live Web Search',
      badgeColor: 'bg-emerald-950/80 text-emerald-300 border border-emerald-800',
    },
    {
      icon: Database,
      title: '3. Bifrost Semantic Cache Protection',
      description: 'Updates cache metadata with exact TTL policies. Validated responses are cached; poisoned or outdated claims are instantly purged via cache clear APIs.',
      color: 'from-purple-500 to-indigo-600',
      badge: 'Gateway Plugin',
      badgeColor: 'bg-purple-950/80 text-purple-300 border border-purple-800',
    },
  ];

  return (
    <section className="relative py-24 bg-slate-950 text-slate-100 overflow-hidden border-t border-slate-800/80" id="solution">
      {/* Background colorful glow */}
      <div className="absolute top-1/3 right-0 w-96 h-96 bg-primary-900/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 left-10 w-96 h-96 bg-emerald-900/15 rounded-full blur-3xl pointer-events-none" />

      <div className="relative max-w-6xl mx-auto px-4 sm:px-6 z-10">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-950/80 text-emerald-300 font-bold text-xs uppercase tracking-wider mb-4 border border-emerald-800/80 shadow-sm">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span>Architecture &amp; Pipeline</span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-4 tracking-tight">
            How FreshGuard <span className="gradient-text">Protects Your LLM Stack</span>
          </h2>
          <p className="text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto font-normal leading-relaxed">
            A high-speed Go plugin between your AI application, Tavily search, and the Bifrost semantic gateway.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-12 gap-10 items-center">
          {/* Left Column: 3 Steps */}
          <div className="lg:col-span-6 space-y-6">
            {steps.map((step, index) => (
              <motion.div
                key={step.title}
                className="bg-slate-900/80 rounded-2xl p-6 border border-slate-800 hover:border-cyan-500/50 shadow-xl transition-all group"
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.15 }}
              >
                <div className="flex items-start gap-4">
                  <div className={`flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br ${step.color} text-white flex items-center justify-center shadow-md group-hover:scale-105 transition-transform`}>
                    <step.icon className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-lg font-bold text-white group-hover:text-cyan-400 transition-colors">
                        {step.title}
                      </h3>
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${step.badgeColor}`}>
                        {step.badge}
                      </span>
                    </div>
                    <p className="text-slate-400 text-sm leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Right Column: Live Interactive Simulator Card */}
          <motion.div
            className="lg:col-span-6 bg-slate-900/90 text-slate-100 rounded-2xl p-6 sm:p-7 shadow-2xl border border-slate-800 relative overflow-hidden"
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            {/* Terminal Window Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-5">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-500 inline-block" />
                <span className="w-3 h-3 rounded-full bg-amber-500 inline-block" />
                <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
                <span className="text-xs font-mono text-slate-400 ml-2">freshguard-interceptor.log</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>Interception Active</span>
              </div>
            </div>

            {/* Simulated Live Query */}
            <div className="space-y-4 font-mono text-xs sm:text-sm">
              {/* User Prompt */}
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                <div className="text-slate-400 text-[11px] uppercase tracking-wider mb-1">Incoming LLM Query</div>
                <div className="text-cyan-300 font-medium">"What is the latest per-token price of GPT-4o?"</div>
              </div>

              {/* Intercepted Claim */}
              <div className="p-3.5 rounded-xl bg-slate-950 border border-amber-900/60">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-amber-400 text-[11px] uppercase tracking-wider font-bold">Detected Temporal Claim</span>
                  <span className="text-[10px] bg-amber-950 text-amber-300 px-1.5 py-0.5 rounded border border-amber-800">Category: Pricing</span>
                </div>
                <div className="text-slate-200">Claim: <span className="text-amber-300">"Input $5.00 / 1M tokens"</span></div>
              </div>

              {/* Tavily Verification Step */}
              <div className="p-3.5 rounded-xl bg-slate-950 border border-emerald-900/60">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    <Search className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-emerald-400 text-[11px] uppercase tracking-wider font-bold">Tavily Live Evidence</span>
                  </div>
                  <span className="text-[10px] bg-emerald-950 text-emerald-300 px-2 py-0.5 rounded border border-emerald-800 font-sans font-bold">9ms retrieval</span>
                </div>
                <div className="text-slate-300 text-xs">Evidence: openai.com/api/pricing cites <span className="text-emerald-400 font-bold">$2.50 / 1M tokens</span>.</div>
                <div className="mt-2 text-rose-400 font-bold flex items-center gap-1.5">
                  <span>Result:</span>
                  <span className="bg-rose-950/80 px-2 py-0.5 rounded border border-rose-800 text-xs">Outdated Claim Contradicted</span>
                </div>
              </div>

              {/* Bifrost Gateway Action */}
              <div className="p-3.5 rounded-xl bg-purple-950/30 border border-purple-800/60 flex items-center justify-between">
                <div>
                  <div className="text-purple-300 font-bold text-xs">Bifrost Gateway Action</div>
                  <div className="text-slate-300 text-xs mt-0.5">Stale entry purged; cache re-populated with verified data (TTL: 24h)</div>
                </div>
                <div className="text-right">
                  <div className="text-emerald-400 font-bold text-sm">✓ Protected</div>
                  <div className="text-[11px] text-slate-400">Total latency: &lt; 20ms</div>
                </div>
              </div>
            </div>

            {/* Bottom mini metrics */}
            <div className="grid grid-cols-3 gap-3 mt-5 pt-4 border-t border-slate-800 text-center">
              <div>
                <div className="text-emerald-400 font-bold text-lg">Verified</div>
                <div className="text-[11px] text-slate-400">Web Evidence Grounding</div>
              </div>
              <div>
                <div className="text-cyan-400 font-bold text-lg">&lt; 20ms</div>
                <div className="text-[11px] text-slate-400">Plugin Middleware Overhead</div>
              </div>
              <div>
                <div className="text-purple-400 font-bold text-lg">Fail-Safe</div>
                <div className="text-[11px] text-slate-400">Fail-Open / Closed Modes</div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}