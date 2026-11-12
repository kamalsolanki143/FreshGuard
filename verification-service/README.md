# FreshGuard Verification Service

FastAPI-based real-time freshness and factual verification service for LLM-generated responses.

**Implementation Owner**: Ayush

---

## Capabilities

- **Factual Claim Extraction**: Extracts discrete, time-sensitive factual assertions from text across categories (`software_version`, `pricing`, `leadership`, `product_availability`, `recent_events`, `statistics`).
- **Real-Time Evidence Retrieval**: Bounded, concurrent web search using the Tavily Search API.
- **Deterministic & Semantic Verification**: Fast-path SemVer comparisons for software releases combined with model-driven verdict assessments.
- **Freshness Policy Enforcement**: Dynamic TTL calculation and staleness detection.
- **Semantic Caching & Idempotency**: Persistent cache with fingerprinting and fast-path duplicate `request_id` resolution.
- **Contract Compatibility**: Conforms to `shared/schemas/verification_api.json` and the Bifrost Go Gateway plugin.

---

## Supported LLM Providers

Configured via the `LLM_PROVIDER` environment variable:

1. **`mock`** *(Default)*:
   - Zero external credentials required.
   - Deterministic canned responses for local development, integration, and contract testing.
2. **`gemini`**:
   - Google Gemini Developer API using the official `google-genai` Python SDK.
   - Default model: `gemini-2.5-flash` (free tier eligible: 15 RPM, 1M TPM, 1,500 RPD in Google AI Studio).
   - Asynchronous structured outputs validated against Pydantic schemas.
   - Environment variables: `GEMINI_API_KEY`, `GEMINI_MODEL`.
3. **`openai`**:
   - OpenAI or OpenAI-compatible inference endpoints via asynchronous HTTPX.
   - Default model: `gpt-4o-mini`.
   - Environment variables: `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`.

---

## Configuration

Copy `.env.example` to `.env` and configure appropriate variables:

```bash
# LLM Provider Selection (mock, gemini, openai)
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash

# Search Configuration
TAVILY_API_KEY=tvly-...

# Server & Database
ENVIRONMENT=development
PORT=8000
DATABASE_URL=sqlite+aiosqlite:///./freshguard.db

# Authentication (see section below)
API_AUTH_MODE=disabled
VERIFICATION_SERVICE_API_KEY=
```

---

## Authentication

Verification endpoints (`POST /v1/verifications`, `GET /v1/verifications/{id}`) are
protected by an `X-API-Key` header. Health endpoints (`/health`, `/health/ready`)
are always public.

### Modes

Configured via `API_AUTH_MODE`:

| Mode | Behaviour | Permitted Environments |
|---|---|---|
| `disabled` | No authentication required. | `development`, `test` |
| `warn` | Missing/invalid key is logged, request allowed. | `staging`, `development`, `test` |
| `enforce` | Valid `X-API-Key` required; invalid requests → HTTP 401. | `production`, `staging`, `development`, `test` |

### Environment Enforcement Matrix

Authentication requirements are strictly enforced at service startup based on `ENVIRONMENT`:

- **Production (`ENVIRONMENT=production` / `prod`)**:
  - `API_AUTH_MODE` **MUST** be set to `enforce`.
  - `VERIFICATION_SERVICE_API_KEY` **MUST** be non-empty.
  - Startup fails immediately with `ConfigurationError` if `API_AUTH_MODE` is `disabled` or `warn`, or if the key is missing/empty. Never silently downgrades.
- **Staging (`ENVIRONMENT=staging`)**:
  - `API_AUTH_MODE` must be `warn` or `enforce`.
  - Startup fails if set to `disabled`.
  - If `enforce` is selected, `VERIFICATION_SERVICE_API_KEY` must be non-empty.
- **Development & Testing (`ENVIRONMENT=development` / `test`)**:
  - All modes permitted (`disabled`, `warn`, `enforce`).
  - If `enforce` is selected, `VERIFICATION_SERVICE_API_KEY` must be non-empty.

### Required Request Header

```
X-API-Key: <your-secret-key>
```

### Local Development Setup

```bash
# No authentication required:
ENVIRONMENT=development
API_AUTH_MODE=disabled
VERIFICATION_SERVICE_API_KEY=
```

### Staging Setup (Rollout)

```bash
# Warn mode allows unauthenticated/migrating callers during rollout:
ENVIRONMENT=staging
API_AUTH_MODE=warn
VERIFICATION_SERVICE_API_KEY=
```

### Production Configuration

```bash
# Generate a strong key (do not commit to source control):
# openssl rand -hex 32

ENVIRONMENT=production
API_AUTH_MODE=enforce
VERIFICATION_SERVICE_API_KEY=<your-generated-secret-here>
```

Set `VERIFICATION_SERVICE_API_KEY` as a **Render Secret Environment Variable**,
never as a plain-text value in `render.yaml`.

The service will refuse to start if `ENVIRONMENT=production` and `API_AUTH_MODE` is not `enforce`
or `VERIFICATION_SERVICE_API_KEY` is missing.

### Integration (Go Client)

The Go Bifrost plugin client must be updated by Kamal to send:
```
X-API-Key: <same-secret>
```
Both sides must share the same key value. Coordinate key rotation out-of-band.

---

## Running the Service

```bash
# Start server using the dynamic runner
python run.py

# Or directly with Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Testing

```bash
# Run all unit and integration tests
pytest tests/ -v
```
