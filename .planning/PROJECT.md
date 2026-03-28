# MacroPulse

## What This Is

MacroPulse is a macro regime signal API and developer dashboard that classifies current market conditions into one of four regimes (expansion, recovery, tightening, risk_off) using a frozen HMM/PCA/GARCH model trained on Fed liquidity, yield curve, and market data. It serves quant traders, algo funds, and financial developers who need structured macro context for portfolio allocation decisions via a simple REST API.

## Core Value

**The signal must be accurate, fresh, and delivered with zero friction** — if the regime classification is stale, wrong, or the API is hard to integrate, everything else fails.

## Requirements

### Validated

<!-- Shipped and confirmed working in production -->

- ✓ Daily pipeline: FRED + market ingestion → feature engineering → HMM inference → regime classification — v0
- ✓ REST API: `/v1/signals/latest`, `/v1/signals/{date}`, `/v1/signals/range`, `/v1/regime/current`, `/v1/regime/history`, `/v1/liquidity`, `/v1/scorecard`, `/v1/backtest`, `/v1/performance` — v0
- ✓ WebSocket real-time regime streaming — v0
- ✓ Tier-based API key auth (free/paid/owner) with rate limiting — v0
- ✓ React dashboard with regime signal card, risk score, equity exposure, signal conviction — v0
- ✓ Regime calendar (heatmap grid) with date range filtering — v0
- ✓ AI macro commentary panel (Claude-powered, requires ANTHROPIC_API_KEY) — v0
- ✓ Marketing site (macropulse.live) with hero, integration, FAQ sections — v0
- ✓ API docs page at macropulse.live/api-docs — v0
- ✓ Webhook delivery system (regime change alerts) — v0
- ✓ APScheduler daily pipeline at 18:30 UTC — v0

### Active

<!-- v1.1 milestone — production hardening -->

- [ ] **SECURITY**: All secrets removed from `.env` in git history; rotated and stored in environment only
- [ ] **SECURITY**: Lemon Squeezy webhook rejects all events when `LS_WEBHOOK_SECRET` is unset (no silent accept)
- [ ] **SECURITY**: OTP and auth endpoints rate-limited with exponential backoff (brute-force protection)
- [ ] **SECURITY**: `model_artifacts` volume is read-only from API container
- [ ] **ASYNC**: `psycopg2` replaced with `asyncpg` or `psycopg3` async driver (eliminate thread-pool blocking)
- [ ] **OBSERVABILITY**: Prometheus `/metrics` endpoint exposed; Grafana dashboard with pipeline failure alerting
- [ ] **BILLING**: Paddle integration complete and live (checkout, subscription management, webhook)
- [ ] **COMPLIANCE**: GDPR user data deletion endpoint
- [ ] **TESTING**: Auth routes, billing webhooks, and DB migrations covered by automated tests
- [ ] **INFRA**: Automated pipeline failure alerting (Telegram/email on pipeline `status=failed`)

### Out of Scope

- Mobile app — not planned
- Real-time chat or community features — not the product
- Model retraining UI — ops tooling, CLI is sufficient
- Database replication — single VPS constraint; acceptable risk for now
- Kubernetes / managed cloud migration — deferred to v2.0

## Current Milestone: v1.1 — Production Hardening

**Goal:** Close all critical security gaps, eliminate the sync DB bottleneck, add observability, and complete Paddle billing — making MacroPulse institutionally deployable and monetization-ready.

**Target features:**
- Secret rotation + `.env` git history purge
- Webhook signature enforcement (no silent bypass)
- OTP brute-force protection
- Async DB driver migration (psycopg2 → asyncpg)
- Prometheus metrics + pipeline failure alerting
- Paddle billing completion
- GDPR erasure endpoint
- Test coverage for auth, webhooks, migrations

## Context

- Live at `api.macropulse.live` (Docker on VPS, Nginx + Certbot)
- Marketing site at `macropulse.live` (same deployment)
- v1.0 completed: bugs fixed, dashboard polished, marketing site ready, API docs consolidated
- Professional assessment scored 6.0/10 — security gaps are the primary blocker for institutional adoption
- `.env` committed to repo contains live Brevo API key and MTA Ed25519 private key — must be rotated immediately
- Synchronous psycopg2 in async FastAPI is the dominant performance bottleneck under concurrent load
- Paddle approval pending; Lemon Squeezy webhook has silent-accept vulnerability when secret unset

## Constraints

- **Tech stack**: Python/FastAPI + React/Vite + TimescaleDB — no rewrites
- **Deployment**: Docker Compose on single VPS — no Kubernetes or managed cloud yet
- **Zero downtime**: Fixes must deploy without service interruption
- **No breaking API changes**: Existing API consumers must not be affected

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|------------|
| Frozen model pattern (train once, infer daily) | Deterministic, auditable, no daily retraining risk | ✓ Good |
| TimescaleDB over raw PostgreSQL | Native time-series hypertables, chunked queries | ✓ Good |
| APScheduler in-process vs external cron | Simpler deployment, single container | ⚠️ Revisit (single point of failure) |
| Separate alerting.py + alerts.py | Accident — needs consolidation | ⚠️ Revisit |
| Owner key in source | Expedient for v0 | ⚠️ Revisit — fix in v1.0 |

---
*Last updated: 2026-03-28 — v1.1 milestone started (production hardening)*
