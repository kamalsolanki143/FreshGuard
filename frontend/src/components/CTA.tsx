import { motion } from 'framer-motion';
import { Clock, Users, Shield, ArrowRight, Github, Sparkles } from 'lucide-react';
import { APP_CONFIG } from '../lib/constants';

export function CTA() {
  return (
    <section className="relative py-28 bg-slate-950 text-white overflow-hidden" id="cta">
      {/* Background glowing mesh gradients */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-gradient-to-br from-cyan-600/25 to-primary-600/20 blur-3xl rounded-full pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-gradient-to-tl from-purple-600/25 to-pink-600/20 blur-3xl rounded-full pointer-events-none" />

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6 text-center z-10">
        {/* Top badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-900 border border-slate-800 text-cyan-400 text-xs sm:text-sm font-semibold mb-8 backdrop-blur-md shadow-lg"
        >
          <Sparkles className="h-4 w-4 text-cyan-400" />
          <span>Production-Ready Open Source Gateway Plugin</span>
        </motion.div>

        {/* Main CTA Heading */}
        <motion.h2
          className="text-4xl sm:text-5xl md:text-6xl font-black mb-6 tracking-tight leading-tight"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          Protect Your LLM Responses{' '}
          <span className="block mt-2">
            <span className="gradient-text">Starting Today</span>
          </span>
        </motion.h2>

        {/* Description with high-contrast text */}
        <motion.p
          className="text-lg sm:text-xl text-slate-300 mb-12 max-w-2xl mx-auto leading-relaxed"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          Integrate the FreshGuard plugin into your Bifrost gateway in minutes. Eliminate outdated hallucinations with automated live web evidence.
        </motion.p>

        {/* Buttons with clear, matching high-contrast colors */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
          <motion.a
            href={APP_CONFIG.github}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full sm:w-auto px-9 py-4 bg-gradient-to-r from-cyan-500 via-primary-500 to-purple-600 text-white rounded-xl font-black text-lg shadow-2xl shadow-cyan-500/25 hover:shadow-cyan-500/40 flex items-center justify-center gap-2 transition-all"
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
          >
            <Github className="h-5 w-5" />
            <span>Deploy From GitHub</span>
            <ArrowRight className="h-5 w-5 ml-1" />
          </motion.a>

          <motion.a
            href={`mailto:${APP_CONFIG.email}`}
            className="w-full sm:w-auto px-9 py-4 bg-white hover:bg-slate-100 text-slate-900 border-2 border-white rounded-xl font-black text-lg shadow-xl hover:text-primary-600 flex items-center justify-center gap-2 transition-all"
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
          >
            <span>Request Enterprise Demo</span>
          </motion.a>
        </div>

        {/* 3 High-contrast info cards */}
        <motion.div
          className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto text-left"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition-colors">
            <div className="w-10 h-10 rounded-xl bg-cyan-950 text-cyan-400 flex items-center justify-center mb-4 border border-cyan-800">
              <Shield className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-white text-base mb-1.5">Plug &amp; Play Integration</h3>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
              Native Go middleware plugin that drops cleanly into existing Bifrost semantic gateway pipelines.
            </p>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition-colors">
            <div className="w-10 h-10 rounded-xl bg-purple-950 text-purple-400 flex items-center justify-center mb-4 border border-purple-800">
              <Users className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-white text-base mb-1.5">Enterprise Ready</h3>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
              Configurable fail-open/fail-closed policies, custom TTL categories, and Redis cluster support.
            </p>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition-colors">
            <div className="w-10 h-10 rounded-xl bg-emerald-950 text-emerald-400 flex items-center justify-center mb-4 border border-emerald-800">
              <Clock className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-white text-base mb-1.5">Sub-20ms Overhead</h3>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
              Optimized parallel verification threads ensure user response latency remains ultra-responsive.
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
