import { motion } from 'framer-motion';
import { AlertTriangle, TrendingDown, DollarSign, Users2, ShieldAlert } from 'lucide-react';

export function ProblemStatement() {
  const problems = [
    {
      icon: DollarSign,
      title: 'Costly Pricing Hallucinations',
      description: 'LLMs confidently cite outdated product rates and subscription tiers, generating user disputes and cart abandonment.',
      stat: '$2.3M+',
      statLabel: 'Lost in ecommerce billing discrepancies',
      color: 'rose',
      borderClass: 'border-rose-200/90 hover:border-rose-400',
      bgClass: 'bg-rose-50/60',
      iconBg: 'bg-rose-600 text-white',
      badgeClass: 'bg-rose-100 text-rose-800',
    },
    {
      icon: AlertTriangle,
      title: 'Invented Facts & Versions',
      description: 'Generative AI models fabricate release numbers, API parameters, and specifications when knowledge cutoffs expire.',
      stat: '30%',
      statLabel: 'Of unverified temporal claims are incorrect',
      color: 'amber',
      borderClass: 'border-amber-200/90 hover:border-amber-400',
      bgClass: 'bg-amber-50/60',
      iconBg: 'bg-amber-600 text-white',
      badgeClass: 'bg-amber-100 text-amber-800',
    },
    {
      icon: Users2,
      title: 'Outdated Leadership & Contact',
      description: 'Executive departures, corporate acquisitions, and team changes happen daily, but LLMs answer from static historical weights.',
      stat: '7 Days',
      statLabel: 'Average staleness for fast-changing org claims',
      color: 'purple',
      borderClass: 'border-purple-200/90 hover:border-purple-400',
      bgClass: 'bg-purple-50/60',
      iconBg: 'bg-purple-600 text-white',
      badgeClass: 'bg-purple-100 text-purple-800',
    },
    {
      icon: TrendingDown,
      title: 'Silent Cache Poisoning',
      description: 'Traditional semantic caches blindly save outdated responses and serve them to thousands of subsequent requests.',
      stat: '40%',
      statLabel: 'Semantic cache degradation over 30 days',
      color: 'cyan',
      borderClass: 'border-cyan-200/90 hover:border-cyan-400',
      bgClass: 'bg-cyan-50/60',
      iconBg: 'bg-cyan-600 text-white',
      badgeClass: 'bg-cyan-100 text-cyan-800',
    },
  ];

  return (
    <section className="py-24 bg-gradient-to-b from-white via-slate-50 to-white relative overflow-hidden" id="problem">
      {/* Decorative ambient color spots */}
      <div className="absolute top-1/2 left-0 w-72 h-72 bg-rose-200/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-80 h-80 bg-amber-200/20 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-rose-100 text-rose-800 font-bold text-xs uppercase tracking-wider mb-4 border border-rose-200">
            <ShieldAlert className="h-4 w-4 text-rose-600" />
            <span>The Silent Risk In AI Applications</span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-slate-900 mb-4 tracking-tight">
            The <span className="gradient-text-rose">Hard Truth</span> About LLM Freshness
          </h2>
          <p className="text-lg sm:text-xl text-slate-700 max-w-3xl mx-auto font-medium">
            LLMs cannot know what happened yesterday, yet they answer time-sensitive queries with absolute confidence.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
          {problems.map((problem, index) => (
            <motion.div
              key={problem.title}
              className={`rounded-2xl p-6 sm:p-7 bg-white border-2 ${problem.borderClass} shadow-lg shadow-slate-200/60 hover:shadow-xl transition-all duration-300 flex flex-col justify-between group`}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ y: -4 }}
            >
              <div>
                <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl ${problem.iconBg} mb-5 shadow-md group-hover:scale-105 transition-transform`}>
                  <problem.icon className="h-6 w-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3 group-hover:text-primary-600 transition-colors">
                  {problem.title}
                </h3>
                <p className="text-slate-700 text-sm leading-relaxed mb-6">
                  {problem.description}
                </p>
              </div>

              <div className={`p-4 rounded-xl ${problem.bgClass} border border-slate-200/80 text-center`}>
                <div className="text-2xl sm:text-3xl font-black text-slate-900 mb-1">
                  {problem.stat}
                </div>
                <div className="text-xs font-semibold text-slate-600">
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
