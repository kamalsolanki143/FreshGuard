import { motion } from 'framer-motion';
import { Github, Twitter, Linkedin, Mail, Shield, Heart } from 'lucide-react';
import { APP_CONFIG } from '../lib/constants';

export function Footer() {
  return (
    <footer className="bg-slate-950 text-slate-300 pt-16 pb-12 border-t border-slate-800" id="footer">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <motion.div
          className="grid grid-cols-2 md:grid-cols-4 gap-8 sm:gap-10 mb-12"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          {/* Brand info */}
          <div className="col-span-2 md:col-span-1">
            <a href="/" className="flex items-center space-x-2.5 mb-4 inline-block group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 via-primary-600 to-purple-600 flex items-center justify-center text-white shadow-md">
                <Shield className="h-5 w-5" />
              </div>
              <span className="text-2xl font-black text-white group-hover:text-primary-400 transition-colors">
                Fresh<span className="text-primary-500">Guard</span>
              </span>
            </a>
            <p className="text-slate-400 text-sm leading-relaxed mb-4">
              Real-time freshness verification for LLM responses with Tavily-powered live evidence and Bifrost semantic cache protection.
            </p>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-semibold text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Open Source MIT License</span>
            </div>
          </div>

          {/* Navigation Links */}
          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-wider mb-4">Product</h3>
            <ul className="space-y-2.5 text-sm font-medium">
              <li><a href="#problem" className="text-slate-400 hover:text-cyan-400 transition-colors">The Problem</a></li>
              <li><a href="#solution" className="text-slate-400 hover:text-cyan-400 transition-colors">Pipeline Solution</a></li>
              <li><a href="#features" className="text-slate-400 hover:text-cyan-400 transition-colors">Key Features</a></li>
              <li><a href="#how-it-works" className="text-slate-400 hover:text-cyan-400 transition-colors">How It Works</a></li>
              <li><a href="#benefits" className="text-slate-400 hover:text-cyan-400 transition-colors">ROI &amp; Benefits</a></li>
            </ul>
          </div>

          {/* Architecture Links */}
          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-wider mb-4">Resources</h3>
            <ul className="space-y-2.5 text-sm font-medium">
              <li><a href={APP_CONFIG.github} target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-cyan-400 transition-colors">GitHub Repository</a></li>
              <li><a href="https://tavily.com" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-cyan-400 transition-colors">Tavily Search API</a></li>
              <li><a href="#faq" className="text-slate-400 hover:text-cyan-400 transition-colors">Frequently Asked Questions</a></li>
              <li><a href={`mailto:${APP_CONFIG.email}`} className="text-slate-400 hover:text-cyan-400 transition-colors">Architecture Consultation</a></li>
            </ul>
          </div>

          {/* Community & Contact */}
          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-wider mb-4">Connect</h3>
            <div className="flex space-x-3 mb-5">
              <a
                href={APP_CONFIG.github}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl hover:bg-slate-800 hover:text-cyan-400 transition-colors text-slate-300"
                aria-label="GitHub"
              >
                <Github className="h-5 w-5" />
              </a>
              <a
                href="https://twitter.com"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl hover:bg-slate-800 hover:text-cyan-400 transition-colors text-slate-300"
                aria-label="Twitter"
              >
                <Twitter className="h-5 w-5" />
              </a>
              <a
                href="https://linkedin.com"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl hover:bg-slate-800 hover:text-cyan-400 transition-colors text-slate-300"
                aria-label="LinkedIn"
              >
                <Linkedin className="h-5 w-5" />
              </a>
            </div>
            <div>
              <a
                href={`mailto:${APP_CONFIG.email}`}
                className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-cyan-400 transition-colors font-medium"
              >
                <Mail className="h-4 w-4" />
                <span>{APP_CONFIG.email}</span>
              </a>
            </div>
          </div>
        </motion.div>

        {/* Bottom copyright line */}
        <div className="border-t border-slate-800/80 pt-8 flex flex-col sm:flex-row justify-between items-center gap-4 text-xs text-slate-500 font-medium">
          <p>&copy; {new Date().getFullYear()} FreshGuard. Open source software released under MIT.</p>
          <div className="flex items-center gap-1.5 text-slate-400">
            <span>Built with</span>
            <Heart className="h-3.5 w-3.5 text-rose-500 fill-rose-500 inline" />
            <span>for high-reliability AI systems</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
