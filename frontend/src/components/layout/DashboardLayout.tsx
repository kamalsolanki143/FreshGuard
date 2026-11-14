import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import {
  Shield,
  LayoutDashboard,
  History,
  Database,
  Blocks,
  Settings,
  BookOpen,
  ArrowLeft,
  Menu,
  X,
  Sparkles,
  User,
  LogOut,
  UserCheck,
  LogIn,
} from 'lucide-react';
import { useAuth } from '../../lib/authContext';
import { checkHealth } from '../../lib/api';

interface NavItem {
  name: string;
  href: string;
  icon: any;
  badge?: string;
}

const SIDEBAR_ITEMS: NavItem[] = [
  { name: 'Overview', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Verify Workspace', href: '/dashboard/verify', icon: Sparkles, badge: 'Live API' },
  { name: 'Verification History', href: '/dashboard/history', icon: History },
  { name: 'Cache Protection', href: '/dashboard/cache', icon: Database },
  { name: 'Integrations', href: '/dashboard/integrations', icon: Blocks },
  { name: 'Documentation', href: '/docs', icon: BookOpen },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export function DashboardLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isGuest, loginAsGuest, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [serviceStatus, setServiceStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  // Check health periodically
  useEffect(() => {
    let mounted = true;
    const verifyHealth = async () => {
      try {
        await checkHealth();
        if (mounted) setServiceStatus('online');
      } catch {
        if (mounted) setServiceStatus('offline');
      }
    };
    verifyHealth();
    const interval = setInterval(verifyHealth, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/', { replace: true });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col lg:flex-row font-sans">
      {/* Mobile Top Header */}
      <div className="lg:hidden flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800">
        <Link to="/" className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-primary-600 flex items-center justify-center">
            <Shield className="h-4 w-4 text-white" />
          </div>
          <span className="font-bold text-lg text-white">FreshGuard</span>
        </Link>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
          aria-label="Toggle Navigation Drawer"
        >
          {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Sidebar for Desktop & Mobile Overlay */}
      <aside
        className={`${
          mobileMenuOpen ? 'block' : 'hidden'
        } lg:block w-full lg:w-64 bg-slate-900/95 border-r border-slate-800/80 flex flex-col flex-shrink-0 z-40 fixed lg:sticky top-0 h-auto lg:h-screen overflow-y-auto`}
      >
        {/* Brand Header */}
        <div className="p-5 border-b border-slate-800/80">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 via-primary-600 to-purple-600 flex items-center justify-center shadow-md shadow-primary-500/25">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-black tracking-tight text-white text-lg group-hover:text-cyan-400 transition-colors">
                  Fresh<span className="text-primary-400">Guard</span>
                </span>
              </div>
              <span className="text-[11px] text-slate-400 font-medium block">
                Verification Gateway
              </span>
            </div>
          </Link>

          {/* Session Mode Badge */}
          <div className="mt-4 px-3 py-1.5 bg-gradient-to-r from-cyan-950/60 to-primary-950/60 border border-cyan-800/60 rounded-lg flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5 text-cyan-300 font-semibold">
              <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
              <span>{isGuest ? 'Judge Demo Mode' : user ? 'Developer Console' : 'Guest Preview'}</span>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-900/80 text-cyan-200">
              {user ? 'Active' : 'Preview'}
            </span>
          </div>
        </div>

        {/* Sidebar Nav Links */}
        <nav className="p-3 space-y-1 flex-1">
          {SIDEBAR_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                  isActive
                    ? 'bg-primary-600/20 text-white border border-primary-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-4 w-4 ${isActive ? 'text-primary-400' : 'text-slate-400'}`} />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-primary-500/20 text-primary-300 border border-primary-500/30">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User / Session Profile Footer */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/60 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-cyan-400 font-bold text-xs flex-shrink-0">
                {user && !user.isGuest ? (
                  <UserCheck className="h-4 w-4 text-emerald-400" />
                ) : user ? (
                  <User className="h-4 w-4" />
                ) : (
                  <LogIn className="h-4 w-4 text-amber-400" />
                )}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-slate-200 truncate">
                  {user?.name || 'Unauthenticated'}
                </p>
                <p className="text-[10px] text-slate-400 truncate">
                  {user?.email || 'Sign in or start demo'}
                </p>
              </div>
            </div>
            {user ? (
              <button
                onClick={handleLogout}
                title="Sign Out / Reset Session"
                className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <LogOut className="h-4 w-4" />
              </button>
            ) : (
              <Link
                to="/login"
                title="Sign In"
                className="p-1.5 text-cyan-400 hover:text-cyan-300 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <LogIn className="h-4 w-4" />
              </Link>
            )}
          </div>

          <Link
            to="/"
            className="flex items-center justify-center gap-1.5 w-full py-1.5 text-xs text-slate-400 hover:text-slate-200 bg-slate-800/60 hover:bg-slate-800 rounded-lg border border-slate-800 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to Public Website</span>
          </Link>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Navbar */}
        <header className="h-16 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              FreshGuard Workspace
            </span>
            <span className="text-slate-600">/</span>
            <span className="text-sm font-bold text-slate-200 capitalize">
              {location.pathname.split('/')[2] || 'Overview'}
            </span>
          </div>

          {/* Top Actions & Indicators */}
          <div className="flex items-center gap-4">
            {/* Live Service Indicator */}
            <div
              className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${
                serviceStatus === 'online'
                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                  : serviceStatus === 'offline'
                  ? 'bg-amber-950/60 text-amber-400 border-amber-800/60'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  serviceStatus === 'online'
                    ? 'bg-emerald-400 animate-pulse'
                    : serviceStatus === 'offline'
                    ? 'bg-amber-400'
                    : 'bg-slate-500'
                }`}
              />
              <span>
                {serviceStatus === 'online'
                  ? 'Verification API Connected'
                  : serviceStatus === 'offline'
                  ? 'Backend Standby / Sleep'
                  : 'Connecting to API...'}
              </span>
            </div>

            {/* Quick Action Button */}
            <Link
              to="/dashboard/verify"
              className="hidden sm:flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 bg-gradient-to-r from-cyan-600 to-primary-600 text-white rounded-lg hover:opacity-95 shadow-sm shadow-primary-500/25 transition-all"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>Verify Claim</span>
            </Link>
          </div>
        </header>

        {/* Dynamic Demo / Session Status Banner */}
        {isGuest ? (
          <div className="bg-gradient-to-r from-cyan-950/90 via-primary-950/70 to-purple-950/90 border-b border-cyan-800/50 px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-cyan-400 flex-shrink-0 animate-pulse" />
              <span className="font-bold text-cyan-300">Demo Mode:</span>
              <span className="text-slate-200">
                {serviceStatus === 'online'
                  ? 'Guest Evaluator session active. Connected to Verification Microservice. Temporal claim extraction and rule-based evaluation active.'
                  : 'Guest Evaluator session active. Running in standby mode while verification backend connects.'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="px-2.5 py-1 bg-cyan-900/70 hover:bg-cyan-800 text-cyan-200 font-semibold rounded-md border border-cyan-700/70 transition-colors"
              >
                Sign In as Developer
              </Link>
            </div>
          </div>
        ) : user ? (
          <div className="bg-slate-900/90 border-b border-slate-800 px-6 py-2 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
              <span className="font-bold text-slate-200">Developer Account:</span>
              <span className="text-slate-300 font-mono">{user.email}</span>
              <span className="text-slate-500">({user.role})</span>
            </div>
            <span className="text-[11px] text-emerald-400 font-semibold">Bifrost Gateway Ready</span>
          </div>
        ) : (
          <div className="bg-amber-950/70 border-b border-amber-800/60 px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs text-amber-200">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span>Viewing in unauthenticated state. Activate guest evaluator mode or sign in with a developer account.</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={loginAsGuest}
                className="px-2.5 py-1 bg-amber-900/70 hover:bg-amber-800 text-amber-100 font-semibold rounded-md border border-amber-700/70 transition-colors"
              >
                Activate Evaluator Demo
              </button>
              <Link
                to="/login"
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-md border border-slate-700 transition-colors"
              >
                Sign In
              </Link>
            </div>
          </div>
        )}

        {/* Workspace Content Outlet */}
        <main className="p-6 md:p-8 flex-1 max-w-7xl mx-auto w-full">
          <Outlet />
        </main>
      </div>
    </div>
  );
}