# Phase 1: Security & Backend Bugs — Research

**Date:** 2026-03-18
**Requirements:** SEC-01, SEC-02, SEC-03, BUG-01, BUG-02

---

## Summary

All five bugs have been identified and fully diagnosed through codebase analysis. Each fix is localized — none require architectural changes or new dependencies. All changes are backward-compatible.

---

## SEC-01: Missing .env.example Entries

**File:** `.env.example`

The following settings exist in `config/settings.py` (all with empty-string defaults, all loaded from env) but are **completely absent from `.env.example`**:

| Variable | Purpose | settings.py line |
|----------|---------|-----------------|
| `OWNER_API_KEY` | Master auth key — tier=owner, bypasses all tier gates | 73 |
| `ANTHROPIC_API_KEY` | AI commentary endpoint (Claude) | 58 |
| `BREVO_API_KEY` | Transactional email (Brevo HTTP API) | 97 |
| `BREVO_SENDER_EMAIL` | Override sender email | 98 |
| `DISCORD_WEBHOOK_URL` | Daily macro signal posts to Discord channel | 107 |
| `X_API_KEY` | Twitter/X integration | 110 |
| `X_API_SECRET` | Twitter/X integration | 111 |
| `X_ACCESS_TOKEN` | Twitter/X integration | 112 |
| `X_ACCESS_TOKEN_SECRET` | Twitter/X integration | 113 |

`OWNER_API_KEY` is the most critical — it's a master credential that bypasses all tier gates and rate limiting. Without documentation, a fresh deployer has no way to know it exists, and no guidance on how to generate a value.

**Fix:** Add all missing variables to `.env.example` with descriptive comments. For `OWNER_API_KEY`, include a note on how to generate a secure value (e.g., `python -c "import secrets; print('mp_' + secrets.token_urlsafe(32))"`).

---

## SEC-02 + BUG-01: Duplicate Alerting + Data Lag (daily_pipeline.py)

Both issues live in `data/pipelines/daily_pipeline.py`.

### SEC-02: Duplicate Regime Change Alerts

**The pipeline fires two separate alert systems for the same regime change:**

**Call 1 (line ~224):** `alert_regime_change()` from `services/alerting.py`
- Sends HTML email to `settings.alert_recipients` (operator SMTP)
- POSTs JSON to `settings.webhook_url` (operator Slack/Discord)
- Intended audience: operator/team notifications

**Call 2 (line ~237):** `send_regime_change_alerts()` from `services/alerts.py`
- Iterates all starter/pro users from DB
- Sends formatted email to each user
- POSTs webhook to each pro/owner user's configured `webhook_url`
- Intended audience: paying subscribers

**Why this is a bug:** Both are triggered by the same regime change condition in the same pipeline run. Any user whose email appears in both `settings.alert_recipients` AND the subscriber DB receives two notifications. More importantly, the operator's `settings.webhook_url` fires twice if the pipeline's alerting.py call is triggered alongside alerts.py's delivery to pro users who share the same webhook endpoint.

**Root cause:** `alerting.py` was the original system; `alerts.py` was added later as the per-user delivery system. The pipeline accumulated both calls without removing the original.

**Fix:** Remove the `alert_regime_change()` call from the regime change block (lines ~220-230). Keep `alert_regime_change()` only where it already correctly fires for **drift warnings** (lines ~266-270) — that use case is appropriate (operator-level model quality alerts). `send_regime_change_alerts()` becomes the sole path for regime change notifications.

### BUG-01: Data Lag Off-by-One

**File:** `data/pipelines/daily_pipeline.py`, line ~147

```python
# Current (fires at 4+ days stale)
if latest_fred_date and (today - latest_fred_date).days > 3:

# Fixed (fires at 3+ days stale)
if latest_fred_date and (today - latest_fred_date).days >= 3:
```

**Why `>= 3` is correct:** FRED data is normally 1–2 calendar days behind. Three calendar days of lag signals a real data delivery problem (weekend + holiday gap, or API outage). The requirement says "after 3 days of staleness" — `>= 3` fires on day 3, `> 3` fires on day 4.

No other staleness thresholds exist in the codebase. `api/routes/pipeline.py` only reads the stored `data_lag` flag; `database/queries.py` only stores it. Single-location fix.

---

## SEC-03: Rate Limit Anonymous Counter Race

**File:** `api/middleware/rate_limit.py`, lines ~194–219 (anonymous path)

The middleware has two code paths:
1. **Authenticated (DB-persisted):** Uses atomic `UPDATE ... RETURNING` SQL — correct and safe
2. **Anonymous (in-memory):** Uses `_anon_counters: dict[str, tuple[str, int]]` — UNSAFE

The anonymous path reads, checks, and writes the counter in three non-atomic steps with no locking:

```python
date_str, count = _anon_counters[client_ip]   # read
if date_str != today:
    count = 0
if count >= limit:
    return 429_response
count += 1
_anon_counters[client_ip] = (today, count)    # write
```

In an async event loop, `await call_next(request)` elsewhere can yield control between these steps. Two concurrent requests from the same IP can both read `count=49`, both see `count < 50`, both increment to 50, both write back — only one increment counted. Under sustained load a client can make significantly more than the configured limit.

**Why NOT `run_in_executor`:** The counter is in-memory Python — no blocking I/O. `run_in_executor` adds thread overhead for no benefit. The correct fix for async TOCTOU is a per-key `asyncio.Lock`.

**No `asyncpg` in requirements.txt.** No `run_in_executor` patterns exist anywhere in the codebase. Switching to async DB for anonymous counters is out of scope.

**Fix:** Add `_anon_locks: defaultdict[str, asyncio.Lock]` at module level. Wrap the read-check-increment-write block with `async with _anon_locks[client_ip]:`.

```python
import asyncio
from collections import defaultdict

_anon_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# In the anonymous path:
async with _anon_locks[client_ip]:
    date_str, count = _anon_counters[client_ip]
    if date_str != today:
        count = 0
    if count >= limit:
        return 429_response
    count += 1
    _anon_counters[client_ip] = (today, count)
```

This serializes concurrent requests from the same IP at the lock level without blocking the entire event loop.

---

## BUG-02: WebSocket Set Mutation Mid-Broadcast

**File:** `api/routes/websocket.py`, line ~52

`broadcast_regime()` iterates `_connections` (a plain `set[WebSocket]`) and yields at each `await ws.send_text(message)`. Between yields, another coroutine (`regime_stream`'s `finally` block) can call `_connections.discard(ws)`, mutating the set during iteration:

```
RuntimeError: Set changed size during iteration
```

When this exception propagates, the broadcast loop dies. All connected clients AFTER the disconnected one in iteration order receive nothing.

**Fix:** Snapshot the set before iterating:

```python
for ws in list(_connections):   # was: for ws in _connections:
```

`list(_connections)` creates a copy at that moment. The underlying set can be modified freely; iteration continues on the snapshot. Stale connections are still caught by the `except Exception` block and discarded via `_connections.discard(ws)` after the loop.

`regime_stream`'s disconnect handling (`finally: _connections.discard(ws)`) is already correct — no changes needed there.

---

## Validation Architecture

Tests to verify each fix:

| Requirement | Verification |
|------------|-------------|
| SEC-01 | `grep OWNER_API_KEY .env.example` returns a match |
| SEC-02 | `grep -n "alert_regime_change" data/pipelines/daily_pipeline.py` shows calls only in drift block (lines 260+), not in regime change block |
| SEC-03 | `grep "_anon_locks" api/middleware/rate_limit.py` returns a match; `grep "asyncio.Lock" api/middleware/rate_limit.py` returns a match |
| BUG-01 | `grep ">= 3" data/pipelines/daily_pipeline.py` returns the data-lag guard line |
| BUG-02 | `grep "list(_connections)" api/routes/websocket.py` returns a match |
