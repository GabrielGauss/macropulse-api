# Architecture

**Analysis Date:** 2026-03-28

## Pattern Overview

**Overall:** Layered monolithic system with clear separation between API backend, frontend SPA, and ML inference pipeline.

**Key Characteristics:**
- FastAPI REST API + WebSocket server with PostgreSQL persistence
- React 18 SPA frontend with Recharts visualization and Tailwind CSS
- Scheduled daily macro regime pipeline (APScheduler + scikit-learn models)
- Frozen ML model artifacts for PCA/HMM inference
- Tier-based API rate limiting and feature gating

## Layers

**API Route Layer:**
- Purpose: HTTP request/response handling for regime signals, analysis, backtest, billing, webhooks
- Location: `api/routes/`
- Contains: 14 route modules (regime, analysis, backtest, billing, commentary, dashboard, forecast, performance, model, pipeline, public, signals, webhook, websocket)
- Depends on: Auth system, rate limiting, business logic services
- Used by: Frontend SPA, external IRL Engine integrations, public API consumers

**Business Logic / Services Layer:**
- Purpose: Domain-specific computations (ML inference, drift detection, alerts, billing webhooks, data sync)
- Location: `services/`
- Contains: 20 service modules (orchestrator, inference, scheduler, alerts, drift_monitor, email, paddle, backtest, performance, etc.)
- Depends on: ML models, database queries, external APIs (Paddle, Anthropic, FRED)
- Used by: Routes, pipeline, each other via dependency injection

**Data Pipeline Layer:**
- Purpose: Scheduled daily processing flow: ingest FRED/market data → feature engineering → validation → PCA/HMM inference → drift monitoring → alert/broadcast
- Location: `data/pipelines/daily_pipeline.py`
- Invocation: APScheduler cron job (18:30 UTC by default)
- Entry point: `run_daily_pipeline()` → orchestrates all steps, stores results to DB
- Returns: Regime probabilities, volatility state, drift metrics for next day

**Data Ingestion & Processing:**
- Purpose: Fetch external market/economic data, build ML-ready features
- Location: `data/ingestion/` (fred_client, market_client), `data/processing/` (feature_engineering)
- Consumed by: Daily pipeline, historical backfill

**ML Model Layer:**
- Purpose: Frozen scikit-learn models loaded at startup; perform latent regime detection via PCA + HMM
- Location: `models/` (pca_model, hmm_model, garch_model, regime_classifier)
- Semantics: Read-only (no retraining in API process); artifact files loaded from `models/artifacts/`
- Used by: Services (inference.py), daily pipeline

**Database & Persistence:**
- Purpose: Store API keys, user metadata, regime history, features, drift metrics, pipeline logs
- Location: `database/connection.py` (ThreadedConnectionPool), `database/queries.py`, `database/migrations/`
- Technology: PostgreSQL with psycopg2; 8 migration files establishing schemas
- Lifecycle: Initialized in API startup (lifespan), migrated on app boot

**Frontend View Layer:**
- Purpose: React SPA with lazy-loaded domain-specific views (Inflation, Growth, Rates, Commodities, FX, Crypto, Liquidity, Signals, Backtest, Performance, Account)
- Location: `frontend/src/views/`
- Rendered by: Main `App.jsx` dispatcher; views lazy-load via `React.lazy()`

**Frontend Component Layer:**
- Purpose: Reusable UI building blocks (charts, cards, gauges, modals, tables)
- Location: `frontend/src/components/`
- Technologies: Recharts (charting), Lucide icons, Tailwind CSS
- Patterns: Functional components, React hooks, CSS Grid/Flexbox layout

**Configuration & Initialization:**
- Purpose: Centralized typed settings from environment variables
- Location: `config/settings.py`
- Scope: Database credentials, API keys, model hyperparameters, pipeline thresholds, auth config
- Initialization: Loaded at app startup via pydantic-settings with LRU cache singleton

## Data Flow

**Daily Regime Signal Generation (scheduled pipeline):**

1. APScheduler fires cron job → `_run_pipeline_with_alert()` in scheduler
2. Pipeline fetches FRED series (WALCL, DGS10, DGS2, etc.) and market data (VIX, etc.)
3. Raw data validation (checks for missing/all-NaN critical series)
4. Feature engineering: combine FRED + market indicators → 20+ macro features
5. Feature validation (schema, bounds, NaN checks)
6. PCA transform: 20+ features → 4 latent factors (frozen model)
7. HMM inference: factors → 4 regime probabilities + best-state
8. Regime mapping: HMM state → {expansion, recovery, tightening, risk_off}
9. Store results to PostgreSQL (regimes table)
10. Drift detection: PCA variance change, regime persistence, feature mean-shift
11. Alert if drift detected via email/Slack webhook
12. Broadcast via WebSocket to connected frontend clients
13. Log pipeline success/failure to database

**API Request Flow (synchronous):**

1. HTTP request arrives with optional `X-MacroPulse-Key` header
2. RateLimitMiddleware checks: path exemption, auth key validity, daily quota, IP lock
3. If authenticated: `require_api_key()` dependency validates key hash against DB, returns user tier
4. Route handler checks tier gating (e.g., `require_paid` blocks free tier)
5. Business logic executes (fetch from DB, compute, format response)
6. Response serialized via Pydantic models
7. Rate limit headers added (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
8. Response returned

**Frontend Data Synchronization:**

1. Page load: `useFetch` hook calls `api.getCurrentRegime()` → `/v1/regime/current`
2. WebSocket connection opens: `useRegimeSocket()` subscribes to real-time regime updates
3. User navigates to view (e.g., BacktestView): lazy-loaded, calls domain-specific API endpoints
4. Charts rendered with Recharts from fetched data
5. Error boundary catches failures, displays fallback UI

**Authentication Flow:**

1. New user: `register()` endpoint → creates user record, sends OTP via Brevo email
2. User submits OTP: `verify()` → marks email verified, generates API key (stored as SHA-256 hash)
3. Key stored in localStorage on frontend
4. Subsequent requests: header `X-MacroPulse-Key: mp_<token>` → hashed and looked up in database

**Billing Webhook Flow (Paddle):**

1. Paddle payment event → POST to `/v1/webhook/paddle` with signed payload
2. Webhook handler verifies signature, parses subscription tier
3. Updates user record in database (tier, subscription_id, expires_at)
4. On next API request, `require_paid()` checks DB tier, grants/denies access

## Key Abstractions

**RegimeResponse (API Contract):**
- Purpose: Canonical response format for regime signals
- Examples: `api/routes/regime.py`, `api/schemas/responses.py`
- Fields: timestamp, macro_regime, risk_score, probabilities (4 regimes), volatility_state, signature
- Signature: Ed25519 signed via `mta_signer.py` for IRL Engine verification

**PipelineRun (Audit Trail):**
- Purpose: Track each daily pipeline execution (status, data lag, duration, errors)
- Storage: `pipeline_runs` table
- Used by: Status endpoint, debugging, alerting

**FeatureValidationReport:**
- Purpose: Capture data quality issues (missing cols, out-of-bounds, NaN)
- Pattern: `passed` boolean + `errors` list
- Used by: `validate_raw_fred()`, `validate_features()` in `services/validation.py`

**DriftMetrics:**
- Purpose: Quantify ML model stability changes (PCA variance shift, regime persistence, feature mean-shift)
- Computed by: `drift_monitor.py` service
- Thresholds: Configurable via settings (PIPELINE_DRIFT_VARIANCE_WARN, PIPELINE_DRIFT_PERSISTENCE_WARN, etc.)
- Action: Triggers alert if any metric crosses threshold

**API Key Record (Database Row):**
- Purpose: Store API key metadata for billing, usage tracking, and feature access
- Fields: key_hash (SHA-256), user_id, email, tier, daily_requests, usage_date, created_at, last_used, ip_lock_address, ip_lock_expires
- Tier Logic: Free (50 req/day) → Starter (500 req/day) → Pro (unlimited)

## Entry Points

**API Startup:**
- Location: `api/main.py`
- Triggers: `uvicorn api.main:app --reload` or container boot
- Responsibilities:
  - Lifespan context manager runs migrations, starts scheduler, inits signer
  - Mounts all route routers (15 routers)
  - Attaches middleware (CORS, rate limiting)
  - Mounts static frontend if built

**Daily Pipeline Job:**
- Location: `data/pipelines/daily_pipeline.py` → `run_daily_pipeline()`
- Triggers: APScheduler cron (18:30 UTC by default)
- Responsibilities: Full end-to-end macro signal processing; stores results; fires alerts; broadcasts WebSocket

**Frontend SPA Entry:**
- Location: `frontend/src/main.jsx` → `App.jsx`
- Triggers: Browser navigation to `/`
- Responsibilities: Renders layout (Header, Sidebar, Route dispatcher); manages guide mode state; connects WebSocket

**WebSocket Real-time Stream:**
- Location: `api/routes/websocket.py`
- Triggers: Client opens `/ws/regime` connection
- Responsibilities: Broadcasts regime updates to all connected clients when pipeline completes

## Error Handling

**Strategy:** Multi-layered with graceful degradation.

**Pipeline Errors:**
- Critical data missing → Halt pipeline, alert owner, return stale signal
- Feature validation fails → Log error, alert owner, increment failure counter
- HMM convergence fails → Raise RuntimeError, pipeline halts, stale signal persists
- Drift detection fails → Log warning, don't block signal delivery

**API Errors:**
- Authentication failed (invalid key) → 403 Forbidden with detail message
- Rate limit exceeded → 429 Too Many Requests with reset timestamp
- Missing required tier → 403 Forbidden with upgrade URL
- DB unavailable → 503 Service Unavailable; health check marks "degraded"
- Route not found → 404 Not Found

**Database Errors:**
- Connection pool exhausted → Retry with exponential backoff; log warning
- Transaction rollback → Logged, request fails, user sees 500 or partial response
- Migration failure → App halts on startup; admin must fix and redeploy

**Frontend Errors:**
- ErrorBoundary catches React component crashes, displays fallback UI
- useFetch hook captures fetch failures, renders error message
- WebSocket disconnect → Reconnection attempted; chart shows stale data with warning

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging (stdlib) configured in `api/main.py`
- Level: INFO (configurable via LOG_LEVEL env var)
- Format: `timestamp | level | logger_name | message`
- Pipeline: Logs major steps, data lag, drift warnings, errors
- Middleware: Logs auth failures (invalid keys), rate limit violations

**Validation:**
- Data validation: `services/validation.py` checks raw FRED/market data for completeness, bounds, NaN
- Feature validation: Ensures engineered features have correct shape, no NaN/Inf, within historical bounds
- Schema validation: Pydantic models validate API request/response payloads; FastAPI auto-rejects invalid JSON
- Model validation: HMM convergence check; PCA variance threshold check before using factors

**Authentication:**
- API Key: SHA-256 hash stored in DB; verified on every request via `require_api_key()` dependency
- Owner Key: Special env var `OWNER_API_KEY` bypasses DB lookup, grants full access, no rate limit
- Dev Mode: If no keys configured and DB is empty, all requests allowed (localhost development)
- Tier Gating: `require_paid()` dependency blocks free-tier users from premium endpoints

**Rate Limiting:**
- Per-API-key daily quotas: Free=50, Starter=500, Pro=0 (unlimited)
- Per-IP for unauthenticated requests: 50 requests/day (in-memory counter)
- IP Locking: Free/Starter keys bound to single IP address; 15-minute timeout after inactivity
- Cache: Tier lookups cached per-day to reduce DB load; upgrades take effect next day
- Headers: Response includes X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

**Billing Integration:**
- Paddle webhooks: Signature verified, user tier/subscription updated in DB
- Feature Gating: Endpoints check `key_record["tier"]` before allowing access
- Portal: Unauthenticated link to Paddle customer portal for subscription management

---

*Architecture analysis: 2026-03-28*
