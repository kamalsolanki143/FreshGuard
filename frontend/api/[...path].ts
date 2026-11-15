declare const process: {
  env: Record<string, string | undefined>;
};

type VercelRequest = AsyncIterable<Uint8Array> & {
  method?: string;
  url?: string;
  headers: Record<string, string | string[] | undefined>;
};
type VercelResponse = {
  status: (code: number) => VercelResponse;
  setHeader: (name: string, value: string) => void;
  send: (body: string | Uint8Array) => void;
  end: () => void;
};

const MAX_BODY_BYTES = 1_048_576;
const BACKEND = (process.env.BACKEND_API_URL || "https://freshguard-verification.onrender.com").replace(/\/+$/, "");

function allowedRoute(path: string, method: string): boolean {
  if (method === "GET" && (path === "/health" || path === "/health/ready")) return true;
  if (method === "POST" && path === "/v1/verifications") return true;
  if (method === "GET" && /^\/v1\/verifications\/[^/]+$/.test(path)) {
    const id = path.slice("/v1/verifications/".length);
    try {
      const decoded = decodeURIComponent(id);
      return decoded.length > 0 && decoded !== "." && decoded !== ".." && !decoded.includes("/") && !decoded.includes("\\\\");
    } catch {
      return false;
    }
  }
  return false;
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const method = (req.method || "GET").toUpperCase();
  const url = new URL(req.url || "/", "https://vercel.invalid");
  const path = url.pathname.replace(/^\/api(?=\/)/, "");
  if (!allowedRoute(path, method)) {
    res.status(404).send(JSON.stringify({ code: "NOT_FOUND", message: "API route not found." }));
    return;
  }

  const headers: Record<string, string> = { Accept: "application/json" };
  const contentType = req.headers["content-type"];
  if (typeof contentType === "string") headers["Content-Type"] = contentType;
  const requestId = req.headers["x-request-id"];
  if (typeof requestId === "string") headers["X-Request-ID"] = requestId;

  const apiKey = process.env.VERIFICATION_SERVICE_API_KEY;
  if (!apiKey) {
    res.status(503).send(JSON.stringify({ code: "PROXY_MISCONFIGURED", message: "Backend API key is not configured on Vercel." }));
    return;
  }
  headers["X-API-Key"] = apiKey;
  const forwardedFor = req.headers["x-forwarded-for"];
  if (typeof forwardedFor === "string" && forwardedFor.trim()) {
    headers["X-FG-Client-IP"] = forwardedFor.split(",").pop()!.trim();
  }

  let body: Uint8Array | undefined;
  if (method !== "GET" && method !== "HEAD") {
    const chunks: Uint8Array[] = [];
    let total = 0;
    for await (const chunk of req) {
      total += chunk.byteLength;
      if (total > MAX_BODY_BYTES) {
        res.status(413).send(JSON.stringify({ code: "REQUEST_TOO_LARGE", message: "Request body exceeds 1 MiB." }));
        return;
      }
      chunks.push(chunk);
    }
    body = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      body.set(chunk, offset);
      offset += chunk.byteLength;
    }
  }

  try {
    const upstream = await fetch(`${BACKEND}${path}${url.search}`, {
      method,
      headers,
      body: body as BodyInit | undefined,
      signal: AbortSignal.timeout(60_000),
    });
    const text = await upstream.text();
    res.status(upstream.status);
    res.setHeader("Content-Type", upstream.headers.get("content-type") || "application/json");
    res.setHeader("Cache-Control", "no-store");
    res.send(text);
  } catch {
    res.status(502).send(JSON.stringify({
      code: "BACKEND_UNAVAILABLE",
      message: "Verification backend is temporarily unavailable. Please retry.",
    }));
  }
}
