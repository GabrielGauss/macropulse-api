# Phase 8: asyncpg Migration - Research

**Researched:** 2026-03-30
**Domain:** Python asyncio / PostgreSQL driver migration (psycopg2 → asyncpg)
**Confidence:** HIGH

---

## Summary

MacroPulse currently uses psycopg2 with a `ThreadedConnectionPool` and a synchronous context manager `get_sync_cursor()`. The entire database layer is synchronous and every call site blocks the FastAPI event loop (no `run_in_executor` — pure blocking calls from async handlers). This phase replaces the psycopg2 pool with an asyncpg pool and converts every call site to the async pattern.

The migration has two separable concerns: (1) replacing the pool/connection module (`database/connection.py`) and (2) re-implementing every function in `database/queries.py` using the asyncpg API. The call sites in routes, middleware, and `api/main.py` then only require `await` additions and function-signature changes (sync → async def). Tests must be converted from `unittest.mock` `MagicMock` stubs of `get_sync_cursor` to `AsyncMock` stubs of the new `get_db_conn()` async context manager.

**Primary recommendation:** Replace `get_sync_cursor()` with `get_db_conn()` — an async context manager that acquires a connection from the asyncpg pool. This is a mechanical 1-to-1 substitution across all call sites. The biggest gotcha is the parameter-style change (%s / %(name)s → $1/$2/$3) and the fact that asyncpg returns `Record` objects, not dicts.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DB-10 | All database operations use asyncpg connection pool (no psycopg2 in production paths) | asyncpg.create_pool() replaces ThreadedConnectionPool; psycopg2-binary removed from requirements.txt |
| DB-11 | Async context managers replace synchronous cursor usage throughout | `get_db_conn()` replaces `get_sync_cursor()`; all queries converted to async def |
| DB-12 | Connection pool tuned: min_size=5, max_size=20, command_timeout=30 | asyncpg.create_pool() accepts exactly these kwargs |
| DB-13 | All existing tests updated to use async fixtures | pytest-asyncio + AsyncMock replaces MagicMock; conftest.py gains async fixtures |
</phase_requirements>

---

## Complete Call-Site Inventory

This is the full list of every location that must change. Counted from reading the source files directly.

### `database/connection.py` — FULL REWRITE
The entire file is replaced. Current contents:
- `_get_pool()` — synchronous lazy-init with threading.Lock
- `get_sync_connection()` — borrows raw connection
- `get_sync_cursor()` — the context manager used at every call site (26 uses in queries.py alone)
- `close_pool()` — called from lifespan shutdown
- `init_schema()` — one direct get_sync_cursor call

### `database/queries.py` — FULL REWRITE (26 call sites)
Every function uses `get_sync_cursor()` and must become `async def` with `get_db_conn()`.

| Function | Pattern | Note |
|----------|---------|------|
| `upsert_macro_features` | execute | %(name)s → $1..$14 positional args |
| `upsert_macro_factors` | execute | %(name)s → $1..$5 |
| `upsert_macro_regime` | execute | %(name)s → $1..$8 |
| `upsert_drift_metrics` | execute | %(name)s → $1..$6 |
| `fetch_latest_pipeline_run` | fetchrow | returns Row or None |
| `insert_pipeline_run` | execute | %(name)s → $1..$6 |
| `fetch_current_regime` | fetchrow | |
| `fetch_regime_history` | fetch | dynamic WHERE clause, positional params |
| `fetch_public_chart_data` | fetch | single positional $1 |
| `create_newsletter_subscriber` | execute | |
| `fetch_latest_liquidity` | fetch | |
| `fetch_latest_factors` | fetch | |
| `fetch_latest_drift` | fetch | |
| `create_user` | fetchrow | RETURNING → fetchrow |
| `get_user_by_email` | fetchrow | |
| `get_user_by_id` | fetchrow | |
| `update_paddle_customer` | execute | |
| `get_user_by_paddle_customer` | fetchrow | |
| `get_user_by_ls_customer` | fetchrow | |
| `upsert_ls_subscription` | execute | |
| `upgrade_user_tier` | execute | |
| `create_api_key` | fetchrow | RETURNING → fetchrow |
| `get_api_key_by_hash` | fetchrow | |
| `get_active_keys_for_user` | fetch | |
| `revoke_api_keys_for_user` | execute | |
| `touch_api_key` | execute | |
| `check_and_set_ip_lock` | fetchrow | complex CTE; uses str.replace for INTERVAL |
| `increment_daily_usage` | fetchrow | RETURNING daily_requests |
| `get_daily_usage` | fetchrow | |
| `get_alert_recipients` | fetch | |
| `update_webhook_url` | execute | already uses %s positional (not %(name)s) |
| `fetch_subscriber_emails` | fetch | returns list of strings |
| `create_email_verification` | execute (×2) | two sequential executes — needs explicit transaction |
| `verify_email_code` | execute + fetchrow (×2) | two sequential statements — needs explicit transaction |
| `fetch_latest_features` | fetch | |
| `check_and_record_attempt` | fetchrow | complex upsert; uses str.replace for INTERVAL |

### `api/main.py` — 4 direct call sites
| Line | Usage | Change needed |
|------|-------|---------------|
| 57–70 | `_run_migrations()` — calls `get_sync_cursor()` per SQL file | Rename to `async def _run_migrations()`; await inside lifespan |
| 178–183 | `health_check()` route — `with get_sync_cursor()` for SELECT 1 | Make route `async def`; use `get_db_conn()` |

### `api/routes/auth.py` — 1 direct call site
| Line | Usage | Change needed |
|------|-------|---------------|
| 229–235 | `recover_verify()` — fetches tier before revoking keys | Already `def` (sync); make `async def`; use `get_db_conn()` |
| All handler functions | Call `queries.*()` synchronously | Must become `async def` with `await queries.*()` |

### `api/routes/billing.py` — 1 direct call site + indirect via queries
| Line | Usage | Change needed |
|------|-------|---------------|
| 216–229 | `paddle_webhook()` — idempotency check with `get_sync_cursor` | Already `async def`; switch to `get_db_conn()` |
| `_ls_provision()`, `_ls_handle()` | Call `queries.*()` synchronously | These are called from async handlers; must become async |

### `api/middleware/auth_rate_limit.py` — 1 direct call site
| Line | Usage | Change needed |
|------|-------|---------------|
| 78 | `_set_backoff_if_needed()` — `with get_sync_cursor()` | Make `async def`; update callers |
| `check_auth_rate_limit()` | Sync function called from sync route handlers | Must become `async def` since it calls async DB |

### `api/middleware/rate_limit.py` — indirect only
The `RateLimitMiddleware.dispatch()` calls `from database.queries import get_api_key_by_hash`, `check_and_set_ip_lock`, `increment_daily_usage`, `get_daily_usage` — all via `_resolve_limit()` which is a sync helper. These must become awaited calls.

### `api/auth.py` — indirect only
`_lookup_key()` calls `get_api_key_by_hash()`; `require_api_key()` is already `async def` but calls `_lookup_key()` synchronously. `_lookup_key()` must be async and awaited.

### `tests/conftest.py` — needs update for DB-13
`mock_auth_rl_cursor` patches `get_sync_cursor` with a sync context manager mock. Must be updated to patch `get_db_conn` (the new name) with an `AsyncMock`.

### `tests/test_auth_rate_limit.py` — needs update for DB-13
Line 179: patches `database.queries.get_sync_cursor`. Must be updated to `database.queries.get_db_conn` with `AsyncMock`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncpg | >=0.29,<1.0 | Async PostgreSQL driver | Fastest Python PG driver; native protocol; built for asyncio |
| pytest-asyncio | >=0.23,<1.0 | Async test support | Standard pytest plugin for async def tests and fixtures |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio (stdlib) | 3.11+ | Event loop | Already present; no change |
| unittest.mock.AsyncMock | 3.8+ (stdlib) | Mock async context managers | Replaces MagicMock for async db fixtures |

### Removed
- `psycopg2-binary` — remove from `requirements.txt` entirely once migration is complete

**Installation:**
```bash
pip install "asyncpg>=0.29,<1.0" "pytest-asyncio>=0.23,<1.0"
```

---

## Architecture Patterns

### Recommended New Module Structure
```
database/
├── connection.py    # asyncpg pool lifecycle + get_db_conn() context manager
├── queries.py       # all async def query functions (no change to filename)
├── migrations/      # .sql files (unchanged)
└── schema.sql       # unchanged
```

### Pattern 1: Pool Lifecycle in connection.py

**What:** Module-level asyncpg pool, initialized once in the FastAPI lifespan, shared for the process lifetime.

**When to use:** Everywhere. A single pool per process is the correct asyncpg pattern.

```python
# Source: https://magicstack.github.io/asyncpg/current/api/index.html
import asyncpg
import contextlib
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None

_POOL_MIN = 5   # DB-12
_POOL_MAX = 20  # DB-12
_CMD_TIMEOUT = 30  # DB-12

async def init_pool(dsn: str) -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=_POOL_MIN,
        max_size=_POOL_MAX,
        command_timeout=_CMD_TIMEOUT,
    )
    logger.info("asyncpg pool initialised (min=%d max=%d timeout=%ds).",
                _POOL_MIN, _POOL_MAX, _CMD_TIMEOUT)

async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("asyncpg pool closed.")

@contextlib.asynccontextmanager
async def get_db_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a connection from the pool. Auto-releases on exit."""
    assert _pool is not None, "Pool not initialised — call init_pool() first"
    async with _pool.acquire() as conn:
        yield conn
```

### Pattern 2: Async Query Functions in queries.py

**What:** All query functions become `async def`, use `get_db_conn()`, and use positional `$1`/`$2` placeholders.

**Key differences from psycopg2:**

| psycopg2 | asyncpg |
|----------|---------|
| `%s` or `%(name)s` | `$1`, `$2`, `$3` (positional only, no named params) |
| `cur.execute(sql, dict)` | `await conn.execute(sql, *args)` (args as positional) |
| `cur.fetchone()` | `await conn.fetchrow(sql, *args)` |
| `cur.fetchall()` | `await conn.fetch(sql, *args)` |
| `cur.fetchone()["col"]` | `row["col"]` (asyncpg Record supports key access) |
| Returns `RealDictCursor` rows (dict-like) | Returns `asyncpg.Record` (also dict-like via `row["col"]`) |
| `dict(row)` required for plain dict | `dict(row)` also works for Record |
| Named params `%(key)s` | No named params — must convert to positional |

**Single-row write example:**
```python
# Source: https://magicstack.github.io/asyncpg/current/usage.html
async def upsert_macro_features(row: dict[str, Any]) -> None:
    sql = """
        INSERT INTO macro_features (
            time, net_liquidity, d_liquidity, d_sp500, d_vix,
            d_dxy, d_hy_spread, d_yield_curve, d_10y, d_2y,
            d_gold, d_oil, d_btc, d_eth
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (time) DO UPDATE SET
            net_liquidity = EXCLUDED.net_liquidity,
            ...
    """
    row.setdefault("d_gold", 0)
    row.setdefault("d_oil", 0)
    row.setdefault("d_btc", 0)
    row.setdefault("d_eth", 0)
    async with get_db_conn() as conn:
        await conn.execute(
            sql,
            row["time"], row["net_liquidity"], row["d_liquidity"],
            row["d_sp500"], row["d_vix"], row["d_dxy"],
            row["d_hy_spread"], row["d_yield_curve"], row["d_10y"],
            row["d_2y"], row["d_gold"], row["d_oil"],
            row["d_btc"], row["d_eth"],
        )
```

**Single-row read with RETURNING:**
```python
async def create_user(email: str, name: str | None = None) -> dict[str, Any]:
    sql = """
        INSERT INTO users (email, name)
        VALUES ($1, $2)
        RETURNING id, email, name, created_at;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, email, name)
        return dict(row)   # asyncpg.Record → plain dict
```

**Multi-row read:**
```python
async def fetch_regime_history(
    start: dt.date | None = None,
    end: dt.date | None = None,
    limit: int = 90,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    args: list[Any] = []
    if start:
        args.append(start)
        conditions.append(f"time >= ${len(args)}")
    if end:
        args.append(end)
        conditions.append(f"time <= ${len(args)}")
    args.append(limit)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT * FROM macro_regimes
        {where}
        ORDER BY time DESC
        LIMIT ${len(args)};
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql, *args)
        return [dict(r) for r in rows]
```

### Pattern 3: Explicit Transactions for Multi-Statement Operations

**What:** Functions that execute two or more statements atomically must use `conn.transaction()`.

**Affected functions:** `create_email_verification` (DELETE + INSERT), `verify_email_code` (UPDATE + UPDATE).

```python
# Source: https://magicstack.github.io/asyncpg/current/usage.html
async def create_email_verification(email: str, code: str) -> None:
    async with get_db_conn() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM email_verifications WHERE email = $1;", email
            )
            await conn.execute(
                """
                INSERT INTO email_verifications (email, code, expires_at)
                VALUES ($1, $2, NOW() + INTERVAL '15 minutes');
                """,
                email, code,
            )
```

### Pattern 4: INTERVAL Literal Workaround

The current code uses `str.replace()` to inject INTERVAL values because psycopg2 cannot parameterise them. asyncpg has the same limitation — PostgreSQL's extended query protocol does not accept parameters inside INTERVAL literals.

**Keep the same str.replace() approach:**
```python
# Current pattern preserved — still needed in asyncpg
sql = sql.replace("WINDOW_INTERVAL", f"{window_minutes} minutes")
await conn.fetchrow(sql, identifier, endpoint)
```

**Or use format-string construction (equivalent, equally safe since values are ints/sanitised strings):**
```python
sql = f"""
    ... INTERVAL '{window_minutes} minutes' ...
"""
```

Neither approach introduces SQL injection risk because `window_minutes` is an integer set from `max_attempts`/`window_minutes` function args, not user input.

### Pattern 5: Async Lifespan in api/main.py

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from database.connection import init_pool, close_pool
    from services.scheduler import start_scheduler, stop_scheduler
    from services.mta_signer import init_signer

    logger.info("Starting MacroPulse API v%s", settings.app_version)
    await init_pool(settings.database_url)   # replaces lazy init
    await _run_migrations()                  # now async
    init_signer(settings.mta_signing_key_hex)
    _validate_webhook_secrets()
    _validate_cors_origins()
    start_scheduler()
    yield
    stop_scheduler()
    await close_pool()
    logger.info("MacroPulse API shut down.")
```

### Pattern 6: Async _run_migrations

```python
async def _run_migrations() -> None:
    from database.connection import get_db_conn

    migrations_dir = Path(__file__).parent.parent / "database" / "migrations"
    if not migrations_dir.is_dir():
        return
    sql_files = sorted(migrations_dir.glob("*.sql"))
    for path in sql_files:
        sql = path.read_text(encoding="utf-8")
        try:
            async with get_db_conn() as conn:
                await conn.execute(sql)
            logger.info("Migration applied: %s", path.name)
        except Exception as exc:
            logger.error("Migration failed (%s): %s", path.name, exc)
            raise
```

### Anti-Patterns to Avoid
- **Named params `%(key)s` with asyncpg:** asyncpg has no named-parameter support. All params must be positional `$1`, `$2`, etc. The common mistake when porting is forgetting to reorder the `%(key)s` dict into a positional list in the right order.
- **Reusing a connection outside its `acquire()` block:** asyncpg connections are returned to the pool when the `async with pool.acquire()` block exits. Do not hold a reference and call methods after exit.
- **Calling sync DB functions from async code without await:** The entire point of this migration. After the migration, calling any `queries.*` function without `await` will silently return a coroutine object, not a result.
- **Using `asyncio.run()` in tests:** pytest-asyncio provides the event loop. Don't nest `asyncio.run()` inside test functions.
- **`init_pool()` not awaited before first request:** Because asyncpg pools are async, the pool cannot be lazily initialised with a threading.Lock trick. It must be created in `lifespan()` before any request arrives.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async context manager for pool acquire | Custom wrapper class | `asyncpg.pool.acquire()` via `@asynccontextmanager` | asyncpg already implements connection lifecycle correctly |
| Async test event loop management | Custom pytest plugin | `pytest-asyncio` | Handles event loop scoping, fixture async teardown, marks |
| Async mocking | MagicMock subclass | `unittest.mock.AsyncMock` (stdlib 3.8+) | AsyncMock properly supports `__aenter__`/`__aexit__` |
| JSONB codec | Custom encoder/decoder in every query | `conn.set_type_codec('jsonb', ...)` once at pool init, or rely on asyncpg's default | asyncpg decodes JSONB to Python dicts automatically by default in recent versions |

**Key insight:** asyncpg's pool handles connection health checking, reconnection, and lifecycle automatically. The only custom code needed is the `@asynccontextmanager` thin wrapper so call sites can use `async with get_db_conn() as conn:` without importing asyncpg directly.

---

## Common Pitfalls

### Pitfall 1: asyncpg.Record is Not a dict
**What goes wrong:** `row["field"]` works (Records support key access), but `row.get("field")` does NOT. Code like `row.get("tier", "free")` silently fails at runtime with `AttributeError: 'asyncpg.Record' object has no attribute 'get'`.
**Why it happens:** `asyncpg.Record` is a C-level type that mimics dict reads but does not inherit from dict.
**How to avoid:** Wrap every `fetchrow`/`fetchmany` result with `dict(row)` before returning from `queries.py` functions. The callers (routes, middleware) then use standard `.get()` safely.
**Warning signs:** Any code in routes that calls `row.get(...)` directly on a value returned from `queries.*` after the migration.

### Pitfall 2: Named Parameters → Positional Only
**What goes wrong:** Queries using `%(name)s` style (psycopg2) are silently passed as positional args to asyncpg, which either throws `asyncpg.exceptions.PostgresSyntaxError` or binds wrong values.
**Why it happens:** asyncpg uses PostgreSQL's extended query protocol which only supports `$1`/`$2` positional placeholders.
**How to avoid:** Every SQL string must be rewritten. For dict-parameterised queries, extract values in `$N` order: `conn.execute(sql, row["col1"], row["col2"], ...)`.
**Warning signs:** Any `%s` or `%(` remaining in queries.py after the migration.

### Pitfall 3: Forgetting `await` on Query Methods
**What goes wrong:** `rows = conn.fetch(sql)` (no await) returns a coroutine. If passed to `[dict(r) for r in rows]`, it will fail with `TypeError: 'coroutine' object is not iterable`. Python will also print a `RuntimeWarning: coroutine was never awaited`.
**Why it happens:** asyncpg methods are coroutines, not regular functions.
**How to avoid:** Every `conn.execute/fetch/fetchrow/fetchval` call needs `await`.

### Pitfall 4: Multi-Statement Functions Without Explicit Transaction
**What goes wrong:** `create_email_verification` does DELETE then INSERT. In asyncpg's default auto-commit mode, the DELETE commits immediately. If the INSERT fails, the DELETE is not rolled back and the old verification code is gone.
**Why it happens:** asyncpg auto-commits each statement when not inside `conn.transaction()`.
**How to avoid:** Wrap all multi-statement functions in `async with conn.transaction():`.
**Affected functions:** `create_email_verification`, `verify_email_code`.

### Pitfall 5: JSONB Codec Registration
**What goes wrong:** asyncpg can return JSONB as a Python dict automatically in recent versions, but this depends on the PostgreSQL server version and codec settings. If not configured, JSONB may arrive as a string.
**Why it happens:** asyncpg does not register a JSONB codec by default in all versions.
**How to avoid:** Register a JSONB codec once on pool init:
```python
async def _init_connection(conn):
    import json
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog',
    )

_pool = await asyncpg.create_pool(
    dsn=dsn,
    min_size=_POOL_MIN,
    max_size=_POOL_MAX,
    command_timeout=_CMD_TIMEOUT,
    init=_init_connection,
)
```
MacroPulse's current schema uses TEXT columns for most flexible fields, so JSONB may not be an active concern here — but register it defensively.

### Pitfall 6: Sync Route Handlers Calling Async Query Functions
**What goes wrong:** After queries.py is converted to async, any route handler still declared as `def` (not `async def`) that calls `await queries.get_user_by_email(...)` raises a `SyntaxError`. Any route handler declared `def` that calls without await gets a coroutine object instead of a result.
**Why it happens:** Many auth route handlers in `api/routes/auth.py` are currently `def`, not `async def`.
**How to avoid:** Every route handler that calls any async query function must be `async def`. This includes all of `auth.py`'s route handlers (`register`, `verify`, `recover`, `recover_verify`, `rotate_key`, `get_me`, `get_usage`).

### Pitfall 7: Middleware Calling Async DB Functions
**What goes wrong:** `RateLimitMiddleware.dispatch()` is already `async def`, but it calls `_resolve_limit()` which is a sync helper that imports and calls sync DB functions inline. After migration, it will call async functions synchronously.
**Why it happens:** The `_resolve_limit()` helper is not `async def` and is called inline with no `await`.
**How to avoid:** Convert `_resolve_limit()` to `async def` and `await` it in `dispatch()`. Similarly `check_auth_rate_limit()` in `auth_rate_limit.py` must become `async def`.

---

## Code Examples

### Conversion Reference: psycopg2 → asyncpg

**Simple fetchrow:**
```python
# BEFORE (psycopg2)
def get_user_by_email(email: str) -> dict[str, Any] | None:
    sql = "SELECT id, email, name FROM users WHERE email = %(email)s;"
    with get_sync_cursor() as cur:
        cur.execute(sql, {"email": email})
        return cur.fetchone()

# AFTER (asyncpg)
async def get_user_by_email(email: str) -> dict[str, Any] | None:
    sql = "SELECT id, email, name FROM users WHERE email = $1;"
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, email)
        return dict(row) if row else None
```

**Simple fetchall → list of dicts:**
```python
# BEFORE
def get_active_keys_for_user(user_id: int) -> list[dict[str, Any]]:
    with get_sync_cursor() as cur:
        cur.execute(sql, {"uid": user_id})
        return cur.fetchall()

# AFTER
async def get_active_keys_for_user(user_id: int) -> list[dict[str, Any]]:
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql, user_id)
        return [dict(r) for r in rows]
```

**Dynamic WHERE with positional params:**
```python
# AFTER — builds positional $N placeholders dynamically
async def fetch_regime_history(
    start: dt.date | None = None,
    end: dt.date | None = None,
    limit: int = 90,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    args: list[Any] = []
    if start:
        args.append(start)
        conditions.append(f"time >= ${len(args)}")
    if end:
        args.append(end)
        conditions.append(f"time <= ${len(args)}")
    args.append(limit)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM macro_regimes {where} ORDER BY time DESC LIMIT ${len(args)};"
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql, *args)
        return [dict(r) for r in rows]
```

**RETURNING clause:**
```python
# AFTER — fetchrow on INSERT...RETURNING
async def create_api_key(user_id: int, key_hash: str, key_prefix: str, tier: str = "free") -> dict[str, Any]:
    sql = """
        INSERT INTO api_keys (user_id, key_hash, key_prefix, tier)
        VALUES ($1, $2, $3, $4)
        RETURNING id, user_id, key_prefix, tier, is_active, created_at;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, user_id, key_hash, key_prefix, tier)
        return dict(row)
```

**fetchval for scalar:**
```python
# AFTER — increment_daily_usage, get_daily_usage
async def increment_daily_usage(key_hash: str) -> int:
    sql = """
        UPDATE api_keys
        SET
            usage_date     = CURRENT_DATE,
            daily_requests = CASE
                                WHEN usage_date = CURRENT_DATE THEN daily_requests + 1
                                ELSE 1
                             END,
            last_used_at   = now()
        WHERE key_hash = $1
        RETURNING daily_requests;
    """
    async with get_db_conn() as conn:
        val = await conn.fetchval(sql, key_hash)
        return int(val) if val is not None else 1
```

### Test Pattern: AsyncMock for get_db_conn

```python
# Source: https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock
from unittest.mock import AsyncMock, MagicMock, patch
import asyncpg
import pytest
import pytest_asyncio

@pytest_asyncio.fixture()
async def mock_db_conn():
    """Async context manager mock for get_db_conn()."""
    mock_conn = AsyncMock(spec=asyncpg.Connection)
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("database.connection.get_db_conn", return_value=mock_ctx):
        yield mock_conn

# Usage in test:
@pytest.mark.asyncio
async def test_get_user_by_email_found(mock_db_conn):
    fake_row = asyncpg.Record.__new__(asyncpg.Record)  # or just use MagicMock
    mock_db_conn.fetchrow.return_value = MagicMock(
        __iter__=lambda s: iter([("id", 1), ("email", "a@b.com")]),
        # simplest approach: just mock dict() conversion
    )
    # ...
```

**Simpler approach — mock the queries module directly:**
```python
# For tests that currently patch queries.* functions,
# simply update the patch target. No asyncpg.Record needed.
@pytest.mark.asyncio
async def test_register_blocks_on_6th_attempt():
    with patch("database.queries.check_and_record_attempt",
               new_callable=AsyncMock,
               return_value={"attempt_count": 6, "locked_until": None, "allowed": False}):
        with pytest.raises(HTTPException):
            await check_auth_rate_limit("1.2.3.4", "register", 5, 60)
```

### pytest.ini Addition for pytest-asyncio

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -q
asyncio_mode = auto
```

Setting `asyncio_mode = auto` means all `async def test_*` functions are treated as async tests without needing `@pytest.mark.asyncio` on each one.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| psycopg2 ThreadedConnectionPool | asyncpg.create_pool() | This phase | Non-blocking DB calls; FastAPI event loop no longer blocked |
| Sync `with get_sync_cursor()` | `async with get_db_conn()` | This phase | All I/O yields to event loop |
| `%s` / `%(name)s` params | `$1`, `$2`, `$3` positional | This phase | Native PostgreSQL protocol params |
| `RealDictCursor` rows (dict subclass) | `asyncpg.Record` | This phase | Must call `dict(row)` before `.get()` |
| `threading.Lock` for pool init | `await init_pool()` in lifespan | This phase | No thread-safety concerns; async init |
| `MagicMock` + sync patch | `AsyncMock` + `@pytest.mark.asyncio` | This phase | Tests can await async DB calls |

**Deprecated/outdated after this phase:**
- `psycopg2`, `psycopg2-binary` — remove from requirements.txt
- `threading` module usage in connection.py — remove entirely
- `psycopg2.extras.RealDictCursor` — replaced by asyncpg Records + dict()
- `get_sync_cursor()` — replaced by `get_db_conn()`
- `get_sync_connection()` — not needed; pool.acquire() handles this

---

## Open Questions

1. **Services layer (scheduler, alerts)**
   - What we know: `services/` had no direct psycopg2 usage found in the scan
   - What's unclear: Whether any service calls `queries.*` synchronously from a background thread (APScheduler can run in threads)
   - Recommendation: Scan `services/` for any direct calls to `database.queries.*`. If APScheduler runs the pipeline in a thread, those calls will need to be `asyncio.run(queries.xxx())` or the scheduler must be configured to run jobs in the async loop.

2. **Health check route signature**
   - What we know: `/health` is currently `def health_check()` (sync), which FastAPI runs in a threadpool
   - What's unclear: After migration it must become `async def` to call `get_db_conn()` — confirm no lifespan ordering issue causes pool to be None during health probes
   - Recommendation: Make `async def health_check()`, pool is guaranteed initialised before the first request since lifespan runs first.

3. **TimescaleDB hypertable DDL in migrations**
   - What we know: schema.sql uses `CREATE EXTENSION IF NOT EXISTS timescaledb`
   - What's unclear: Whether asyncpg's `conn.execute()` handles multi-statement SQL files (it may require splitting on `;`)
   - Recommendation: Test `_run_migrations()` in a dev environment. asyncpg's `execute()` does accept multi-statement SQL strings. If a migration file uses `CREATE EXTENSION` plus `CREATE TABLE` in one file, they can be sent as one `execute()` call.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (already installed) + pytest-asyncio >=0.23 (NEW) |
| Config file | `pytest.ini` — add `asyncio_mode = auto` |
| Quick run command | `pytest tests/ -q -x` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-10 | No psycopg2 import in production paths | static / grep | `grep -r "psycopg2" macropulse/ --include="*.py" \| grep -v test \| grep -v ".pyc"` | ✅ (trivially checkable) |
| DB-11 | get_db_conn() used in all query functions | unit | `pytest tests/test_db_queries.py -x` | ❌ Wave 0 |
| DB-12 | Pool created with min_size=5, max_size=20, command_timeout=30 | unit | `pytest tests/test_db_connection.py -x` | ❌ Wave 0 |
| DB-13 | Async fixtures work; existing tests pass | unit | `pytest tests/ -q` | ✅ (existing tests pass after update) |

### Sampling Rate
- **Per task commit:** `pytest tests/ -q -x`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_db_connection.py` — covers DB-12: pool init params, `get_db_conn()` yields a connection, `close_pool()` awaitable
- [ ] `tests/test_db_queries.py` — covers DB-11: spot-check 3-5 query functions with AsyncMock to confirm async signatures and dict() return values
- [ ] `pytest-asyncio` install: `pip install "pytest-asyncio>=0.23,<1.0"` + add `asyncio_mode = auto` to `pytest.ini`

---

## Sources

### Primary (HIGH confidence)
- [asyncpg API Reference](https://magicstack.github.io/asyncpg/current/api/index.html) — create_pool() params, Pool methods, Connection methods, Record type
- [asyncpg Usage Guide](https://magicstack.github.io/asyncpg/current/usage.html) — transaction patterns, connection context managers, type codecs

### Secondary (MEDIUM confidence)
- [asyncpg GitHub source docs](https://github.com/MagicStack/asyncpg/blob/master/docs/usage.rst) — matches official docs
- [learnbatta asyncpg vs psycopg2 comparison](https://learnbatta.com/blog/asyncpg-psycopg2-comparison/) — confirms %s → $1 difference, fetchall → fetch, fetchone → fetchrow
- [asyncpg Record-to-dict issue #263](https://github.com/MagicStack/asyncpg/issues/263) — confirms dict(record) pattern and lack of `.get()` method on Record

### Tertiary (LOW confidence)
- Medium: "Async Without Tears" — general patterns, not cross-verified against official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — asyncpg API verified directly from official docs
- Architecture: HIGH — patterns derived from official asyncpg documentation and direct codebase inspection
- Pitfalls: HIGH — Record/.get() pitfall verified from GitHub issue; parameter style confirmed from benchmark comparison; transaction requirement is documented asyncpg behavior

**Research date:** 2026-03-30
**Valid until:** 2026-09-30 (asyncpg is stable; API has not changed significantly in years)
