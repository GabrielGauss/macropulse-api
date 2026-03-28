# Codebase Concerns

**Analysis Date:** 2026-03-28

## CRITICAL SECURITY ISSUES

### Secrets Committed to Repository

**Issue:** API keys and cryptographic material checked into version control.
- Files: `.env` (present in repo despite `.gitignore`)
  - Contains: `BREVO_API_KEY`, `MTA_SIGNING_KEY_HEX`, `FRED_API_KEY`, etc.
- Impact: CRITICAL — any clone/leak of repository exposes all API credentials to attackers
- Root cause: `.env` committed despite being in `.gitignore` (file already exists in repo history)
- Fix approach:
  1. Immediately rotate all exposed API keys (BREVO, FRED, MTA signing key)
  2. Remove `.env` from git history: `git filter-branch --tree-filter 'rm -f .env'` or BFG
  3. Add pre-commit hook to prevent `.env` commits
  4. Enforce `.env` exclusion in CI/CD pipeline
  5. Document secrets management: use environment-only (Docker secrets, K8s Secrets, Vault)

---

### Lemon Squeezy Webhook Signature Validation Bypass

**Issue:** Webhook silently returns `True` when `LS_WEBHOOK_SECRET` not set → subscription fraud risk.
- Files: `api/routes/billing.py` line 259-261
- Code:
  ```python
  def _ls_verify_signature(raw_body: bytes, signature: str) -> bool:
      secret = os.getenv("LS_WEBHOOK_SECRET", "").strip()
      if not secret:
          logger.warning("LS_WEBHOOK_SECRET not set — skipping signature check")
          return True  # ← ALLOWS UNAUTHENTICATED WEBHOOKS
  ```
- Attack vector: Attacker sends forged webhook event with `{"variant_name": "pro", "user_email": "victim@example.com"}` → victim's tier upgraded without payment
- Impact: CRITICAL — complete bypass of billing integrity
- Fix approach:
  1. Make `LS_WEBHOOK_SECRET` required in production settings
  2. Raise `HTTPException(500)` if secret missing (fail closed, not open)
  3. Add webhook signature validation test
  4. Log all webhook accepts (for audit trail of fraud attempts)
  5. Add monitoring alert: "Unsigned LS webhook received"

---

### OTP Brute Force — No Rate Limiting on Auth Endpoints

**Issue:** 6-digit OTP codes brute-forceable on `/v1/auth/verify` and `/v1/auth/recover/verify` endpoints.
- Files: `api/routes/auth.py` lines 92-105 (verify), 192-206 (recover/verify)
- Rate limit status: Both endpoints exempt from `_EXEMPT_PATHS` in `api/middleware/rate_limit.py` line 42
  ```python
  "/v1/auth/register", "/v1/auth/recover", "/v1/auth/recover/verify",
  ```
- Attack: Attacker can submit 10⁶ possible codes (1-999999) with no delay; brute force takes ~minutes on high-concurrency load
- Impact: CRITICAL — account takeover for any user
- Fix approach:
  1. Remove `/v1/auth/recover/verify` from exempt paths; apply rate limiting
  2. Add per-email brute-force protection: max 5 failed attempts per email per hour
  3. Implement exponential backoff: 1s after 1st failure, 5s after 2nd, 30s after 3rd, etc.
  4. Store failed attempts in database (not in-memory; survives restarts)
  5. Add test: attempt 6 wrong codes, verify 7th is rejected even if correct
  6. Monitor: alert on >3 failed verifications for same email within 1h

---

### Synchronous psycopg2 in Async FastAPI — Thread Pool Starvation

**Issue:** All database queries use synchronous `psycopg2` (blocking I/O) in async context.
- Files: `database/connection.py` (ThreadedConnectionPool), used throughout `api/routes/`
- Problem: Blocking DB calls consume uvicorn worker threads; under high concurrency, thread pool exhausts → API hangs
- Configuration: `_POOL_MIN = 2, _POOL_MAX = 10` (line 28-29)
  - With 1 concurrent user per thread: max 10 users before queueing
  - Under 1000 concurrent WebSocket clients + 100 API users → guaranteed thread starvation
- Impact: HIGH — API becomes unresponsive during load
- Scaling limit: ~50-100 concurrent requests before degradation
- Fix approach:
  1. Migrate to async PostgreSQL client: `asyncpg` (drop-in replacement)
  2. Convert all queries to async: `async def get_user(...) → dict`
  3. Use `asyncpg` connection pool with configurable min/max
  4. Add load test: 1000 concurrent requests; verify <100ms p99 latency
  5. Temporary mitigation: Increase `_POOL_MAX` to 50, run multiple API containers with load balancer

---

### No Rate Limiting on OTP Generation (Resource Exhaustion)

**Issue:** `/v1/auth/register` and `/v1/auth/recover` endpoints exempt from rate limiting.
- Files: `api/middleware/rate_limit.py` line 42
- Exempt paths:
  ```python
  "/v1/auth/register", "/v1/auth/recover", "/v1/auth/recover/verify",
  ```
- Attack: Attacker can call `/register` with unlimited email addresses → email spam DOS, database bloat
- Impact: MEDIUM-HIGH — denial of service; email server overload
- Fix approach:
  1. Apply rate limiting to `/register` and `/recover` per IP (not exempt)
  2. Suggested limits:
     - Anonymous IP: 5 registrations/hour
     - Registered user: 10 recovery requests/day
  3. Add monitoring: alert if >100 registrations/hour from single IP
  4. Implement email verification cleanup: auto-delete unverified registrations after 24h

---

### No Database Replication (Single Point of Failure)

**Issue:** Single PostgreSQL instance, no replication or failover.
- Files: `docker-compose.yml` line 5-24 (single `timescaledb` service)
- Current state: `timescale_data` volume (local or single-host only)
- Impact: HIGH — any database outage = API down; no recovery
- Fix approach:
  1. Implement PostgreSQL streaming replication (Primary + Replica)
  2. Use Patroni or PgBouncer for automatic failover
  3. Test failover: stop primary, verify replica takes over
  4. Add monitoring: alert if replica lag > 1 second
  5. Document backup strategy: daily pg_dump to S3 (current: none)

---

## High-Priority Security & Reliability Issues

### Model Artifacts Volume Writable from API Container — Model Substitution Risk

**Issue:** `model_artifacts` volume mounted writable to API container; attacker can replace trained models.
- Files: `docker-compose.yml` line 45
  ```yaml
  volumes:
    - model_artifacts:/app/models/artifacts  # writable so retrain works
  ```
- Attack: Attacker with API container access (or RCE) replaces `pca_v2.pkl`, `hmm_v2.pkl` → model produces attacker-controlled regime signals
- Impact: HIGH — signal integrity compromised; can induce false trading signals
- Fix approach:
  1. Separate read-only model serving from retraining process
  2. Create separate retraining container with write access to artifacts
  3. API container mounts artifacts as read-only
  4. Implement model signing: `sign_model()` writes `.sig` file; `load_model()` verifies signature before use
  5. Hash verification: compute SHA256 of model files on startup; alert if mismatch

---

### No CSRF Protection on State-Changing Endpoints

**Issue:** POST endpoints (`/webhook/set`, `/billing/checkout`, etc.) accept requests without CSRF tokens.
- Files: `api/main.py` (no CsrfMiddleware)
- Vulnerable endpoints:
  - `POST /v1/webhook/set` — changes webhook URL
  - `POST /v1/billing/checkout` — initiates payment
  - `POST /v1/auth/rotate` — rotates API key
- Attack: Attacker tricks authenticated user into visiting malicious site; site posts to `/webhook/set` with attacker's URL → user's signals sent to attacker
- Impact: MEDIUM — webhook hijacking, state changes without user consent
- Mitigating factors: API key in header (not cookie), so CSRF less likely than traditional web apps
- Fix approach:
  1. Add CSRF token to all POST/PUT/DELETE endpoints
  2. Implementation options:
     - Use double-submit cookie pattern (API key + CSRF token)
     - For SPA: issue CSRF token on `/auth/me`, require in `X-CSRF-Token` header
  3. Exempt endpoints: internal webhooks (Paddle, LS)
  4. Test: attempt CSRF on `/webhook/set`, verify rejected without token

---

### No GDPR Right to Erasure Endpoint

**Issue:** No endpoint to delete user data; violates GDPR Article 17.
- Files: `database/queries.py`, `api/routes/` (no delete operations)
- Current state: Users can rotate keys but never delete account
- Impact: MEDIUM-LEGAL — GDPR compliance gap
- Fix approach:
  1. Add `DELETE /v1/auth/account` endpoint (requires API key auth)
  2. Implement hard deletion: remove from `users`, `api_keys`, webhooks
  3. Soft delete alternative: mark user as deleted; zero out PII; retain logs
  4. Test: create user → delete → verify inaccessible
  5. Document in API: "Right to be forgotten: request account deletion"

---

## Medium-Priority Issues

### No Prometheus Metrics / Observability

**Issue:** No metrics collection; can't observe API performance, error rates, or pipeline health.
- Files: No metrics middleware found in `api/main.py`
- Current observability: Logs only
- Impact: MEDIUM — ops team blind to issues until they cause outages
- Fix approach:
  1. Integrate `prometheus-client` into FastAPI
  2. Add metrics:
     - Request latency histogram: `request_duration_seconds`
     - Error rates: `http_requests_total{status}`
     - DB connection pool: `db_pool_connections{state}`
     - Pipeline run duration: `pipeline_duration_seconds`
     - Rate limit hits: `rate_limit_exceeded_total`
  3. Export endpoint: `/metrics` for Prometheus scraping
  4. Dashboard: Grafana for API latency, error rates, pipeline status

---

### No Automated Pipeline Failure Alerting

**Issue:** Pipeline failures logged but not alerted; ops team unaware until users complain.
- Files: `data/pipelines/daily_pipeline.py` (logs errors but doesn't notify)
- Current state: `logger.error()` calls but no Slack/email alerts
- Impact: MEDIUM — delayed response to signal delivery failures
- Fix approach:
  1. Add alerting on pipeline failure:
     - Check `pipeline_runs.status = 'error'` every 5 minutes
     - Alert if status != 'success' after scheduled run time (18:30 UTC)
  2. Channels: Slack → #macropulse-alerts, PagerDuty for on-call
  3. Include in alert: error message, run duration, data lag
  4. Test: simulate pipeline failure, verify alert fires within 5 minutes

---

### Limited Test Coverage — Auth, Webhooks, Migrations Untested

**Issue:** Critical paths have no automated tests.
- Files: `tests/test_pipeline_quality.py` (only pipeline tests; no auth, webhook, migration tests)
- Missing coverage:
  - `api/routes/auth.py` — registration, verification, key rotation
  - `api/routes/billing.py` — Paddle/LS webhook handlers
  - `database/migrations/` — schema changes not tested
  - `api/middleware/rate_limit.py` — race conditions not tested
- Impact: HIGH — bugs discovered in production (auth bypass, webhook failures)
- Fix approach:
  1. Add test files:
     - `tests/test_auth_registration.py` — register, verify, recover flow
     - `tests/test_billing_webhooks.py` — Paddle/LS webhook mocking
     - `tests/test_rate_limiting.py` — concurrent requests, edge cases
     - `tests/test_migrations.py` — run migrations on test DB, verify schema
  2. Coverage target: 80%+ for `api/` and `database/`
  3. CI/CD gate: fail deployment if coverage drops

---

### Timezone Bug in Rate Limit Reset

**Issue:** Rate limit reset uses `dt.date.today()` (system timezone) instead of UTC.
- Files: `api/middleware/rate_limit.py` line 71
  ```python
  def _reset_ts() -> int:
      tomorrow = dt.date.today() + dt.timedelta(days=1)  # ← system timezone
  ```
- Impact: MEDIUM — if API server in non-UTC timezone, rate limit resets at wrong time
- Fix approach:
  1. Use UTC-aware datetime:
     ```python
     tomorrow = dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1)
     ```
  2. Ensure container runs in UTC: `TZ=UTC` in docker-compose
  3. Test: run in non-UTC timezone, verify reset at midnight UTC

---

### WebSocket Broadcasts Swallow Exceptions

**Issue:** Exception in one client's send breaks broadcast loop for all clients.
- Files: `api/routes/websocket.py` lines 55-58 (catch-all exception handler)
- Code:
  ```python
  try:
      await client_conn.send_json(...)
  except Exception:
      pass  # ← silently drops failed client
  ```
- Impact: MEDIUM — clients miss updates if previous client connection stale
- Fix approach:
  1. Remove failed connection from set on send error
  2. Log errors: `logger.error("WebSocket send failed for %s", client_conn.client, exc_info=True)`
  3. Graceful degradation: send to all successful clients, log failed ones
  4. Test: disconnect client mid-broadcast, verify other clients receive update

---

## Medium-Priority Tech Debt

### Duplicate Alerting Logic

**Issue:** Two separate alert dispatch systems.
- Files: `services/alerting.py` and `services/alerts.py`
- Impact: MEDIUM — code duplication; confusion about which is authoritative
- Fix approach:
  1. Consolidate into single `services/alerts.py`
  2. Remove one implementation
  3. Update all callers in `data/pipelines/daily_pipeline.py`

---

### In-Process FRED Cache Unbounded Growth

**Issue:** FRED data cached in memory dict without cleanup.
- Files: `data/ingestion/fred_client.py` line 24
- Problem: Cache grows forever; after 1 year, may consume gigabytes
- Impact: MEDIUM — memory leak; stale data if TTL check fails
- Fix approach:
  1. Add periodic cleanup: every 24 hours, remove entries older than 24 hours
  2. Or switch to Redis with automatic expiration
  3. Log cache size: `logger.info("FRED cache size: %.1f MB", cache_memory_estimate())`

---

### Model Version Migration Incomplete

**Issue:** Hard-coded feature column mappings for v1 vs v2; no registry.
- Files: `data/pipelines/daily_pipeline.py` line 160
- Problem: Adding v3+ requires code changes in multiple places
- Impact: MEDIUM — brittle; error-prone
- Fix approach:
  1. Create version registry:
     ```python
     FEATURE_MAPS = {
         "v1": ["col1", "col2", ...],
         "v2": ["col1", "col2", ...],
     }
     ```
  2. Use in pipeline: `cols = FEATURE_MAPS[DEFAULT_MODEL_VERSION]`

---

### Database Schema Lacks Constraints

**Issue:** `macro_regimes.regime` and `volatility_state` are TEXT without CHECK constraints.
- Files: `database/schema.sql` line 74, 80
- Problem: Invalid regime values (typos, garbage) silently persist
- Impact: MEDIUM — invalid data may break downstream queries
- Fix approach:
  1. Add CHECK constraints:
     ```sql
     ALTER TABLE macro_regimes ADD CHECK (
       regime IN ('expansion', 'tightening', 'risk_off', 'recovery')
     );
     ```
  2. Enforce in code: validate before INSERT

---

### Rate Limiter Anonymous Counter Has Race Condition

**Issue:** In-memory `_anon_counters` dict incremented without locking in async context.
- Files: `api/middleware/rate_limit.py` line 219 (inside async lock, actually safe)
- Current code: Uses `_anon_locks[client_ip]` so actually protected
- Status: NOT A BUG — false alarm (already uses async locks correctly)

---

### Feature Engineering Column Order Fragile

**Issue:** Feature matrix column order assumed consistent; no validation.
- Files: `data/processing/feature_engineering.py`, `data/pipelines/daily_pipeline.py` line 161
- Problem: If FRED fetches columns in different order, features misaligned
- Impact: MEDIUM — silent model input corruption
- Fix approach:
  1. Validate after fetch:
     ```python
     expected_cols = ["d_sp500", "d_vix", ...]
     assert list(X.columns) == expected_cols, f"Column mismatch"
     ```
  2. Test: verify column order in test suite

---

## Low-Priority Issues

### HMM Model Optional Fallback Inconsistent

**Issue:** Pipeline falls back to VIX threshold if GARCH missing; backtest may not have same logic.
- Files: `data/pipelines/daily_pipeline.py` lines 164-175
- Impact: LOW — inconsistent behavior; only affects degraded scenarios
- Fix approach: Document fallback strategy; test both paths separately

---

### Naive In-Memory FRED Cache (1-hour TTL)

**Issue:** FRED data published daily; 1-hour cache causes 24 redundant API calls/day.
- Files: `data/ingestion/fred_client.py` line 25
- Impact: LOW — wastes API quota; minor cost
- Fix approach: Increase TTL to 23 hours

---

### PCA Transform Recomputed on Every Backtest Request

**Issue:** Full PCA transformation applied fresh for each backtest window.
- Files: `api/routes/backtest.py` lines 63-71
- Impact: LOW — slower backtest performance
- Fix approach: Cache transformed factor time series in database

---

### In-Process WebSocket Connections Not Persisted

**Issue:** `_connections` set in `api/routes/websocket.py` in-memory only.
- Files: `api/routes/websocket.py` line 24
- Impact: LOW — on container restart, clients disconnect (but client-side auto-reconnect handles this)
- Fix approach: Use Redis pub/sub for horizontal scaling

---

### Model Artifact Paths Hardcoded

**Issue:** Model load methods reference hardcoded paths.
- Files: `models/hmm_model.py` line 100, similar in other models
- Impact: LOW — if paths change, load fails
- Fix approach: Add validation method to check artifact existence before pipeline starts; raise early with clear error

---

### Paddle Webhook Secret Validation Missing

**Issue:** If `paddle_webhook_secret` empty, webhook validation may be bypassed (similar to LS issue).
- Files: `config/settings.py` line 77
- Note: Unlike LS, Paddle handler does check: `verify_webhook()` in `services/paddle.py`
- Status: ALREADY MITIGATED — Paddle handler properly validates

---

## Scaling Limits

**WebSocket Connections:**
- Current capacity: ~100k per process (1MB per connection estimate)
- Scaling path: Redis pub/sub; separate WebSocket server

**Database Connections:**
- Current capacity: 10 concurrent queries
- Scaling path: Make `_POOL_MIN/_POOL_MAX` configurable; use connection pooling proxy (PgBouncer)

**Anonymous Rate Limiter Memory:**
- Current capacity: ~1 million unique IPs (~100MB)
- Scaling path: Switch to Redis INCR for all counters

---

## Summary: Fix Priority

**CRITICAL (Fix immediately):**
1. Remove committed secrets; rotate all API keys
2. Fix Lemon Squeezy webhook validation bypass
3. Add rate limiting to OTP verification endpoints

**HIGH (Fix before production):**
4. Migrate to async PostgreSQL (asyncpg)
5. Add database replication + failover
6. Implement model signing / artifact integrity
7. Add GDPR data deletion endpoint
8. Add CSRF protection to state-changing endpoints

**MEDIUM (Fix in next phase):**
9. Add Prometheus metrics
10. Implement pipeline failure alerting
11. Add auth/webhook/migration tests
12. Fix timezone bug in rate limit reset
13. Fix WebSocket broadcast exception handling

**LOW (Nice to have):**
14. Increase FRED cache TTL
15. Add PCA transform caching
16. Use Redis for WebSocket state

---

*Concerns audit: 2026-03-28*
