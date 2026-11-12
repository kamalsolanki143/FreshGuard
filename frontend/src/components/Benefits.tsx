import { motion } from 'framer-motion';
import { DollarSign, ShieldAlert, Cpu, Sparkles, Check, X, ShieldCheck } from 'lucide-react';

export function Benefits() {
  const benefits = [
    {
      title: 'Eliminate Disputed Billing & Lost Revenue',
      description: 'Stop your AI chatbots from promising outdated discounts or legacy pricing models that cost real money at checkout.',
      icon: DollarSign,
      color: 'from-emerald-500 to-teal-600',
      stat: '100%',
      statLabel: 'Price Verification Coverage',
    },
    {
      title: 'Preserve Brand Reputation & Compliance',
      description: 'Deliver factual leadership, corporate contact, and release info verified against live company sources and news.',
      icon: ShieldAlert,
      color: 'from-blue-500 to-indigo-600',
      stat: '0 Hallucinations',
      statLabel: 'On critical corporate entities',
    },
    {
      title: 'Maximize Semantic Cache ROI',
      description: 'Instead of disabling caching due to staleness concerns, safely cache verified responses with automated freshness checks.',
      icon: Cpu,
      color: 'from-purple-500 to-fuchsia-600',
      stat: '3x More',
      statLabel: 'Usable cache retention time',
    },
    {
      title: 'Zero Architectural Lock-In',
      description: 'Deploy as an open-source Go plugin on your Bifrost gateway. Works with OpenAI, Claude, DeepSeek, Gemini, and open models.',
      icon: ShieldCheck,
      color: 'from-cyan-500 to-blue-600',
      stat: '&lt; 20ms',
      statLabel: 'Low-latency interception',
    },
  ];

  return (
    <section className="py-24 bg-white relative overflow-hidden" id="benefits">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-purple-100 text-purple-800 font-bold text-xs uppercase tracking-wider mb-4 border border-purple-200">
            <Sparkles className="h-4 w-4 text-purple-600" />
            <span>Measurable Impact</span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-slate-900 mb-4 tracking-tight">
            Why Teams Trust <span className="gradient-text">FreshGuard</span>
          </h2>
          <p className="text-lg sm:text-xl text-slate-700 max-w-3xl mx-auto font-medium">
            Real enterprise advantages for AI engineering teams running production LLMs.
          </p>
        </motion.div>

        {/* 4 Core Benefits */}
        <div className="grid md:grid-cols-2 gap-6 sm:gap-8 mb-16">
          {benefits.map((benefit, index) => (
            <motion.div
              key={benefit.title}
              className="bg-slate-50/80 rounded-2xl p-6 sm:p-8 border-2 border-slate-200/90 hover:border-primary-400 shadow-md hover:shadow-xl hover:bg-white transition-all duration-300 flex flex-col justify-between group"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ y: -4 }}
            >
              <div className="flex items-start gap-5 mb-6">
                <div className={`flex-shrink-0 w-14 h-14 rounded-2xl bg-gradient-to-br ${benefit.color} text-white flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform`}>
                  <benefit.icon className="h-7 w-7" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-900 mb-2 group-hover:text-primary-600 transition-colors">
                    {benefit.title}
                  </h3>
                  <p className="text-slate-700 text-sm leading-relaxed">
                    {benefit.description}
                  </p>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200/80 flex items-center justify-between">
                <span className="text-2xl font-black text-slate-900">{benefit.stat}</span>
                <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">{benefit.statLabel}</span>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Before vs After Comparison Card */}
        <motion.div
          className="rounded-2xl border-2 border-slate-200 shadow-xl overflow-hidden bg-white"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <div className="bg-slate-900 text-white p-5 sm:p-6 text-center">
            <h3 className="text-xl sm:text-2xl font-black">Traditional LLM Setup vs. FreshGuard Protected</h3>
            <p className="text-slate-300 text-sm mt-1">See how real-time freshness verification transforms reliability</p>
          </div>

          <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-200">
            {/* Without FreshGuard */}
            <div className="p-6 sm:p-8 bg-rose-50/30">
              <div className="flex items-center gap-2 mb-4 text-rose-700 font-bold text-base">
                <X className="h-5 w-5 bg-rose-100 rounded-full p-0.5" />
                <span>Standard LLM Gateway</span>
              </div>
              <ul className="space-y-3 text-sm text-slate-700 font-medium">
                <li className="flex items-start gap-2">
                  <span className="text-rose-500 font-bold">✕</span>
                  <span>Serves outdated answers once knowledge cutoff date passes</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-500 font-bold">✕</span>
                  <span>Semantic cache blindly retains invalid prices and stale API keys</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-500 font-bold">✕</span>
                  <span>No verification against authoritative web sources</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-500 font-bold">✕</span>
                  <span>Customer discovers pricing errors at time of purchase</span>
                </li>
              </ul>
            </div>

            {/* With FreshGuard */}
            <div className="p-6 sm:p-8 bg-emerald-50/30">
              <div className="flex items-center gap-2 mb-4 text-emerald-700 font-bold text-base">
                <Check className="h-5 w-5 bg-emerald-100 rounded-full p-0.5" />
                <span>With FreshGuard + Bifrost</span>
              </div>
              <ul className="space-y-3 text-sm text-slate-800 font-semibold">
                <li className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span>Real-time claim verification using live Tavily web search</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span>Only validated answers saved with intelligent TTL metadata</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span>Automatic eviction and purging of contradicted claims</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span>Sub-20ms overhead with configurable fail-open/closed rules</span>
                </li>
              </ul>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
