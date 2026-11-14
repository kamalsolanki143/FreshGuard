# FreshGuard — Free Hackathon Production Deployment Guide

## 1. Zero-Cost Free-Tier Architecture Overview

FreshGuard is structured for 100% free hosting across three modern cloud platforms with zero recurring monthly infrastructure costs:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLOUDFLARE PAGES (Frontend)                     │
│  - Repository: kamalsolanki143/FreshGuard (root: frontend)             │
│  - Global CDN static hosting + React Router SPA fallback (_redirects)   │
│  - Edge Function Reverse Proxy (frontend/functions/api/[[path]].ts)     │
│  - Injects VERIFICATION_SERVICE_API_KEY server-side (never in bundle) │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                 HTTPS /api/* (Zero CORS, Secure Proxy)
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    RENDER FREE WEB SERVICE (Backend API)               │
│  - Repository: kamalsolanki143/FreshGuard (root: verification-service) │
│  - Python 3.11 FastAPI + Uvicorn (:PORT)                               │
│  - Liveness: /health | Readiness: /health/ready                        │
│  - Cold-start resilient (handles 30-50s free tier spin-up)             │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                   DATABASE_URL (SSL Required, Pooled)
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   NEON FREE SERVERLESS POSTGRESQL (DB)                 │
│  - Persistent SQL history & cache storage (scale-to-zero)              │
│  - Reconnect resilience with pool_pre_ping & pool_recycle              │
│  - Replaces ephemeral container SQLite on Render free tier             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Step 1: Database Setup (Neon Free PostgreSQL)

Render free web services operate with ephemeral disks that reset whenever the service sleeps or restarts. Connecting a free Neon PostgreSQL database gives durable persistence for verification records, claims, and audit history.

1. Create a free account at [neon.tech](https://neon.tech).
2. Create a new project (e.g., `freshguard-production`) in AWS `us-east-2` or `eu-central-1`.
3. In the Neon Console Dashboard, locate your **Connection String**.
4. Select the connection string format:
   ```
   postgres://username:password@ep-cold-pond-12345.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   *(FreshGuard automatically normalizes `postgres://` or `postgresql://` into `postgresql+asyncpg://` with connection pooling enabled).*
5. Run the schema migration locally or through Render build:
   ```bash
   cd verification-service
   python -m app.database.migrate "postgresql+asyncpg://username:password@ep-cold-pond-12345.us-east-2.aws.neon.tech/neondb?sslmode=require"
   ```
   All 4 tables (`verification_records`, `claim_records`, `evidence_records`, `freshness_policy_records`) will be verified and initialized.

---

## 3. Step 2: Backend API Setup (Render Free Web Service)

Deploy the Python FastAPI verification engine on Render's free tier.

### Option A: One-Click Blueprint (`render.yaml`)
1. In the Render Dashboard ([dashboard.render.com](https://dashboard.render.com)), click **New +** -> **Blueprint**.
2. Connect repository: `kamalsolanki143/FreshGuard`.
3. Select branch: `main`.
4. Render detects `render.yaml` automatically.
5. Provide secrets when prompted:
   - `DATABASE_URL`: Your Neon PostgreSQL connection string (or leave default for ephemeral SQLite).
   - `TAVILY_API_KEY`: Your Tavily search API key.
   - `VERIFICATION_SERVICE_API_KEY`: A 32-character hex secret (e.g. `openssl rand -hex 32`).

### Option B: Manual Web Service Setup
1. In the Render Dashboard, click **New +** -> **Web Service**.
2. Connect repository: `kamalsolanki143/FreshGuard` (branch: `main`).
3. Set the service properties:
   - **Name:** `freshguard-verification`
   - **Region:** Oregon (US West) or Ohio (US East)
   - **Root Directory:** `verification-service`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free ($0.00/mo)
4. Under **Advanced** -> **Health Check Path**, enter:
   ```
   /health/ready
   ```
5. Configure Environment Variables:
   | Key | Value | Purpose |
   | :--- | :--- | :--- |
   | `PYTHON_VERSION` | `3.11.9` | Pinned Python runtime |
   | `ENVIRONMENT` | `staging` or `production` | Enables security hardening |
   | `DEBUG` | `false` | Disables interactive debug handlers |
   | `LOG_LEVEL` | `INFO` | Production logging |
   | `CORS_ORIGINS` | `https://freshguard.pages.dev,http://localhost:3000,http://localhost:4173` | Allowed origins |
   | `DATABASE_URL` | `postgresql+asyncpg://...` (Neon) | Persistent database connection |
   | `API_AUTH_MODE` | `warn` (demo) or `enforce` | Controls X-API-Key requirement |
   | `VERIFICATION_SERVICE_API_KEY` | `<secret-key>` | Shared backend API secret |
   | `TAVILY_API_KEY` | `<tavily-key>` | External web search grounding |
   | `LLM_PROVIDER` | `mock` or `openai` or `gemini` | Verification evaluation model |

---

## 4. Step 3: Frontend Setup (Cloudflare Pages)

Deploy the React 18 / Vite SaaS application on Cloudflare Pages.

1. In the Cloudflare Dashboard ([dash.cloudflare.com](https://dash.cloudflare.com)), navigate to **Workers & Pages** -> **Create application** -> **Pages** -> **Connect to Git**.
2. Authorize GitHub and select `kamalsolanki143/FreshGuard`.
3. Set Build Settings:
   - **Framework preset:** `Vite`
   - **Build command:** `npm ci && npm run build`
   - **Build output directory:** `dist`
   - **Root directory:** `frontend`
4. Environment Variables (Cloudflare Pages Dashboard -> Settings -> Environment variables):
   | Key | Value | Type |
   | :--- | :--- | :--- |
   | `BACKEND_API_URL` | `https://freshguard-verification.onrender.com` | Plain text |
   | `VERIFICATION_SERVICE_API_KEY` | `<same-secret-as-render>` | **Secret (Encrypted)** |
5. Click **Save and Deploy**.
6. Cloudflare automatically compiles `frontend/functions/api/[[path]].ts` as an Edge Reverse Proxy and configures `_redirects` for React Router SPA routes.

---

## 5. Security & Secret Protection Architecture

- **Zero Secrets in Frontend Bundle:** The Vite build output (`dist/`) contains no API keys or database connection strings.
- **Strict Edge Proxy:** `functions/api/[[path]].ts` forwards only approved routes (`/health`, `/health/ready`, `/v1/verifications`, `/v1/verifications/:id`) and methods (`GET`, `POST`).
- **Body Size Caps:** Requests with bodies exceeding 1 MiB are rejected with `413 Payload Too Large`.
- **Server-Side Key Injection:** The Edge Function injects `X-API-Key` server-side, preventing public users from viewing or modifying credentials.

---

## 6. Cold-Start & Inactivity Management

Render's free tier spins down containers after 15 minutes of inactivity. FreshGuard handles this gracefully:
1. **Frontend status banner:** Displays *"Backend Standby / Sleep"* when the microservice is offline, without crashing the user interface.
2. **Cold-start detection:** The Cloudflare proxy intercepts 502/503/504 errors and returns `BACKEND_COLD_START`, informing the user that the service is waking up (~30-50s).
3. **Auto-retry:** The frontend API client automatically retries once after a brief pause when a cold start is detected.
4. **Judge Demo Mode:** Hackathon evaluators can immediately explore the complete dashboard, presets, history, and cache views without waiting for backend wake-up.
