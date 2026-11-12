import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, Github } from 'lucide-react';
import { useState } from 'react';
import { APP_CONFIG } from '../lib/constants';

export function FloatingCTA() {
  const [visible, setVisible] = useState(true);

  if (!visible) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        className="fixed bottom-5 right-5 z-40 max-w-sm w-[calc(100%-40px)] sm:w-auto bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl border-2 border-primary-200/80 p-5"
        initial={{ opacity: 0, scale: 0.9, y: 80 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 80 }}
        transition={{ duration: 0.4, type: 'spring', damping: 20 }}
      >
        <button
          className="absolute top-3 right-3 p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          onClick={() => setVisible(false)}
          aria-label="Close notification"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="pr-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-black uppercase tracking-wider text-primary-700">
              FreshGuard v1.0
            </span>
          </div>

          <h3 className="text-base font-bold text-slate-900 mb-1.5">
            Ready to stop LLM hallucinations?
          </h3>
          <p className="text-slate-600 text-xs leading-relaxed mb-4">
            Try the Tavily-powered real-time verification pipeline in your Bifrost gateway today.
          </p>

          <div className="flex gap-2.5">
            <a
              href="#solution"
              className="flex-1 px-3.5 py-2 bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 text-white rounded-lg font-bold text-xs text-center shadow-md shadow-primary-500/20 hover:opacity-95 transition-opacity flex items-center justify-center gap-1"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>Pipeline</span>
            </a>
            <a
              href={APP_CONFIG.github}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 rounded-lg font-bold text-xs text-center transition-colors flex items-center justify-center gap-1"
            >
              <Github className="h-3.5 w-3.5" />
              <span>GitHub</span>
            </a>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
