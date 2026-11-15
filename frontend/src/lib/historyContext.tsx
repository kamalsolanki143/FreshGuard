import React, { createContext, useContext, useState, useEffect } from 'react';
import { VerificationResponse } from '../types';

interface HistoryContextType {
  history: VerificationResponse[];
  addVerification: (res: VerificationResponse) => void;
  clearHistory: () => void;
  getStats: () => {
    total: number;
    claimsChecked: number;
    supported: number;
    contradicted: number;
    unclear: number;
    fresh: number;
    stale: number;
  };
}

const HistoryContext = createContext<HistoryContextType | undefined>(undefined);

const HISTORY_STORAGE_KEY = 'freshguard_verification_history';

export function HistoryProvider({ children }: { children: React.ReactNode }) {
  const [history, setHistory] = useState<VerificationResponse[]>(() => {
    try {
      const saved = sessionStorage.getItem(HISTORY_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed.filter((item) => !String(item?.request_id || '').startsWith('demo-req-'));
        }
      }
    } catch {
      // ignore
    }
    return [];
  });

  useEffect(() => {
    try {
      sessionStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
    } catch {
      // ignore
    }
  }, [history]);

  const addVerification = (res: VerificationResponse) => {
    setHistory((prev) => [res, ...prev.filter((item) => item.request_id !== res.request_id)]);
  };

  const clearHistory = () => {
    setHistory([]);
  };

  const getStats = () => {
    let claimsChecked = 0;
    let supported = 0;
    let contradicted = 0;
    let unclear = 0;
    let fresh = 0;
    let stale = 0;

    for (const v of history) {
      claimsChecked += v.claims_checked || (v.claims ? v.claims.length : 0);
      if (v.freshness_status === 'FRESH') fresh++;
      if (v.freshness_status === 'STALE') stale++;

      const claimsList = v.claims || v.results || [];
      for (const c of claimsList) {
        const verd = (c.verdict || '').toLowerCase();
        if (verd === 'supported') supported++;
        else if (verd === 'contradicted') contradicted++;
        else unclear++;
      }
    }

    return {
      total: history.length,
      claimsChecked,
      supported,
      contradicted,
      unclear,
      fresh,
      stale,
    };
  };

  return (
    <HistoryContext.Provider value={{ history, addVerification, clearHistory, getStats }}>
      {children}
    </HistoryContext.Provider>
  );
}

export function useHistory() {
  const ctx = useContext(HistoryContext);
  if (!ctx) {
    throw new Error('useHistory must be used within a HistoryProvider');
  }
  return ctx;
}

