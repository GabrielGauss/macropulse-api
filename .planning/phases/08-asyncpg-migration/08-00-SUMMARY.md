---
phase: "08-asyncpg-migration"
plan: "00"
subsystem: "database"
tags: [asyncpg, connection-pool, lifespan, fastapi, async]
dependency_graph:
  requires: []
  provides: [database.connection.init_pool, database.connection.close_pool, database.connection.get_db_conn]
  affects: [api/main.py, database/queries.py]
tech_stack:
  added: [asyncpg>=0.29,<1.0]
  removed: [psycopg2-binary]
  patterns: [asynccontextmanager, asyncpg.create_pool with init callback]
key_files:
  created: []
  modified:
    - database/connection.py
    - api/main.py
    - requirements.txt
decisions:
  - "Added get_sync_cursor() compatibility shim in connection.py to keep unmigrated callers (queries.py, routes) importable at startup — shim raises RuntimeError at call time; removed in plan 08-01"
  - "JSONB codec registered per-connection via asyncpg create_pool init= callback rather than post-pool set_type_codec (correct asyncpg pattern)"
metrics:
  duration: "~8 minutes"
  completed: "2026-03-30"
  tasks_completed: 2
  files_modified: 3
---

# Phase 08 Plan 00: asyncpg Pool + Async Connection Layer Summary

asyncpg pool replacing psycopg2 ThreadedConnectionPool, with JSONB codec registration, env-var-configurable pool sizes, and async lifespan wiring in api/main.py.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewrite database/connection.py for asyncpg | 279ea0c | database/connection.py, requirements.txt |
| 2 | Update api/main.py lifespan and health route | 279ea0c | api/main.py |

## What Was Built

### database/connection.py

Complete rewrite replacing psycopg2 with asyncpg:

- `_pool: asyncpg.Pool | None = None` — module-level pool variable
- `_POOL_MIN` / `_POOL_MAX` read from `DB_POOL_MIN` / `DB_POOL_MAX` env vars (defaults 5/20)
- `_CMD_TIMEOUT = 30` seconds
- `init_pool(dsn: str)` — creates asyncpg pool with `min_size`, `max_size`, `command_timeout`, and `init=_init_connection`
- `_init_connection(conn)` — per-connection JSONB codec registration (`json.dumps` / `json.loads`)
- `close_pool()` — awaits `_pool.close()`
- `get_db_conn()` — `@asynccontextmanager` yielding `asyncpg.Connection` via `_pool.acquire()`
- `get_sync_cursor()` — compatibility shim (importable, raises `RuntimeError` at call time) to keep unmigrated modules importable until plan 08-01

### api/main.py

Three targeted changes:

1. `_run_migrations()` converted to `async def`, uses `async with get_db_conn() as conn: await conn.execute(sql)`
2. `lifespan()` imports `init_pool, close_pool`; calls `await init_pool(settings.database_url)`, `await _run_migrations()`, `await close_pool()`
3. `health_check()` converted to `async def`, uses `async with get_db_conn() as conn: await conn.execute("SELECT 1")`

### requirements.txt

- Removed: `psycopg2-binary>=2.9,<3.0`
- Added: `asyncpg>=0.29,<1.0`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added get_sync_cursor() compatibility shim**
- **Found during:** Task 2 verification (`from api.main import app`)
- **Issue:** `database/queries.py` and other unmigrated modules still import `get_sync_cursor` from `database.connection`. This broke the import chain: api/main.py → routes → auth_rate_limit.py → queries.py → ImportError
- **Fix:** Added a `@contextlib.contextmanager` stub `get_sync_cursor()` that imports cleanly but raises `RuntimeError("get_sync_cursor() was removed in plan 08-00. Use 'async with get_db_conn() as conn:' instead.")` at call time. This satisfies the plan's `from api.main import app` success criterion while keeping the contract clear for 08-01.
- **Files modified:** database/connection.py
- **Commit:** 279ea0c

## Verification Results

```
PASS: connection exports OK  (from database.connection import init_pool, close_pool, get_db_conn)
PASS: app imports OK         (from api.main import app)
PASS: no legacy symbols in main.py
PASS: asyncpg in requirements
PASS: psycopg2 removed
```

## Self-Check: PASSED

- `database/connection.py` — exists and verified
- `api/main.py` — exists and verified
- `requirements.txt` — exists and verified
- commit `279ea0c` — confirmed in git log
