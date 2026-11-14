import { motion } from 'framer-motion';
import { AlertTriangle, TrendingDown, DollarSign, Users2, ShieldAlert } from 'lucide-react';

export function ProblemStatement() {
  const problems = [
    {
      icon: DollarSign,
      title: 'Costly Pricing Hallucinations',
      description: 'LLMs confidently cite outdated product rates, subscription tiers, and discounts, generating customer disputes and cart abandonment.',
      stat: 'High Financial Risk',
      statLabel: 'Billing discrepancies from outdated model cutoffs',
      color: 'rose',
      borderClass: 'border-rose-900/50 hover:border-rose-500/70',
      bgClass: 'bg-rose-950/30',
      iconBg: 'bg-rose-950 border border-rose-800 text-rose-400',
      statColor: 'text-rose-400',
    },
    {
      icon: AlertTriangle,
      title: 'Invented Facts & Versions',
      description: 'Generative AI models fabricate release numbers, deprecated API parameters, and software specifications when knowledge cutoffs expire.',
      stat: 'Knowledge Cutoff',
      statLabel: 'Temporal claims become inaccurate without web grounding',
      color: 'amber',
      borderClass: 'border-amber-900/50 hover:border-amber-500/70',
      bgClass: 'bg-amber-950/30',
      iconBg: 'bg-amber-950 border border-amber-800 text-amber-400',
      statColor: 'text-amber-400',
    },
    {
      icon: Users2,
      title: 'Outdated Leadership & Contact',
      description: 'Executive departures, corporate acquisitions, and team transitions happen daily, but static models answer from stale historical training data.',
      stat: 'Dynamic Real-World',
      statLabel: 'Corporate roles & leadership shift continuously',
      color: 'purple',
      borderClass: 'border-purple-900/50 hover:border-purple-500/70',
      bgClass: 'bg-purple-950/30',
      iconBg: 'bg-purple-950 border border-purple-800 text-purple-400',
      statColor: 'text-purple-400',
    },
    {
      icon: TrendingDown,
      title: 'Silent Cache Poisoning',
      description: 'Traditional semantic caches blindly save outdated model responses and repeatedly serve contradicted answers to subsequent user requests.',
      stat: 'Compounded Drift',
      statLabel: 'Stale semantic cache entries survive indefinitely without TTL',
      color: 'cyan',
      borderClass: 'border-cyan-900/50 hover:border-cyan-500/70',
      bgClass: 'bg-cyan-950/30',
      iconBg: 'bg-cyan-950 border border-cyan-800 text-cyan-400',
      statColor: 'text-cyan-400',
    },
  ];

  return (
    <section className="py-24 bg-slate-900/60 relative overflow-hidden border-t border-slate-800/80" id="problem">
      {/* Decorative ambient color spots */}
      <div className="absolute top-1/2 left-0 w-80 h-80 bg-rose-900/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-80 h-80 bg-amber-900/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-rose-950/80 text-rose-300 font-bold text-xs uppercase tracking-wider mb-4 border border-rose-800/60 shadow-sm">
            <ShieldAlert className="h-4 w-4 text-rose-400" />
            <span>The Silent Risk In AI Applications</span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-4 tracking-tight">
            The <span className="gradient-text-rose">Hard Truth</span> About LLM Freshness
          </h2>
          <p className="text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto font-normal leading-relaxed">
            LLMs cannot know what happened yesterday, yet they answer time-sensitive queries with absolute confidence.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
          {problems.map((problem, index) => (
            <motion.div
              key={problem.title}
              className={`rounded-2xl p-6 sm:p-7 bg-slate-950/90 border-2 ${problem.borderClass} shadow-xl shadow-slate-950/50 hover:shadow-2xl transition-all duration-300 flex flex-col justify-between group`}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ y: -4 }}
            >
              <div>
                <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl ${problem.iconBg} mb-5 shadow-md group-hover:scale-105 transition-transform`}>
                  <problem.icon className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-white mb-3 group-hover:text-cyan-400 transition-colors">
                  {problem.title}
                </h3>
                <p className="text-slate-400 text-sm leading-relaxed mb-6">
                  {problem.description}
                </p>
              </div>

              <div className={`p-4 rounded-xl ${problem.bgClass} border border-slate-800 text-center`}>
                <div className={`text-xl sm:text-2xl font-black mb-1 ${problem.statColor}`}>
                  {problem.stat}
                </div>
                <div className="text-xs font-semibold text-slate-400 leading-tight">
                  {problem.statLabel}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}