import { useState } from 'react';
import { Menu, X, Shield, Github, Sparkles, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { APP_CONFIG } from '../lib/constants';

interface NavItem {
  name: string;
  href: string;
}

const NAV_ITEMS: NavItem[] = [
  { name: 'Problem', href: '#problem' },
  { name: 'Solution', href: '#solution' },
  { name: 'Features', href: '#features' },
  { name: 'How It Works', href: '#how-it-works' },
  { name: 'Benefits', href: '#benefits' },
  { name: 'FAQ', href: '#faq' },
];

export function Navigation({ scrolled }: { scrolled: boolean }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <motion.nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-white/95 backdrop-blur-md shadow-md border-b border-slate-200/80'
          : 'bg-white/70 backdrop-blur-sm border-b border-slate-200/40'
      }`}
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      {/* Top colorful gradient accent line */}
      <div className="h-1 w-full bg-gradient-to-r from-cyan-500 via-primary-500 to-purple-600" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Brand Logo */}
          <motion.a
            href="/"
            className="flex items-center space-x-2.5 group"
            whileHover={{ scale: 1.02 }}
            transition={{ type: 'spring', damping: 20 }}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 via-primary-600 to-purple-600 flex items-center justify-center shadow-md shadow-primary-500/20 group-hover:shadow-primary-500/35 transition-shadow">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="text-xl font-black tracking-tight text-slate-900 group-hover:text-primary-600 transition-colors">
                  Fresh<span className="text-primary-600">Guard</span>
                </span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Live
                </span>
              </div>
              <span className="text-[11px] text-slate-500 font-medium -mt-1 hidden sm:block">
                LLM Freshness Verification
              </span>
            </div>
          </motion.a>

          {/* Desktop Nav Items */}
          <div className="hidden lg:flex items-center space-x-6">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.name}
                href={item.href}
                className="text-slate-700 hover:text-primary-600 font-semibold text-sm transition-colors py-1 px-2 rounded-md hover:bg-primary-50/70"
              >
                {item.name}
              </a>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="hidden sm:flex items-center space-x-3">
            <motion.a
              href={APP_CONFIG.github}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3.5 py-2 text-sm font-semibold text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors border border-slate-200"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              <Github className="h-4 w-4" />
              <span>GitHub</span>
            </motion.a>

            <motion.a
              href="#cta"
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-bold text-white bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 rounded-lg shadow-md shadow-primary-500/25 hover:shadow-primary-500/40 hover:opacity-95 transition-all"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              <Sparkles className="h-4 w-4" />
              <span>{APP_CONFIG.ctaText}</span>
            </motion.a>
          </div>

          {/* Mobile menu trigger */}
          <motion.button
            className="lg:hidden p-2 rounded-lg text-slate-700 hover:bg-slate-100 transition-colors"
            onClick={() => setMobileOpen(!mobileOpen)}
            whileTap={{ scale: 0.95 }}
            aria-label="Toggle navigation menu"
          >
            {mobileOpen ? <X className="h-6 w-6 text-slate-900" /> : <Menu className="h-6 w-6 text-slate-900" />}
          </motion.button>
        </div>
      </div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="lg:hidden bg-white border-b border-slate-200 shadow-xl"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-5 py-4 space-y-3">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.name}
                  href={item.href}
                  className="block py-2 text-slate-800 hover:text-primary-600 font-semibold transition-colors"
                  onClick={() => setMobileOpen(false)}
                >
                  {item.name}
                </a>
              ))}
              <div className="pt-3 border-t border-slate-100 flex flex-col gap-2.5">
                <a
                  href={APP_CONFIG.github}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-slate-100 text-slate-800 rounded-lg font-semibold text-sm hover:bg-slate-200 transition-colors"
                >
                  <Github className="h-4 w-4" />
                  <span>GitHub Repository</span>
                  <ExternalLink className="h-3.5 w-3.5 text-slate-500" />
                </a>
                <a
                  href="#cta"
                  className="flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 text-white rounded-lg font-bold text-sm shadow-md"
                  onClick={() => setMobileOpen(false)}
                >
                  <Sparkles className="h-4 w-4" />
                  <span>{APP_CONFIG.ctaText}</span>
                </a>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}
