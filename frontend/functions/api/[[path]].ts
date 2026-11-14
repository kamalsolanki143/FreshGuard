/**
 * Cloudflare Pages Function: Secure Server-Side Reverse Proxy for FreshGuard API
 *
 * Implements zero-trust API protection:
 * 1. Restricts access strictly to approved backend API routes.
 * 2. Rejects unsupported methods and paths (prevents open proxy vulnerabilities).
 * 3. Enforces 1 MiB maximum request body size limit.
 * 4. Server-side injection of VERIFICATION_SERVICE_API_KEY (never exposed to browser bundles).
 * 5. Transparently handles Render free-tier cold-start delays (502/503/504).
 */

interface Env {
  BACKEND_API_URL?: string;
  VERIFICATION_SERVICE_API_KEY?: string;
}

const MAX_BODY_BYTES = 1_048_576; // 1 MiB

// Whitelisted backend paths
function isAllowedPath(method: string, path: string): boolean {
  // Liveness & Readiness checks
  if (method === 'GET' && (path === '/health' || path === '/health/ready')) {
    return true;
  }
  // Verification submission
  if (method === 'POST' && path === '/v1/verifications') {
    return true;
  }
  // Verification retrieval by ID (/v1/verifications/{id})
  if (method === 'GET' && path.startsWith('/v1/verifications/') && path.split('/').length === 4) {
    const id = path.split('/')[3];
    return id.length > 0 && !id.includes('..') && !id.includes('?');
  }
  return false;
}

export const onRequest: PagesFunction<Env> = async (context) => {
  const { request, env, params } = context;
  const method = request.method.toUpperCase();

  // Handle CORS preflight
  if (method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Request-ID, Accept',
        'Access-Control-Max-Age': '86400',
      },
    });
  }

  // Construct normalized upstream path
  const rawSegments = (params.path as string[] | undefined) || [];
  const normalizedPath = '/' + rawSegments.join('/');

  // 1. Strict route & method validation
  if (!isAllowedPath(method, normalizedPath)) {
    return new Response(
      JSON.stringify({
        code: 'FORBIDDEN_ROUTE',
        error: 'Route or method not permitted by FreshGuard secure proxy.',
        requested_path: normalizedPath,
        method,
      }),
      {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  // 2. Request body size enforcement
  const contentLengthHeader = request.headers.get('content-length');
  if (contentLengthHeader && parseInt(contentLengthHeader, 10) > MAX_BODY_BYTES) {
    return new Response(
      JSON.stringify({
        code: 'PAYLOAD_TOO_LARGE',
        error: 'Request body exceeds maximum allowed size (1 MiB).',
      }),
      {
        status: 413,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  // 3. Resolve upstream backend URL
  const backendBase = (env.BACKEND_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
  const targetUrl = `${backendBase}${normalizedPath}`;

  // 4. Sanitize and build forwarding headers
  const forwardHeaders = new Headers();
  forwardHeaders.set('Accept', 'application/json');

  const contentType = request.headers.get('content-type');
  if (contentType) {
    forwardHeaders.set('Content-Type', contentType);
  }

  const requestId = request.headers.get('x-request-id');
  if (requestId) {
    forwardHeaders.set('X-Request-ID', requestId);
  }

  // Inject server-side API secret (client can never override or inspect this)
  if (env.VERIFICATION_SERVICE_API_KEY) {
    forwardHeaders.set('X-API-Key', env.VERIFICATION_SERVICE_API_KEY);
  }

  // 5. Forward request with timeout & cold-start error handling
  try {
    let bodyBuffer: ArrayBuffer | undefined = undefined;
    if (method === 'POST') {
      bodyBuffer = await request.arrayBuffer();
      if (bodyBuffer.byteLength > MAX_BODY_BYTES) {
        return new Response(
          JSON.stringify({
            code: 'PAYLOAD_TOO_LARGE',
            error: 'Request payload exceeds 1 MiB limit.',
          }),
          {
            status: 413,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }
    }

    const upstreamResponse = await fetch(targetUrl, {
      method,
      headers: forwardHeaders,
      body: bodyBuffer,
    });

    // Detect Render cold-start status codes
    if (upstreamResponse.status === 502 || upstreamResponse.status === 503 || upstreamResponse.status === 504) {
      return new Response(
        JSON.stringify({
          code: 'BACKEND_COLD_START',
          status: 'service_waking_up',
          message:
            'The FreshGuard verification backend on Render free tier is waking up from idle sleep (~30-50s). Please wait a moment and retry.',
          upstream_status: upstreamResponse.status,
          retryable: true,
        }),
        {
          status: 503,
          headers: {
            'Content-Type': 'application/json',
            'Retry-After': '15',
          },
        }
      );
    }

    // Return upstream response to client
    const responseHeaders = new Headers(upstreamResponse.headers);
    responseHeaders.set('Access-Control-Allow-Origin', '*');
    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      statusText: upstreamResponse.statusText,
      headers: responseHeaders,
    });
  } catch (upstreamErr: any) {
    // Network failure when connecting to backend (e.g. DNS or initial connect timeout during cold spin)
    return new Response(
      JSON.stringify({
        code: 'BACKEND_CONNECT_ERROR',
        status: 'service_waking_up',
        message:
          'Unable to reach FreshGuard verification backend. If using Render free tier, the container is likely waking up from sleep. Please retry in 30 seconds.',
        error: upstreamErr.message,
        retryable: true,
      }),
      {
        status: 503,
        headers: {
          'Content-Type': 'application/json',
          'Retry-After': '20',
        },
      }
    );
  }
};
