import { motion } from 'framer-motion';
import { ArrowRight, Bot, Cpu, Search, CheckCircle, Database, ShieldCheck } from 'lucide-react';

export function HowItWorks() {
  const steps = [
    {
      step: '01',
      title: 'LLM Response Intercepted',
      description: 'Your application queries OpenAI, Claude, Gemini, or any LLM through the Bifrost API gateway.',
      icon: Bot,
      color: 'from-blue-600 to-cyan-600',
    },
    {
      step: '02',
      title: 'Temporal Claim Extraction',
      description: 'FreshGuard automatically parses pricing figures, version numbers, dates, and executive names.',
      icon: Cpu,
      color: 'from-cyan-600 to-teal-600',
    },
    {
      step: '03',
      title: 'Tavily Live Web Evidence',
      description: 'Dispatches targeted web search queries to verify facts against current authoritative websites.',
      icon: Search,
      color: 'from-emerald-600 to-green-600',
    },
    {
      step: '04',
      title: 'Evidence-Based Judgment',
      description: 'Claims are evaluated: Supported, Contradicted, or Unclear with calculated confidence scores.',
      icon: CheckCircle,
      color: 'from-amber-600 to-orange-600',
    },
    {
      step: '05',
      title: 'Freshness Ledger Stored',
      description: 'Verification results and timestamped metadata are linked with category TTL rules (24h to 7d).',
      icon: Database,
      color: 'from-purple-600 to-indigo-600',
    },
    {
      step: '06',
      title: 'Safe Cached Delivery',
      description: 'Accurate responses are safely cached in Bifrost; contradicted claims are rejected or flagged.',
      icon: ShieldCheck,
      color: 'from-fuchsia-600 to-pink-600',
    },
  ];

  return (
    <section className="py-24 bg-gradient-to-b from-slate-50 via-white to-slate-50 relative overflow-hidden" id="how-it-works">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-100 text-cyan-800 font-bold text-xs uppercase tracking-wider mb-4 border border-cyan-200">
            <ArrowRight className="h-4 w-4 text-cyan-600" />
            <span>Step-by-Step Flow</span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-slate-900 mb-4 tracking-tight">
            How <span className="gradient-text">FreshGuard Operates</span>
          </h2>
          <p className="text-lg sm:text-xl text-slate-700 max-w-3xl mx-auto font-medium">
            From raw LLM output to verified, cache-protected answers in milliseconds.
          </p>
        </motion.div>

        {/* 3 Columns x 2 Rows Grid for clear legibility */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
          {steps.map((step, index) => (
            <motion.div
              key={step.step}
              className="bg-white rounded-2xl p-6 sm:p-7 border-2 border-slate-200/90 hover:border-primary-400 shadow-md hover:shadow-xl transition-all duration-300 relative group flex flex-col justify-between"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ y: -4 }}
            >
              <div>
                <div className="flex items-center justify-between mb-5">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${step.color} text-white flex items-center justify-center font-bold text-lg shadow-md`}>
                    <step.icon className="h-6 w-6" />
                  </div>
                  <span className="text-2xl font-black text-slate-300 group-hover:text-primary-600 transition-colors font-mono">
                    {step.step}
                  </span>
                </div>

                <h3 className="text-xl font-bold text-slate-900 mb-2.5 group-hover:text-primary-600 transition-colors">
                  {step.title}
                </h3>
                <p className="text-slate-700 text-sm leading-relaxed">
                  {step.description}
                </p>
              </div>

              <div className="mt-6 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-slate-500">
                <span>Phase {index < 3 ? '1: Inspection' : '2: Enforcement'}</span>
                <span className="text-primary-600 font-bold group-hover:translate-x-1 transition-transform inline-flex items-center">
                  Next &rarr;
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
