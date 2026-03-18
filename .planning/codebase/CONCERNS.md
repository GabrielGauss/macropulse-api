# Codebase Concerns

**Analysis Date:** 2026-03-18

## Tech Debt

**Credential Exposure in source code:**
- Issue: Owner API key hardcoded in `api/auth.py` line 86
- Files: `api/auth.py`
- Impact: Master key exposed; if repo is leaked or cloned, attacker has full system access
- Fix approach: Move `owner_api_key` to environment variables only, never embed in code. Use Settings pattern from pydantic-settings (already in place for other keys)

**Duplicate alerting logic:**
- Issue: Two separate alert dispatch systems running — `services/alerting.py` and `services/alerts.py`
- Files: `data/pipelines/daily_pipeline.py` lines 224-230 and 233-244
- Impact: Alerts may fire twice; confusion about which system is authoritative; maintenance burden
- Fix approach: Consolidate into single alerting module. Choose one implementation path, remove the other.

**WebSocket connection state not persisted across restarts:**
- Issue: `_connections` set in `api/routes/websocket.py` is in-memory only
- Files: `api/routes/websocket.py` line 24
- Impact: On container restart, all connected clients receive stale/broken connection; no reconnection broadcasting; clients stuck on disconnect waiting for next pipeline run
- Fix approach: Use Redis pub/sub or message broker for horizontal scaling; document that WebSocket is best-effort, clients should auto-reconnect (already implemented)

**Naive in-process FRED cache:**
- Issue: FRED data cached in `_series_cache` dict (`data/ingestion/fred_client.py` line 24) without expiration cleanup
- Files: `data/ingestion/fred_client.py`
- Impact: Memory leak over time; stale cached data returned if TTL check fails; no cache invalidation on retraining
- Fix approach: Implement periodic cleanup task (prune expired entries every 24h). Or use Redis with automatic TTL.

**Model version migration incomplete:**
- Issue: Code checks for `version == "v1"` to use different feature columns (`data/pipelines/daily_pipeline.py` line 160)
- Files: `data/pipelines/daily_pipeline.py`, `data/processing/feature_engineering.py`
- Impact: Hard-coded version check; difficult to add v3+; brittle version handling
- Fix approach: Move version-specific feature mappings to a registry dict: `FEATURE_MAPS = {"v1": [...], "v2": [...]}`

**Database schema lacks constraints:**
- Issue: `macro_regimes.regime` and `macro_regimes.volatility_state` are TEXT without CHECK constraints
- Files: `database/schema.sql` lines 74, 80
- Impact: Invalid regime values (typos, garbage) silently persist; downstream queries may break if unexpected regime names appear
- Fix approach: Add CHECK constraints: `CHECK (regime IN ('expansion', 'tightening', 'risk_off', 'recovery'))` and similar for volatility_state

**Rate limiter in-memory counter vulnerable to race conditions:**
- Issue: Anonymous IP counter in `_anon_counters` dict (line 219) incremented without locking in async context
- Files: `api/middleware/rate_limit.py` lines 218-219
- Impact: Under high concurrency, multiple requests from same IP may bypass rate limit (TOCTOU race)
- Fix approach: Use atomic database operations or Redis INCR for all counters (authenticated path already uses DB)

---

## Known Bugs

**Data lag guard off-by-one in comparison:**
- Symptoms: Pipeline claims data_lag=true when FRED is only 2 days stale; should allow up to 3 days
- Files: `data/pipelines/daily_pipeline.py` line 147
- Trigger: Run pipeline when latest FRED data is from 2 days ago
- Workaround: None — pipeline halts with partial result. Manually run `scripts/retrain_models.py` to clear stale models

**HMM model not found error crashes pipeline without fallback:**
- Symptoms: "Module not found: hmm_v2.pkl" causes pipeline failure instead of degraded inference
- Files: `models/hmm_model.py` line 100 (load method)
- Trigger: Run pipeline with `DEFAULT_MODEL_VERSION=v2` but artifact doesn't exist (e.g., retraining not completed)
- Workaround: Use environment variable to point to valid model version, or copy from backup

**WebSocket broadcasts swallow exceptions silently:**
- Symptoms: Connected clients don't receive updates if a single client's connection fails
- Files: `api/routes/websocket.py` lines 55-56 (catch-all in broadcast_regime)
- Trigger: Client connection in stale state (half-closed); sending causes exception
- Workaround: Client-side auto-reconnect logic in `useRegimeSocket.js` handles this partially

**Timezone mismatch in rate limit reset:**
- Symptoms: Rate limit resets at different time than user expects if system is not in UTC
- Files: `api/middleware/rate_limit.py` line 66 (uses date.today() not UTC-aware)
- Trigger: Run on non-UTC system; rate limit resets at local midnight not UTC midnight
- Workaround: Always run in UTC timezone container or set TZ=UTC in env

---

## Security Considerations

**API key transmitted in plaintext over HTTP (non-prod only):**
- Risk: If frontend runs over HTTP (local dev), API keys visible in browser history, referer headers, logs
- Files: `frontend/src/lib/api.js`
- Current mitigation: Header-based auth only (not query params); dev mode auto-enabled locally
- Recommendations: Enforce HTTPS in production; add CSP headers; rotate dev keys regularly

**Database credentials in environment variables (standard practice, acceptable):**
- Risk: `.env` file contains `DB_PASSWORD` in plaintext
- Files: `config/settings.py` lines 34-38
- Current mitigation: `.env` listed in `.gitignore`; not committed to repo
- Recommendations: Use secrets manager (e.g., AWS Secrets, Vault) in production; audit `.env` file permissions

**FRED API key in plaintext environment:**
- Risk: FRED key has read-only access but is valuable; if leaked, attacker can query economic data (low impact but should be rotated)
- Files: `data/ingestion/fred_client.py` line 31
- Current mitigation: Key scoped to FRED API only (no write access); short TTL on cached data
- Recommendations: Rotate quarterly; log usage; consider using read-only service account

**Owner key stored in settings with no audit trail:**
- Risk: Owner key grants full system access (all tiers, no rate limits, all features)
- Files: `api/auth.py` line 83-90; `config/settings.py` line 73
- Current mitigation: Hardcoded email check (line 86) assumes only internal access
- Recommendations: Implement key rotation mechanism; log all owner-key requests; use separate owner DB key with audit logging

**Paddle webhook secret not validated if missing:**
- Risk: If `paddle_webhook_secret` is empty string, webhook validation may be bypassed
- Files: `config/settings.py` line 77
- Current mitigation: None detected
- Recommendations: Make `paddle_webhook_secret` required in production settings; validate in webhook handler

---

## Performance Bottlenecks

**PCA model transform recomputed on every request:**
- Problem: In backtest endpoint, PCA transformation applied fresh for each date window instead of cached
- Files: `api/routes/backtest.py` lines 63-71; `services/backtest.py` (full transform applied)
- Cause: No caching of PCA outputs; full 60+ day feature matrix retransformed for historical data
- Improvement path: Cache transformed factor time series in database or disk; reuse during backtest

**FRED cache TTL only 1 hour — frequent re-fetches:**
- Problem: FRED data published daily or less frequently; 1-hour cache means 24 redundant API calls/day
- Files: `data/ingestion/fred_client.py` line 25
- Cause: Conservative cache window doesn't account for FRED publish schedule
- Improvement path: Increase TTL to 23 hours; add manual invalidation on upstream alert

**Database queries not indexed on time ranges:**
- Problem: `fetch_regime_history(limit=2)` scans full table without index
- Files: `database/queries.py` (read operations); `database/schema.sql` (no indexes created)
- Cause: Schema uses TimescaleDB hypertables but no explicit indexes defined
- Improvement path: Add indexes on `macro_regimes(time DESC)`, `macro_features(time DESC)` for range queries

**HMM predict_proba called twice per pipeline run:**
- Problem: `predict_proba()` called once (line 191), but if GARCH model missing, classifier may call predict again implicitly
- Files: `data/pipelines/daily_pipeline.py` lines 191, 202
- Cause: Inefficient regime classification logic; redundant matrix operations
- Improvement path: Store proba result; reuse in classifier.classify()

**WebSocket broadcast iterates all clients synchronously:**
- Problem: If 10k clients connected, broadcast blocks until all sends complete
- Files: `api/routes/websocket.py` lines 46-58
- Cause: Synchronous loop; no batching or async gather
- Improvement path: Use `asyncio.gather()` for parallel sends; implement backpressure handling

---

## Fragile Areas

**Feature engineering depends on exact column order:**
- Files: `data/processing/feature_engineering.py`, `data/pipelines/daily_pipeline.py` line 161
- Why fragile: If FRED or market data fetches columns in different order, feature matrix will be silently misaligned; model inputs wrong
- Safe modification: Validate column order before PCA transform; add assertions `X.columns == MODEL_FEATURE_COLS`
- Test coverage: No column-order validation tests; only end-to-end pipeline tests

**GARCH model optional and falls back silently:**
- Files: `data/pipelines/daily_pipeline.py` lines 164-175
- Why fragile: If GARCH model missing, code falls back to VIX threshold. Backtest endpoint may not have same logic.
- Safe modification: Implement explicit fallback strategy; test both paths separately
- Test coverage: No tests for missing GARCH scenario; only happy path tested

**Pipeline orchestrator tight coupling to database:**
- Files: `data/pipelines/daily_pipeline.py` (line 66-75 _log_run calls queries directly)
- Why fragile: If queries fail, pipeline logs fail but pipeline continues (good). If database is down, pipeline blocks.
- Safe modification: Add circuit breaker for DB writes; make pipeline succeed even if logging fails
- Test coverage: No tests with simulated DB failure; only integration tests

**Model artifact paths hardcoded in load methods:**
- Files: `models/hmm_model.py` line 100, `models/pca_model.py` (similar), `models/regime_classifier.py` (similar)
- Why fragile: If artifacts directory moved or model version renamed, all load calls fail with cryptic "file not found" errors
- Safe modification: Add validation method to check artifact existence before pipeline starts; raise early with clear error
- Test coverage: Artifacts assumed to exist; no tests with missing artifacts

**Validation logic split across three functions with inconsistent thresholds:**
- Files: `services/validation.py` lines 38-128
- Why fragile: NaN ratio threshold (0.3) hardcoded; z-score outlier (6.0) hardcoded; stale data check (10 rows) hardcoded
- Safe modification: Move thresholds to Settings; parameterize validation functions
- Test coverage: Some unit tests exist but threshold values not tested against boundary cases

---

## Scaling Limits

**In-process WebSocket connection set limited by single process memory:**
- Current capacity: ~100k connections per process (rough estimate, ~1MB per connection)
- Limit: Machine memory; typical server 8-32GB → 8k-32k stable connections
- Scaling path: Move to Redis pub/sub or Kafka; separate WebSocket server from API; use load balancer

**FRED cache grows unbounded:**
- Current capacity: Depends on number of series × date ranges cached; typical ~10-100 MB for 1 year of 20 series
- Limit: Process memory; ~5GB available in container → cache fills after 50-500 days runtime
- Scaling path: Implement periodic cache cleanup; use Redis with eviction policy; switch to persistent cache store

**Database connection pool size hardcoded at 2-10:**
- Current capacity: 10 concurrent queries; queue beyond that
- Limit: Database connection limits (typically 100 per user in PostgreSQL); thread pool in API
- Scaling path: Make `_POOL_MIN` and `_POOL_MAX` configurable in Settings; add connection pool monitoring

**Rate limiter in-memory anonymous counter grows with unique IPs:**
- Current capacity: ~1 million IPs → ~100MB memory for counter dict
- Limit: Process memory; fills after 1M unique IPs per day
- Scaling path: Use Redis INCR for all counters (authenticated path already does); implement TTL

**Daily pipeline runtime increases with historical data lookback:**
- Current capacity: 60-day lookback → ~5-10s pipeline run; 5-year backtest → 120s+
- Limit: Scheduler timeout; if pipeline > 1 hour, next scheduled run may overlap
- Scaling path: Implement incremental feature computation; cache intermediate results; add async pipeline mode

---

## Dependencies at Risk

**hmmlearn (~0.3.x) is unmaintained:**
- Risk: No updates in 2+ years; potential for model instability with scikit-learn API changes
- Impact: If scikit-learn bumped to 1.5+, HMM fitting may break
- Migration plan: Monitor scikit-learn release notes; consider `pomegranate` or `statsmodels` HMM as backup

**fredapi (0.5.x) minimal maintenance:**
- Risk: Low activity; may lag behind FRED API changes (unlikely but possible)
- Impact: FRED data fetches may fail silently or return incomplete data
- Migration plan: Switch to direct HTTP requests using `httpx` already in dependencies; wrap FRED client

**anthropic SDK version lock (>=0.40,<2.0) permissive:**
- Risk: Major version bump (1.0, 2.0) may have breaking changes
- Impact: Anthropic commentary endpoint may fail if SDK upgraded
- Migration plan: Pin to ~0.40.0 for stability; add version constraints in tests

**pandas 2.2+ removed some legacy APIs:**
- Risk: Code using deprecated DataFrame methods may break on minor version bump
- Impact: Feature engineering pipeline may fail with AttributeError
- Migration plan: Audit codebase for pandas deprecation warnings; use `-W ignore::FutureWarning` sparingly; test with latest pandas quarterly

---

## Missing Critical Features

**No circuit breaker for external API calls (FRED, Anthropic, Paddle):**
- Problem: If FRED API is down, pipeline fails immediately; no graceful degradation
- Blocks: Real-time signal delivery during market events when data is most important
- Approach: Implement circuit breaker pattern (e.g., `PyBreaker`) for FRED; return last-known-good regime on failure

**No model monitoring/alerting dashboard:**
- Problem: Drift metrics computed but not visualized; no alerts if PCA variance drops below threshold
- Blocks: Operations team can't detect model degradation proactively
- Approach: Add drift metrics endpoint; expose via dashboard; send alerts if thresholds crossed

**No data lineage or audit trail:**
- Problem: Can't trace which FRED source data → features → regime output (compliance gap)
- Blocks: Audit requirements; debugging historical inference failures
- Approach: Log data source versions; store feature provenance; add audit endpoint

**No model A/B testing framework:**
- Problem: Can only run one model version at a time; can't compare v1 vs v2 performance on live data
- Blocks: Gradual rollout of new models; confidence in model improvements
- Approach: Add multi-version inference; compute metrics for all versions in parallel

---

## Test Coverage Gaps

**No integration tests for full pipeline:**
- What's not tested: End-to-end pipeline with real/mock FRED data, database writes, alerting dispatch
- Files: `data/pipelines/daily_pipeline.py` (no corresponding test file)
- Risk: Silent failures if validation logic broken; regression on feature engineering changes
- Priority: High — pipeline is critical path

**No tests for error handling scenarios:**
- What's not tested: FRED API timeout, database connection lost, model artifact missing, invalid feature values
- Files: `services/validation.py`, `data/ingestion/fred_client.py`, `models/hmm_model.py`
- Risk: Pipeline crashes in production without graceful fallback
- Priority: High — affects reliability

**No tests for authentication edge cases:**
- What's not tested: Invalid API key format, expired key, rate limit bypass attempts, concurrent requests
- Files: `api/auth.py`, `api/middleware/rate_limit.py`
- Risk: Security vulnerabilities if auth logic broken
- Priority: High — security critical

**No tests for WebSocket connection drops:**
- What's not tested: Client disconnect mid-broadcast, stale connection handling, high concurrency
- Files: `api/routes/websocket.py`, `frontend/src/hooks/useRegimeSocket.js`
- Risk: Clients stuck in disconnected state; silent failures
- Priority: Medium — affects user experience

**No UI tests for real-time updates:**
- What's not tested: Dashboard updates when regime changes, stale data displayed, loading states
- Files: `frontend/src/components/RegimeCard.jsx`, `frontend/src/views/*.jsx`
- Risk: Users see outdated regime signals
- Priority: Medium — affects product perception

**No load tests:**
- What's not tested: 1k concurrent WebSocket clients, 1k req/sec API load, database connection exhaustion
- Files: API as a whole
- Risk: Performance issues discovered only in production
- Priority: Medium — affects scaling

**No feature validation unit tests:**
- What's not tested: NaN ratios at boundary (0.29999, 0.30), z-score outliers (5.99, 6.01), stale data patterns
- Files: `services/validation.py`
- Risk: Subtle bugs in threshold comparisons; data passes validation when it shouldn't
- Priority: Medium — affects data quality

---

## Architecture Concerns

**Scheduler in-process with API (no separation of concerns):**
- Issue: Daily pipeline runs in background of API process; blocking the API if pipeline slow
- Files: `api/main.py` lines 56-66; `services/scheduler.py`
- Impact: During pipeline run, API requests slow; pipeline can starve if too many concurrent requests
- Recommendation: Separate scheduler into standalone process; trigger API via webhook when complete

**Model versioning strategy not scalable:**
- Issue: Hard-coded feature column mappings for v1 vs v2; no registry
- Files: `data/pipelines/daily_pipeline.py` line 160
- Impact: Adding v3+ requires code changes in multiple places; error-prone
- Recommendation: Use version registry pattern (config file or database table)

---

*Concerns audit: 2026-03-18*
