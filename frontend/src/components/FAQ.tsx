import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { ChevronDown, HelpCircle, Mail } from 'lucide-react';
import { FAQ as FAQData, APP_CONFIG } from '../lib/constants';

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="py-24 bg-slate-900/60 relative overflow-hidden border-t border-slate-800/80" id="faq">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 relative z-10">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-950/80 text-indigo-300 font-bold text-xs uppercase tracking-wider mb-4 border border-indigo-800/80 shadow-sm">
            <HelpCircle className="h-4 w-4 text-indigo-400" />
            <span>Got Questions?</span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-4 tracking-tight">
            Frequently Asked <span className="gradient-text">Questions</span>
          </h2>
          <p className="text-lg sm:text-xl text-slate-300 max-w-2xl mx-auto font-normal leading-relaxed">
            Everything you need to know about integrating and deploying FreshGuard.
          </p>
        </motion.div>

        <div className="space-y-4">
          {FAQData.map((item, index) => {
            const isOpen = openIndex === index;
            return (
              <motion.div
                key={index}
                className={`rounded-2xl transition-all duration-200 overflow-hidden border ${
                  isOpen
                    ? 'bg-slate-900 border-cyan-500/80 shadow-xl shadow-cyan-950/50'
                    : 'bg-slate-950/80 border-slate-800 hover:border-slate-700 shadow-md'
                }`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: index * 0.08 }}
              >
                <button
                  className="w-full px-6 py-5 text-left flex justify-between items-center gap-4 transition-colors"
                  onClick={() => setOpenIndex(isOpen ? null : index)}
                  aria-expanded={isOpen}
                >
                  <span className={`font-bold text-base sm:text-lg transition-colors ${
                    isOpen ? 'text-cyan-400' : 'text-white'
                  }`}>
                    {item.question}
                  </span>
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                    isOpen ? 'bg-cyan-950 text-cyan-400 border border-cyan-800' : 'bg-slate-800 text-slate-400'
                  }`}>
                    <ChevronDown
                      className={`h-5 w-5 transition-transform duration-300 ${
                        isOpen ? 'rotate-180' : 'rotate-0'
                      }`}
                    />
                  </div>
                </button>

                <AnimatePresence>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                    >
                      <div className="px-6 pb-6 pt-2 text-slate-300 text-sm sm:text-base leading-relaxed border-t border-slate-800/80">
                        {item.answer}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>

        <motion.div
          className="mt-14 p-8 rounded-2xl bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border border-slate-800 text-center shadow-2xl"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <h3 className="text-xl font-bold text-white mb-2">Have a specific architectural requirement?</h3>
          <p className="text-slate-400 text-sm max-w-xl mx-auto mb-6">
            We are here to help you configure custom extraction models, Tavily domain filtering, and Redis/Bifrost integrations.
          </p>
          <a
            href={`mailto:${APP_CONFIG.email}`}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 text-white rounded-xl font-bold shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/35 hover:opacity-95 transition-all text-sm"
          >
            <Mail className="h-4 w-4" />
            <span>Contact FreshGuard Team</span>
          </a>
        </motion.div>
      </div>
    </section>
  );
}