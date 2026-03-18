# Technology Stack

**Analysis Date:** 2026-03-18

## Languages

**Primary:**
- Python 3.11+ - Backend API, data pipelines, ML models
- TypeScript/JavaScript - Frontend dashboard (React)

**Secondary:**
- SQL - TimescaleDB queries (PostgreSQL dialect)
- Bash - Deployment and utility scripts

## Runtime

**Environment:**
- Python 3.12 (Docker) / 3.11+ (local development)
- Node.js 20 (Alpine for Docker builds)

**Package Manager:**
- Python: pip
- Node.js: npm
- Lockfile: `frontend/package-lock.json` present

## Frameworks

**Core:**
- FastAPI 0.110+ - REST API and WebSocket server
- React 18.3.1 - Dashboard UI
- Uvicorn 0.29+ - ASGI server (production-grade)

**Testing:**
- pytest (available via dev dependencies, no specific version in requirements.txt)
- Vite 5.3.1 - Frontend dev server and build tool

**Build/Dev:**
- Docker & Docker Compose - Containerization
- Nginx (Alpine) - Reverse proxy and SSL termination
- Certbot - Let's Encrypt certificate management

## Key Dependencies

**Critical:**
- `pydantic>=2.6` - Request/response validation and settings management
- `pydantic-settings>=2.2` - Environment variable typed configuration
- `psycopg2-binary>=2.9` - PostgreSQL database driver
- `APScheduler>=3.10` - Background task scheduling (daily pipeline runs)

**Data Ingestion:**
- `fredapi>=0.5` - Federal Reserve Economic Data API client
- `yfinance>=0.2.36` - Yahoo Finance market data (S&P 500, VIX, DXY, crypto)

**Scientific/ML:**
- `numpy>=1.26` - Numerical computing
- `pandas>=2.2` - Data manipulation and time series
- `scikit-learn>=1.4` - Machine learning (PCA implementation)
- `hmmlearn>=0.3` - Gaussian Hidden Markov Model
- `arch>=6.0` - GARCH volatility modeling
- `statsmodels>=0.14` - Time series analysis (ARIMA forecasts)
- `joblib>=1.3` - Model serialization (frozen model artifacts)

**AI/ML Enhancement:**
- `anthropic>=0.40` - Claude API for macro commentary generation
- `plotly>=5.20` - Interactive charting

**HTTP & Async:**
- `httpx>=0.27` - Async HTTP client (Paddle API calls, webhooks, alerts)
- `websockets>=12.0` - WebSocket protocol (real-time regime streaming)

**Frontend:**
- `recharts^2.12.7` - React charting library
- `lucide-react^0.383.0` - Icon library
- `tailwindcss^3.4.4` - Utility CSS framework
- `autoprefixer^10.4.19` - PostCSS plugin for vendor prefixes

## Configuration

**Environment:**
- Configuration loaded from `.env` file via `pydantic-settings`
- File location: `config/settings.py` (`get_settings()` singleton)
- Development defaults enable local setup without full secret configuration

**Build:**
- `pyproject.toml` contains ruff (linter) and mypy (type checker) configuration
- Ruff target Python 3.11, line length 100
- Mypy strict mode enabled
- Dockerfile uses multi-stage build: Node.js frontend stage → Python API stage
- Frontend dist bundled into API container at `frontend/dist`

## Platform Requirements

**Development:**
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (for full stack)
- PostgreSQL 16 with TimescaleDB extension (via Docker)

**Production:**
- Docker runtime
- PostgreSQL 16 with TimescaleDB extension
- Let's Encrypt certificate provisioning
- SSL/TLS termination via Nginx
- Cron scheduling (APScheduler handles in-process via lifespan)

## Database

**Primary:** TimescaleDB (PostgreSQL 16)
- Hypertables for time-series data: `macro_features`, `macro_factors`, `macro_regimes`, `model_drift_metrics`
- Connection pooling via psycopg2
- Database URL: `postgresql://{user}:{password}@{host}:{port}/{name}`
- Schema initialization via `database/schema.sql` (runs on Docker compose up)

## Key Versions

- FastAPI: 0.110+
- Uvicorn: 0.29+
- Pydantic: 2.6+
- Python: 3.11+ (3.12 in Docker)
- Node.js: 20 (Alpine)
- React: 18.3.1
- TimescaleDB: latest-pg16

---

*Stack analysis: 2026-03-18*
