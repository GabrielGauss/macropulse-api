# MacroPulse — Production Deployment

## Prerequisites

- VPS: 4+ GB RAM, 2+ vCPUs (TimescaleDB is memory-intensive)
- Docker + Docker Compose
- Domain pointing to server IP
- FRED API key (free at fred.stlouisfed.org)
- Stripe account with products created

## 1. Clone and Configure

```bash
git clone https://github.com/GabrielGauss/macropulse.git
cd macropulse
cp .env.example .env
```

Edit `.env` — required fields for production:

```env
ENV=production
DATABASE_URL=postgresql://macropulse:<password>@timescaledb:5432/macropulse
FRED_API_KEY=<your-fred-key>
OWNER_API_KEY=<generate: python -c "import secrets; print('mp_' + secrets.token_urlsafe(32))">
OWNER_EMAIL=<your-email>

# Ed25519 MTA signing key:
# python -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; k=Ed25519PrivateKey.generate(); print(k.private_bytes_raw().hex())"
MTA_SIGNING_KEY_HEX=<64-char hex>

# Stripe billing
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_STARTER_PRICE_ID=price_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_STARTER_PRODUCT_ID=prod_...
STRIPE_PRO_PRODUCT_ID=prod_...

# Brevo for email alerts
BREVO_API_KEY=<brevo-api-key>

# Anthropic for LLM narrative
ANTHROPIC_API_KEY=sk-ant-...

# Operator alert email (pipeline failure/staleness)
PIPELINE_ALERT_EMAIL=<your-email>
```

## 2. Start Services

```bash
docker compose up -d
```

Starts: TimescaleDB, API server (FastAPI + APScheduler), Nginx.

## 3. Train Initial Models

Models must be trained before the API can serve regime signals:

```bash
docker compose exec api python scripts/retrain_models.py
```

Takes ~5 minutes on first run. Run whenever macro conditions change significantly.

## 4. Configure Stripe Webhooks

In the Stripe Dashboard → Developers → Webhooks, create an endpoint:

- **URL**: `https://api.yourdomain.com/v1/billing/stripe/webhook`
- **Events**: `checkout.session.completed`, `customer.subscription.updated`,
  `customer.subscription.deleted`, `invoice.payment_succeeded`,
  `invoice.payment_failed`, `customer.subscription.trial_will_end`

Copy the signing secret → `STRIPE_WEBHOOK_SECRET` in `.env`.

For IRL Engine subscriptions, create a second endpoint:
- **URL**: `https://api.yourdomain.com/v1/irl/billing/stripe/webhook`
- Same event list. Copy signing secret → `STRIPE_IRL_WEBHOOK_SECRET`.

## 5. Nginx + SSL

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
certbot --nginx -d api.yourdomain.com
```

## 6. Verify

```bash
curl https://api.yourdomain.com/health
# → {"status":"ok","version":"...","checks":{"database":"ok"}}

curl https://api.yourdomain.com/v1/public/regime
# → {"date":"...","regime":"recovery","risk_score":...}
```

## Operations

```bash
# Check pipeline status
curl -H "X-MacroPulse-Key: <owner-key>" https://api.yourdomain.com/v1/pipeline/status

# View logs
docker compose logs api --tail=100 -f

# Retrain models
docker compose exec api python scripts/retrain_models.py

# Database backup
docker compose exec timescaledb pg_dump -U macropulse macropulse \
  | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip -c backup_YYYYMMDD.sql.gz | docker compose exec -T timescaledb psql -U macropulse macropulse

# Force-run the daily pipeline immediately
curl -X POST -H "X-MacroPulse-Key: <owner-key>" https://api.yourdomain.com/v1/pipeline/run
```

## Monitoring

| Endpoint | What to check |
|----------|--------------|
| `GET /health` | `checks.database == "ok"` |
| `GET /metrics` | Prometheus scrape endpoint |
| `GET /v1/pipeline/status` | `last_run` recency, `status == "success"` |
| `GET /v1/drift` | `drift_detected: false` |

The APScheduler runs 4 jobs:
- **Daily Pipeline** — 21:00 UTC (configurable via `PIPELINE_CRON_HOUR`/`PIPELINE_CRON_MINUTE`)
- **Weekly Digest** — Monday 09:00 UTC (email to all newsletter subscribers)
- **Staleness Check** — every 30 minutes (emails `PIPELINE_ALERT_EMAIL` if >26h since last run)
- **DB Pool Metrics** — every 60 seconds (updates Prometheus gauges)

## Required Env Vars (Production Startup Guards)

The API refuses to start if these are missing when `ENV=production`:

| Variable | Requirement |
|----------|-------------|
| `MTA_SIGNING_KEY_HEX` | Valid 64-char Ed25519 hex — raises `ValueError` if invalid |
| `STRIPE_WEBHOOK_SECRET` | Must be set — raises `RuntimeError` if missing |
| `ENV` | Must be `production` to activate all startup guards |
| `CORS_ORIGINS` | Must not contain `*` — raises `RuntimeError` if wildcard |

In `ENV=development`, missing secrets log a warning instead of raising — allowing local dev without credentials.
