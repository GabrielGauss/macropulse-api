# External Integrations

**Analysis Date:** 2026-03-28

## APIs & External Services

**Macroeconomic Data:**
- FRED (Federal Reserve Economic Data)
  - SDK/Client: `fredapi>=0.5` package
  - Auth: `FRED_API_KEY` environment variable (required)
  - Endpoint: https://api.stlouisfed.org/fred/
  - Series ingested:
    - WALCL - Fed Total Assets
    - RRPONTSYD - Reverse Repo Outstanding
    - WTREGEN - Treasury General Account Balance
    - DGS10 - 10-Year Treasury Yield
    - DGS2 - 2-Year Treasury Yield
    - BAMLH0A0HYM2 - HY OAS Spread
  - Implementation: `data/ingestion/fred_client.py`
  - Features: 1-hour TTL in-process caching, exponential backoff retry (3 attempts max)
  - Called by: Daily pipeline via `services/scheduler.py`

**Market Data:**
- Yahoo Finance
  - SDK/Client: `yfinance>=0.2.36` package
  - Auth: None (public data)
  - Symbols pulled:
    - ^GSPC (S&P 500)
    - ^VIX (Volatility Index)
    - DX=F (Dollar Index Futures)
    - GC=F (Gold Futures)
    - CL=F (Crude Oil Futures)
    - BTC-USD (Bitcoin)
    - ETH-USD (Ethereum)
  - Implementation: `data/ingestion/market_client.py` with `yfinance.download()`
  - Lookback: 756 trading days (~3 years) via `data_lookback_days` config
  - Called by: Daily data pipeline

**AI Commentary:**
- Anthropic Claude API
  - SDK/Client: `anthropic>=0.40` package
  - Auth: `ANTHROPIC_API_KEY` environment variable (optional)
  - Model: `claude-sonnet-4-6`
  - Endpoint: `GET /v1/regime/commentary`
  - Implementation: `api/routes/commentary.py` lines 1-60+
  - Context sent to Claude:
    - Current regime probabilities (expansion, tightening, risk_off, recovery)
    - Regime history (past 7 days)
    - Recent liquidity trend
    - PCA factor loadings
  - Response cached by (regime_timestamp, regime_name) to avoid redundant API calls
  - System prompt: Senior macro strategist role with quantitative analysis instructions
  - Output: JSON with headline, narrative (2-3 paragraphs), key_signals, watch_for

## Data Storage

**Databases:**
- TimescaleDB (PostgreSQL 16)
  - Connection: `postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}`
  - Client: `psycopg2-binary>=2.9` (ThreadedConnectionPool, min=2 max=10 connections)
  - Pool managed by: `database/connection.py` with `get_sync_cursor()` context manager
  - URL configured via: `config/settings.py` properties `database_url` and `async_database_url`
  - Docker image: `timescale/timescaledb:latest-pg16`
  - Tables (from `database/schema.sql` and migrations in `database/migrations/`):
    - `users` - User accounts, subscription tiers (free/starter/pro), API keys
    - `pipeline_runs` - Pipeline execution metadata and status
    - `model_versions` - Model artifact registry and performance metrics
    - `macro_features` - Feature engineering results (hypertable with time-series compression)
    - `macro_factors` - PCA latent factors (hypertable)
    - `macro_regimes` - Regime classification with probabilities (hypertable)
    - `model_drift_metrics` - PCA explained variance, persistence, feature shifts
  - Auto-migrations: `_run_migrations()` in `api/main.py` runs all `.sql` files in `database/migrations/` on startup

**File Storage:**
- Local filesystem only
  - Model artifacts directory: `models/artifacts/` (joblib-serialized PCA + HMM models)
  - Persistence: Docker volume `model_artifacts` maps to container `/app/models/artifacts`
  - Model versioning: `DEFAULT_MODEL_VERSION` config (v1, v2, etc.)
  - Lifecycle: Trained in `services/` during pipeline, loaded in `models/inference.py`

**Caching:**
- In-process TTL cache
  - Location: `data/ingestion/fred_client.py` module-level `_series_cache` dict
  - TTL: 1 hour per series
  - Hit rate: Reduces redundant FRED API calls during pipeline retries or dev testing
  - Cleared on: Series-specific clear via `clear_fred_cache()` or global via `clear_all_fred_cache()`

## Authentication & Identity

**Auth Provider:**
- Custom header-based API key authentication
  - Implementation: `api/auth.py` (`require_api_key` dependency)
  - Header locations: `X-API-Key` header or `api_key` query parameter
  - Storage: Database `users` table (tier, created_at, last_used)
  - Dev mode: Empty `API_KEYS=[]` list disables auth enforcement (all requests pass)
  - Production mode: `API_KEYS` list checked via DB lookup or hardcoded list
  - Master key: `OWNER_API_KEY` (tier="owner", bypasses all rate limits and tier gates)
  - Owner email: `OWNER_EMAIL` config (default: owner@macropulse.live) returned in responses
  - Tier system:
    - `free` - 50 requests/day, basic endpoints only
    - `starter` - 500 requests/day ($49/mo via Paddle)
    - `pro` - Unlimited requests, all endpoints ($199/mo via Paddle)
    - `owner` - Master key, no limits

## Payment & Billing

**Billing Provider:**
- Paddle Billing (subscription management)
  - API Key: `PADDLE_API_KEY` (Bearer token in Authorization header)
  - Webhook Secret: `PADDLE_WEBHOOK_SECRET` (HMAC-SHA256 signature verification)
  - Environment: `PADDLE_ENVIRONMENT` (sandbox or production)
  - API Base URLs:
    - Sandbox: https://sandbox-api.paddle.com
    - Production: https://api.paddle.com
  - Endpoints:
    - `POST {base}/transactions` - Create checkout session (requires price_id, customer email)
    - `POST {base}/customers/{customer_id}/portal-sessions` - Generate customer portal URL
  - Implementation: `services/paddle.py` and `api/routes/billing.py`
  - Tiers and Pricing:
    - Starter: `PADDLE_STARTER_PRICE_ID` (pri_01...) = $49/month
    - Pro: `PADDLE_PRO_PRICE_ID` (pri_01...) = $199/month
  - Product IDs (used for webhook event filtering):
    - Starter product: `pro_01kkhzzr1c1f1fta693c6p6nzv`
    - Pro product: `pro_01kkj01cx467jt6v4c5g2hakrd`
  - Webhook receiver: `POST /v1/billing/webhook` (no auth, signature verified in `services/paddle.py`)
  - Webhook events handled:
    - `subscription.activated` - User upgraded, update DB tier to starter/pro
    - `subscription.updated` - Tier change, update DB
    - `subscription.canceled` - Downgrade to free tier
    - `subscription.paused` - Downgrade to free tier
  - Custom data flow: User ID and tier embedded in checkout → webhook handler matches and updates user record
  - HTTP client: `httpx>=0.27` for async API calls (timeout: 15 seconds)

## Email & Notifications

**Transactional Email (Brevo):**
- API Key: `BREVO_API_KEY` (xkeysib-... format from https://app.brevo.com)
- Sender override: `BREVO_SENDER_EMAIL` (optional, defaults to noreply@macropulse.live)
- Endpoint: https://api.brevo.com/v3/smtp/email
- Implementation: `services/email.py`
- Async HTTP: `urllib.request` (synchronous POST, fire-and-forget error handling)
- Sends:
  - Welcome email on user signup
  - API key delivery email
  - Newsletter subscription confirmation
  - Regime change alerts (optional)
- Feature: Fails silently if BREVO_API_KEY not configured (dev mode fallback)

**SMTP Email Alerts (Operator):**
- Configuration:
  - Host: `SMTP_HOST`
  - Port: `SMTP_PORT` (default: 587)
  - User: `SMTP_USER`
  - Password: `SMTP_PASSWORD`
  - Recipients: `ALERT_RECIPIENTS` (list of emails)
- Implementation: `services/alerts.py`
- Triggers:
  - Pipeline execution failures
  - Regime state transitions
  - Model drift threshold breaches (variance, persistence, feature shift)
  - Custom webhook alerts via `WEBHOOK_URL`
- HTTP client: `httpx` for async sends

**Discord Webhooks:**
- Generic: `WEBHOOK_URL` (Slack/Discord/Teams compatible)
  - Triggers: Operator-level alerts (pipeline status, errors)
- Discord-specific: `DISCORD_WEBHOOK_URL`
  - Triggers: Daily macro signal posts to Discord channel
  - Format: Human-friendly regime narrative with emoji reactions
- HTTP client: `httpx` (async POST)

**X (Twitter) Integration:**
- Configuration present but NOT yet integrated:
  - `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
  - Placeholder in settings (lines 115-119 of `config/settings.py`)
  - Service file created but inactive: `services/twitter.py`

## Monitoring & Observability

**Error Tracking:**
- Not detected - no Sentry, Rollbar, DataDog, or similar integration

**Logs:**
- stdout logging to console (Docker captures via container logs)
- Format: `%(asctime)s | %(levelname)-8s | %(name)s | %(message)s`
- Level: Controlled by `LOG_LEVEL` environment variable (default: INFO)
- Logger: Standard Python `logging` module (all modules instantiate `logger = logging.getLogger(__name__)`)
- Production logs can be piped to external systems via Docker log drivers

**Model Drift Monitoring:**
- Metrics stored in `model_drift_metrics` table
- Tracked: PCA explained variance change, regime persistence ratios, feature mean/std shifts
- Thresholds (configurable):
  - `pipeline_drift_variance_warn` - Variance drop fraction (default: 0.10)
  - `pipeline_drift_persistence_warn` - Persistence ratio (default: 0.97)
  - `pipeline_drift_feature_shift_warn` - Feature z-score shift (default: 1.5)
- Triggers: Retraining workflow when exceeded

## CI/CD & Deployment

**Hosting:**
- Self-hosted Docker Compose on Linux server
- Services:
  - `timescaledb` - PostgreSQL 16 + TimescaleDB (port 5432 internal)
  - `api` - FastAPI + Uvicorn (port 8000 internal, exposed to Nginx)
  - `nginx` - Alpine reverse proxy, SSL termination (ports 80/443 external)
  - `certbot` - Let's Encrypt cert renewal (runs in loop, 12-hour sleep between checks)
- Health checks: DB health (`pg_isready`), API health (`/health` endpoint)

**CI Pipeline:**
- Not detected - no GitHub Actions, GitLab CI, Jenkins, or CircleCI integration

**Deployment:**
- Docker image: Built via `Dockerfile` (multi-stage)
  - Stage 1: Node 20 Alpine, builds React frontend to `dist/`
  - Stage 2: Python 3.12 slim, installs requirements.txt, copies built frontend
- Docker Compose: Orchestrates all services with health checks and depends_on
- SSL/TLS: Certbot auto-renews Let's Encrypt certificates to `certbot_conf` volume
- Nginx: Reverse proxy handles external traffic, forwards to API container on port 8000
- Volume management: `model_artifacts`, `timescale_data`, `certbot_www`, `certbot_conf`

## Environment Configuration

**Required env vars:**
- `FRED_API_KEY` - FRED data ingestion (critical for pipeline)
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - PostgreSQL connection
- `PADDLE_API_KEY`, `PADDLE_WEBHOOK_SECRET` - Billing integration
- `PADDLE_STARTER_PRICE_ID`, `PADDLE_PRO_PRICE_ID` - Paddle price IDs (pri_01...)
- `PADDLE_CLIENT_TOKEN` - Paddle dashboard authentication

**Optional env vars:**
- `ANTHROPIC_API_KEY` - Claude API for commentary (gracefully skipped if missing)
- `API_KEYS` - Comma-separated list of valid API keys (empty list = dev mode, no auth)
- `OWNER_API_KEY` - Master key (tier="owner", all features, no rate limit)
- `OWNER_EMAIL` - Email returned in owner-key API responses (default: owner@macropulse.live)
- `WEBHOOK_URL` - Generic webhook for operator alerts
- `DISCORD_WEBHOOK_URL` - Discord channel webhook for daily signals
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_RECIPIENTS` - Email alerts
- `BREVO_API_KEY` - Brevo transactional email (optional)
- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` - X (Twitter) integration (not yet used)
- `PIPELINE_CRON_HOUR`, `PIPELINE_CRON_MINUTE` - Scheduler timing (default: 18:30 UTC)
- `MTA_SIGNING_KEY_HEX` - Ed25519 private key (hex) for regime signature verification (IRL Engine integration)
- `CORS_ORIGINS` - List of allowed CORS origins (default: localhost:3000, localhost:5173)
- `LOG_LEVEL` - Logging verbosity (default: INFO)

**Secrets location:**
- `.env` file (Git-ignored via `.gitignore`)
- Do NOT commit `.env` to Git
- Reference: `.env.example` (safe to commit, shows all available variables with documentation)

## Webhooks & Callbacks

**Incoming Webhooks:**
- `POST /v1/billing/webhook` - Paddle subscription events
  - Implementation: `api/routes/billing.py`
  - Signature verification: HMAC-SHA256 in `Paddle-Signature` header (ts=...; h1=...)
  - Verification: `services/paddle.py` `verify_webhook()` function
  - Replay protection: 5-minute timestamp window (prevents old webhooks from being replayed)
  - Payload format: JSON event object with event_type, data
  - Matched user: Via custom_data.user_id (preferred) or paddle_customer_id lookup
  - Actions:
    - `subscription.activated` → `upgrade_user_tier(user_id, tier)`
    - `subscription.updated` → `upgrade_user_tier(user_id, tier)`
    - `subscription.canceled` → `upgrade_user_tier(user_id, "free")`
    - `subscription.paused` → `upgrade_user_tier(user_id, "free")`

**Outgoing Webhooks/Notifications:**
- Generic webhook: `WEBHOOK_URL` (Slack/Discord/Teams compatible)
  - Implementation: `services/alerts.py`
  - Triggers: Pipeline failures, regime transitions, drift alerts
  - Payload: JSON with status, message, timestamp
- Discord webhook: `DISCORD_WEBHOOK_URL`
  - Content: Daily regime signals posted as formatted message
  - Timing: Post-pipeline completion (18:30 UTC daily)
- Email (SMTP): `ALERT_RECIPIENTS`
  - Alerts: Pipeline failures, model drift warnings, regime changes
  - Sender: Configured via SMTP_USER
- X (Twitter): Not yet integrated

## Real-Time Streaming

**WebSocket:**
- Endpoint: `GET /ws/regime`
- Implementation: `api/routes/websocket.py`
- Protocol: WebSocket (RFC 6455 via `websockets>=12.0` package)
- Connection flow:
  1. Client connects to `/ws/regime`
  2. Server accepts and stores connection in in-memory registry
  3. Pipeline completes daily → new regime signal published
  4. All connected clients receive regime update immediately
- Message format: JSON regime object with timestamp, regime, probabilities, confidence
- Auto-reconnect: Client-side exponential backoff (frontend handles)
- Features: Broadcast to all clients when regime changes, maintains connection pool

---

*Integration audit: 2026-03-28*
