---
phase: "08-asyncpg-migration"
plan: "01"
subsystem: "database"
tags: [asyncpg, queries, async, migration, positional-params]
dependency_graph:
  requires: [database.connection.get_db_conn]
  provides: [database.queries.*]
  affects: [api/routes, api/middleware, scheduler]
tech_stack:
  added: []
  removed: [psycopg2 cursor usage, get_sync_cursor shim calls]
  patterns: [asyncpg positional params $N, conn.fetchrow/fetch/execute, conn.transaction()]
key_files:
  created: []
  modified:
    - database/queries.py
decisions:
  - "Used conn.transaction() for create_email_verification (DELETE+INSERT) and verify_email_code (UPDATE+UPDATE) to ensure atomicity"
  - "Preserved str.replace INTERVAL pattern for check_and_set_ip_lock and check_and_record_attempt — asyncpg cannot parameterise INTERVAL literals"
  - "fetch_subscriber_emails returns list[str] via [row['email'] for row in rows] — not list[dict]"
  - "fetch_regime_history builds dynamic $N positional args to support optional start/end date filters"
metrics:
  duration: "~5 minutes"
  completed: "2026-03-31"
  tasks_completed: 1
  files_modified: 1
---

# Phase 08 Plan 01: Rewrite all query functions in queries.py to asyncpg Summary

All 36 database query functions migrated from synchronous psycopg2 cursor calls to async asyncpg, with positional $N parameters, dict-wrapped returns, and explicit transactions for multi-statement functions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Convert all query functions to asyncpg | 421ccef | database/queries.py |

## What Was Built

### database/queries.py

Complete conversion of all 36 query functions:

**Import change:**
- Removed: `from database.connection import get_sync_cursor`
- Added: `from database.connection import get_db_conn`

**Function conversion (all 36 functions):**
- All `def` → `async def`
- All `with get_sync_cursor() as cur:` → `async with get_db_conn() as conn:`
- All `%(name)s` and `%s` params → positional `$1`, `$2`, ... `$N`
- All `cur.execute()` → `await conn.execute()`
- All `cur.fetchone()` → `row = await conn.fetchrow(); return dict(row) if row else None`
- All `cur.fetchall()` → `rows = await conn.fetch(); return [dict(r) for r in rows]`
- RETURNING clause queries use `await conn.fetchrow()` → `return dict(row)`

**Special cases handled correctly:**

1. `create_email_verification` — DELETE + INSERT wrapped in `async with conn.transaction()`
2. `verify_email_code` — Two UPDATE statements wrapped in `async with conn.transaction()`
3. `check_and_set_ip_lock` — Uses `str.replace("WINDOW_INTERVAL", f"{_IP_LOCK_MINUTES} minutes")` before execute; asyncpg positional $1/$2 for key_hash and client_ip
4. `check_and_record_attempt` — Same `str.replace` pattern for window_minutes INTERVAL; $1/$2 for identifier and endpoint
5. `fetch_regime_history` — Dynamic WHERE clause with `args.append(val); conditions.append(f"${len(args)}")` pattern
6. `fetch_subscriber_emails` — Returns `[row["email"] for row in rows]` (list[str], not list[dict])
7. `upsert_macro_features` — 14 positional args ($1..$14) with explicit key ordering
8. `increment_daily_usage` — Returns scalar `int(row["daily_requests"])` via fetchrow

## Deviations from Plan

None — the migration was mechanical and executed exactly as specified. The file was already partially scaffolded (some functions already had asyncpg signatures in the working tree); the full conversion was applied uniformly.

## Verification Results

```
PASS: no legacy params (grep for %s, %( returns 0)
PASS: no get_sync_cursor reference
PASS: all top-level functions are async (36 async defs, 0 sync defs)
PASS: transactions present (2 conn.transaction() blocks)
PASS: queries importable (python -c "import database.queries")
```

## Self-Check: PASSED

- `database/queries.py` — exists and verified (268 insertions, 256 deletions)
- commit `421ccef` — confirmed in git log
