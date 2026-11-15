# FreshGuard production deployment checklist

## Vercel (project root: `frontend`)

Set these server-side environment variables for Production and Preview as appropriate:

- `BACKEND_API_URL=https://freshguard-4srf.onrender.com`
- `VERIFICATION_SERVICE_API_KEY`: the same secret configured on Render.

Do not use a `VITE_` prefix for either secret. The Vercel serverless proxy injects the API key and keeps it out of browser JavaScript. Redeploy after changing environment variables.

## Render

Configure:

- `API_AUTH_MODE=enforce`
- `VERIFICATION_SERVICE_API_KEY`: same value as Vercel
- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_REQUESTS_PER_MINUTE=10`
- `LLM_PROVIDER=gemini`
- `GEMINI_API_KEY` and `GEMINI_MODEL=gemini-2.5-flash`
- `TAVILY_API_KEY`

The demo rate limiter uses in-process memory and is suitable only for a single Render instance. For multiple instances or durable abuse protection, move rate-limit state to Redis or an API gateway policy.

The default SQLite database on Render's ephemeral filesystem is not durable across instance replacement/redeploy. Use a persistent disk or managed PostgreSQL for durable verification history.

## Cloudflare WAF false positives

Do not disable the WAF globally. When a legitimate code/SQL example is blocked, inspect the Cloudflare Security Events entry and identify the exact managed rule ID. Add a narrowly scoped exception for that false-positive rule on the verification API POST path only (the public path may be `/v1/verifications` or the proxied `/api/v1/verifications`, depending on where Cloudflare sits). Keep authentication, request-size limits, and rate limiting enabled. Confirm the application still returns structured JSON for application-generated errors.

## Smoke checks after deployment

1. `GET /api/health` returns 200 JSON.
2. `GET /api/health/ready` returns 200 JSON with database readiness.
3. POST a harmless verification request through `/api/v1/verifications`; record its `verification_id`.
4. GET that ID through `/api/v1/verifications/{verification_id}` and confirm it returns the same record.
5. Confirm missing and incorrect API keys return 401 on direct backend requests.
6. Confirm `text/plain`, invalid categories, whitespace-only text, and `mode=async` return 415/422 rather than 500.
7. Confirm the 11th request from the same client within one minute returns 429 when rate limiting is enabled.
8. Check `/robots.txt`, `/sitemap.xml`, and an unknown URL (404).
