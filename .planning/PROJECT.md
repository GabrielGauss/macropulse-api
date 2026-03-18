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

<!-- v1.0 milestone — ship-ready -->

- [ ] Dashboard calendar shows correct date range for user's tier on mount
- [ ] API docs consolidated into one excellent page
- [ ] Marketing site hero section optimized (code snippet vs better hook)
- [ ] FAQ accordion closes on re-click
- [ ] Security: owner key moved out of source code
- [ ] Duplicate alerting system consolidated
- [ ] Data lag off-by-one bug fixed
- [ ] Rate limit race condition fixed (async-safe counter)

### Out of Scope

- Stripe/Paddle payment integration — next milestone
- User self-serve registration UI — next milestone
- Mobile app — not planned
- Real-time chat or community features — not the product
- Model retraining UI — ops tooling, CLI is sufficient

## Context

- Live at `api.macropulse.live` (Docker on VPS, Nginx + Certbot)
- Marketing site at `macropulse.live` (same deployment)
- Owner API key currently hardcoded in `api/auth.py:86` — critical fix needed
- Two alerting modules coexist: `services/alerting.py` and `services/alerts.py` — causes double-fires
- Zero automated tests across the entire codebase — testing left for future milestone
- AI commentary panel is built but locked (no ANTHROPIC_API_KEY in prod env yet)
- Calendar `viewDays` initializes to 30 (free tier default) even for owner, because tier resolves async after mount

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
*Last updated: 2026-03-18 — initial GSD initialization from codebase map*
