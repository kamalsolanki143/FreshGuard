import { VerificationRequest, VerificationResponse, HealthResponse, ReadyResponse } from '../types';

// The Vite development proxy forwards /api to http://localhost:8000
const API_BASE = '/api';

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

  const response = await fetch(`${API_BASE}/v1/verifications`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.message || errJson.detail || JSON.stringify(errJson);
    } catch {
      // ignore
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
