---
phase: 01-security-backend-bugs
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - api/middleware/rate_limit.py
autonomous: true
requirements:
  - SEC-03
must_haves:
  truths:
    - "Concurrent anonymous requests from the same IP cannot both pass the rate-limit check simultaneously — the counter increment is serialized per IP"
    - "The asyncio.Lock is acquired before reading _anon_counters and released after writing — the entire read-check-increment-write block is atomic within one event loop"
    - "Lock acquisition does not block the event loop for other IPs — each IP has its own independent lock"
  artifacts:
    - path: "api/middleware/rate_limit.py"
      provides: "Race-free anonymous rate limit counter using per-IP asyncio.Lock"
      contains: "_anon_locks"
  key_links:
    - from: "api/middleware/rate_limit.py (_anon_locks)"
      to: "anonymous path dispatch block (lines ~193-225)"
      via: "async with _anon_locks[client_ip]: wraps the read-check-increment-write block"
      pattern: "async with _anon_locks\\[client_ip\\]"
---

<objective>
Fix the TOCTOU race condition in the anonymous (unauthenticated) rate-limit counter in api/middleware/rate_limit.py. The current code reads and writes _anon_counters in three non-atomic steps with no locking; two concurrent async requests can both slip through the same counter value. The fix is a per-IP asyncio.Lock that serializes the entire check-and-increment within one event loop.

Purpose: SEC-03 — under concurrent anonymous traffic a client can exceed their configured daily limit because multiple requests read the same counter value before any of them writes back.

Output: api/middleware/rate_limit.py with _anon_locks defaultdict added at module level and the anonymous dispatch block wrapped in async with _anon_locks[client_ip].
</objective>

<execution_context>
@C:/Users/gabri/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/gabri/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add asyncio import and _anon_locks module-level dict</name>
  <files>api/middleware/rate_limit.py</files>
  <action>
Open api/middleware/rate_limit.py.

Step 1 — Add asyncio import. The imports block currently starts at line 24 with `from __future__ import annotations`. The standard library imports are on lines 26-29:

```python
import datetime as dt
import hashlib
import logging
from collections import defaultdict
```

Add `import asyncio` immediately after `from __future__ import annotations` and before `import datetime as dt`. The imports block becomes:

```python
from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import logging
from collections import defaultdict
```

Step 2 — Add _anon_locks dict at module level. The current module-level dict for anonymous counters is at line 57:

```python
_anon_counters: dict[str, tuple[str, int]] = defaultdict(lambda: ("", 0))
```

Immediately after that line, add:

```python
# Per-IP async locks — serialize the read-check-increment-write block.
_anon_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
```

No other changes in this task.
  </action>
  <verify>
    <automated>grep -n "import asyncio\|_anon_locks" api/middleware/rate_limit.py</automated>
  </verify>
  <done>
`grep` returns two lines: one showing `import asyncio` in the imports block, and one showing `_anon_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)` at module level adjacent to `_anon_counters`.
  </done>
</task>

<task type="auto">
  <name>Task 2: Wrap anonymous counter block with async with _anon_locks[client_ip]</name>
  <files>api/middleware/rate_limit.py</files>
  <action>
In api/middleware/rate_limit.py, navigate to the anonymous dispatch block inside the `else:` branch (currently lines ~192-225). The current code reads:

```python
        else:
            # ── Anonymous path: in-memory IP counter ─────────────────────
            today = dt.date.today().isoformat()
            date_str, count = _anon_counters[client_ip]
            if date_str != today:
                count = 0

            if count >= limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "detail": (
                            f"Daily limit of {limit} requests reached. "
                            "Provide an API key or wait until midnight UTC."
                        ),
                        "reset_at": reset,
                    },
                    headers={
                        "X-RateLimit-Limit":     str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset":     str(reset),
                        "Retry-After": str(reset - int(dt.datetime.now(dt.timezone.utc).timestamp())),
                    },
                )

            count += 1
            _anon_counters[client_ip] = (today, count)

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"]     = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(limit - count)
            response.headers["X-RateLimit-Reset"]     = str(reset)
            return response
```

Replace it with the following — the `async with _anon_locks[client_ip]:` block wraps only the read-check-increment-write operations. The `await call_next(request)` and header-setting code must remain OUTSIDE the lock to avoid holding the lock across a network call:

```python
        else:
            # ── Anonymous path: in-memory IP counter ─────────────────────
            today = dt.date.today().isoformat()
            async with _anon_locks[client_ip]:
                date_str, count = _anon_counters[client_ip]
                if date_str != today:
                    count = 0

                if count >= limit:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "rate_limit_exceeded",
                            "detail": (
                                f"Daily limit of {limit} requests reached. "
                                "Provide an API key or wait until midnight UTC."
                            ),
                            "reset_at": reset,
                        },
                        headers={
                            "X-RateLimit-Limit":     str(limit),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset":     str(reset),
                            "Retry-After": str(reset - int(dt.datetime.now(dt.timezone.utc).timestamp())),
                        },
                    )

                count += 1
                _anon_counters[client_ip] = (today, count)

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"]     = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(limit - count)
            response.headers["X-RateLimit-Reset"]     = str(reset)
            return response
```

Key structural rules:
- `today = dt.date.today().isoformat()` stays outside the lock (read-only, no race concern)
- The entire `date_str, count = ...` read through `_anon_counters[client_ip] = (today, count)` write is inside the lock
- The early-return JSONResponse for 429 is inside the lock (exits immediately, lock released by context manager)
- `await call_next(request)` is outside the lock (never hold a lock across an await that calls downstream code)
- Header assignment and final return are outside the lock
  </action>
  <verify>
    <automated>grep -n "async with _anon_locks" api/middleware/rate_limit.py</automated>
  </verify>
  <done>
`grep` returns one line showing `async with _anon_locks[client_ip]:` in the anonymous dispatch block. The authenticated path (lines ~146-190) is unchanged. The file has no syntax errors (verify with `python -m py_compile api/middleware/rate_limit.py`).
  </done>
</task>

</tasks>

<verification>
From project root:

```bash
# Confirm asyncio imported
grep -n "import asyncio" api/middleware/rate_limit.py

# Confirm lock dict defined at module level
grep -n "_anon_locks" api/middleware/rate_limit.py

# Confirm lock usage in dispatch
grep -n "async with _anon_locks" api/middleware/rate_limit.py

# Syntax check
python -m py_compile api/middleware/rate_limit.py && echo "OK"
```

All four commands must succeed with output.
</verification>

<success_criteria>
1. `import asyncio` appears in the imports block.
2. `_anon_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)` appears at module level next to `_anon_counters`.
3. `async with _anon_locks[client_ip]:` wraps the read-check-increment-write block in the anonymous dispatch branch.
4. `python -m py_compile api/middleware/rate_limit.py` exits with no errors.
5. The authenticated path (key_hash branch) is unchanged.
</success_criteria>

<output>
After completion, create `.planning/phases/01-security-backend-bugs/01-rate-limit-race-SUMMARY.md`
</output>
