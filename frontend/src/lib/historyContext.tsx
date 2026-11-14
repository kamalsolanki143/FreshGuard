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

const SEED_VERIFICATIONS: VerificationResponse[] = [
  {
    verification_id: 'verif_gpt4_pricing_demo',
    request_id: 'demo-req-101',
    status: 'completed',
    freshness_status: 'FRESH',
    requires_refresh: false,
    claims_checked: 1,
    processing_time_ms: 18,
    checked_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    cache_id: 'bf-cache-gpt4-price',
    cache_evicted: false,
    claims: [
      {
        claim_id: 'claim_101',
        category: 'pricing',
        entity: 'OpenAI ChatGPT Plus',
        attribute: 'monthly_subscription',
        verdict: 'supported',
        confidence: 0.98,
        reason: 'Confirmed by OpenAI official product documentation at $20/month.',
        text: 'ChatGPT Plus costs $20/month',
        original_text: 'ChatGPT Plus costs $20/month',
        checked_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
        evidence: [
          {
            evidence_id: 'ev_101',
            title: 'OpenAI Pricing & Subscription Plans',
            url: 'https://openai.com/pricing',
            snippet: 'ChatGPT Plus subscription is available for $20/month providing GPT-4 access.',
            source_type: 'official_docs',
          },
        ],
      },
    ],
  },
  {
    verification_id: 'verif_python312_demo',
    request_id: 'demo-req-102',
    status: 'completed',
    freshness_status: 'FRESH',
    requires_refresh: false,
    claims_checked: 1,
    processing_time_ms: 22,
    checked_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    cache_id: 'bf-cache-python-rel',
    cache_evicted: false,
    claims: [
      {
        claim_id: 'claim_102',
        category: 'software_version',
        entity: 'Python',
        attribute: 'latest_release',
        verdict: 'supported',
        confidence: 0.99,
        reason: 'Python 3.12 is confirmed active stable release according to Python.org release schedule.',
        text: 'Python 3.12 is the active release',
        original_text: 'Python 3.12 is the active release',
        checked_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
        evidence: [
          {
            evidence_id: 'ev_102',
            title: 'Python Release Schedule',
            url: 'https://www.python.org/downloads/',
            snippet: 'Python 3.12 is the current major release series with ongoing security support.',
            source_type: 'official_docs',
          },
        ],
      },
    ],
  },
  {
    verification_id: 'verif_stale_cache_contra',
    request_id: 'demo-req-103',
    status: 'completed',
    freshness_status: 'STALE',
    requires_refresh: true,
    claims_checked: 1,
    processing_time_ms: 31,
    checked_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    cache_id: 'bf-cache-gpt4-free-stale',
    cache_evicted: true,
    claims: [
      {
        claim_id: 'claim_103',
        category: 'pricing',
        entity: 'OpenAI GPT-4 API',
        attribute: 'pricing_tier',
        verdict: 'contradicted',
        confidence: 0.99,
        reason: 'Contradicted: GPT-4 API is a commercial paid pay-as-you-go service, not free of charge.',
        text: 'GPT-4 API is completely free for all commercial users',
        original_text: 'GPT-4 API is completely free for all commercial users',
        corrected_value: 'Paid per 1k tokens (input/output tiered pricing)',
        checked_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
        evidence: [
          {
            evidence_id: 'ev_103',
            title: 'OpenAI Developer Platform API Pricing',
            url: 'https://openai.com/api/pricing/',
            snippet: 'GPT-4 API usage is metered per 1,000 tokens based on context window and modality.',
            source_type: 'official_docs',
          },
        ],
      },
    ],
  },
];

const HISTORY_STORAGE_KEY = 'freshguard_verification_history';

export function HistoryProvider({ children }: { children: React.ReactNode }) {
  const [history, setHistory] = useState<VerificationResponse[]>(() => {
    try {
      const saved = sessionStorage.getItem(HISTORY_STORAGE_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch {
      // ignore
    }
    return SEED_VERIFICATIONS;
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

