# External Integrations

**Analysis Date:** 2026-03-18

## APIs & External Services

**Macroeconomic Data:**
- FRED (Federal Reserve Economic Data) - Pulls 6 core series
  - SDK/Client: `fredapi` package (Python wrapper around FRED REST API)
  - Auth: API key via `FRED_API_KEY` environment variable
  - Endpoint: https://api.stlouisfed.org/fred/
  - Series ingested: WALCL (Fed assets), RRPONTSYD (reverse repo), WTREGEN (Treasury account), DGS10/DGS2 (yield curve), BAMLH0A0HYM2 (HY spreads)
  - Implementation: `data/ingestion/fred_client.py`
  - Features: 1-hour TTL in-process caching, exponential backoff retry (3 attempts)

**Market Data:**
- Yahoo Finance - Daily market signals
  - SDK/Client: `yfinance` package
  - Auth: None (public data)
  - Symbols: ^GSPC (S&P 500), ^VIX, DX=F (Dollar Index), GC=F (Gold), CL=F (Oil), BTC-USD, ETH-USD
  - Implementation: `data/ingestion/market_client.py`

**AI Commentary:**
- Anthropic Claude API - Macro narrative generation
  - SDK/Client: `anthropic` package
  - Auth: API key via `ANTHROPIC_API_KEY` environment variable
  - Model: `claude-sonnet-4-6`
  - Endpoint: `GET /v1/regime/commentary`
  - Implementation: `api/routes/commentary.py`
  - Context: Current regime signal, history, liquidity, PCA factors sent to Claude for institutional-grade analysis

## Data Storage

**Databases:**
- TimescaleDB (PostgreSQL 16)
  - Connection: `postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}`
  - Client: `psycopg2-binary` (sync connection pooling)
  - Config: `database/connection.py`
  - Tables:
    - `pipeline_runs` - Pipeline execution metadata
    - `model_versions` - Model artifact registry
    - `macro_features` - Feature engineering results (hypertable)
    - `macro_factors` - PCA latent factors (hypertable)
    - `macro_regimes` - Regime classification with probabilities (hypertable)
    - `model_drift_metrics` - Monitoring statistics (hypertable)
    - `users` - User accounts and subscription tiers (created via migrations)
  - Schema initialization: `database/schema.sql` (auto-run on Docker startup)

**File Storage:**
- Local filesystem only
  - Model artifacts directory: `models/artifacts/` (joblib-serialized PCA and HMM)
  - Mounted as Docker volume `model_artifacts` for persistence
  - Models are versioned (v1, v2, etc.) via `DEFAULT_MODEL_VERSION` config

**Caching:**
- In-process TTL cache (FRED API results)
  - Location: `data/ingestion/fred_client.py` (_series_cache dict)
  - TTL: 1 hour
  - Purpose: Reduce FRED API calls during dev/multiple pipeline runs

## Authentication & Identity

**Auth Provider:**
- Custom header-based authentication
  - Implementation: `api/auth.py`
  - Header: `X-API-Key` or query param `api_key`
  - Dev mode: Empty `API_KEYS` list disables auth for local development
  - Production mode: List of valid keys in `API_KEYS` or database (managed via Paddle webhooks)
  - Special: `OWNER_API_KEY` for master-level access (all features, no rate limit)
  - Tier system: `free`, `starter`, `pro` stored per API key in database

## Payment & Billing

**Billing Provider:**
- Paddle - Subscription management
  - API Key: `PADDLE_API_KEY` (Bearer token)
  - Webhook Secret: `PADDLE_WEBHOOK_SECRET` (HMAC-SHA256 verification)
  - Environment: `PADDLE_ENVIRONMENT` (sandbox or production)
  - Endpoints:
    - Checkout creation: `{API_BASE}/transactions` (POST)
    - Customer portal: `{API_BASE}/customers/{id}/portal-sessions` (POST)
    - Webhook receiver: `POST /v1/billing/webhook` (no auth, signature verified)
  - Implementation: `services/paddle.py`, `api/routes/billing.py`
  - Tiers:
    - Starter ($49/mo): `PADDLE_STARTER_PRICE_ID` (pri_01...)
    - Pro ($199/mo): `PADDLE_PRO_PRICE_ID` (pri_01...)
  - Product IDs (hardcoded for webhook filtering):
    - Starter: `pro_01kkhzzr1c1f1fta693c6p6nzv`
    - Pro: `pro_01kkj01cx467jt6v4c5g2hakrd`
  - Webhook events handled:
    - `subscription.activated` / `subscription.updated` - Upgrade tier
    - `subscription.canceled` / `subscription.paused` - Downgrade to free
    - Custom data embedded during checkout: user_id, tier for reliable webhook matching

## Email & Notifications

**Email Alerts (SMTP):**
- Configuration:
  - Host: `SMTP_HOST`
  - Port: `SMTP_PORT` (587)
  - User: `SMTP_USER`
  - Password: `SMTP_PASSWORD`
  - Recipients: `ALERT_RECIPIENTS` (list)
- Implementation: `services/alerts.py`
- Triggers: Pipeline failures, regime transitions, drift threshold breaches

**Transactional Email (Brevo):**
- API Key: `BREVO_API_KEY` (xkeysib-... format)
- Sender override: `BREVO_SENDER_EMAIL`
- Purpose: Future user notifications (signup confirmation, password reset, etc.)

**Slack/Discord Webhooks:**
- Generic webhook URL: `WEBHOOK_URL` (operator alerts - pipeline status, errors)
- Discord-specific: `DISCORD_WEBHOOK_URL` (daily signal posts to Discord channel)
- Implementation: `services/alerts.py`
- HTTP client: `httpx` (async)

## Monitoring & Observability

**Error Tracking:**
- Not detected - no Sentry, DataDog, or similar integration

**Logs:**
- stdout logging to console (Docker captures via container logs)
- Format: `%(asctime)s | %(levelname)-8s | %(name)s | %(message)s`
- Level: Controlled by `LOG_LEVEL` environment variable (default: INFO)
- Loggers: Standard Python logging module

**Performance Monitoring:**
- Model drift metrics stored in `model_drift_metrics` table
  - Tracks: PCA explained variance, regime persistence, feature mean/std shifts
  - Triggers retraining when drift exceeds thresholds

## CI/CD & Deployment

**Hosting:**
- Docker Compose on Linux server (self-hosted)
- Nginx container handles SSL/TLS termination
- Certbot container auto-renews Let's Encrypt certificates

**CI Pipeline:**
- Not detected - no GitHub Actions, GitLab CI, or Jenkins

**Deployment:**
- Docker image builds via Dockerfile (multi-stage: frontend → API)
- Frontend built to `frontend/dist`, bundled into API image
- Production served via Nginx on ports 80/443
- Let's Encrypt automation via Certbot in Docker

## Environment Configuration

**Required env vars:**
- `FRED_API_KEY` - FRED data ingestion (required)
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - Database connection
- `PADDLE_API_KEY`, `PADDLE_WEBHOOK_SECRET` - Billing
- `PADDLE_STARTER_PRICE_ID`, `PADDLE_PRO_PRICE_ID` - Price IDs for tiers
- `PADDLE_CLIENT_TOKEN` - Paddle dashboard auth
- `ANTHROPIC_API_KEY` - Claude commentary (optional)

**Optional env vars:**
- `API_KEYS` - Comma-separated list of API keys (empty = dev mode, no auth)
- `OWNER_API_KEY` - Master key
- `WEBHOOK_URL` - Operator alerts
- `DISCORD_WEBHOOK_URL` - Discord daily signals
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_RECIPIENTS` - Email alerts
- `BREVO_API_KEY` - Transactional email
- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` - X (Twitter) integration (not yet integrated)

**Secrets location:**
- `.env` file (Git-ignored via `.gitignore`)
- Example: `.env.example` (safe to commit, shows all available vars)

## Webhooks & Callbacks

**Incoming Webhooks:**
- `POST /v1/billing/webhook` - Paddle subscription events
  - Signature: HMAC-SHA256 in `Paddle-Signature` header
  - Replay protection: 5-minute timestamp validation
  - Triggers: User tier upgrades/downgrades

**Outgoing Webhooks/Notifications:**
- Generic webhook: `WEBHOOK_URL` (Slack/Discord/Teams compatible)
  - Alerts: Pipeline failures, regime transitions
- Discord webhook: `DISCORD_WEBHOOK_URL`
  - Content: Daily regime signals (human-friendly post)
- Email (SMTP): `ALERT_RECIPIENTS`
  - Alerts: Pipeline failures, drift warnings
- X (Twitter): Configuration present (`X_API_KEY`, etc.) but not yet integrated

## Real-Time Streaming

**WebSocket:**
- Endpoint: `GET /ws/regime`
- Protocol: WebSocket (via `websockets>=12.0`)
- Implementation: `api/routes/websocket.py`
- Features: Real-time regime updates as pipeline completes, auto-reconnect with exponential backoff
- Broadcasts to all connected clients when new regime signal available

---

*Integration audit: 2026-03-18*
