import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, Github, Sparkles, LayoutDashboard, Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { APP_CONFIG } from '../../lib/constants';
import { useAuth } from '../../lib/authContext';

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const { user, loginAsGuest } = useAuth();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 30);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleDemoAccess = () => {
    if (!user) {
      loginAsGuest();
    }
    navigate('/dashboard/verify');
  };

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-slate-900/95 backdrop-blur-md shadow-xl border-b border-slate-800'
          : 'bg-slate-950/80 backdrop-blur-sm border-b border-slate-800/60'
      }`}
    >
      {/* Accent gradient line */}
      <div className="h-0.5 w-full bg-gradient-to-r from-cyan-500 via-primary-500 to-purple-600" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Brand Logo */}
          <Link to="/" className="flex items-center space-x-2.5 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 via-primary-600 to-purple-600 flex items-center justify-center shadow-lg shadow-primary-500/20 group-hover:shadow-primary-500/35 transition-shadow">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="text-xl font-black tracking-tight text-white group-hover:text-cyan-400 transition-colors">
                  Fresh<span className="text-primary-400">Guard</span>
                </span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
                  v{APP_CONFIG.version}
                </span>
              </div>
              <span className="text-[11px] text-slate-400 font-medium -mt-1 hidden sm:block">
                Trust the answer. Verify its freshness.
              </span>
            </div>
          </Link>

          {/* Desktop Nav Items */}
          <div className="hidden lg:flex items-center space-x-7">
            <Link to="/" className="text-slate-300 hover:text-white font-medium text-sm transition-colors">
              Home
            </Link>
            <a href="/#problem" className="text-slate-300 hover:text-white font-medium text-sm transition-colors">
              Problem & Solution
            </a>
            <a href="/#how-it-works" className="text-slate-300 hover:text-white font-medium text-sm transition-colors">
              Pipeline Steps
            </a>
            <a href="/#features" className="text-slate-300 hover:text-white font-medium text-sm transition-colors">
              Features
            </a>
            <a href="/#architecture" className="text-slate-300 hover:text-white font-medium text-sm transition-colors">
              Architecture
            </a>
            <Link to="/docs" className="text-slate-300 hover:text-white font-medium text-sm transition-colors">
              Docs
            </Link>
          </div>

          {/* Action CTAs */}
          <div className="hidden sm:flex items-center space-x-3">
            <a
              href={APP_CONFIG.github}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-800 rounded-lg transition-colors border border-slate-700/80"
            >
              <Github className="h-4 w-4" />
              <span>GitHub</span>
            </a>

            <Link
              to="/dashboard"
              className="flex items-center gap-1.5 px-3.5 py-2 text-sm font-semibold text-slate-200 hover:text-white bg-slate-800 hover:bg-slate-700/90 rounded-lg border border-slate-700 transition-all"
            >
              <LayoutDashboard className="h-4 w-4 text-cyan-400" />
              <span>Dashboard</span>
            </Link>

            <button
              onClick={handleDemoAccess}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-bold text-white bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 rounded-lg shadow-md shadow-primary-500/25 hover:shadow-primary-500/40 hover:opacity-95 transition-all"
            >
              <Sparkles className="h-4 w-4" />
              <span>Try Live Demo</span>
            </button>
          </div>

          {/* Mobile menu button */}
          <div className="flex sm:hidden">
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 focus:outline-none"
            >
              {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="sm:hidden border-b border-slate-800 bg-slate-900/98 backdrop-blur-xl px-4 pt-3 pb-6 space-y-3"
          >
            <div className="flex flex-col space-y-2">
              <Link
                to="/"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-base font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Home
              </Link>
              <a
                href="/#problem"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-base font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Problem & Solution
              </a>
              <a
                href="/#how-it-works"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-base font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Pipeline Steps
              </a>
              <a
                href="/#features"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-base font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Features
              </a>
              <Link
                to="/docs"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-base font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Documentation
              </Link>
              <Link
                to="/dashboard"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-base font-semibold text-cyan-400 hover:bg-slate-800 rounded-lg flex items-center gap-2"
              >
                <LayoutDashboard className="h-4 w-4" />
                <span>Dashboard</span>
              </Link>
            </div>

            <div className="pt-3 border-t border-slate-800 flex flex-col gap-2">
              <button
                onClick={() => {
                  setMobileOpen(false);
                  handleDemoAccess();
                }}
                className="w-full py-2.5 px-4 text-center font-bold text-white bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 rounded-lg shadow-lg flex items-center justify-center gap-2"
              >
                <Sparkles className="h-4 w-4" />
                <span>Try Live Demo</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
