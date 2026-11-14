import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../lib/authContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Route protection wrapper for FreshGuard application workspace.
 * Requires a valid session (Developer Account or Judge Demo Mode).
 * Unauthenticated visitors are redirected to /login with the intended destination preserved.
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user } = useAuth();
  const location = useLocation();

  // Validate both in-memory state and active storage session to prevent bfcache leaks
  let hasValidSession = false;
  try {
    const rawStored = sessionStorage.getItem('freshguard_active_session');
    hasValidSession = Boolean(user && rawStored);
  } catch {
    hasValidSession = Boolean(user);
  }

  if (!hasValidSession) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
