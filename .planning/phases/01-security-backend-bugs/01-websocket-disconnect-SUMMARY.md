---
phase: 01-security-backend-bugs
plan: 04
subsystem: api
tags: [websocket, concurrency, python, fastapi]

# Dependency graph
requires: []
provides:
  - Race-safe WebSocket broadcast using list(_connections) snapshot in broadcast_regime()
affects: [websocket, api]

# Tech tracking
tech-stack:
  added: []
  patterns: [Snapshot mutable set before iteration to prevent RuntimeError on concurrent mutation]

key-files:
  created: []
  modified:
    - api/routes/websocket.py

key-decisions:
  - "Use list(_connections) snapshot instead of iterating _connections directly — prevents RuntimeError when a client disconnect mutates the set mid-iteration"

patterns-established:
  - "Snapshot pattern: always copy mutable shared state (list(set)) before iteration in async contexts where concurrent coroutines can mutate it"

requirements-completed: [BUG-02]

# Metrics
duration: <1min
completed: 2026-03-18
---

# Phase 1 Plan 04: WebSocket Disconnect Summary

**Race-safe WebSocket broadcast via list(_connections) snapshot — prevents RuntimeError when client disconnects mid-iteration**

## Performance

- **Duration:** <1 min
- **Started:** 2026-03-18T19:13:04Z
- **Completed:** 2026-03-18T19:13:24Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Changed `for ws in _connections:` to `for ws in list(_connections):` in `broadcast_regime()`
- Prevents `RuntimeError: Set changed size during iteration` when a client disconnect fires `_connections.discard(ws)` concurrently during a broadcast
- Stale-connection cleanup loop and `finally: _connections.discard(ws)` remain unchanged — no behavior change beyond eliminating the race

## Task Commits

Each task was committed atomically:

1. **Task 1: Snapshot _connections before iterating in broadcast_regime()** - `c7b02a8` (fix)

**Plan metadata:** _(docs commit added below)_

## Files Created/Modified

- `api/routes/websocket.py` — one-word fix: `list(_connections)` snapshot prevents RuntimeError on concurrent set mutation

## Decisions Made

- Used `list(_connections)` snapshot (simplest, zero-overhead for small connection sets) rather than a threading lock or copy-on-write structure — consistent with existing in-process pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- BUG-02 resolved; broadcast loop now survives any client disconnect without interrupting remaining connected clients
- Ready to proceed with remaining Phase 1 plans

---
*Phase: 01-security-backend-bugs*
*Completed: 2026-03-18*
