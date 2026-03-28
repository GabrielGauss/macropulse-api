# MacroPulse — Production Deployment

## Prerequisites

- VPS: 4+ GB RAM, 2+ vCPUs (TimescaleDB is memory-intensive)
- Docker + Docker Compose
- Domain pointing to server IP
- FRED API key (free at fred.stlouisfed.org)

## 1. Clone and Configure

```bash
git clone https://github.com/GabrielGauss/macropulse.git
cd macropulse
cp .env.example .env
```

Edit `.env` — required fields:
```env
DATABASE_URL=postgresql://macropulse:<password>@postgres:5432/macropulse
FRED_API_KEY=<your-fred-key>
OWNER_API_KEY=<openssl rand -hex 32>
OWNER_EMAIL=<your-email>
# Generate MTA signing key:
# python -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; k=Ed25519PrivateKey.generate(); print(k.private_bytes_raw().hex())"
MTA_SIGNING_KEY_HEX=<64-char hex>
```

## 2. Start Services

```bash
docker compose up -d
```

This starts: PostgreSQL, API server, and frontend build.

## 3. Train Initial Models

Models must be trained before the API can serve regime signals:

```bash
docker compose exec api python scripts/retrain_models.py
```

This takes ~5 minutes on first run.

## 4. Nginx + SSL

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
    }
}
```

```bash
certbot --nginx -d api.yourdomain.com
```

## 5. Verify

```bash
curl https://api.yourdomain.com/health
# → {"status":"ok","version":"0.1.0","checks":{"database":"ok"}}
```

## Operations

```bash
# Check pipeline status
curl -H "X-MacroPulse-Key: <owner-key>" https://api.yourdomain.com/v1/pipeline/status

# View logs
docker compose logs api --tail=100 -f

# Retrain models (run when market conditions change significantly)
docker compose exec api python scripts/retrain_models.py

# Database backup
docker compose exec postgres pg_dump -U macropulse macropulse \
  | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip -c backup_YYYYMMDD.sql.gz | docker compose exec -T postgres psql -U macropulse macropulse
```

## Monitoring

- Health: `GET /health` — check `checks.database == "ok"`
- Pipeline: `GET /v1/pipeline/status` — check `last_run` recency
- Drift: `GET /v1/drift` — watch for `drift_detected: true`
