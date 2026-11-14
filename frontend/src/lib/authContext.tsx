import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserSession } from '../types';

interface AuthContextType {
  user: UserSession | null;
  isGuest: boolean;
  loginAsGuest: () => void;
  login: (email: string, pass: string) => Promise<{ success: boolean; error?: string }>;
  signup: (name: string, email: string, pass: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const SESSION_KEY = 'freshguard_active_session';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserSession | null>(() => {
    try {
      const stored = sessionStorage.getItem(SESSION_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // ignore parsing error
    }
    // Start with null if no session stored; visitors become guest by clicking demo or developer by signing in
    return null;
  });

  useEffect(() => {
    if (user) {
      try {
        sessionStorage.setItem(SESSION_KEY, JSON.stringify(user));
      } catch {
        // ignore
      }
    } else {
      sessionStorage.removeItem(SESSION_KEY);
    }
  }, [user]);

  const loginAsGuest = () => {
    const guestUser: UserSession = {
      name: 'Hackathon Judge / Evaluator',
      email: 'judge@freshguard.demo',
      role: 'Guest Evaluator',
      isGuest: true,
      loggedInAt: new Date().toISOString(),
    };
    setUser(guestUser);
  };

  const login = async (email: string, pass: string) => {
    // Note: Python verification service is a microservice without user tables.
    // In demo mode, validate format and authorize user safely without pretending false backend auth.
    if (!email || !pass) {
      return { success: false, error: 'Email and password are required.' };
    }
    if (!email.includes('@')) {
      return { success: false, error: 'Please enter a valid email address.' };
    }
    if (pass.length < 6) {
      return { success: false, error: 'Password must be at least 6 characters.' };
    }

    const authUser: UserSession = {
      name: email.split('@')[0],
      email: email,
      role: 'Developer Account (Demo Session)',
      isGuest: false,
      loggedInAt: new Date().toISOString(),
    };
    setUser(authUser);
    return { success: true };
  };

  const signup = async (name: string, email: string, pass: string) => {
    if (!name || !email || !pass) {
      return { success: false, error: 'All fields are required.' };
    }
    if (!email.includes('@')) {
      return { success: false, error: 'Please enter a valid email address.' };
    }
    if (pass.length < 6) {
      return { success: false, error: 'Password must be at least 6 characters.' };
    }

    const newUser: UserSession = {
      name: name,
      email: email,
      role: 'Standard Developer (Demo Session)',
      isGuest: false,
      loggedInAt: new Date().toISOString(),
    };
    setUser(newUser);
    return { success: true };
  };

  const logout = () => {
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isGuest: !!user?.isGuest,
        loginAsGuest,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

