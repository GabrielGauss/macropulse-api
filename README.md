# MacroPulse

**Real-time macro regime intelligence for quantitative trading.**

MacroPulse runs a daily data pipeline (FRED + market data) through an HMM/PCA model to
classify the current macro regime and deliver it via REST API and WebSocket stream.
It also serves as the Market Truth Anchor (MTA) for [IRL Engine](https://github.com/GabrielGauss/irl-engine) — a pre-execution compliance layer for AI trading agents.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, asyncpg |
| Database | TimescaleDB (PostgreSQL 16) |
| ML | scikit-learn (HMM), arch (GARCH), statsmodels (ARIMA) |
| Frontend | React 18, Vite, Tailwind CSS |
| Infra | Docker Compose, Nginx, Certbot |

## Quick Start (Local Development)

```bash
git clone https://github.com/GabrielGauss/macropulse.git
cd macropulse

# Configure environment
cp .env.example .env
# Required: DATABASE_URL, FRED_API_KEY, OWNER_API_KEY

# Start database
docker compose up -d postgres

# Install and run API
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

# Start frontend (new terminal)
cd frontend && npm install && npm run dev
```

## Testing

```bash
pytest tests/ -v
```

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md).

## API Documentation

See `site/api-docs.html` or the live docs at your deployed instance at `/docs`.

## Architecture

```
FRED / Market Data
        ↓
  Daily Pipeline (APScheduler)
        ↓
  HMM + GARCH + ARIMA
        ↓
  PostgreSQL (TimescaleDB)
        ↓
  FastAPI REST + WebSocket
        ↓
  React Dashboard / External Agents
```

## MTA Integration (IRL Engine)

MacroPulse exposes `GET /v1/regime/current` with an Ed25519-signed regime payload.
This is consumed by IRL Engine as the Market Truth Anchor for pre-execution compliance.
See `docs/mta-spec.md` or [IRL Engine](https://github.com/GabrielGauss/irl-engine/blob/master/docs/public/10-mta-operator-spec.md) for the interface contract.
