declare const process: {
  env: Record<string, string | undefined>;
};

type VercelRequest = AsyncIterable<Uint8Array> & {
  method?: string;
  url?: string;
  headers: Record<string, string | string[] | undefined>;
  body?: any;
  query?: Record<string, string | string[] | undefined>;
};

type VercelResponse = {
  status: (code: number) => VercelResponse;
  setHeader: (name: string, value: string) => void;
  send: (body: string | Uint8Array) => void;
  end: () => void;
};

const MAX_BODY_BYTES = 1_048_576;
const BACKEND = (process.env.BACKEND_API_URL || "https://freshguard-4srf.onrender.com").replace(/\/+$/, "");

function allowedRoute(path: string, method: string): boolean {
  if (method === "GET" && (path === "/health" || path === "/health/ready")) return true;
  if (method === "POST" && path === "/v1/verifications") return true;
  if (method === "GET" && /^\/v1\/verifications\/[^/]+$/.test(path)) {
    const id = path.slice("/v1/verifications/".length);
    try {
      const decoded = decodeURIComponent(id);
      return decoded.length > 0 && decoded !== "." && decoded !== ".." && !decoded.includes("/") && !decoded.includes("\\");
    } catch {
      return false;
    }
  }
  return false;
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const method = (req.method || "GET").toUpperCase();
  const url = new URL(req.url || "/", "https://vercel.invalid");
  let path = url.pathname.replace(/^\/api(?=\/)/, "");

  if (path === "/[...path]" || path === "" || path === "/") {
    const qPath = req.query?.path;
    if (Array.isArray(qPath)) path = "/" + qPath.join("/");
    else if (typeof qPath === "string") path = "/" + qPath;
  }

  const matchedPath = req.headers["x-matched-path"] as string | undefined;
  if (matchedPath?.startsWith("/api/")) {
    path = matchedPath.replace(/^\/api(?=\/)/, "");
  }

  if (!allowedRoute(path, method)) {
    res.setHeader("Content-Type", "application/json");
    res.status(404).send(JSON.stringify({
      code: "NOT_FOUND",
      message: `API route '${path}' with method ${method} not found.`,
      path,
      retryable: false,
    }));
    return;
  }

  const headers: Record<string, string> = { Accept: "application/json" };
  const contentType = req.headers["content-type"];
  if (typeof contentType === "string") headers["Content-Type"] = contentType;
  const requestId = (req.headers["x-request-id"] as string) || `proxy-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
  headers["X-Request-ID"] = requestId;

  const apiKey = process.env.VERIFICATION_SERVICE_API_KEY;
  if (apiKey) headers["X-API-Key"] = apiKey;

  const forwardedFor = req.headers["x-forwarded-for"];
  if (typeof forwardedFor === "string" && forwardedFor.trim()) {
    headers["X-FG-Client-IP"] = forwardedFor.split(",").pop()!.trim();
  }

  let bodyData: BodyInit | undefined;
  if (method !== "GET" && method !== "HEAD") {
    if (req.body !== undefined && req.body !== null) {
      if (typeof req.body === "string") bodyData = req.body;
      else if (typeof req.body === "object") bodyData = JSON.stringify(req.body);
      if (!headers["Content-Type"]) headers["Content-Type"] = "application/json";
    } else {
      try {
        const chunks: Uint8Array[] = [];
        let total = 0;
        for await (const chunk of req) {
          total += chunk.byteLength;
          if (total > MAX_BODY_BYTES) {
            res.setHeader("Content-Type", "application/json");
            res.status(413).send(JSON.stringify({
              code: "REQUEST_TOO_LARGE",
              message: "Request body exceeds 1 MiB.",
              request_id: requestId,
              retryable: false,
            }));
            return;
          }
          chunks.push(chunk);
        }
        if (total > 0) {
          const combined = new Uint8Array(total);
          let offset = 0;
          for (const chunk of chunks) {
            combined.set(chunk, offset);
            offset += chunk.byteLength;
          }
          bodyData = combined as BodyInit;
        }
      } catch {
        // The platform may have already consumed the request stream.
      }
    }
  }

  try {
    const upstreamUrl = `${BACKEND}${path}${url.search}`;
    const upstream = await fetch(upstreamUrl, {
      method,
      headers,
      body: bodyData,
      signal: AbortSignal.timeout(45_000),
    });
    const responseText = await upstream.text();
    res.status(upstream.status);
    res.setHeader("Content-Type", upstream.headers.get("content-type") || "application/json");
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("X-Request-ID", requestId);
    res.send(responseText);
  } catch (fetchErr: any) {
    const isTimeout = fetchErr.name === "TimeoutError" || String(fetchErr.message || "").toLowerCase().includes("timeout");
    const statusCode = isTimeout ? 504 : 502;
    res.setHeader("Content-Type", "application/json");
    res.setHeader("X-Request-ID", requestId);
    res.status(statusCode).send(JSON.stringify({
      code: isTimeout ? "GATEWAY_TIMEOUT" : "BACKEND_UNAVAILABLE",
      message: isTimeout
        ? "Verification backend timed out. It may be waking up from idle sleep on Render free tier. Please retry."
        : "Verification backend is temporarily unreachable. Please retry in a few moments.",
      request_id: requestId,
      retryable: true,
      details: {
        error_name: fetchErr.name,
        error_message: fetchErr.message,
        backend_url: BACKEND,
        path,
      },
    }));
  }
}
