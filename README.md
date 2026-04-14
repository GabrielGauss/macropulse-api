# MacroPulse

**Probabilistic macro regime intelligence for quantitative trading and autonomous agents.**

MacroPulse runs a daily data pipeline (FRED + market data) through a PCA + Gaussian HMM model to
classify the current macro environment into one of four regimes and deliver it via REST API,
WebSocket stream, and automated alerts. It also serves as the **Market Truth Anchor (MTA)** for
[IRL Engine](https://github.com/GabrielGauss/irl-engine) — a cryptographic compliance protocol
for AI trading agents.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, asyncpg |
| Database | TimescaleDB (PostgreSQL 16) |
| ML | scikit-learn (Gaussian HMM), statsmodels (ARIMA), arch (GARCH) |
| AI | Anthropic Claude Haiku (LLM narrative for regime commentary) |
| Frontend | React 18, Vite, Tailwind CSS |
| Billing | Stripe Checkout + Customer Portal |
| Alerts | Brevo (email), Discord webhooks, X/Twitter OAuth 1.0a |
| Infra | Docker Compose, Nginx, Certbot, APScheduler |

## Regimes

| Regime | Equity Exposure | Meaning |
|--------|----------------|---------|
| Expansion | 100% | Fed liquidity ample, spreads tight, vol suppressed |
| Recovery | 75% | Liquidity re-injecting after stress, positive bias |
| Tightening | 25% | Fed draining, spreads widening, reduce exposure |
| Risk-Off | 0% | Acute stress, capital preservation only |

## Quick Start (Local Development)

```bash
git clone https://github.com/GabrielGauss/macropulse.git
cd macropulse

# Configure environment
cp .env.example .env
# Required: FRED_API_KEY, OWNER_API_KEY, MTA_SIGNING_KEY_HEX

# Start database
docker compose up -d timescaledb

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

See [DEPLOYMENT.md](DEPLOYMENT.md) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## API Reference

Full documentation at [macropulse.live/api-docs.html](https://macropulse.live/api-docs.html)
or the live Swagger UI at `https://api.macropulse.live/docs`.

### Endpoint Map

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check + DB status |
| GET | `/v1/public/regime` | None | Live regime + interpretation (free entry point) |
| GET | `/v1/public/chart-data` | None | 730 days of regime history for the marketing chart |
| GET | `/v1/public/latest` | None | Current regime snapshot for terminal display |
| POST | `/v1/public/subscribe` | None | Newsletter subscribe |
| GET | `/v1/signals/latest` | API key | Full signal package — regime, scorecard, factors, narrative |
| GET | `/v1/signals/{date}` | API key | Signal package for a specific date |
| GET | `/v1/signals/range` | API key | Signal packages for a date range |
| GET | `/v1/signals/history` | API key | Regime history with probabilities (90 days default) |
| GET | `/v1/regime/current` | API key | Ed25519-signed regime for IRL Engine MTA |
| GET | `/v1/regime/history` | API key | Full regime history with probabilities |
| GET | `/v1/liquidity` | Paid | Net Fed liquidity decomposition |
| GET | `/v1/scorecard` | Paid | Macro scorecard across 5 factor domains |
| GET | `/v1/forecast` | Paid | 5-day ARIMA regime probability forecast |
| POST | `/v1/backtest` | Paid | Regime-conditional strategy backtest |
| GET | `/v1/performance` | Paid | Strategy vs buy-and-hold performance |
| GET | `/v1/commentary` | Paid | LLM-generated macro narrative |
| GET | `/v1/account` | API key | Account info, tier, usage, billing portal link |
| POST | `/v1/webhook/set` | Pro | Configure regime-change webhook |
| GET | `/v1/irl/heartbeat` | IRL key | Signed heartbeat for Layer 2 anti-replay |
| GET | `/v1/irl/audit` | IRL Audit key | Deep factor + stress decomposition (L2) |
| POST | `/v1/auth/register` | None | Start email registration |
| POST | `/v1/auth/verify` | None | Complete registration, receive API key |
| POST | `/v1/auth/rotate` | API key | Rotate API key |
| DELETE | `/v1/auth/me` | API key | GDPR erasure — anonymise account |
| GET | `/v1/billing/stripe/checkout` | API key | Create Stripe Checkout session |
| GET | `/v1/billing/stripe/portal` | API key | Create Stripe Customer Portal session |

## Architecture

```
FRED / Market Data
        ↓
  Daily Pipeline (APScheduler — 21:00 UTC)
        ↓
  PCA → Gaussian HMM → Regime Classifier
        ↓
  TimescaleDB (PostgreSQL 16)
        ↓
  ┌─────────────────────────────────────────────────────┐
  │  FastAPI REST + WebSocket                           │
  │  ├── /v1/signals/*       (regime + scorecard)       │
  │  ├── /v1/forecast        (ARIMA 5-day projection)   │
  │  ├── /v1/irl/*           (MTA heartbeat + audit)    │
  │  └── /v1/public/*        (unauthenticated)          │
  └─────────────────────────────────────────────────────┘
        ↓                          ↓
  React Dashboard          IRL Engine agents
  (api.macropulse.live)    (pre-execution compliance)
        ↓
  Alerts: Email + Discord + X/Twitter
  (regime change + weekly digest)
```

## MTA Integration (IRL Engine)

MacroPulse exposes `GET /v1/regime/current` with an Ed25519-signed regime payload.
IRL Engine consumes this as its **Market Truth Anchor** for pre-execution compliance checks.
The `GET /v1/irl/heartbeat` endpoint provides anti-replay tokens for Layer 2 (L2) operation.

See [IRL Engine](https://github.com/GabrielGauss/irl-engine) or the
[IRL Whitepaper](https://macropulse.live/irl-whitepaper.html) for the full protocol specification.

## Scheduler Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Daily Pipeline | 21:00 UTC | FRED fetch → PCA → HMM → DB write → alerts |
| Weekly Digest | Mon 09:00 UTC | Email digest to all newsletter subscribers |
| Staleness Check | Every 30 min | Alert if pipeline hasn't run in >26h |
| DB Pool Metrics | Every 60s | Prometheus pool size/idle gauges |
