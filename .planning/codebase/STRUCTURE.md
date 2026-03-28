# Codebase Structure

**Analysis Date:** 2026-03-28

## Directory Layout

```
macropulse/
├── .planning/
│   └── codebase/                      # Analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
│
├── api/                               # FastAPI application (REST + WebSocket)
│   ├── main.py                        # App entry point with lifespan + middleware
│   ├── auth.py                        # API key authentication (SHA-256 hash validation)
│   ├── deps.py                        # Dependency injection (tier gating)
│   ├── middleware/
│   │   └── rate_limit.py              # Per-key/per-IP rate limiting middleware
│   ├── routes/                        # 14 route modules
│   │   ├── regime.py                  # GET /v1/regime/current, /regime/history
│   │   ├── websocket.py               # GET /ws/regime
│   │   ├── auth.py                    # POST /v1/auth/register, /verify, /rotate, etc.
│   │   ├── billing.py                 # POST /v1/billing/checkout, /portal
│   │   ├── backtest.py                # POST /v1/backtest
│   │   ├── commentary.py              # GET /v1/regime/commentary
│   │   ├── dashboard.py               # GET /v1/dashboard
│   │   ├── forecast.py                # GET /v1/forecast
│   │   ├── analysis.py                # GET /v1/analysis/composite
│   │   ├── performance.py             # GET /v1/performance
│   │   ├── signals.py                 # GET /v1/signals/latest
│   │   ├── model.py                   # GET /v1/model/transition-matrix, /feature-loadings
│   │   ├── pipeline.py                # GET /v1/pipeline/status, POST /trigger
│   │   ├── public.py                  # GET /v1/public/* (unauthenticated)
│   │   ├── public_config.py           # GET /v1/public/config (currencies, holidays)
│   │   └── webhook.py                 # POST /v1/webhook/* (Paddle, generic webhooks)
│   └── schemas/
│       └── responses.py               # Pydantic models (RegimeResponse, DriftResponse, etc.)
│
├── config/
│   └── settings.py                    # Centralized config (pydantic-settings with .env)
│
├── data/                              # Data ingestion + feature engineering
│   ├── ingestion/
│   │   ├── fred_client.py             # FRED API client (fetch_all_fred)
│   │   └── market_client.py           # Market data fetcher (fetch_market_data)
│   ├── processing/
│   │   └── feature_engineering.py     # Feature transforms (build_features)
│   └── pipelines/
│       └── daily_pipeline.py          # Scheduled pipeline orchestrator
│
├── database/
│   ├── connection.py                  # ThreadedConnectionPool + context managers
│   ├── queries.py                     # Prepared SQL queries (fetch, insert, update)
│   └── migrations/
│       ├── 001_user_management.sql    # Users, roles
│       ├── 002_paddle_billing.sql     # Paddle subscription tracking
│       ├── 003_auth_and_usage.sql     # API keys, daily usage counters
│       ├── 004_ip_lock.sql            # IP lock state
│       ├── 005_otp_attempts.sql       # OTP attempt tracking
│       ├── 006_lemonsqueezy_billing.sql # Alternative billing
│       ├── 007_webhook_idempotency.sql # Webhook deduplication
│       └── 008_schema_hardening.sql   # Security/integrity constraints
│
├── models/                            # ML model classes + artifacts
│   ├── pca_model.py                   # PCA wrapper (4 components, 80% variance)
│   ├── hmm_model.py                   # Gaussian HMM wrapper (4 regimes)
│   ├── garch_model.py                 # GARCH volatility model
│   ├── regime_classifier.py           # State index → regime name mapping
│   └── artifacts/
│       └── v1/                        # Frozen model serializations
│           ├── pca.pkl
│           ├── hmm.pkl
│           ├── classifier.pkl
│           └── garch.pkl
│
├── services/                          # Business logic + integrations
│   ├── scheduler.py                   # APScheduler startup/shutdown
│   ├── inference.py                   # Model loading + prediction
│   ├── orchestrator.py                # Multi-domain signal aggregation
│   ├── drift_monitor.py               # PCA variance, persistence, feature shift
│   ├── backtest.py                    # Historical regime P&L
│   ├── performance.py                 # Portfolio metrics
│   ├── scorecard.py                   # Build composite scorecard
│   ├── signals.py                     # Trading signal logic
│   ├── alerts.py                      # Email/Slack alerting
│   ├── email.py                       # Brevo email service
│   ├── discord.py                     # Discord webhook posting
│   ├── twitter.py                     # X (Twitter) posting
│   ├── paddle.py                      # Paddle billing API client
│   ├── mta_signer.py                  # Ed25519 signature (IRL Engine)
│   ├── narrative.py                   # AI narrative generation
│   ├── fomc_calendar.py               # FOMC meeting dates
│   ├── validation.py                  # Data quality checks
│   └── digest.py                      # Daily digest compilation
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx                   # React app entry point
│   │   ├── App.jsx                    # Main router + layout
│   │   ├── index.css                  # Tailwind CSS imports
│   │   ├── components/                # Reusable UI components
│   │   │   ├── Header.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── RegimeCard.jsx
│   │   │   ├── RegimeTimeline.jsx
│   │   │   ├── LiquidityChart.jsx
│   │   │   ├── FactorsChart.jsx
│   │   │   ├── DriftPanel.jsx
│   │   │   ├── SignalGauges.jsx
│   │   │   ├── MacroHeatmap.jsx
│   │   │   ├── RegimeCalendar.jsx
│   │   │   ├── ForecastCard.jsx
│   │   │   ├── CommentaryCard.jsx
│   │   │   ├── CompositeAnalysisCard.jsx
│   │   │   ├── AlertSettings.jsx
│   │   │   ├── WebhookGuide.jsx
│   │   │   ├── ApiKeyManager.jsx
│   │   │   ├── RegisterModal.jsx
│   │   │   ├── RecoverModal.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   ├── ChartTooltip.jsx
│   │   │   └── AssetBias.jsx
│   │   ├── views/                     # Page-level components (lazy-loaded)
│   │   │   ├── InflationView.jsx
│   │   │   ├── GrowthView.jsx
│   │   │   ├── RatesView.jsx
│   │   │   ├── CommoditiesView.jsx
│   │   │   ├── FXView.jsx
│   │   │   ├── CryptoView.jsx
│   │   │   ├── QuantView.jsx
│   │   │   ├── LiquidityView.jsx
│   │   │   ├── SignalsView.jsx
│   │   │   ├── BacktestView.jsx
│   │   │   ├── PerformanceView.jsx
│   │   │   └── AccountView.jsx
│   │   ├── hooks/                     # Custom React hooks
│   │   │   ├── useFetch.js            # Generic data fetching hook
│   │   │   ├── useRegimeSocket.js     # WebSocket subscription hook
│   │   │   └── useCountdown.js        # Timer hook
│   │   └── lib/
│   │       ├── api.js                 # Centralized API client methods
│   │       ├── guideMode.js           # Guide mode context
│   │       └── utils.js               # Utility functions
│   ├── dist/                          # Built frontend (gitignored)
│   ├── public/
│   │   └── index.html                 # HTML entry point
│   ├── package.json                   # Dependencies (React 18, Recharts, Vite)
│   ├── vite.config.js                 # Vite build config
│   └── tailwind.config.js             # Tailwind CSS config
│
├── tests/
│   ├── conftest.py                    # Pytest fixtures
│   └── test_pipeline_quality.py       # Pipeline validation tests
│
├── scripts/                           # Utility scripts
│   └── (maintenance scripts)
│
├── notebooks/
│   └── (Jupyter notebooks for exploration)
│
├── content/
│   └── (Static content files)
│
├── site/
│   └── (Marketing site content)
│
├── nginx/
│   └── (Nginx reverse proxy config)
│
├── docker-compose.yml                 # Local dev stack (API + PostgreSQL)
├── Dockerfile                         # Docker image for API
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Python project metadata
├── .env.example                       # Template environment variables
├── README.md                          # Project overview
├── DEPLOYMENT.md                      # Deployment instructions
└── pytest.ini                         # Pytest configuration
```

## Directory Purposes

**api/**
- Purpose: FastAPI application with REST endpoints + WebSocket server
- Contains: Route handlers, authentication, middleware, response schemas
- Key files: `main.py` (entry point), `auth.py` (API key validation), `middleware/rate_limit.py`

**config/**
- Purpose: Centralized configuration management
- Contains: Environment variable loading via pydantic-settings
- Key files: `settings.py` (single source of truth for app config)

**data/**
- Purpose: Data ingestion, feature engineering, and scheduled pipeline orchestration
- Contains: External API clients (FRED, market data), feature transforms, daily pipeline orchestrator
- Key files: `pipelines/daily_pipeline.py` (main workflow)

**database/**
- Purpose: Database connection pooling, query builders, schema migrations
- Contains: ThreadedConnectionPool wrapper, SQL queries, migration files
- Key files: `connection.py`, `queries.py`, `migrations/*.sql`

**models/**
- Purpose: ML model classes and frozen artifact storage
- Contains: PCA, HMM, GARCH, regime classifier wrappers
- Key files: Serialized `.pkl` files in `artifacts/v1/` (gitignored but required at runtime)

**services/**
- Purpose: Domain business logic (inference, drift detection, alerts, billing, etc.)
- Contains: 20 service modules for different concerns
- Key files: `scheduler.py` (pipeline scheduling), `inference.py` (model loading), `drift_monitor.py`

**frontend/**
- Purpose: React SPA user interface
- Contains: Components, views, hooks, API client, state management
- Key files: `src/main.jsx` (entry), `src/App.jsx` (router), `src/lib/api.js` (API client)

**tests/**
- Purpose: Automated testing for pipeline quality and data validation
- Contains: Pytest test files and fixtures
- Key files: `test_pipeline_quality.py`

**scripts/**
- Purpose: Maintenance and administrative utilities
- Contains: Model retraining, data backfill, schema migrations
- Run manually or via CI/CD

## Key File Locations

**Entry Points:**
- Backend: `api/main.py` — FastAPI app creation, lifespan management, middleware mounting
- Frontend: `frontend/src/main.jsx` — React DOM root, App component wrapper
- Pipeline: `data/pipelines/daily_pipeline.py` → `run_daily_pipeline()` function

**Configuration:**
- `config/settings.py` — Pydantic Settings object with .env loading
- `frontend/vite.config.js` — Vite bundler configuration
- `docker-compose.yml` — Local development stack (API + PostgreSQL)

**Core Logic:**
- `api/routes/regime.py` — `/v1/regime/*` endpoints (current signal, history, export)
- `services/inference.py` — Load frozen models, run PCA/HMM inference
- `services/scheduler.py` — APScheduler initialization and job definition
- `api/auth.py` — API key hash validation and tier lookup
- `api/middleware/rate_limit.py` — Per-key/per-IP daily quota enforcement

**Testing:**
- `tests/test_pipeline_quality.py` — Pipeline validation and quality checks
- `tests/conftest.py` — Pytest fixtures (DB mocks, test data)

**Database:**
- `database/connection.py` — PostgreSQL connection pool management
- `database/queries.py` — Prepared SQL queries for all entities
- `database/migrations/*.sql` — Schema definitions (8 files, auto-applied on startup)

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `daily_pipeline.py`, `drift_monitor.py`)
- React components: `PascalCase.jsx` (e.g., `RegimeCard.jsx`, `UserModal.jsx`)
- Utilities/hooks: `camelCase.js` (e.g., `useFetch.js`, `api.js`)
- Configuration: `lowercase_with_extension` (e.g., `vite.config.js`, `tailwind.config.js`)

**Directories:**
- Plural nouns: `routes/`, `schemas/`, `services/`, `components/`, `migrations/`
- Functional grouping: `ingestion/`, `processing/`, `pipelines/`, `artifacts/`

**Python Functions:**
- Async: prefix with `async def` (e.g., `async def dispatch(...)`)
- Dependency injection: named as nouns/adjectives (e.g., `require_api_key`, `require_paid`)
- Private helpers: prefix with `_` (e.g., `_run_migrations()`, `_resolve_limit()`)

**Database:**
- Tables: plural lowercase (e.g., `users`, `api_keys`, `regimes`, `pipeline_runs`)
- Columns: snake_case (e.g., `created_at`, `updated_at`, `daily_requests`)
- Migrations: `NNN_description.sql` (zero-padded, auto-ordered)

## Where to Add New Code

**New REST Endpoint:**
1. Create function in `api/routes/{domain}.py`
2. Use FastAPI decorators: `@router.get()`, `@router.post()`
3. Add dependencies: `Depends(require_api_key)`, `Depends(require_paid)` for gating
4. Define Pydantic response model in `api/schemas/responses.py`
5. Implement business logic in `services/` if it's domain-specific

**New React Component:**
1. Create file: `frontend/src/components/ComponentName.jsx`
2. Use functional component with React hooks
3. Import via: `import ComponentName from './components/ComponentName'`
4. For lazy-loading (views): use `React.lazy(() => import('./views/ViewName'))`
5. API calls via: `import { api } from '../lib/api'`

**New Service/Business Logic:**
1. Create file: `services/service_name.py`
2. Import at top: `from config.settings import get_settings`
3. Add logging: `logger = logging.getLogger(__name__)`
4. Export main function or class
5. Import in routes/pipeline as needed

**New Database Migration:**
1. Create file: `database/migrations/NNN_description.sql` (increment NNN)
2. Use `IF NOT EXISTS` clauses for idempotency
3. Migrations auto-run on API startup via `_run_migrations()` in `api/main.py`

**New API Key Tier:**
1. Update `TIER_LIMITS` dict in `api/middleware/rate_limit.py`
2. Update `TIER_LIMITS` comment in `api/deps.py`
3. Update database schema in migration if needed
4. Endpoints check `key_record["tier"]` to gate features

**New External Integration:**
1. Create client class in `services/{service_name}.py`
2. Load credentials from `config/settings.py` (add new env vars)
3. Wrap errors with try/except, log failures
4. Test with sandbox/dev credentials first
5. Add integration doc to codebase notes

## Special Directories

**frontend/dist/:**
- Purpose: Built frontend artifacts (index.html, JS bundles, CSS)
- Generated: `npm run build` in `frontend/`
- Committed: No (gitignored)
- Served: Mounted at `/` in API via `StaticFiles` middleware if present

**models/artifacts/:**
- Purpose: Frozen model serializations (joblib pickle files)
- Generated: Training script (not in repo) or manually
- Committed: No (gitignored, required at runtime)
- Structure: `v1/pca.pkl`, `v1/hmm.pkl`, `v1/classifier.pkl`, `v1/garch.pkl`

**database/migrations/:**
- Purpose: Versioned schema definitions
- Generated: Manually when schema changes
- Committed: Yes (always committed to git)
- Ordering: Numeric prefix (001, 002, etc.) ensures execution order
- Idempotency: All DDL uses `IF NOT EXISTS` to allow safe re-runs

**tests/:**
- Purpose: Automated test suite
- Generated: Test files committed; test artifacts (fixtures) generated at runtime
- Committed: Yes (test code committed)
- Run: `pytest` or `pytest -v` from project root

**scripts/:**
- Purpose: Administrative utilities (backfill, retraining, schema repair)
- Generated: Manually as needed
- Committed: Yes (utilities committed to git)
- Run: `python scripts/script_name.py` with appropriate args

---

*Structure analysis: 2026-03-28*
