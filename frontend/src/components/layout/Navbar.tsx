import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  Shield,
  Github,
  Sparkles,
  LayoutDashboard,
  Menu,
  X,
  LogIn,
  LogOut,
  UserCheck,
  ChevronDown,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { APP_CONFIG } from '../../lib/constants';
import { useAuth } from '../../lib/authContext';

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);

  const navigate = useNavigate();
  const location = useLocation();
  const { user, isGuest, logout } = useAuth();

  // Scroll detection for navbar styling
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close menus on route change
  useEffect(() => {
    setMobileOpen(false);
    setAccountMenuOpen(false);
  }, [location.pathname]);

  // Click outside listener for Account dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target as Node)) {
        setAccountMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    setAccountMenuOpen(false);
    setMobileOpen(false);
    navigate('/', { replace: true });
  };

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-slate-900/95 backdrop-blur-md shadow-xl border-b border-slate-800'
          : 'bg-slate-950/85 backdrop-blur-sm border-b border-slate-800/60'
      }`}
    >
      {/* Top accent gradient line */}
      <div className="h-0.5 w-full bg-gradient-to-r from-cyan-500 via-primary-500 to-purple-600" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Brand Logo & Tagline */}
          <Link to="/" className="flex items-center space-x-2.5 group flex-shrink-0">
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

          {/* Desktop Navigation Links */}
          <div className="hidden lg:flex items-center space-x-6 xl:space-x-7">
            <Link to="/" className="text-slate-300 hover:text-white font-medium text-sm transition-colors">
              Home
            </Link>
            <a href="/#problem" className="text-slate-300 hover:text-white font-medium text-sm transition-colors">
              Problem &amp; Solution
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

          {/* Right Action CTAs */}
          <div className="hidden sm:flex items-center space-x-3">
            <a
              href={APP_CONFIG.github}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-800 rounded-lg transition-colors border border-slate-700/80"
              title="GitHub Repository"
            >
              <Github className="h-4 w-4" />
              <span>GitHub</span>
            </a>

            {/* CONDITIONAL RENDERING BASED ON AUTHENTICATION STATE */}
            {user ? (
              /* --- LOGGED-IN STATE --- */
              <div className="flex items-center space-x-3">
                {/* Dashboard Access Button */}
                <Link
                  to="/dashboard"
                  className="flex items-center gap-1.5 px-3.5 py-2 text-sm font-semibold text-white bg-gradient-to-r from-cyan-600 to-primary-600 hover:opacity-95 rounded-lg shadow-md shadow-primary-500/25 transition-all"
                >
                  <LayoutDashboard className="h-4 w-4" />
                  <span>Dashboard</span>
                </Link>

                {/* Account & Profile Dropdown */}
                <div className="relative" ref={accountMenuRef}>
                  <button
                    onClick={() => setAccountMenuOpen(!accountMenuOpen)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/90 hover:bg-slate-700/90 border border-slate-700 rounded-lg text-xs font-semibold text-slate-200 transition-colors focus:outline-none"
                    aria-label="Toggle user account menu"
                  >
                    <div className="w-6 h-6 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-cyan-300 font-bold text-[11px]">
                      {isGuest ? (
                        <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                      ) : (
                        <UserCheck className="h-3.5 w-3.5 text-emerald-400" />
                      )}
                    </div>
                    <span className="max-w-[110px] truncate">{user.name || 'Evaluator'}</span>
                    <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                  </button>

                  <AnimatePresence>
                    {accountMenuOpen && (
                      <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        transition={{ duration: 0.15 }}
                        className="absolute right-0 mt-2 w-64 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden z-50 divide-y divide-slate-800"
                      >
                        {/* Identity & Status Header */}
                        <div className="p-3.5 bg-slate-950/60">
                          <p className="text-xs font-bold text-white truncate">{user.name}</p>
                          <p className="text-[11px] text-slate-400 truncate">{user.email}</p>
                          <div className="mt-2 flex items-center justify-between text-[10px]">
                            <span className="font-semibold text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800">
                              {isGuest ? 'Judge Demo Mode' : 'Developer Console'}
                            </span>
                            <span className="flex items-center gap-1 text-emerald-400">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              <span>Active Session</span>
                            </span>
                          </div>
                        </div>

                        {/* Dropdown Links */}
                        <div className="p-1.5 space-y-0.5">
                          <Link
                            to="/dashboard"
                            className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-200 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                          >
                            <LayoutDashboard className="h-3.5 w-3.5 text-cyan-400" />
                            <span>Open Dashboard</span>
                          </Link>
                          <Link
                            to="/dashboard/verify"
                            className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-200 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                          >
                            <Sparkles className="h-3.5 w-3.5 text-primary-400" />
                            <span>Verify Workspace</span>
                          </Link>
                        </div>

                        {/* Logout Action */}
                        <div className="p-1.5">
                          <button
                            onClick={handleLogout}
                            className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 rounded-lg transition-colors"
                          >
                            <LogOut className="h-3.5 w-3.5" />
                            <span>Log Out</span>
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            ) : (
              /* --- LOGGED-OUT STATE --- */
              <div className="flex items-center space-x-3">
                {/* Login Button */}
                <Link
                  to="/login"
                  className="flex items-center gap-1.5 px-3.5 py-2 text-sm font-semibold text-slate-200 hover:text-white bg-slate-800/90 hover:bg-slate-700/90 rounded-lg border border-slate-700 hover:border-cyan-500/50 transition-all shadow-sm"
                  title="Sign in with developer credentials"
                >
                  <LogIn className="h-4 w-4 text-cyan-400" />
                  <span>Login</span>
                </Link>

                {/* Try Live Demo Button (Directs to /login) */}
                <Link
                  to="/login"
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-bold text-white bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 rounded-lg shadow-md shadow-primary-500/25 hover:shadow-primary-500/40 hover:opacity-95 transition-all"
                  title="Access FreshGuard live evaluator sandbox"
                >
                  <Sparkles className="h-4 w-4" />
                  <span>Try Live Demo</span>
                </Link>
              </div>
            )}
          </div>

          {/* Mobile hamburger menu toggle */}
          <div className="flex sm:hidden">
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 focus:outline-none"
              aria-label="Toggle Navigation Menu"
            >
              {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Slide-Out Drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="sm:hidden border-b border-slate-800 bg-slate-900/98 backdrop-blur-xl px-4 pt-3 pb-6 space-y-3"
          >
            {/* Mobile Navigation Links */}
            <div className="flex flex-col space-y-1.5">
              <Link
                to="/"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Home
              </Link>
              <a
                href="/#problem"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Problem &amp; Solution
              </a>
              <a
                href="/#how-it-works"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Pipeline Steps
              </a>
              <a
                href="/#features"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Features
              </a>
              <a
                href="/#architecture"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Architecture
              </a>
              <Link
                to="/docs"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 rounded-lg"
              >
                Docs
              </Link>
            </div>

            {/* Mobile Auth Actions */}
            <div className="pt-3 border-t border-slate-800 flex flex-col gap-2.5">
              {user ? (
                /* Authenticated Mobile Actions */
                <>
                  <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
                    <p className="text-xs font-bold text-white truncate">{user.name}</p>
                    <p className="text-[11px] text-slate-400 truncate">{user.email}</p>
                    <span className="mt-1 inline-block text-[10px] font-semibold text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800">
                      {isGuest ? 'Judge Demo Mode' : 'Developer Console'}
                    </span>
                  </div>

                  <Link
                    to="/dashboard"
                    onClick={() => setMobileOpen(false)}
                    className="w-full py-2.5 px-4 text-center font-bold text-white bg-gradient-to-r from-cyan-600 to-primary-600 rounded-lg shadow-md flex items-center justify-center gap-2"
                  >
                    <LayoutDashboard className="h-4 w-4" />
                    <span>Open Dashboard</span>
                  </Link>

                  <button
                    onClick={handleLogout}
                    className="w-full py-2.5 px-4 text-center font-semibold text-rose-400 bg-rose-950/40 hover:bg-rose-950/60 border border-rose-900/50 rounded-lg flex items-center justify-center gap-2"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Log Out</span>
                  </button>
                </>
              ) : (
                /* Logged-out Mobile Actions */
                <>
                  <Link
                    to="/login"
                    onClick={() => setMobileOpen(false)}
                    className="w-full py-2.5 px-4 text-center font-bold text-slate-200 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 flex items-center justify-center gap-2 transition-colors text-sm"
                  >
                    <LogIn className="h-4 w-4 text-cyan-400" />
                    <span>Login</span>
                  </Link>

                  <Link
                    to="/login"
                    onClick={() => setMobileOpen(false)}
                    className="w-full py-2.5 px-4 text-center font-bold text-white bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 rounded-lg shadow-lg flex items-center justify-center gap-2 transition-opacity text-sm"
                  >
                    <Sparkles className="h-4 w-4" />
                    <span>Try Live Demo</span>
                  </Link>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
