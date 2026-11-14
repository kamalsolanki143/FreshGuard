import { VerificationRequest, VerificationResponse, HealthResponse, ReadyResponse } from '../types';

// The API base defaults to '/api' (handled by Vite proxy in dev, Cloudflare Pages Functions in production)
// Can be overridden via VITE_API_URL environment variable if connecting directly to a deployed backend.
const rawApiBase = (import.meta.env.VITE_API_URL as string | undefined) || '/api';
export const API_BASE = rawApiBase.replace(/\/+$/, '');

/**
 * Helper to execute a fetch request with automatic single retry for cold-start 502/503/504 errors.
 */
async function fetchWithColdStartRetry(url: string, options: RequestInit, retries = 1): Promise<Response> {
  try {
    const res = await fetch(url, options);
    // If upstream is cold-starting or temporarily unavailable, retry once after short delay
    if ((res.status === 502 || res.status === 503 || res.status === 504) && retries > 0) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      return fetchWithColdStartRetry(url, options, retries - 1);
    }
    return res;
  } catch (err: any) {
    if (retries > 0) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      return fetchWithColdStartRetry(url, options, retries - 1);
    }
    throw err;
  }
}

/**
 * Submits text to the FreshGuard Verification Service for real-time claim extraction and verification.
 */
export async function submitVerification(req: VerificationRequest): Promise<VerificationResponse> {
  const payload = {
    request_id: req.request_id || `web-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    text: req.text,
    mode: req.mode || 'blocking',
    categories: req.categories || ['pricing', 'software_version', 'leadership'],
  };

  let response: Response;
  try {
    response = await fetchWithColdStartRetry(`${API_BASE}/v1/verifications`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  } catch (netErr: any) {
    throw new Error(
      `Network connection failed. The verification backend may be waking up from sleep on Render free tier. Details: ${netErr.message}`
    );
  }

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.code === 'BACKEND_COLD_START' || response.status === 503) {
        throw new Error(
          errJson.message || 'Verification service on Render is waking up from idle sleep (~30-50s). Please retry in a moment.'
        );
      }
      errorDetail = errJson.message || errJson.detail || JSON.stringify(errJson);
    } catch (parseErr: any) {
      if (parseErr.message && parseErr.message.includes('waking up')) throw parseErr;
      // ignore JSON parse error
    }
    throw new Error(`Verification request failed: ${errorDetail}`);
  }

  return response.json();
}

/**
 * Retrieves a historical verification record by its unique verification ID.
 */
export async function getVerification(verificationId: string): Promise<VerificationResponse> {
  const trimmed = verificationId.trim();
  const response = await fetch(`${API_BASE}/v1/verifications/${encodeURIComponent(trimmed)}`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Verification with ID "${trimmed}" was not found in the database.`);
    }
    throw new Error(`Failed to retrieve verification (${response.status} ${response.statusText})`);
  }

  return response.json();
}

/**
 * Checks verification service health (/health).
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`, {
    headers: { 'Accept': 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Service returned HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Checks database readiness (/health/ready).
 */
export async function checkHealthReady(): Promise<ReadyResponse> {
  const response = await fetch(`${API_BASE}/health/ready`, {
    headers: { 'Accept': 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Database check returned HTTP ${response.status}`);
  }
  return response.json();
}

