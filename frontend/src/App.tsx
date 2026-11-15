import { BrowserRouter as Router, Routes, Route, useLocation, Link } from 'react-router-dom';
import { useEffect } from 'react';
import { AuthProvider } from './lib/authContext';
import { HistoryProvider } from './lib/historyContext';

import { LandingPage } from './pages/LandingPage';
import { DocsPage } from './pages/DocsPage';
import { LoginPage } from './pages/auth/LoginPage';
import { SignupPage } from './pages/auth/SignupPage';

import { DashboardLayout } from './components/layout/DashboardLayout';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { OverviewPage } from './pages/dashboard/OverviewPage';
import { VerifyPage } from './pages/dashboard/VerifyPage';
import { HistoryPage } from './pages/dashboard/HistoryPage';
import { CachePage } from './pages/dashboard/CachePage';
import { IntegrationsPage } from './pages/dashboard/IntegrationsPage';
import { SettingsPage } from './pages/dashboard/SettingsPage';

function RouteEffects() {
  const location = useLocation();

  useEffect(() => {
    const titles: Record<string, string> = {
      '/': 'FreshGuard | Real-time LLM Freshness Verification',
      '/docs': 'Documentation | FreshGuard',
      '/login': 'Sign In | FreshGuard',
      '/signup': 'Create Account | FreshGuard',
      '/dashboard': 'Overview | FreshGuard',
      '/dashboard/verify': 'Verify Workspace | FreshGuard',
      '/dashboard/history': 'Verification History | FreshGuard',
      '/dashboard/cache': 'Cache Protection | FreshGuard',
      '/dashboard/integrations': 'Integrations | FreshGuard',
      '/dashboard/settings': 'Settings | FreshGuard',
    };
    document.title = titles[location.pathname] || 'FreshGuard';
  }, [location.pathname]);

  useEffect(() => {
    if (!location.hash) return;
    let target: string;
    try {
      target = decodeURIComponent(location.hash.slice(1));
    } catch {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      document.getElementById(target)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [location.pathname, location.hash]);

  return null;
}

function NotFoundPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-6">
      <div className="max-w-lg text-center space-y-4">
        <p className="text-sm font-bold tracking-widest text-cyan-400">404</p>
        <h1 className="text-3xl font-black">Page not found</h1>
        <p className="text-slate-400">The page you requested does not exist or may have moved.</p>
        <Link to="/" className="inline-flex rounded-lg bg-cyan-600 px-4 py-2 font-semibold text-white">Return home</Link>
      </div>
    </main>
  );
}

export function App() {
  return (
    <AuthProvider>
      <HistoryProvider>
        <Router>
          <RouteEffects />
          <Routes>
            {/* Public Marketing & Docs Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/docs" element={<DocsPage />} />

            {/* Authentication & Guest Access Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            {/* Application Dashboard Shell & Workspaces (Protected) */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<OverviewPage />} />
              <Route path="verify" element={<VerifyPage />} />
              <Route path="history" element={<HistoryPage />} />
              <Route path="cache" element={<CachePage />} />
              <Route path="integrations" element={<IntegrationsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Router>
      </HistoryProvider>
    </AuthProvider>
  );
}

export default App;
