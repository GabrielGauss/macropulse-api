---
phase: 07-auth-endpoint-rate-limiting
plan: "01"
subsystem: auth-rate-limiting
tags: [security, rate-limiting, auth, middleware, testing]
dependency_graph:
  requires:
    - 07-00 (auth_rate_limits table + check_and_record_attempt + auth_rate_limit middleware)
  provides:
    - register() rate-limited by IP (SEC-30)
    - verify() rate-limited by email (SEC-32)
    - recover() rate-limited by email with backoff (SEC-31)
    - recover_verify() rate-limited by email with backoff (SEC-31, SEC-32)
    - /v1/auth/verify in _EXEMPT_PATHS (daily middleware bypass)
    - 8 passing tests for SEC-30 through SEC-33
  affects:
    - api/routes/auth.py — all public auth handlers
    - api/middleware/rate_limit.py — _EXEMPT_PATHS expanded
    - tests/test_auth_rate_limit.py — xfail stubs replaced with real tests
tech_stack:
  added: []
  patterns:
    - Request parameter injection (FastAPI auto-injects Request without breaking existing callers)
    - Patch at binding site (database.queries.get_sync_cursor) not at origin (database.connection.get_sync_cursor)
    - Rate limit check as first statement — email extraction allowed before check when email IS the identifier
key_files:
  created: []
  modified:
    - api/routes/auth.py (rate limit calls wired into all four handlers + Request import)
    - api/middleware/rate_limit.py (/v1/auth/verify added to _EXEMPT_PATHS)
    - tests/test_auth_rate_limit.py (8 xfail stubs replaced with 8 passing tests)
    - .planning/REQUIREMENTS.md (SEC-30 through SEC-33 marked Complete)
decisions:
  - "Email extraction before check_auth_rate_limit in verify() and recover_verify() — email is the rate-limit identifier, so it must be extracted first. This is not a side effect and does not reveal information before the check fires."
  - "Patch database.queries.get_sync_cursor not database.connection.get_sync_cursor — queries.py imports get_sync_cursor at module level; patch must target the binding site to intercept calls correctly."
  - "recover() check fires before queries.get_user_by_email() — anti-enumeration: attacker must not learn if email exists before hitting the limit."
metrics:
  duration: ~15 min
  completed_date: "2026-03-30"
  tasks_completed: 3
  files_modified: 4
---

# Phase 7 Plan 01: Wire Auth Rate Limits + Tests Summary

**One-liner:** Activated auth brute-force protection by wiring check_auth_rate_limit() into all four handlers (IP for register, email+backoff for recover/verify), added /v1/auth/verify to _EXEMPT_PATHS, and replaced 8 xfail stubs with passing tests.

## What Was Built

### Task 1: Rate limits wired into auth.py + _EXEMPT_PATHS updated

`api/routes/auth.py` was edited to import `check_auth_rate_limit` and `get_client_ip` from `api.middleware.auth_rate_limit`, and `Request` from `starlette.requests`.

Four handlers updated:

- `register(body, request)`: Added `request: Request` to signature. `get_client_ip(request)` extracts the IP, then `check_auth_rate_limit(identifier=client_ip, endpoint="register", max_attempts=5, window_minutes=60)` fires before any DB or email work.

- `verify(body)`: Email extracted first (it IS the identifier), then `check_auth_rate_limit(identifier=email, endpoint="verify_otp", max_attempts=5, window_minutes=15)` fires before `queries.verify_email_code()`.

- `recover(body, request)`: Added `request: Request` to signature. Email extracted, then `check_auth_rate_limit(identifier=email, endpoint="recover", max_attempts=5, window_minutes=15, with_backoff=True)` fires BEFORE `queries.get_user_by_email()` — critical for anti-enumeration.

- `recover_verify(body)`: Email and code extracted, then `check_auth_rate_limit(identifier=email, endpoint="recover_verify", max_attempts=5, window_minutes=15, with_backoff=True)` fires before `queries.verify_email_code()`.

`api/middleware/rate_limit.py`: `/v1/auth/verify` added to `_EXEMPT_PATHS` with inline comment noting it has its own rate limiting (SEC-32). No other lines modified.

### Task 2: 8 passing tests (replacing xfail stubs)

`tests/test_auth_rate_limit.py` completely rewritten. All 8 `@pytest.mark.xfail` stubs replaced with real implementations:

- `test_register_blocks_on_6th_attempt` (SEC-30): Counter-based fake returns allowed=False on 6th call; asserts HTTPException(429).
- `test_register_window_reset` (SEC-30): Simulates window expiry by returning allowed=True after the blocked call; asserts no exception on reset call.
- `test_register_retry_after_header` (SEC-30): locked_until set 300s in future; asserts Retry-After header present and >= 1.
- `test_recover_blocks_on_6th_attempt` (SEC-31): Same pattern as register but endpoint="recover", with_backoff=True.
- `test_recover_backoff_at_attempt_3` (SEC-31): Patches both `check_and_record_attempt` and `_set_backoff_if_needed`; asserts backoff called with correct args on attempt_count=3.
- `test_verify_otp_blocks_after_5` (SEC-32): Returns allowed=False after 5 calls; asserts 429.
- `test_otp_row_exhausted_after_5_wrong` (SEC-32): Patches verify_email_code; confirms call count does not increase when rate limit fires (rate limit fires before verify call in handler).
- `test_state_is_db_not_memory` (SEC-33): Patches `database.queries.get_sync_cursor` (binding site); calls `check_and_record_attempt` directly; asserts `mock_cur.execute.called` is True; verifies no identifier-keyed dicts exist in `auth_rate_limit` module namespace.

### Task 3: REQUIREMENTS.md updated

SEC-30 through SEC-33 changed from `[ ]` to `[x]`. Traceability table rows updated from "Pending" to "Complete (07-01)".

## Verification Results

```
python -c "from api.routes.auth import register, verify, recover, recover_verify; print('ok')"
ok

grep -c "check_auth_rate_limit" api/routes/auth.py
5  (1 import line + 4 call sites)

grep "/v1/auth/verify" api/middleware/rate_limit.py
    "/v1/auth/verify",  # has its own auth rate limiting (SEC-32)

pytest tests/test_auth_rate_limit.py -v
8 passed in 12.74s

pytest tests/test_auth_rate_limit.py tests/test_security.py tests/test_billing.py -v
12 passed in 15.83s

pytest tests/ -q
19 passed in 15.75s

grep -c "\- \[x\] \*\*SEC-3[0-3]\*\*" .planning/REQUIREMENTS.md
4
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Patching get_sync_cursor at wrong binding site**
- **Found during:** Task 2
- **Issue:** `test_state_is_db_not_memory` initially patched `database.connection.get_sync_cursor`, but `database/queries.py` imports `get_sync_cursor` at module level — the name binding in `database.queries` namespace was never replaced, causing the real function to be called and failing with a connection error.
- **Fix:** Changed patch target to `database.queries.get_sync_cursor` (where it's bound and used).
- **Files modified:** `tests/test_auth_rate_limit.py`
- **Commit:** d4f5d13

## Commits

- `e788e60`: feat(07-01): wire check_auth_rate_limit into all four auth handlers
- `d4f5d13`: feat(07-01): implement 8 passing auth rate limit tests (SEC-30 through SEC-33)
- `d766451`: chore(07-01): mark SEC-30 through SEC-33 complete in REQUIREMENTS.md

## Self-Check: PASSED

- `api/routes/auth.py` contains check_auth_rate_limit — EXISTS (5 matches: 1 import + 4 calls)
- `api/middleware/rate_limit.py` contains /v1/auth/verify — EXISTS
- `tests/test_auth_rate_limit.py` has 8 passing tests — CONFIRMED (pytest output)
- `.planning/REQUIREMENTS.md` has 4 checked SEC-3x entries — CONFIRMED (grep returns 4)
- Commit e788e60 — EXISTS
- Commit d4f5d13 — EXISTS
- Commit d766451 — EXISTS
