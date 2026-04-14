---
phase: 07-auth-endpoint-rate-limiting
plan: "00"
subsystem: auth-rate-limiting
tags: [security, rate-limiting, database, middleware, postgresql]
dependency_graph:
  requires: []
  provides:
    - auth_rate_limits DB table (009_auth_rate_limits.sql)
    - check_and_record_attempt() atomic upsert (database/queries.py)
    - check_auth_rate_limit() + get_client_ip() middleware (api/middleware/auth_rate_limit.py)
    - xfail test stubs SEC-30 through SEC-33 (tests/test_auth_rate_limit.py)
    - mock_auth_rl_cursor fixture (tests/conftest.py)
  affects:
    - Plan 07-01 wires check_auth_rate_limit() into auth handlers
tech_stack:
  added: []
  patterns:
    - INSERT ... ON CONFLICT upsert with WINDOW_INTERVAL str.replace() (psycopg2 INTERVAL workaround)
    - Fail-open DB error handling in middleware (log + return, no raise)
    - Docker bridge IP trust (172.18.x.x) for X-Forwarded-For
    - xfail(strict=True) stubs keep suite green until implementation
key_files:
  created:
    - database/migrations/009_auth_rate_limits.sql
    - api/middleware/auth_rate_limit.py
    - tests/test_auth_rate_limit.py
  modified:
    - database/queries.py (appended check_and_record_attempt())
    - tests/conftest.py (appended mock_auth_rl_cursor fixture)
decisions:
  - "WINDOW_INTERVAL substituted via str.replace() before cur.execute() — psycopg2 cannot parameterise %(var)s inside INTERVAL literals (same pattern as check_and_set_ip_lock)"
  - "check_auth_rate_limit() fails open on DB error — logs but does not raise — auth endpoints must not become unavailable due to rate-limit table issues"
  - "mock_auth_rl_cursor patches database.connection.get_sync_cursor — consistent with Phase 6 fixture pattern in conftest.py"
metrics:
  duration: ~8 min
  completed_date: "2026-03-30"
  tasks_completed: 3
  files_modified: 5
---

# Phase 7 Plan 00: Auth Rate Limiting DB Foundation Summary

**One-liner:** DB-persisted auth rate limiting using atomic INSERT...ON CONFLICT upsert with WINDOW_INTERVAL str.replace() workaround, fail-open middleware, and xfail stubs for SEC-30 through SEC-33.

## What Was Built

### Task 1: Migration 009 and check_and_record_attempt()

`database/migrations/009_auth_rate_limits.sql` creates the `auth_rate_limits` table with idempotent DDL. Schema: `id` (BIGSERIAL PK), `identifier` (TEXT), `endpoint` (TEXT with CHECK constraint), `attempt_count` (INT), `window_start` (TIMESTAMPTZ), `locked_until` (TIMESTAMPTZ nullable), `updated_at` (TIMESTAMPTZ), plus a UNIQUE constraint on `(identifier, endpoint)` and a supporting index.

`check_and_record_attempt()` in `database/queries.py` performs a single-round-trip atomic upsert:
- INSERT on new identifier/endpoint pairs (attempt_count=1)
- ON CONFLICT DO UPDATE: resets attempt_count to 1 and window_start to now() when window expired; otherwise increments attempt_count
- locked_until CASE: clears on window expiry, preserves active future locks, else NULL
- RETURNING attempt_count, locked_until — no separate read
- Post-fetch: evaluates `allowed` using `dt.datetime.now(dt.timezone.utc)` for timezone-aware comparison

### Task 2: auth_rate_limit.py middleware module

`api/middleware/auth_rate_limit.py` provides three functions:

- `get_client_ip(request)`: Replicates Docker bridge trust logic from `rate_limit.py` — trusts X-Forwarded-For only when direct host starts with "172.18.", falls back to `direct_host or "unknown"`.

- `check_auth_rate_limit(identifier, endpoint, max_attempts, window_minutes, with_backoff=False)`: Calls `queries.check_and_record_attempt()` inside try/except — on any DB exception, logs error and returns (fail open). When `with_backoff=True` and attempt_count >= 3, calls `_set_backoff_if_needed()`. When `not allowed`, computes retry_after from locked_until (or default 60s), raises `HTTPException(429)` with `Retry-After` header.

- `_set_backoff_if_needed(identifier, endpoint, attempt_count)`: Applies progressive lockout via a separate targeted UPDATE — `_BACKOFF_SCHEDULE = {3: 30, 4: 60, 5: 300}`. Silently swallows DB errors (backoff is UX, not a hard limit).

### Task 3: Test stubs and conftest fixture

`tests/test_auth_rate_limit.py` contains all 8 xfail(strict=True) stubs:
- test_register_blocks_on_6th_attempt (SEC-30)
- test_register_window_reset (SEC-30)
- test_register_retry_after_header (SEC-30)
- test_recover_blocks_on_6th_attempt (SEC-31)
- test_recover_backoff_at_attempt_3 (SEC-31)
- test_verify_otp_blocks_after_5 (SEC-32)
- test_otp_row_exhausted_after_5_wrong (SEC-32)
- test_state_is_db_not_memory (SEC-33)

`tests/conftest.py` gained the `mock_auth_rl_cursor` fixture — patches `database.connection.get_sync_cursor` with a MagicMock returning `{"attempt_count": 1, "locked_until": None}`.

## Verification Results

```
pytest tests/test_auth_rate_limit.py -v
8 xfailed in 1.17s

pytest tests/ -q
11 passed, 8 xfailed in 5.39s
```

All checks passed:
- `grep -c "CREATE TABLE IF NOT EXISTS auth_rate_limits" database/migrations/009_auth_rate_limits.sql` → 1
- `python -c "from database.queries import check_and_record_attempt; print('ok')"` → ok
- `python -c "from api.middleware.auth_rate_limit import check_auth_rate_limit, get_client_ip; print('ok')"` → ok

## Deviations from Plan

All three tasks were executed with files already partially present (migration, middleware, and test stubs had been pre-created). The only missing artifact was the `mock_auth_rl_cursor` fixture in `tests/conftest.py`, which was appended as required.

No architectural deviations. Plan executed as written.

## Commits

- `34afa8e`: feat(07-00): auth_rate_limits migration + rate limit module (SEC-30–33 foundation)

## Self-Check: PASSED

- `database/migrations/009_auth_rate_limits.sql` — EXISTS
- `database/queries.py` contains `check_and_record_attempt` — EXISTS
- `api/middleware/auth_rate_limit.py` — EXISTS
- `tests/test_auth_rate_limit.py` — EXISTS (8 stubs)
- `tests/conftest.py` contains `mock_auth_rl_cursor` — EXISTS
- Commit 34afa8e — EXISTS
