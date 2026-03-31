---
phase: "08-asyncpg-migration"
plan: "02"
subsystem: "api"
tags: [asyncpg, async, route-handlers, middleware, tests, pytest-asyncio]
dependency_graph:
  requires: [database.connection.get_db_conn, database.queries.*]
  provides: [api.routes.auth.*, api.routes.billing.*, api.middleware.auth_rate_limit.check_auth_rate_limit, api.middleware.rate_limit._resolve_limit, api.auth._lookup_key]
  affects: [tests/conftest.py, tests/test_auth_rate_limit.py]
tech_stack:
  added: [pytest-asyncio>=0.23,<1.0]
  removed: [get_sync_cursor shim in database/connection.py]
  patterns: [async def route handlers, await queries.*, AsyncMock for async context managers, asyncio_mode=auto]
key_files:
  created: []
  modified:
    - api/routes/auth.py
    - api/routes/billing.py
    - api/middleware/auth_rate_limit.py
    - api/middleware/rate_limit.py
    - api/auth.py
    - database/connection.py
    - pytest.ini
    - requirements.txt
    - tests/conftest.py
    - tests/test_auth_rate_limit.py
    - .planning/REQUIREMENTS.md
decisions:
  - "Patched database.queries.get_db_conn (not database.connection.get_db_conn) in test_state_is_db_not_memory — queries.py uses 'from database.connection import get_db_conn' which binds the name to queries module namespace"
  - "All 8 test functions in test_auth_rate_limit.py converted to async def with AsyncMock side_effect returning coroutines — asyncio_mode=auto handles the event loop"
  - "recover_verify tier lookup replaced: get_sync_cursor block removed, now uses await queries.get_active_keys_for_user(user_id) — same data, async path"
  - "billing.py _ls_handle and _ls_provision converted to async def — all queries.* calls inside are now awaited"
metrics:
  duration: "~15 minutes"
  completed: "2026-03-31"
  tasks_completed: 3
  files_modified: 11
---

# Phase 08 Plan 02: Route Handlers + Middleware Async Wiring + Tests Summary

Full async wiring of all API call sites: 7 auth route handlers, billing webhooks and helpers, rate-limit middleware, and the auth dependency — all converted to async def with await queries.*, and the get_sync_cursor shim deleted. Test suite updated with pytest-asyncio and AsyncMock; all 19 tests pass.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Convert route handlers and middleware to async | 966a049 | api/routes/auth.py, api/routes/billing.py, api/middleware/auth_rate_limit.py, api/middleware/rate_limit.py, api/auth.py, database/connection.py |
| 2 | Update tests for AsyncMock and pytest-asyncio | 966a049 | pytest.ini, requirements.txt, tests/conftest.py, tests/test_auth_rate_limit.py |
| 3 | Mark DB-10–DB-13 complete in REQUIREMENTS.md | 966a049 | .planning/REQUIREMENTS.md |

## What Was Built

### api/routes/auth.py

All 7 handlers converted to `async def`:
- `register`, `verify`, `recover`, `recover_verify`, `rotate_key`, `get_me`, `get_usage`
- `await check_auth_rate_limit(...)` at each protected handler entry point
- `await queries.*` at every database call
- `recover_verify`: removed `get_sync_cursor` block; tier now fetched via `await queries.get_active_keys_for_user(user_id)`

### api/routes/billing.py

- `create_checkout`, `get_portal`, `get_ls_portal` converted to `async def`
- `_ls_provision` and `_ls_handle` converted to `async def` — all internal `queries.*` calls awaited
- `paddle_webhook` idempotency block: replaced `get_sync_cursor` with `async with get_db_conn() as conn:` using `$1` positional params

### api/middleware/auth_rate_limit.py

- `_set_backoff_if_needed`: `def` → `async def`; `get_sync_cursor` block replaced with `async with get_db_conn() as conn: await conn.execute(sql, ...)` using `$1`/`$2`/`$3` params
- `check_auth_rate_limit`: `def` → `async def`; `await queries.check_and_record_attempt(...)` and `await _set_backoff_if_needed(...)`
- Import: `get_sync_cursor` removed; `get_db_conn` added

### api/middleware/rate_limit.py

- `_resolve_limit`: `def` → `async def`; `record = await get_api_key_by_hash(key_hash)`
- `get_usage_today`: `def` → `async def`; `return await get_daily_usage(client_id)`
- `RateLimitMiddleware.dispatch`: `await _resolve_limit(...)`, `await check_and_set_ip_lock(...)`, `await increment_daily_usage(...)`, `await get_daily_usage(...)`

### api/auth.py

- `_lookup_key`: `def` → `async def`; `return await get_api_key_by_hash(...)`
- `require_api_key`: `await _lookup_key(...)`, `await _check(...)`, `await touch_api_key(...)`

### database/connection.py

- Deleted `get_sync_cursor()` compatibility shim (all call sites eliminated)

### pytest.ini

Added `asyncio_mode = auto` — pytest-asyncio auto-detects async test functions.

### requirements.txt

Added `pytest-asyncio>=0.23,<1.0` under new Testing section.

### tests/conftest.py

`mock_auth_rl_cursor` fixture rewritten:
- Patches `database.connection.get_db_conn` (was `database.connection.get_sync_cursor`)
- Uses `AsyncMock` for `__aenter__`/`__aexit__`
- Mock conn has `AsyncMock` for `fetchrow` and `execute`

### tests/test_auth_rate_limit.py

All 8 test functions converted to `async def`:
- `fake_attempt` side-effects are now `async def` coroutines
- `patch(..., new=AsyncMock(return_value=...))` pattern for non-side-effect mocks
- `test_state_is_db_not_memory`: patches `database.queries.get_db_conn` (correct — queries module binds the name); asserts `mock_conn.fetchrow.called or mock_conn.execute.called`
- `test_recover_backoff_at_attempt_3`: `_set_backoff_if_needed` patched with `AsyncMock`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Patched database.queries.get_db_conn instead of database.connection.get_db_conn**
- **Found during:** Task 2, test_state_is_db_not_memory failed with AssertionError: Pool not initialised
- **Issue:** `database/queries.py` uses `from database.connection import get_db_conn` — this binds `get_db_conn` to the `database.queries` namespace. Patching `database.connection.get_db_conn` does not affect the already-bound reference in `database.queries`.
- **Fix:** Changed patch target to `database.queries.get_db_conn`
- **Files modified:** tests/test_auth_rate_limit.py
- **Commit:** 966a049

**2. [Rule 1 - Bug] recover_verify tier fetch rewritten without get_sync_cursor**
- **Found during:** Task 1 — auth.py recover_verify had an inline `get_sync_cursor` block for fetching tier
- **Issue:** The plan mentioned this would need conversion; the sync block used a raw SQL query with `%s` placeholder
- **Fix:** Replaced with `await queries.get_active_keys_for_user(user_id)` which already returns active key records including `tier`
- **Files modified:** api/routes/auth.py
- **Commit:** 966a049

## Deferred Items

Pre-existing warning in test_pipeline_quality.py: `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited` on `queries.insert_pipeline_run()` call in daily_pipeline.py. This is an out-of-scope issue in the scheduler/pipeline layer — not introduced by this plan. Logged to deferred-items for phase 09.

## Verification Results

```
PASS: api/ source files — no get_sync_cursor or psycopg2 references
PASS: tests/ — no get_sync_cursor references
PASS: from api.main import app — exits 0
PASS: 19 passed, 0 failed, 2 warnings (pre-existing) — pytest exits 0
```

## Self-Check: PASSED

- `api/routes/auth.py` — exists, all 7 handlers are async def
- `api/routes/billing.py` — exists, create_checkout/get_portal/get_ls_portal/_ls_provision/_ls_handle async
- `api/middleware/auth_rate_limit.py` — exists, check_auth_rate_limit and _set_backoff_if_needed async
- `api/middleware/rate_limit.py` — exists, _resolve_limit and get_usage_today async
- `api/auth.py` — exists, _lookup_key async
- `database/connection.py` — get_sync_cursor shim deleted
- `pytest.ini` — asyncio_mode = auto present
- `requirements.txt` — pytest-asyncio present
- `tests/conftest.py` — AsyncMock fixtures
- `tests/test_auth_rate_limit.py` — async test functions, get_db_conn patches
- commit `966a049` — confirmed in git log
