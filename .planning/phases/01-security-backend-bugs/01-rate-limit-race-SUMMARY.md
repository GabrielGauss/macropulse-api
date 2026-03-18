---
phase: 01-security-backend-bugs
plan: 01
subsystem: api
tags: [asyncio, rate-limiting, concurrency, middleware, fastapi]

# Dependency graph
requires: []
provides:
  - Race-free anonymous rate-limit counter using per-IP asyncio.Lock in api/middleware/rate_limit.py
affects: [02-security-backend-bugs, api-middleware]

# Tech tracking
tech-stack:
  added: []
  patterns: [per-IP asyncio.Lock serializing read-check-increment-write in async middleware]

key-files:
  created: []
  modified:
    - api/middleware/rate_limit.py

key-decisions:
  - "Keep await call_next(request) outside the asyncio.Lock to avoid holding the lock across network I/O"
  - "Use defaultdict(asyncio.Lock) so locks are created on first access per IP with no manual initialization"
  - "today = dt.date.today().isoformat() stays outside the lock — read-only, no race concern"

patterns-established:
  - "Lock scope: wrap only the read-check-increment-write block, never I/O-awaiting operations"

requirements-completed: [SEC-03]

# Metrics
duration: 5min
completed: 2026-03-18
---

# Phase 1 Plan 1: Rate-Limit Race Condition Summary

**Per-IP asyncio.Lock serializing the anonymous rate-limit read-check-increment-write block, eliminating TOCTOU race under concurrent requests (SEC-03)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-18T19:13:03Z
- **Completed:** 2026-03-18T19:18:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added `import asyncio` to stdlib imports
- Added `_anon_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)` at module level
- Wrapped the entire anonymous counter read-check-increment-write block in `async with _anon_locks[client_ip]:`
- `await call_next(request)` left outside the lock — no lock held across network calls
- Syntax verified with `python -m py_compile`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add asyncio import and _anon_locks module-level dict** - `7adb9dd` (feat)
2. **Task 2: Wrap anonymous counter block with async with _anon_locks[client_ip]** - `7e7eb34` (fix)

## Files Created/Modified
- `api/middleware/rate_limit.py` - Added per-IP asyncio locks and atomic counter block

## Decisions Made
- Lock scope is tight: only the counter state read and write are inside the lock. The downstream `await call_next(request)` stays outside to prevent holding the lock while awaiting network I/O, which would effectively serialize ALL anonymous requests rather than just the counter operations.
- `defaultdict(asyncio.Lock)` chosen over explicit dict with `setdefault` — cleaner, idiomatic, locks created lazily per IP.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SEC-03 resolved. Anonymous rate limiting is now concurrency-safe.
- Remaining blocker: SEC-01 (hardcoded owner API key at `api/auth.py:86`) still needs resolution before public exposure.

---
*Phase: 01-security-backend-bugs*
*Completed: 2026-03-18*
