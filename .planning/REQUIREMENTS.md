# Requirements: MacroPulse v1.1 — Production Hardening

**Defined:** 2026-03-28
**Core Value:** Signal must be accurate, fresh, and delivered with zero friction — and the infrastructure serving it must be secure, observable, and monetizable.

## v1.1 Requirements

### Security — Secrets

- [ ] **SEC-10**: All secrets (BREVO_API_KEY, MTA_SIGNING_KEY_HEX, FRED_API_KEY, OWNER_API_KEY) removed from `.env` committed to git history via `git filter-repo`; `.env` added to `.gitignore`
- [ ] **SEC-11**: All previously committed secrets rotated: new Brevo API key, new MTA Ed25519 key pair, new owner API key issued
- [ ] **SEC-12**: `.env.example` documents every required environment variable with description and format; no real values present
- [ ] **SEC-13**: Production secrets managed via environment injection (not committed files) — deployment guide updated

### Security — Webhooks

- [x] **SEC-20**: Lemon Squeezy webhook handler rejects all events and returns 500 at startup if `LS_WEBHOOK_SECRET` is not set — silent accept removed
- [x] **SEC-21**: Lemon Squeezy webhook signature verification fails closed: any HMAC mismatch → 401, request logged, no event processed
- [x] **SEC-22**: Paddle webhook handler logs and rejects events with timestamp outside 5-minute replay window (existing guard verified and tested)

### Security — Auth Endpoints

- [x] **SEC-30**: `/v1/auth/register` rate-limited: max 5 registration attempts per IP per hour
- [x] **SEC-31**: `/v1/auth/recover` and `/v1/auth/recover/verify` rate-limited: max 5 OTP attempts per email per 15 minutes; exponential backoff after 3 failures
- [x] **SEC-32**: OTP verification lockout: after 5 failed OTP attempts the OTP is invalidated and a new one must be requested
- [x] **SEC-33**: Rate limit state for auth endpoints persists in DB (not in-memory) — survives process restart

### Security — Infrastructure

- [x] **SEC-40**: `model_artifacts` Docker volume mounted read-only in the API container (`ro` flag in docker-compose.yml) — prevents model substitution via API compromise
- [x] **SEC-41**: Nginx CSP header configured: `Content-Security-Policy` blocks inline scripts, restricts sources to macropulse.live origin
- [x] **SEC-42**: `CORS_ORIGINS` validated at startup — app refuses to start if wildcard `*` is set in production (`ENV=production`)

### Async Database

- [x] **DB-10**: `psycopg2.ThreadedConnectionPool` replaced with `asyncpg` connection pool throughout `database/connection.py` and `database/queries.py`
- [x] **DB-11**: All database query functions are `async def` — no synchronous DB calls blocking FastAPI's event loop
- [x] **DB-12**: Connection pool parameters configurable via env vars: `DB_POOL_MIN`, `DB_POOL_MAX` (defaults 2, 10)
- [x] **DB-13**: All existing tests pass with the async driver; no query regressions

### Observability

- [ ] **OBS-01**: `GET /metrics` endpoint exposes Prometheus metrics in text exposition format (no auth required; document to firewall to internal only)
- [ ] **OBS-02**: Key metrics exposed: `macropulse_api_requests_total` (by endpoint, status), `macropulse_pipeline_runs_total` (by status), `macropulse_pipeline_last_success_timestamp`, `macropulse_active_api_keys` (by tier), `macropulse_db_pool_size`
- [ ] **OBS-03**: Pipeline failure alerting: when `pipeline_runs.status = 'failed'`, an alert fires within 5 minutes via email (Brevo) to the owner address configured in env
- [ ] **OBS-04**: Pipeline staleness alert: if `macropulse_pipeline_last_success_timestamp` is >26 hours old (missed daily run), alert fires
- [ ] **OBS-05**: Grafana dashboard JSON file committed to `infrastructure/grafana/macropulse-dashboard.json` — importable to any Grafana instance

### Billing — Paddle

- [ ] **BILL-01**: Paddle checkout session created via `POST /v1/billing/paddle/checkout` for starter and pro tiers
- [ ] **BILL-02**: Paddle webhook handler processes `subscription.activated`, `subscription.cancelled`, `subscription.updated` events and updates `users.paddle_subscription_status` and `api_keys.tier`
- [ ] **BILL-03**: Paddle webhook idempotency: duplicate event IDs are deduplicated via `webhook_idempotency` table (same pattern as existing Lemon Squeezy dedup)
- [ ] **BILL-04**: `GET /v1/billing/paddle/portal` returns Paddle customer portal URL for subscription management
- [ ] **BILL-05**: Tier downgrade on `subscription.cancelled`: user's API key tier reverted to `free` within one webhook processing cycle

### Compliance — GDPR

- [ ] **GDPR-01**: `DELETE /v1/auth/me` endpoint: deletes the authenticated user's account, all associated API keys, and anonymizes their email in `users` table (replace with `deleted_<uuid>@macropulse.invalid`)
- [ ] **GDPR-02**: User deletion cascades: `api_keys` deactivated, `webhook_idempotency` records for that user's events retained for audit (not deleted), `users.deleted_at` timestamp set
- [ ] **GDPR-03**: Privacy policy page at `macropulse.live/privacy` documenting data categories, retention periods, and erasure rights
- [ ] **GDPR-04**: Data retention: `email_verifications` records older than 30 days auto-deleted via daily cleanup job (prevent unbounded OTP table growth)

### Testing

- [ ] **TEST-01**: Auth route tests: registration, OTP verification, recovery, key rotation — using FastAPI TestClient with DB fixtures
- [ ] **TEST-02**: Billing webhook tests: Paddle `subscription.activated` and `subscription.cancelled` with valid and invalid signatures
- [ ] **TEST-03**: Lemon Squeezy webhook tests: valid signature, invalid signature, missing secret (must return 500)
- [ ] **TEST-04**: Rate limit middleware tests: OTP endpoint lockout after 5 attempts; auth endpoint per-IP throttle
- [ ] **TEST-05**: DB migration tests: all migrations in `database/migrations/` apply cleanly to a fresh TimescaleDB schema in CI

## Future Requirements

### Database Reliability

- **DB-F01**: PostgreSQL streaming replication to a hot standby replica
- **DB-F02**: Automated daily backup with point-in-time recovery (PITR) via pg_basebackup to S3

### Signal Expansion

- **SIG-F01**: Intraday signal updates (4h cadence) using on-chain and funding rate data
- **SIG-F02**: Crypto-native signal layer: on-chain liquidity, open interest, funding rates as additional PCA features

### Commercial

- **COMM-F01**: Self-serve registration UI (email → OTP → API key issued without manual steps)
- **COMM-F02**: Usage dashboard: per-key request history, rate limit headroom, next reset time

## Out of Scope

| Feature | Reason |
|---------|--------|
| Kubernetes / managed cloud | Single VPS constraint; acceptable for current scale |
| Model retraining UI | CLI is sufficient; UI adds complexity without value |
| Mobile app | Not the product's target use case |
| Real-time chat / community | Out of scope for a signal API product |
| Database replication (v1.1) | Single VPS; deferred to v2.0 with cloud migration |
| SGX/TEE model attestation | v3 roadmap item |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-10 | Phase 6 | Pending |
| SEC-11 | Phase 6 | Pending |
| SEC-12 | Phase 6 | Pending |
| SEC-13 | Phase 6 | Pending |
| SEC-20 | Phase 6 | Complete |
| SEC-21 | Phase 6 | Complete |
| SEC-22 | Phase 6 | Complete |
| SEC-40 | Phase 6 | Complete (06-03) |
| SEC-41 | Phase 6 | Complete (06-03) |
| SEC-42 | Phase 6 | Complete |
| SEC-30 | Phase 7 | Complete (07-01) |
| SEC-31 | Phase 7 | Complete (07-01) |
| SEC-32 | Phase 7 | Complete (07-01) |
| SEC-33 | Phase 7 | Complete (07-01) |
| DB-10 | Phase 8 | Complete (08-00, 08-01) |
| DB-11 | Phase 8 | Complete (08-01) |
| DB-12 | Phase 8 | Complete (08-00) |
| DB-13 | Phase 8 | Complete (08-02) |
| OBS-01 | Phase 9 | Pending |
| OBS-02 | Phase 9 | Pending |
| OBS-03 | Phase 9 | Pending |
| OBS-04 | Phase 9 | Pending |
| OBS-05 | Phase 9 | Pending |
| BILL-01 | Phase 10 | Pending |
| BILL-02 | Phase 10 | Pending |
| BILL-03 | Phase 10 | Pending |
| BILL-04 | Phase 10 | Pending |
| BILL-05 | Phase 10 | Pending |
| GDPR-01 | Phase 11 | Pending |
| GDPR-02 | Phase 11 | Pending |
| GDPR-03 | Phase 11 | Pending |
| GDPR-04 | Phase 11 | Pending |
| TEST-01 | Phase 12 | Pending |
| TEST-02 | Phase 12 | Pending |
| TEST-03 | Phase 12 | Pending |
| TEST-04 | Phase 12 | Pending |
| TEST-05 | Phase 12 | Pending |

**Coverage:**
- v1.1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 — traceability confirmed, roadmap created*
