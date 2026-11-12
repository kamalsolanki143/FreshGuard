import { motion } from 'framer-motion';
import {
  Calendar,
  Globe,
  Shield,
  Timer,
  AlertCircle,
  Database,
  Sparkles,
  CheckCircle,
} from 'lucide-react';

export function Features() {
  const featureList = [
    {
      title: 'Time-Sensitive Claim Extraction',
      description: 'Automatically detects pricing terms, version numbers, and leadership changes in LLM completions before caching.',
      icon: Calendar,
      color: 'from-blue-500 to-cyan-500',
      badge: 'Regex + Spacy NLP',
      badgeColor: 'bg-blue-100 text-blue-800 border-blue-200',
      borderAccent: 'hover:border-cyan-400',
    },
    {
      title: 'Tavily Live Web Evidence',
      description: 'Verifies claims in real-time against fresh web search results using Tavily Search API with sub-second response times.',
      icon: Globe,
      color: 'from-emerald-500 to-teal-500',
      badge: 'Authoritative Sources',
      badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      borderAccent: 'hover:border-emerald-400',
    },
    {
      title: 'Smart Semantic Cache Shield',
      description: 'Hooks into Bifrost semantic caching. Only claims validated by authoritative web sources are eligible for cache storage.',
      icon: Shield,
      color: 'from-purple-500 to-indigo-600',
      badge: 'Bifrost Compatible',
      badgeColor: 'bg-purple-100 text-purple-800 border-purple-200',
      borderAccent: 'hover:border-purple-400',
    },
    {
      title: 'Category-Based TTL Policies',
      description: 'Configurable time-to-live thresholds: 24h for pricing & software versions, 7 days for leadership and corporate records.',
      icon: Timer,
      color: 'from-amber-500 to-orange-500',
      badge: 'Customizable Rules',
      badgeColor: 'bg-amber-100 text-amber-800 border-amber-200',
      borderAccent: 'hover:border-amber-400',
    },
    {
      title: 'Fail-Open & Fail-Closed Modes',
      description: 'Configure high-availability fail-open modes for maximum uptime or strict fail-closed modes for financial compliance.',
      icon: AlertCircle,
      color: 'from-rose-500 to-red-500',
      badge: 'Enterprise Reliability',
      badgeColor: 'bg-rose-100 text-rose-800 border-rose-200',
      borderAccent: 'hover:border-rose-400',
    },
    {
      title: 'Native Go Bifrost Plugin',
      description: 'Ultra-low overhead Go middleware designed to plug directly into Bifrost API gateways with zero runtime dependencies.',
      icon: Database,
      color: 'from-indigo-500 to-purple-600',
      badge: 'Sub-20ms Overhead',
      badgeColor: 'bg-indigo-100 text-indigo-800 border-indigo-200',
      borderAccent: 'hover:border-indigo-400',
    },
  ];

  return (
    <section className="py-24 bg-white relative overflow-hidden" id="features">
      {/* Decorative gradient spot */}
      <div className="absolute top-0 right-1/4 w-80 h-80 bg-purple-200/20 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-100 text-primary-800 font-bold text-xs uppercase tracking-wider mb-4 border border-primary-200">
            <Sparkles className="h-4 w-4 text-primary-600" />
            <span>Comprehensive Toolset</span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-slate-900 mb-4 tracking-tight">
            Built for <span className="gradient-text">Speed, Accuracy &amp; Resilience</span>
          </h2>
          <p className="text-lg sm:text-xl text-slate-700 max-w-3xl mx-auto font-medium">
            Everything your engineering team needs to eliminate hallucinations from customer-facing LLM applications.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
          {featureList.map((feature, index) => (
            <motion.div
              key={feature.title}
              className={`bg-slate-50/80 rounded-2xl p-6 sm:p-7 border-2 border-slate-200/90 ${feature.borderAccent} shadow-sm hover:shadow-xl hover:bg-white transition-all duration-300 flex flex-col justify-between group`}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ y: -4 }}
            >
              <div>
                <div className="flex items-center justify-between mb-5">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform`}>
                    <feature.icon className="h-6 w-6" />
                  </div>
                  <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${feature.badgeColor}`}>
                    {feature.badge}
                  </span>
                </div>

                <h3 className="text-xl font-bold text-slate-900 mb-2.5 group-hover:text-primary-600 transition-colors">
                  {feature.title}
                </h3>
                <p className="text-slate-700 text-sm leading-relaxed mb-6">
                  {feature.description}
                </p>
              </div>

              <div className="pt-4 border-t border-slate-200 flex items-center text-xs font-bold text-primary-700">
                <CheckCircle className="h-4 w-4 mr-1.5 text-primary-600" />
                <span>Production-ready module</span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
