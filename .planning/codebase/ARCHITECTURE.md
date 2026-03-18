# Architecture

**Analysis Date:** 2026-03-18

## Pattern Overview

**Overall:** Layered multi-tier system with clear separation between data ingestion, feature engineering, model inference, REST/WebSocket API, and React frontend. The architecture follows a frozen-model pattern where ML artifacts train once and serialize, enabling deterministic daily inference runs.

**Key Characteristics:**
- **Data ingestion** decoupled from inference via feature store (TimescaleDB hypertables)
- **Frozen model pattern** — models train once via `scripts/retrain_models.py`, serialize via joblib, daily pipeline only runs inference
- **13-step orchestrated pipeline** — each step independently testable with validation guards
- **Stateless inference service** — models loaded once per process, reused across requests
- **Idempotent database writes** — `INSERT … ON CONFLICT DO UPDATE` for safe re-runs
- **Real-time WebSocket streaming** — connected dashboards update instantly on pipeline completion
- **Tier-based feature gating** — API routes enforce subscription tier access via `@require_paid` decorator

## Layers

**Data Ingestion Layer:**
- Purpose: Fetch raw macroeconomic and market data from external sources
- Location: `data/ingestion/` (`fred_client.py`, `market_client.py`)
- Contains: FRED API client, Yahoo Finance market data fetcher
- Depends on: External APIs (FRED, Yahoo Finance), config settings
- Used by: Daily pipeline orchestrator

**Feature Engineering Layer:**
- Purpose: Transform raw series into stationary features suitable for PCA/HMM
- Location: `data/processing/feature_engineering.py`
- Contains: Net Liquidity Proxy computation, log returns, first differences, yield curve
- Depends on: Pandas, NumPy, raw data
- Used by: Daily pipeline, backtest service
- Output: 10-13 stationary features (d_liquidity, d_sp500, d_vix, d_dxy, d_hy_spread, d_yield_curve, d_10y, d_2y, d_gold, d_oil, d_btc, d_eth)

**Validation Layer:**
- Purpose: Catch data quality issues early to prevent model drift
- Location: `services/validation.py`
- Contains: `validate_raw_fred()`, `validate_market_data()`, `validate_features()`
- Validates: NaN ratios, value ranges, z-score outliers, data staleness (>3 days)
- Used by: Daily pipeline (steps 2 & 4)

**Model Layer (Frozen Inference):**
- Purpose: Probabilistic macro regime classification
- Location: `models/`
- Contains:
  - `pca_model.py` — PCA + StandardScaler wrapper (4 components, 80% variance threshold)
  - `hmm_model.py` — Gaussian HMM wrapper (4 regimes, full covariance)
  - `garch_model.py` — Volatility forecasting (for volatility_state field)
  - `regime_classifier.py` — State index → regime name mapping (expansion, tightening, risk_off, recovery)
- Artifact location: `models/artifacts/{version}/` (pca.pkl, hmm.pkl, classifier.pkl, garch.pkl)
- Used by: Inference service, daily pipeline
- Loading: Lazy-loaded via `RegimeInferenceService` property accessors

**Inference Service:**
- Purpose: Stateless wrapper over frozen models for PCA → HMM → regime classification
- Location: `services/inference.py` (`RegimeInferenceService` class)
- Public method: `infer(feature_matrix: np.ndarray, vix_diff: float) -> dict`
- Returns: regime probabilities, risk_score, volatility_state, model_version
- Used by: Daily pipeline (step 8), backtest service, ad-hoc scripts

**Pipeline Orchestrator:**
- Purpose: Coordinates end-to-end daily macro regime computation
- Location: `data/pipelines/daily_pipeline.py` (`run_daily_pipeline()` function)
- 13-step flow:
  1. Fetch FRED + market data
  2. Validate raw data (NaN, ranges, staleness)
  3. Compute engineered features
  4. Validate features
  5. Store features → TimescaleDB (upsert)
  6. Data-lag guard (skip inference if >3 days stale)
  7. Load frozen models → PCA transform
  8. HMM inference → regime probabilities
  9. Store regime results → TimescaleDB (upsert)
  10. Detect regime change → fire alerts (email/webhook)
  11. Compute & store drift metrics (variance drift, persistence, feature shift)
  12. Broadcast regime update via WebSocket
  13. Log pipeline run metadata
- Entry point: Called by `services/scheduler.py` on cron schedule (default 18:30 UTC)
- Error handling: Partial failures captured as `status=partial` in pipeline_runs table

**Drift Monitoring Service:**
- Purpose: Detect model degradation via PCA variance shift, HMM persistence, feature shift
- Location: `services/drift_monitor.py`
- Metrics: `compute_pca_variance_drift()`, `compute_regime_persistence()`, `compute_feature_shift()`
- Thresholds: variance_warn=0.10, persistence_warn=0.97, feature_shift_warn=1.5
- Triggers: Alerts if any metric exceeds threshold

**Alerting Service:**
- Purpose: Email and webhook notifications on regime change or drift threshold
- Location: `services/alerting.py`
- Methods: `alert_regime_change()`, `alert_drift_warning()`
- Channels: SMTP (email), webhook (Slack/Discord/Teams)
- Used by: Daily pipeline (step 10)

**Database Persistence Layer:**
- Purpose: Store time-series features, PCA factors, regime outputs, metadata
- Technology: TimescaleDB (PostgreSQL with hypertable extension)
- Location: `database/connection.py`, `database/schema.sql`, `database/queries.py`
- Connection pooling: ThreadedConnectionPool (min=2, max=10) via `get_sync_cursor()` context manager
- Tables (6 total):
  - `macro_features` (hypertable) — raw engineered features, indexed on time
  - `macro_factors` (hypertable) — PCA latent factors (factor_1-4)
  - `macro_regimes` (hypertable) — regime probabilities + risk_score
  - `drift_metrics` (hypertable) — variance drift, persistence, feature shift
  - `pipeline_runs` (regular) — pipeline execution logs (status, duration, error_message, model_version)
  - `model_versions` (regular) — registry of trained model artifacts with metadata
- All time-series writes use upsert semantics: `INSERT … ON CONFLICT (time) DO UPDATE SET …`

**REST API Layer:**
- Purpose: Serve regime signals, historical data, backtest, analysis to authenticated clients
- Framework: FastAPI with Uvicorn
- Location: `api/main.py` (entry point), `api/routes/` (11 routers)
- Key routes:
  - `/v1/regime/current` — latest macro regime signal
  - `/v1/regime/history` — historical signals with date filtering + pagination
  - `/v1/liquidity` — net liquidity proxy time series
  - `/v1/factors` — PCA latent factors time series
  - `/v1/drift` — model drift metrics
  - `/v1/backtest` — historical regime replay with signal statistics
  - `/v1/forecast` — ARIMA forecast
  - `/v1/analysis` — rule-based composite analysis
  - `/v1/commentary` — AI-generated macro commentary (Anthropic API)
  - `/ws/regime` — WebSocket real-time regime stream
- Middleware: CORS, rate limiting (`@app.add_middleware`)
- Auth: API key header (`X-API-Key`) or query param, with tier-based access control
- Lifespan manager: Starts/stops scheduler and DB pool on app startup/shutdown

**WebSocket Layer:**
- Purpose: Broadcast regime updates to connected dashboards in real-time
- Location: `api/routes/websocket.py`
- Endpoint: `/ws/regime`
- Broadcast mechanism: `broadcast_regime_update()` called by daily pipeline (step 12)
- Client reconnection: Exponential backoff (1s → 32s)
- Message format: JSON regime output with timestamp

**Authentication Layer:**
- Purpose: Validate API keys and enforce subscription tier restrictions
- Location: `api/auth.py`, `api/routes/auth.py`, `api/deps.py`
- Mechanism:
  - Development mode: Empty `API_KEYS` list bypasses auth
  - Production: Header `X-API-Key` or query `?api_key=` validated against configured keys
  - Tiers: `free` (30 days history limit), `starter` (90 days), `pro` (unlimited), `owner` (all features, no limit)
- Enforcement: `@require_api_key` decorator on routes, `@require_paid` for tier-gated features
- Paddle billing integration: Subscription tier synced from Paddle API on auth

**Frontend Layer:**
- Purpose: Real-time dashboard for macro regime signals, backtests, analysis
- Framework: React 18 with Vite, Recharts for charting, Tailwind CSS
- Location: `frontend/src/`
- Architecture: Single-page app with lazy-loaded views (InflationView, GrowthView, etc.)
- Entry point: `frontend/src/main.jsx` → `App.jsx` (router logic)
- Client API: `frontend/src/lib/api.js` (fetch wrapper with auth, error handling)
- State: React hooks + WebSocket connection context
- Key views: Dashboard (RegimeCard, Timeline, Charts), Backtest, Analysis, Settings
- Build: Vite bundler, deployed to `frontend/dist`, served by nginx in production

**Scheduler:**
- Purpose: Background job runner for daily pipeline
- Technology: APScheduler with background scheduler
- Location: `services/scheduler.py`
- Lifecycle: Started/stopped by FastAPI lifespan manager
- Cron config: `PIPELINE_CRON_HOUR`, `PIPELINE_CRON_MINUTE` (default 18:30 UTC)
- Misfire grace time: 3600s (if missed, will run within 1 hour window)

## Data Flow

**Daily Pipeline Flow:**

1. **Trigger** — APScheduler fires `run_daily_pipeline()` on cron schedule
2. **Data Fetch** — `fetch_all_fred()` (7 series), `fetch_market_data()` (SP500, VIX, DXY, yields)
3. **Validation 1** — Check NaN ratios, value ranges, staleness (>3 days → data_lag=true, skip to end)
4. **Feature Engineering** — `build_features()` produces 10-13 stationary features
5. **Validation 2** — Check feature NaN, z-score outliers, missing columns
6. **Feature Store** — Upsert features to `macro_features` table
7. **Lag Guard** — Check FRED publication lag; if >3 days, return last known regime
8. **Model Load** — `RegimeInferenceService.infer()` loads PCA + HMM artifacts
9. **Inference** — Transform features via PCA, predict state probabilities via HMM, classify regime
10. **Regime Store** — Upsert regime output to `macro_regimes` table
11. **Regime Change Alert** — If regime != previous, send email + webhook
12. **Drift Compute** — `compute_pca_variance_drift()`, `compute_regime_persistence()`, `compute_feature_shift()`, upsert to `drift_metrics`
13. **Drift Alert** — If any drift metric exceeds threshold, send alert
14. **WebSocket Broadcast** — Call `broadcast_regime_update()` to connected clients
15. **Pipeline Log** — Insert run metadata (status, duration, error_message, model_version) to `pipeline_runs`

**Request → Response Flow (API):**

1. Client sends HTTP GET to `/v1/regime/current` with optional `X-API-Key` header
2. FastAPI route handler calls `queries.fetch_current_regime()` (SQL SELECT)
3. Queries return dict row with regime data
4. Handler constructs Pydantic `RegimeResponse` model
5. FastAPI serializes to JSON, returns with 200 status
6. Client receives JSON, renders on dashboard

**WebSocket Flow (Real-time):**

1. Client connects to `/ws/regime` (WebSocket upgrade)
2. Connection stored in `_ws_manager` (set of connections)
3. Pipeline completes, calls `broadcast_regime_update(regime_dict)`
4. Broadcasts JSON message to all connected clients
5. Client receives message, updates React state, rerenders dashboard
6. On disconnect or error, connection removed from manager; client attempts reconnect with exponential backoff

**State Management:**

- Feature state: Persisted to `macro_features` hypertable (immutable time-series)
- Regime state: Persisted to `macro_regimes` hypertable (immutable, indexed by time)
- Transient state: React hooks in frontend (current regime, user tier, guide mode toggle)
- Model state: Frozen artifacts in `models/artifacts/{version}/`; loaded once per process
- Connection state: ThreadedConnectionPool maintains 2-10 active DB connections

## Key Abstractions

**RegimeInferenceService:**
- Purpose: Single interface for loading frozen models and running end-to-end inference
- Examples: `services/inference.py`
- Pattern: Lazy-loading properties + method `infer(feature_matrix, vix_diff) → dict`
- Benefit: Models loaded once per process, reused across pipeline runs and API requests

**Feature Matrix (np.ndarray):**
- Purpose: Standardized input format for PCA/HMM
- Shape: (T, K) where T = time steps, K = 10-13 features
- Invariant: All NaN and outliers validated before passing to models
- Used by: PCA transform, HMM inference

**Regime Probabilities (dict):**
- Purpose: Standardized output format for regime classification
- Schema: `{expansion: float, tightening: float, risk_off: float, recovery: float}`
- Sum = 1.0 (normalized via HMM posterior)
- Used by: Database, API responses, frontend rendering

**Pipeline Run (dict):**
- Purpose: Audit trail for pipeline executions
- Schema: `{run_ts, status, data_lag, duration_sec, error_message, model_version}`
- Inserted to `pipeline_runs` table after every run (success or failure)

**Drift Metrics (dict):**
- Purpose: Monitor model degradation signals
- Schema: `{time, variance_drift, persistence_drift, feature_shift}`
- Thresholds: variance_warn=0.10, persistence_warn=0.97, feature_shift_warn=1.5
- Compared against thresholds to trigger alerts

## Entry Points

**Daily Pipeline:**
- Location: `data/pipelines/daily_pipeline.py` (`run_daily_pipeline()` function)
- Triggers: APScheduler cron (daily at configured time)
- Also callable from CLI: `python scripts/run_daily_pipeline.py --target-date 2026-03-18 --model-version v1`
- Responsibilities: Execute all 13 steps, handle errors gracefully, return regime output dict

**REST API:**
- Location: `api/main.py` (`app` FastAPI object)
- Triggers: HTTP requests to any `/v1/*` or `/ws/*` endpoint
- Also called via: Manual API testing, client dashboards, webhooks
- Responsibilities: Authenticate request, enforce tier limits, query database, return JSON/WebSocket stream

**Model Training:**
- Location: `scripts/retrain_models.py`
- Triggers: Manual execution when drift metrics indicate degradation
- Responsibilities: Load historical features from database, train PCA + HMM, serialize to `models/artifacts/v{N}/`, update `DEFAULT_MODEL_VERSION` in .env

**Database Initialization:**
- Location: `scripts/init_db.py`
- Triggers: One-time setup on fresh database
- Responsibilities: Create TimescaleDB extension, create all tables, set up indexes

**Web Dashboard:**
- Location: `frontend/src/main.jsx` (React root)
- Triggers: Browser loads dashboard URL (http://localhost:3000 dev, http://localhost/80 prod)
- Responsibilities: Render SPA, connect WebSocket to `/ws/regime`, authenticate with API key, fetch regime history, render charts

## Error Handling

**Strategy:** Layered validation with graceful degradation. Data validation catches issues early; pipeline logs partial failures; API returns last-known state if pipeline fails.

**Patterns:**

- **Data Validation** — `validate_raw_fred()`, `validate_market_data()`, `validate_features()` in step 2 & 4 of pipeline. If validation fails, pipeline logs error and skips inference.

- **Lag Guard** — If FRED data >3 days stale, pipeline sets `data_lag=true`, skips steps 7-12 (inference), returns last known regime from database. This prevents stale signals.

- **Partial Success** — Pipeline catches exceptions in steps 7-13, inserts `status=partial` to `pipeline_runs`, continues to step 15 (logging). Client can check `pipeline_runs` table to audit failures.

- **API Error Handling** — Route handlers catch `HTTPException(404)` if no regime data found, return JSON `{detail: "No regime data available."}`. Rate limiting returns `429 Too Many Requests`.

- **Database Connection** — `get_sync_cursor()` context manager catches exceptions, rolls back transaction, returns connection to pool. No connection leaks.

- **Model Loading** — Lazy loading via properties; if artifact not found, raises `FileNotFoundError` with clear path. Retry on next pipeline run or API request.

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module
- Config: `basicConfig()` in `api/main.py`, level from `LOG_LEVEL` env var
- Pattern: Each module has logger `logger = logging.getLogger(__name__)`, logs to stdout with timestamp + level + module name

**Validation:**
- Centralized in `services/validation.py` with three functions: `validate_raw_fred()`, `validate_market_data()`, `validate_features()`
- Checks: NaN ratios (<10%), value ranges (market data sanity), z-score outliers (>4 std devs), FRED staleness (>3 days)
- Enforcement: Called in pipeline steps 2 & 4; failures logged as `data_lag=true` or partial success

**Authentication:**
- Mechanism: API key in header (`X-API-Key`) or query param (`?api_key=`)
- Dev mode: Empty `API_KEYS` list disables auth
- Prod mode: Keys validated against configured list; tier synced from Paddle
- Enforcement: `@require_api_key` decorator on all routes; `@require_paid` for tier-gated features
- Tier gates: Free (30 days), Starter (90 days), Pro (unlimited), Owner (all features, no rate limit)

**Monitoring:**
- Pipeline run audit trail: `pipeline_runs` table logs every execution (status, duration, error_message, model_version)
- Model versioning: `model_versions` table tracks trained artifacts with metadata (PCA variance, HMM regime count, notes)
- Drift detection: `drift_metrics` table tracks variance, persistence, feature shift; thresholds trigger alerts
- Health endpoint: GET `/health` returns `{status: "ok", version: "0.1.0"}`

---

*Architecture analysis: 2026-03-18*
