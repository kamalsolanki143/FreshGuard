import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './lib/authContext';
import { HistoryProvider } from './lib/historyContext';

import { LandingPage } from './pages/LandingPage';
import { DocsPage } from './pages/DocsPage';
import { LoginPage } from './pages/auth/LoginPage';
import { SignupPage } from './pages/auth/SignupPage';

import { DashboardLayout } from './components/layout/DashboardLayout';
import { OverviewPage } from './pages/dashboard/OverviewPage';
import { VerifyPage } from './pages/dashboard/VerifyPage';
import { HistoryPage } from './pages/dashboard/HistoryPage';
import { CachePage } from './pages/dashboard/CachePage';
import { IntegrationsPage } from './pages/dashboard/IntegrationsPage';
import { SettingsPage } from './pages/dashboard/SettingsPage';

export function App() {
  return (
    <AuthProvider>
      <HistoryProvider>
        <Router>
          <Routes>
            {/* Public Marketing & Docs Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/docs" element={<DocsPage />} />

            {/* Authentication & Guest Access Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            {/* Application Dashboard Shell & Workspaces */}
            <Route path="/dashboard" element={<DashboardLayout />}>
              <Route index element={<OverviewPage />} />
              <Route path="verify" element={<VerifyPage />} />
              <Route path="history" element={<HistoryPage />} />
              <Route path="cache" element={<CachePage />} />
              <Route path="integrations" element={<IntegrationsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            {/* Fallback to Home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </HistoryProvider>
    </AuthProvider>
  );
}

export default App;
