// FreshGuard Frontend Type Definitions
// Exactly matches Python Verification Service and Go Plugin contracts

export type LifecycleStatus = 'accepted' | 'completed' | 'failed';
export type FreshnessStatus = 'FRESH' | 'STALE' | 'UNCERTAIN' | 'NOT_REQUIRED';
export type ClaimCategory = 'pricing' | 'software_version' | 'leadership' | 'general';
export type ClaimVerdict = 'supported' | 'contradicted' | 'unclear';

export interface EvidenceItem {
  evidence_id: string;
  title?: string;
  source_title?: string;
  url?: string;
  source_url?: string;
  content?: string;
  snippet?: string;
  relevance_score?: number;
  source_type?: string;
  retrieved_at?: string;
  published_at?: string;
}

export interface ClaimVerdictResult {
  claim_id: string;
  verdict: ClaimVerdict;
  confidence: number;
  reason: string;
  evidence_ids?: string[];
  evidence?: EvidenceItem[];
  corrected_value?: string | null;
  checked_at?: string;
  category?: ClaimCategory;
  entity?: string;
  attribute?: string;
  original_text?: string;
  text?: string;
}

export interface VerificationResponse {
  request_id: string;
  verification_id?: string;
  status: LifecycleStatus;
  freshness_status?: FreshnessStatus | null;
  requires_refresh: boolean;
  claims_checked: number;
  results?: ClaimVerdictResult[];
  claims?: ClaimVerdictResult[];
  processing_time_ms?: number;
  checked_at?: string;
  cache_id?: string;
  cache_evicted?: boolean;
  cache_eviction_error?: string;
  error?: string;
}

export interface VerificationRequest {
  request_id: string;
  text: string;
  mode?: 'blocking' | 'async';
  categories?: string[];
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface ReadyResponse {
  status: string;
  service: string;
  database: string;
}

export interface UserSession {
  name: string;
  email: string;
  role: string;
  isGuest: boolean;
  loggedInAt: string;
}
