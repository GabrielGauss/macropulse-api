# Codebase Structure

**Analysis Date:** 2026-03-18

## Directory Layout

```
macropulse/
├── api/                           # FastAPI application (REST + WebSocket)
│   ├── main.py                    # App entry point with lifespan + middleware
│   ├── auth.py                    # API key authentication logic
│   ├── deps.py                    # Dependency injection (tier requirements)
│   ├── middleware/
│   │   └── rate_limit.py          # Rate limiting middleware
│   ├── routes/                    # 11 routers (regime, auth, billing, etc.)
│   │   ├── regime.py              # GET /v1/regime/* endpoints
│   │   ├── websocket.py           # WebSocket /ws/regime
│   │   ├── auth.py                # Auth + user management
│   │   ├── billing.py             # Paddle billing integration
│   │   ├── backtest.py            # Historical regime backtest
│   │   ├── commentary.py          # AI macro commentary (Anthropic API)
│   │   ├── dashboard.py           # Dashboard data aggregation
│   │   ├── forecast.py            # ARIMA forecast
│   │   ├── analysis.py            # Composite analysis rules
│   │   ├── performance.py         # Portfolio performance
│   │   ├── signals.py             # Trading signal endpoints
│   │   ├── model.py               # Model metadata
│   │   ├── pipeline.py            # Pipeline trigger + logs
│   │   ├── public.py              # Public landing page data
│   │   ├── public_config.py       # Public config (currencies, holidays)
│   │   └── webhook.py             # Paddle webhook receiver
│   └── schemas/
│       └── responses.py           # Pydantic models (RegimeResponse, etc.)
│
├── data/                          # Data ingestion + feature engineering
│   ├── ingestion/
│   │   ├── fred_client.py         # FRED API client (fetch_all_fred)
│   │   └── market_client.py       # Yahoo Finance client (fetch_market_data)
│   ├── processing/
│   │   └── feature_engineering.py # Stationary transforms (build_features)
│   └── pipelines/
│       └── daily_pipeline.py      # Orchestrator (13-step flow, run_daily_pipeline)
│
├── models/                        # ML models (frozen inference pattern)
│   ├── artifacts/                 # Serialized joblib artifacts (gitignored)
│   │   ├── v1/                    # Version 1 models
│   │   │   ├── pca.pkl            # PCA + scaler
│   │   │   ├── hmm.pkl            # Gaussian HMM
│   │   │   ├── classifier.pkl     # Regime classifier
│   │   │   └── garch.pkl          # GARCH volatility model
│   │   └── v2/                    # Future versions
│   ├── pca_model.py               # PCAModel class (fit + predict_proba)
│   ├── hmm_model.py               # HMMModel class (fit + predict_proba)
│   ├── garch_model.py             # GARCHModel class for volatility
│   └── regime_classifier.py       # RegimeClassifier (state → label mapping)
│
├── database/                      # Data persistence (TimescaleDB)
│   ├── connection.py              # ThreadedConnectionPool manager
│   ├── schema.sql                 # DDL (6 tables, hypertables)
│   ├── queries.py                 # Parameterized SQL (upserts, reads)
│   └── migrations/                # Future schema versioning
│
├── services/                      # Business logic layer
│   ├── inference.py               # RegimeInferenceService (frozen model wrapper)
│   ├── drift_monitor.py           # Drift metrics (variance, persistence, shift)
│   ├── alerting.py                # Email + webhook alerts
│   ├── validation.py              # Data validation guards
│   ├── backtest.py                # Historical regime replay
│   ├── scheduler.py               # APScheduler cron runner
│   └── scorecard.py               # Scorecard aggregation logic
│
├── config/                        # Configuration
│   └── settings.py                # Pydantic Settings (all env vars)
│
├── scripts/                       # CLI entry points
│   ├── run_daily_pipeline.py      # Manual pipeline trigger
│   ├── retrain_models.py          # Model training (PCA + HMM)
│   └── init_db.py                 # Database initialization
│
├── frontend/                      # React dashboard (Vite)
│   ├── src/
│   │   ├── main.jsx               # React root entry
│   │   ├── App.jsx                # Main app component (router logic)
│   │   ├── index.css              # Global styles (Tailwind base)
│   │   ├── components/            # React components (19 total)
│   │   │   ├── Header.jsx         # Top navigation + auth
│   │   │   ├── Sidebar.jsx        # Left sidebar (section switcher)
│   │   │   ├── RegimeCard.jsx     # Current regime display
│   │   │   ├── RegimeTimeline.jsx # Historical regime timeline
│   │   │   ├── RegimeCalendar.jsx # Calendar heatmap
│   │   │   ├── LiquidityChart.jsx # Liquidity proxy chart
│   │   │   ├── FactorsChart.jsx   # PCA factors (4 lines)
│   │   │   ├── DriftPanel.jsx     # Drift metrics display
│   │   │   ├── ForecastCard.jsx   # ARIMA forecast
│   │   │   ├── CommentaryCard.jsx # AI macro text + tags
│   │   │   ├── MacroHeatmap.jsx   # Asset class heatmap
│   │   │   ├── SignalGauges.jsx   # Signal gauges (analog dials)
│   │   │   ├── AlertSettings.jsx  # Alert configuration UI
│   │   │   ├── WebhookGuide.jsx   # Webhook integration guide
│   │   │   ├── ErrorBoundary.jsx  # Error boundary (fallback)
│   │   │   ├── ChartTooltip.jsx   # Recharts tooltip wrapper
│   │   │   ├── AssetBias.jsx      # Asset bias visualization
│   │   │   ├── CompositeAnalysisCard.jsx # Analysis results
│   │   │   └── StatCard.jsx       # Small stat box
│   │   ├── views/                 # Lazy-loaded page views (7 total)
│   │   │   ├── InflationView.jsx  # Inflation analysis
│   │   │   ├── GrowthView.jsx     # Growth analysis
│   │   │   ├── RatesView.jsx      # Interest rates analysis
│   │   │   ├── CommoditiesView.jsx # Commodities analysis
│   │   │   ├── FXView.jsx         # Foreign exchange analysis
│   │   │   ├── CryptoView.jsx     # Cryptocurrency analysis
│   │   │   ├── QuantView.jsx      # Quantitative analysis
│   │   │   ├── LiquidityView.jsx  # Liquidity detail
│   │   │   ├── SignalsView.jsx    # Trading signals
│   │   │   ├── BacktestView.jsx   # Backtest results
│   │   │   └── PerformanceView.jsx # Portfolio performance
│   │   ├── hooks/                 # React hooks
│   │   │   ├── useFetch.js        # Fetch wrapper (caching + errors)
│   │   │   └── useRegimeSocket.js # WebSocket connection hook
│   │   └── lib/                   # Utilities
│   │       ├── api.js             # API client (auth + endpoints)
│   │       ├── guideMode.js       # Guide mode context
│   │       └── utils.js           # Helpers (formatting, dates)
│   ├── public/                    # Static assets
│   │   ├── landing.html           # Marketing landing page
│   │   └── (favicon, etc.)
│   ├── dist/                      # Build output (Vite, gitignored)
│   ├── node_modules/              # Dependencies (gitignored)
│   ├── package.json               # Dependencies (React, Recharts, Vite)
│   ├── vite.config.js             # Vite build config
│   └── tailwind.config.js         # Tailwind CSS config
│
├── nginx/                         # Reverse proxy config (production)
│   └── nginx.conf                 # Routes to API + static frontend
│
├── Dockerfile                     # Python API image
├── docker-compose.yml             # Full stack (TimescaleDB + API + nginx)
├── .env.example                   # Example config
├── .env                           # Actual config (gitignored)
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project metadata + ruff + mypy config
├── README.md                      # Documentation
└── .planning/codebase/            # Documentation (this file)
    ├── ARCHITECTURE.md
    ├── STRUCTURE.md
    ├── CONVENTIONS.md
    ├── TESTING.md
    ├── STACK.md
    ├── INTEGRATIONS.md
    └── CONCERNS.md
```

## Directory Purposes

**api/:**
- Purpose: FastAPI web service with REST endpoints and WebSocket streaming
- Contains: Route definitions, authentication, middleware, Pydantic schemas
- Key files: `main.py` (app object + lifespan), `routes/regime.py` (200 lines), `auth.py` (265 lines)

**data/:**
- Purpose: Data ingestion, transformation, and pipeline orchestration
- Contains: API clients (FRED, Yahoo Finance), feature engineering, daily pipeline
- Key files: `pipelines/daily_pipeline.py` (13-step orchestrator)

**models/:**
- Purpose: Machine learning model wrappers and serialized artifacts
- Contains: PCA, HMM, GARCH, regime classifier; serialized joblib files
- Artifact storage: `artifacts/{version}/` directory (generated, gitignored)
- Key files: `hmm_model.py` (Gaussian HMM wrapper), `pca_model.py` (PCA + scaler)

**database/:**
- Purpose: Database connection pool, schema, and parameterized queries
- Contains: psycopg2 connection pool, TimescaleDB DDL, upsert helpers
- Key files: `connection.py` (ThreadedConnectionPool), `schema.sql` (6 tables)

**services/:**
- Purpose: Business logic and infrastructure services
- Contains: Model inference, drift monitoring, alerting, validation, scheduling
- Key files: `inference.py` (RegimeInferenceService), `drift_monitor.py`, `scheduler.py`

**config/:**
- Purpose: Centralized configuration via Pydantic Settings
- Contains: Single `settings.py` file with all env vars typed and validated

**scripts/:**
- Purpose: CLI entry points for one-time operations
- Contains: Pipeline runner, model training, database initialization
- Run as: `python scripts/retrain_models.py --version v2`

**frontend/src/:**
- Purpose: React single-page application
- Contains: Components (RegimeCard, charts), views (InflationView, BacktestView), hooks, API client
- Build: Vite → `frontend/dist/`, served by nginx in production

**nginx/:**
- Purpose: Reverse proxy configuration (production only)
- Contains: Routing rules (API to localhost:8000, static to frontend)

## Key File Locations

**Entry Points:**
- `api/main.py` — FastAPI app (REST + WebSocket)
- `data/pipelines/daily_pipeline.py` — Daily macro pipeline orchestrator
- `frontend/src/main.jsx` — React root
- `scripts/run_daily_pipeline.py` — CLI pipeline trigger
- `scripts/retrain_models.py` — Model training script

**Configuration:**
- `config/settings.py` — All environment variables (Pydantic Settings)
- `.env` — Runtime config (FRED_API_KEY, DB credentials, etc.)
- `docker-compose.yml` — Docker stack configuration

**Core Logic:**
- `data/processing/feature_engineering.py` — Feature transforms (Net Liquidity, log returns, etc.)
- `services/inference.py` — Model inference interface (RegimeInferenceService)
- `data/pipelines/daily_pipeline.py` — 13-step pipeline orchestrator

**Database:**
- `database/schema.sql` — TimescaleDB table definitions (6 tables)
- `database/queries.py` — Parameterized SQL helpers (upserts, selects)
- `database/connection.py` — Connection pool manager

**API Endpoints:**
- `api/routes/regime.py` — `/v1/regime/*` endpoints (190 lines)
- `api/routes/backtest.py` — `/v1/backtest` endpoint
- `api/routes/websocket.py` — `/ws/regime` WebSocket (73 lines)
- `api/routes/commentary.py` — AI commentary endpoint (186 lines)

**Frontend:**
- `frontend/src/App.jsx` — Main component with router logic
- `frontend/src/components/RegimeCard.jsx` — Current regime display
- `frontend/src/components/RegimeTimeline.jsx` — Historical timeline
- `frontend/src/lib/api.js` — API client wrapper

**Models:**
- `models/hmm_model.py` — Gaussian HMM wrapper
- `models/pca_model.py` — PCA + StandardScaler wrapper
- `models/regime_classifier.py` — State → regime name mapping
- `models/artifacts/v1/` — Serialized model artifacts (pca.pkl, hmm.pkl, etc.)

**Testing & Monitoring:**
- `pipeline_runs` table — Pipeline execution logs
- `drift_metrics` table — Model drift indicators
- `model_versions` table — Trained model registry

## Naming Conventions

**Files:**
- Snake case: `daily_pipeline.py`, `feature_engineering.py`, `regime_classifier.py`
- Entry points suffixed `_py`: `main.py`, `init_db.py`
- Route files match domain: `regime.py`, `billing.py`, `analysis.py`
- React components: PascalCase: `RegimeCard.jsx`, `HeaderComponent.jsx`
- React utilities: camelCase: `useFetch.js`, `guideMode.js`

**Directories:**
- Plural for collections: `routes/`, `services/`, `components/`, `schemas/`, `artifacts/`
- Domain-focused: `ingestion/`, `processing/`, `pipelines/`
- Lowercase with underscores: `macro_features`, `macro_regimes`

**Classes:**
- PascalCase: `RegimeInferenceService`, `HMMModel`, `RateLimitMiddleware`
- Suffix descriptive: `*Model`, `*Service`, `*Middleware`, `*Router`

**Functions:**
- Snake case: `run_daily_pipeline()`, `fetch_all_fred()`, `build_features()`
- Verb-first for actions: `fetch_*`, `compute_*`, `validate_*`, `broadcast_*`

**Variables:**
- Snake case: `pipeline_cron_hour`, `net_liquidity`, `feature_matrix`
- Constants UPPER_CASE: `_POOL_MIN`, `_DRIFT_VARIANCE_WARN`
- Private prefixed underscore: `_pca`, `_hmm` (lazy-loaded model properties)

**Tables:**
- Plural snake case: `macro_features`, `macro_regimes`, `drift_metrics`, `pipeline_runs`, `model_versions`
- Columns snake case: `prob_expansion`, `volatility_state`, `model_version`

## Where to Add New Code

**New Feature (e.g., add regime probability thresholds alert):**
- Primary code: `services/alerting.py` (add alert function)
- API endpoint: `api/routes/alerts.py` (new route file)
- Database: `database/schema.sql` (add alerts table if needed)
- Tests: `tests/test_alerting.py`

**New Component/Module (e.g., sentiment analysis):**
- Implementation: `services/sentiment.py` (new service module)
- Ingestion: `data/ingestion/sentiment_client.py` (new data source)
- Integration point: Add to daily pipeline in `data/pipelines/daily_pipeline.py` step
- Database: Update `database/schema.sql` and `database/queries.py`
- API: Add endpoint in `api/routes/` (new router file)

**Utilities:**
- Shared Python helpers: `services/` (if business logic) or `data/processing/` (if data transformation)
- Frontend utilities: `frontend/src/lib/` (utilities.js, formatters, etc.) or `frontend/src/hooks/` (React hooks)
- Common types: `api/schemas/responses.py` (Pydantic models)

**New View or Dashboard Section (e.g., volatility dashboard):**
- React component: `frontend/src/components/VolatilityCard.jsx`
- View file: `frontend/src/views/VolatilityView.jsx`
- API endpoint: Add to existing route or create `api/routes/volatility.py`
- Hook: Create `frontend/src/hooks/useVolatility.js` if custom fetch logic needed

**New ML Model (e.g., LSTM regime forecast):**
- Model class: `models/lstm_model.py`
- Artifact directory: `models/artifacts/{version}/lstm.pkl`
- Integration: Wrap in service layer, call from pipeline
- Endpoint: Add to `api/routes/forecast.py` or new route file

## Special Directories

**models/artifacts/:**
- Purpose: Stores serialized ML models (joblib format)
- Generated: Yes (by `scripts/retrain_models.py`)
- Committed: No (gitignored via `.gitignore`)
- Naming: `{version}/pca.pkl`, `{version}/hmm.pkl`, `{version}/classifier.pkl`, `{version}/garch.pkl`
- Access: Loaded by `RegimeInferenceService` on first use per process

**frontend/dist/:**
- Purpose: Built React SPA output from Vite
- Generated: Yes (`npm run build`)
- Committed: No (gitignored)
- Served by: nginx in production (`/` → `frontend/dist/index.html`)
- Development: Vite dev server watches `frontend/src/` for hot reload

**frontend/node_modules/:**
- Purpose: npm dependencies
- Generated: Yes (`npm install`)
- Committed: No (gitignored)
- Size: Large (excluded from repo)

**database/migrations/:**
- Purpose: Future schema versioning (currently empty, migrations inline in schema.sql)
- Reserved for: Alembic or similar migration tool integration

**.planning/codebase/:**
- Purpose: GSD documentation (this structure)
- Generated: Yes (by GSD map-codebase command)
- Committed: Yes (reference docs)
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md

---

*Structure analysis: 2026-03-18*
