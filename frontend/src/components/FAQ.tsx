import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { ChevronDown, HelpCircle, Mail } from 'lucide-react';
import { FAQ as FAQData, APP_CONFIG } from '../lib/constants';

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="py-24 bg-slate-50 relative overflow-hidden" id="faq">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 relative z-10">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-100 text-indigo-800 font-bold text-xs uppercase tracking-wider mb-4 border border-indigo-200">
            <HelpCircle className="h-4 w-4 text-indigo-600" />
            <span>Got Questions?</span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-slate-900 mb-4 tracking-tight">
            Frequently Asked <span className="gradient-text">Questions</span>
          </h2>
          <p className="text-lg sm:text-xl text-slate-700 max-w-2xl mx-auto font-medium">
            Everything you need to know about integrating and deploying FreshGuard.
          </p>
        </motion.div>

        <div className="space-y-4">
          {FAQData.map((item, index) => {
            const isOpen = openIndex === index;
            return (
              <motion.div
                key={index}
                className={`rounded-2xl transition-all duration-200 overflow-hidden border-2 ${
                  isOpen
                    ? 'bg-white border-primary-500 shadow-lg shadow-primary-500/10'
                    : 'bg-white border-slate-200/90 hover:border-slate-300 shadow-sm'
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
                    isOpen ? 'text-primary-600' : 'text-slate-900'
                  }`}>
                    {item.question}
                  </span>
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                    isOpen ? 'bg-primary-100 text-primary-600' : 'bg-slate-100 text-slate-500'
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
                      <div className="px-6 pb-6 pt-2 text-slate-700 text-sm sm:text-base leading-relaxed border-t border-slate-100">
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
          className="mt-14 p-8 rounded-2xl bg-gradient-to-r from-primary-50 via-indigo-50 to-purple-50 border border-primary-200 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <h3 className="text-xl font-bold text-slate-900 mb-2">Have a specific architectural requirement?</h3>
          <p className="text-slate-700 text-sm max-w-xl mx-auto mb-6">
            We are here to help you configure custom extraction models, Tavily domain filtering, and Redis/Bifrost integrations.
          </p>
          <a
            href={`mailto:${APP_CONFIG.email}`}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 text-white rounded-xl font-bold shadow-lg shadow-primary-500/20 hover:shadow-primary-500/35 hover:opacity-95 transition-all text-sm"
          >
            <Mail className="h-4 w-4" />
            <span>Contact FreshGuard Team</span>
          </a>
        </motion.div>
      </div>
    </section>
  );
}
