---
phase: 07-auth-endpoint-rate-limiting
verified: 2026-04-03T00:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 7: Auth Endpoint Rate Limiting — Verification Report

**Phase Goal:** Registration and OTP recovery flows reject brute-force attempts and survive process restarts without losing rate limit state
**Verified:** 2026-04-03
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | 6th registration attempt from same IP within 1 hour returns 429 with Retry-After header | VERIFIED | `check_auth_rate_limit(max_attempts=5, window_minutes=60)` in `register()`; `test_register_blocks_on_6th_attempt` passes; `test_register_retry_after_header` passes |
| 2 | After 5 failed OTP verification attempts on the same email, the OTP is invalidated and subsequent attempts return 429 | VERIFIED | `verify_email_code()` exhausts OTP row at 5 failures; `check_auth_rate_limit(endpoint="verify_otp", max_attempts=5)` blocks 6th attempt; `test_otp_row_exhausted_after_5_wrong` and `test_verify_otp_blocks_after_5` pass |
| 3 | Rate limit counters survive an API container restart (state in DB, not memory) | VERIFIED | `check_and_record_attempt()` writes to `auth_rate_limits` table via asyncpg; zero module-level dicts hold state; `test_state_is_db_not_memory` verifies DB call is made and no in-memory dict accumulates state |
| 4 | OTP recovery endpoints return a backoff-indicating response after the 3rd failure | VERIFIED | `_set_backoff_if_needed()` applies `_BACKOFF_SCHEDULE = {3: 30, 4: 60, 5: 300}`; `with_backoff=True` on `recover` and `recover_verify`; `test_recover_backoff_at_attempt_3` verifies `_set_backoff_if_needed` is called with correct args |
| 5 | Rate limit check is the first statement in each handler — before any DB write or email send | VERIFIED | `register()` line 59 (before `get_user_by_email` line 64); `verify()` line 104 (before `verify_email_code` line 108); `recover()` line 179 (before `get_user_by_email` line 182); `recover_verify()` line 212 (before `verify_email_code` line 215) |
| 6 | `/v1/auth/verify` added to `_EXEMPT_PATHS` so daily middleware does not interfere | VERIFIED | `api/middleware/rate_limit.py` line 43: `"/v1/auth/verify",  # has its own auth rate limiting (SEC-32)` |
| 7 | All 8 test cases pass (non-xfail) | VERIFIED | `pytest tests/test_auth_rate_limit.py -v` → `8 passed in 0.44s` |
| 8 | REQUIREMENTS.md marks SEC-30 through SEC-33 as Complete | VERIFIED | Four `[x]` entries in checklist; traceability table shows `Complete (07-01)` for all four |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `database/migrations/009_auth_rate_limits.sql` | auth_rate_limits DDL — table + unique index | VERIFIED | `CREATE TABLE IF NOT EXISTS auth_rate_limits` present; idempotent; correct schema with all columns and UNIQUE constraint |
| `database/queries.py` | `check_and_record_attempt()` atomic upsert | VERIFIED | Async function at line 677; single-round-trip INSERT...ON CONFLICT upsert; `WINDOW_INTERVAL` str.replace() workaround for asyncpg INTERVAL limitation; RETURNING clause |
| `api/middleware/auth_rate_limit.py` | `check_auth_rate_limit()` + `get_client_ip()` | VERIFIED | Both functions exported; `check_auth_rate_limit` is async, raises 429 with Retry-After, fails open on DB error; `get_client_ip` replicates Docker bridge trust logic |
| `api/routes/auth.py` | Rate-limited register, verify, recover, recover_verify handlers | VERIFIED | All four handlers call `check_auth_rate_limit` as first meaningful statement; 5 matches (1 import + 4 call sites) |
| `api/middleware/rate_limit.py` | `_EXEMPT_PATHS` with `/v1/auth/verify` added | VERIFIED | Present at line 43 with explanatory comment |
| `tests/test_auth_rate_limit.py` | 8 passing tests covering SEC-30 through SEC-33 | VERIFIED | 8 passed, 0 failed, 0 skipped, 0 xfail |
| `tests/conftest.py` | `mock_auth_rl_cursor` fixture | VERIFIED | Present as async fixture using asyncpg-compatible `AsyncMock` pattern; patches `database.connection.get_db_conn` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `api/routes/auth.py register()` | `check_auth_rate_limit(identifier=client_ip, endpoint="register")` | First statement in handler body | VERIFIED | Line 59: `await check_auth_rate_limit(identifier=client_ip, endpoint="register", max_attempts=5, window_minutes=60)` |
| `api/routes/auth.py recover()` | `check_auth_rate_limit(identifier=email, endpoint="recover", with_backoff=True)` | First statement — before `get_user_by_email()` | VERIFIED | Line 179 precedes line 182 (`get_user_by_email`) |
| `api/routes/auth.py verify()` | `check_auth_rate_limit(identifier=email, endpoint="verify_otp")` | First statement — before `verify_email_code()` | VERIFIED | Line 104 precedes line 108 (`verify_email_code`) |
| `api/middleware/auth_rate_limit.py` | `database/queries.check_and_record_attempt` | `from database import queries` + `await queries.check_and_record_attempt(...)` | VERIFIED | Import at line 19; call at line 113 |
| `database/queries.check_and_record_attempt` | `auth_rate_limits` table | `async with get_db_conn() as conn` | VERIFIED | `INSERT INTO auth_rate_limits` at line 696 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| SEC-30 | 07-00, 07-01 | `/v1/auth/register` rate-limited: max 5 per IP per hour | SATISFIED | `check_auth_rate_limit(endpoint="register", max_attempts=5, window_minutes=60)`; 3 passing tests |
| SEC-31 | 07-00, 07-01 | `/v1/auth/recover` and `/v1/auth/recover/verify` rate-limited: max 5 per email per 15 min; backoff after 3 | SATISFIED | Both handlers use `with_backoff=True`; `_BACKOFF_SCHEDULE = {3: 30, 4: 60, 5: 300}`; 2 passing tests |
| SEC-32 | 07-00, 07-01 | OTP verification lockout: after 5 failed attempts OTP is invalidated | SATISFIED | `verify_email_code()` exhausts OTP row at 5 failures (pre-existing); rate limit blocks 6th via `endpoint="verify_otp"`; 2 passing tests |
| SEC-33 | 07-00, 07-01 | Rate limit state persists in DB — survives process restart | SATISFIED | All state in `auth_rate_limits` table; no module-level counters; `test_state_is_db_not_memory` verifies DB write and no in-memory dict |

All four requirement IDs declared in both plan frontmatters are accounted for. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scanned: `database/migrations/009_auth_rate_limits.sql`, `database/queries.py`, `api/middleware/auth_rate_limit.py`, `api/routes/auth.py`, `api/middleware/rate_limit.py`, `tests/test_auth_rate_limit.py`, `tests/conftest.py`. No TODOs, FIXMEs, placeholder comments, empty return stubs, or console.log-only implementations found.

### Architectural Deviation (Non-Blocking)

The plan (07-00) specified synchronous `get_sync_cursor` (psycopg2) for `check_and_record_attempt()` and `_set_backoff_if_needed()`. The implementation uses async `get_db_conn()` (asyncpg) throughout — consistent with the rest of the codebase's async/asyncpg pattern. This deviation is coherent, correct, and confirmed working by the full test suite. All functions are `async def`, all callers use `await`, tests use `AsyncMock`. No functional impact on the phase goal.

### Human Verification Required

None. All success criteria are verifiable programmatically.

## Full Test Suite

`pytest tests/ -q` → **97 passed in 3.30s** — no regressions introduced.

---

_Verified: 2026-04-03_
_Verifier: Claude (gsd-verifier)_
