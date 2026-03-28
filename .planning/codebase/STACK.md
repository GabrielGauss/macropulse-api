# Technology Stack

**Analysis Date:** 2026-03-28

## Languages

**Primary:**
- Python 3.11+ - Backend API, data pipelines, ML models
- TypeScript/JavaScript - Frontend dashboard (React, Vite)

**Secondary:**
- SQL - TimescaleDB queries (PostgreSQL dialect)
- Bash - Deployment and utility scripts

## Runtime

**Environment:**
- Python 3.12 (Docker slim image) / 3.11+ (local development)
- Node.js 20 (Alpine for Docker builds)

**Package Manager:**
- Python: pip with `requirements.txt`
- Node.js: npm with `frontend/package.json`
- Lockfiles: `package-lock.json` for frontend, `requirements.txt` frozen for backend

## Frameworks

**Core:**
- FastAPI 0.110+ - REST API and WebSocket server (`api/main.py`)
- React 18.3.1 - Dashboard UI with Vite
- Uvicorn 0.29+ - ASGI server (production-grade)

**Testing:**
- pytest - Test runner with config at `pytest.ini`

**Build/Dev:**
- Vite 5.3.1 - Frontend bundler and dev server (`frontend/vite.config.js`)
- Tailwind CSS 3.4.4 - Utility-first CSS framework
- PostCSS 8.4.38 with Autoprefixer 10.4.19 - CSS vendor prefixing
- Docker & Docker Compose - Full stack containerization
- Nginx (Alpine) - Reverse proxy, SSL termination, static file serving
- Certbot - Let's Encrypt certificate renewal automation

## Key Dependencies

**Critical Backend:**
- `pydantic>=2.6` - Request/response validation and settings management
- `pydantic-settings>=2.2` - Environment variable typed configuration (`config/settings.py`)
- `psycopg2-binary>=2.9` - PostgreSQL driver with ThreadedConnectionPool (2-10 connections)
- `APScheduler>=3.10` - Background job scheduling for daily pipeline (18:30 UTC)
- `email-validator>=2.1` - Email validation for user registration
- `cryptography>=42.0` - Ed25519 key handling for MTA signature verification

**Data Ingestion:**
- `fredapi>=0.5` - Federal Reserve Economic Data API (`data/ingestion/fred_client.py`)
- `yfinance>=0.2.36` - Yahoo Finance for VIX, equity indices, DXY (`data/ingestion/market_client.py`)
- `httpx>=0.27` - Async HTTP client (Paddle, Brevo, Anthropic API calls)

**Scientific/ML:**
- `numpy>=1.26` - Numerical array operations
- `pandas>=2.2` - Time series and DataFrame manipulation
- `scikit-learn>=1.4` - HMM, PCA, machine learning pipeline
- `hmmlearn>=0.3` - Gaussian Hidden Markov Model (regime classification)
- `arch>=6.0` - GARCH volatility modeling
- `statsmodels>=0.14` - ARIMA forecasting
- `joblib>=1.3` - Model artifact serialization

**AI/Integration:**
- `anthropic>=0.40` - Claude Sonnet API for AI commentary (`api/routes/commentary.py`)
- `plotly>=5.20` - Interactive data visualization
- `websockets>=12.0` - WebSocket protocol for real-time regime stream (`/ws/regime`)
- `python-dotenv>=1.0` - Environment variable loading

**Frontend:**
- `react^18.3.1` - UI framework
- `react-dom^18.3.1` - React DOM binding
- `recharts^2.12.7` - React charting library (regime, factors, liquidity charts)
- `lucide-react^0.383.0` - Icon library
- Build deps: `@vitejs/plugin-react`, `autoprefixer`, `postcss`, `tailwindcss`, `vite`

## Configuration

**Environment:**
- Loaded via `pydantic-settings` from `.env` file
- Location: `config/settings.py` with `get_settings()` LRU-cached singleton
- `.env.example` documents all variables (FRED_API_KEY, ANTHROPIC_API_KEY, database credentials, billing keys, etc.)
- Development defaults for local setup without full secrets

**Build:**
- `pyproject.toml` contains:
  - ruff: target Python 3.11, line length 100, isort known-first-party groups
  - mypy: strict mode, ignore_missing_imports
- Dockerfile uses multi-stage:
  - Stage 1: Node 20 Alpine builds frontend to `dist/`
  - Stage 2: Python 3.12 slim installs backend + copies built frontend
  - Exposes port 8000 (Uvicorn)

## Platform Requirements

**Development:**
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (for containerized stack)
- PostgreSQL 16 with TimescaleDB extension (via Docker image `timescale/timescaledb:latest-pg16`)

**Production:**
- Docker runtime for containerized API
- TimescaleDB 16 (PostgreSQL 16 + TimescaleDB extension)
- Nginx (reverse proxy, SSL termination)
- Let's Encrypt certificates (renewed via Certbot in separate container)
- APScheduler runs in-process via FastAPI lifespan hooks

## Database

**Primary:** TimescaleDB (PostgreSQL 16)
- Time-series hypertables: `macro_features`, `macro_factors`, `macro_regimes`, `model_drift_metrics`
- Connection pooling: psycopg2 ThreadedConnectionPool (min=2, max=10)
- URL format: `postgresql://{user}:{password}@{host}:{port}/{name}`
- Schema: `database/schema.sql` (applied via migrations in `database/migrations/`)
- Migrations run on app startup via `_run_migrations()` in `api/main.py`

## Key Versions

- FastAPI: 0.110+
- Uvicorn: 0.29+
- Pydantic: 2.6+
- Python: 3.11+ (3.12 in Docker)
- Node.js: 20 (Alpine)
- React: 18.3.1
- Vite: 5.3.1
- TimescaleDB: latest-pg16
- Nginx: Alpine
- Certbot: Latest

---

*Stack analysis: 2026-03-28*
