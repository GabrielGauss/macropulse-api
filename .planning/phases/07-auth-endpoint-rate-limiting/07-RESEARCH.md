# Phase 7: Auth Endpoint Rate Limiting - Research

**Researched:** 2026-03-29
**Domain:** FastAPI auth endpoint hardening — DB-persisted brute-force protection for OTP flows
**Confidence:** HIGH (all findings from direct codebase inspection; no speculation)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEC-30 | `/v1/auth/register` rate-limited: max 5 registration attempts per IP per hour | New `auth_rate_limits` table keyed on IP + `'register'`; IP extracted via trusted-proxy logic already in `rate_limit.py` |
| SEC-31 | `/v1/auth/recover` and `/v1/auth/recover/verify` rate-limited: max 5 OTP attempts per email per 15 minutes; exponential backoff after 3 failures | Same table keyed on email + `'recover'` / `'recover_verify'`; `locked_until` column stores backoff expiry |
| SEC-32 | OTP verification lockout: after 5 failed OTP attempts OTP is invalidated and a new one must be requested | Partially implemented: `email_verifications.attempts` + `_OTP_MAX_ATTEMPTS=5` in `verify_email_code()` exhausts the OTP row. Phase 7 adds the 429 rate-limit gate BEFORE `verify_email_code()` is called, surfacing a proper 429 with Retry-After instead of a generic 400. Also applies to `/v1/auth/verify` (registration flow step 2) — same attack surface |
| SEC-33 | Rate limit state for auth endpoints persists in DB — survives process restart | `auth_rate_limits` table in PostgreSQL via existing `get_sync_cursor()` pool; zero in-memory state |
</phase_requirements>

---

## Summary

MacroPulse already has a sophisticated per-API-key daily rate limiter backed by PostgreSQL (`api_keys.usage_date / daily_requests`), an IP-lock mechanism (`api_keys.last_ip / ip_locked_at`), and OTP attempt tracking (`email_verifications.attempts`). However, all in-scope auth endpoints (`/register`, `/verify`, `/recover`, `/recover/verify`) are either explicitly listed in `_EXEMPT_PATHS` in `api/middleware/rate_limit.py` (the first three) or keyed on an API key that doesn't yet exist at registration time. They have no brute-force protection at the time-window level.

Phase 7 adds a purpose-built `auth_rate_limits` table (migration 009) and a helper module that encodes all per-endpoint limits. Each affected route handler calls `check_auth_rate_limit()` as its first statement — before any DB writes or email sends — and raises HTTP 429 with a `Retry-After` header on violation.

SEC-32 is already partially in place: `verify_email_code()` (queries.py:592) exhausts an OTP row after 5 wrong guesses. That remains as the last line of defense. Phase 7 adds the time-window rate-limit check on top, so callers receive a 429 with backoff instead of only a generic 400 after exhaustion.

**Primary recommendation:** Add `auth_rate_limits` table via migration `009_auth_rate_limits.sql`. Add `check_and_record_attempt()` to `database/queries.py` using the same atomic upsert pattern as the existing `check_and_set_ip_lock()`. Add `check_auth_rate_limit()` helper to `api/middleware/auth_rate_limit.py`. Wire into `register()`, `verify()`, `recover()`, and `recover_verify()` as the first call in each handler. Do not modify `RateLimitMiddleware` — auth endpoints must stay exempt from the daily key limiter.

---

## Existing Codebase — Critical Findings

### Auth Endpoints (api/routes/auth.py)

| Endpoint | Handler | Currently in `_EXEMPT_PATHS`? | Rate Limit Dimension | SEC |
|----------|---------|-------------------------------|---------------------|-----|
| `POST /v1/auth/register` | `register()` line 49 | YES | Per IP, 5/hour | SEC-30 |
| `POST /v1/auth/verify` | `verify()` line 92 | NO (subject to daily middleware; unauthenticated = in-memory counter) | Per email, 5/15 min | SEC-32 |
| `POST /v1/auth/recover` | `recover()` line 162 | YES | Per email, 5/15 min | SEC-31 |
| `POST /v1/auth/recover/verify` | `recover_verify()` line 192 | YES | Per email, 5/15 min | SEC-31, SEC-32 |

`/v1/auth/verify` is not in `_EXEMPT_PATHS` but the daily middleware exemption is irrelevant — unauthenticated requests use an in-memory IP counter that does not persist (violating SEC-33) and does not enforce email-based limits. Phase 7 must add it to `_EXEMPT_PATHS` AND protect it with `check_auth_rate_limit`.

### Partially-Implemented SEC-32 (already in production)

`database/queries.py` lines 589–629:
- Constant `_OTP_MAX_ATTEMPTS = 5`
- `verify_email_code()` increments `email_verifications.attempts` on wrong code
- When `attempts >= 5`, marks `used = TRUE`, blocking all further guesses on that row
- Migration `005_otp_attempts.sql` added the `attempts` column

This handles OTP-row exhaustion at the data layer. Phase 7 adds the complementary time-window rate limit at the route layer. The two mechanisms are independent and work together.

### Existing Upsert Pattern to Follow

`check_and_set_ip_lock()` in `database/queries.py` lines 441–490 demonstrates the exact pattern needed:
- Single `INSERT … ON CONFLICT … DO UPDATE … RETURNING` query — atomic, no TOCTOU
- `%(mins)s` cannot go inside an `INTERVAL` literal directly: uses `.replace("%(mins)s", str(value))` before `cur.execute()` (line 481) — the same workaround applies to window intervals in Phase 7

### Migration Numbering

Last migration: `008_schema_hardening.sql`. Next: **`009_auth_rate_limits.sql`**.

Migration files in `database/migrations/` are applied automatically at startup via `_run_migrations()` in `api/main.py` using `sorted(migrations_dir.glob("*.sql"))`.

### Handlers That Need `request: Request` Parameter

`register()` and `recover()` currently have no `Request` parameter. FastAPI injects it automatically when declared — adding `request: Request` to the signature is non-breaking.

`verify()` and `recover_verify()` receive email via request body (`VerifyRequest.email`) — no `Request` parameter needed for rate limiting (key is email, not IP).

---

## Standard Stack

### Core (all already in project — no new dependencies)
| Library | Purpose | Notes |
|---------|---------|-------|
| psycopg2 (existing) | DB access for `auth_rate_limits` queries | Sync `get_sync_cursor()` only — asyncpg migration is Phase 8 |
| FastAPI `HTTPException` | Return 429 with headers | Already used throughout `auth.py` |
| `datetime.timezone.utc` | Timezone-aware comparisons | Use `dt.datetime.now(dt.timezone.utc)`; naive `datetime.now()` causes comparison errors with `TIMESTAMPTZ` columns |

### No New Dependencies Required
All rate limiting is implemented with plain SQL and the existing psycopg2 connection pool. Redis, `slowapi`, `limits`, and similar libraries are not needed and would violate SEC-33 (DB persistence required).

---

## Architecture Patterns

### New Files

```
api/
└── middleware/
    ├── rate_limit.py           # existing — unchanged
    └── auth_rate_limit.py      # NEW — check_auth_rate_limit() helper

database/
└── migrations/
    └── 009_auth_rate_limits.sql    # NEW — auth_rate_limits table + index
```

### Modified Files
- `database/queries.py` — add `check_and_record_attempt()` function
- `api/routes/auth.py` — add rate-limit calls at top of 4 handlers; add `request: Request` to 2 handlers; add `/v1/auth/verify` to `_EXEMPT_PATHS`

### Pattern: DB-Persisted Sliding Window with Exponential Backoff

The `auth_rate_limits` table holds one row per `(identifier, endpoint)` pair:

```sql
-- 009_auth_rate_limits.sql
CREATE TABLE IF NOT EXISTS auth_rate_limits (
    id             BIGSERIAL    PRIMARY KEY,
    identifier     TEXT         NOT NULL,   -- IP address (register) or email (recover/verify)
    endpoint       TEXT         NOT NULL
                                CHECK (endpoint IN ('register', 'verify_otp', 'recover', 'recover_verify')),
    attempt_count  INT          NOT NULL DEFAULT 0,
    window_start   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    locked_until   TIMESTAMPTZ,             -- NULL = not locked; set for backoff
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (identifier, endpoint)
);

CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_identifier_endpoint
    ON auth_rate_limits (identifier, endpoint);
```

### Pattern: Atomic Upsert Query

Follows the `check_and_set_ip_lock()` approach exactly — one round-trip, no TOCTOU:

```sql
-- Window interval substituted via str.replace() before cur.execute()
-- to avoid %(var)s-inside-INTERVAL psycopg2 limitation
INSERT INTO auth_rate_limits (identifier, endpoint, attempt_count, window_start)
VALUES (%(identifier)s, %(endpoint)s, 1, now())
ON CONFLICT (identifier, endpoint) DO UPDATE
SET
    attempt_count = CASE
        WHEN auth_rate_limits.window_start < now() - 'WINDOW_INTERVAL'::interval
        THEN 1
        ELSE auth_rate_limits.attempt_count + 1
    END,
    window_start = CASE
        WHEN auth_rate_limits.window_start < now() - 'WINDOW_INTERVAL'::interval
        THEN now()
        ELSE auth_rate_limits.window_start
    END,
    locked_until = CASE
        WHEN auth_rate_limits.window_start < now() - 'WINDOW_INTERVAL'::interval
        THEN NULL
        WHEN auth_rate_limits.locked_until IS NOT NULL
          AND auth_rate_limits.locked_until > now()
        THEN auth_rate_limits.locked_until
        ELSE NULL
    END,
    updated_at = now()
RETURNING attempt_count, window_start, locked_until;
```

Backoff (`locked_until`) is set by Python after inspecting the returned `attempt_count` — keeps the SQL readable and backoff logic testable in isolation.

### Exponential Backoff Schedule (SEC-31)

| attempt_count after increment | Backoff applied |
|-------------------------------|-----------------|
| 1–2 | None — allowed |
| 3 | 30 seconds `locked_until` |
| 4 | 60 seconds |
| 5+ (hard limit) | 300 seconds (5 min); 429 returned |

```python
_BACKOFF_SCHEDULE = {3: 30, 4: 60, 5: 300}  # seconds

def _backoff_seconds(attempt_count: int) -> int:
    return _BACKOFF_SCHEDULE.get(attempt_count, 300 if attempt_count > 5 else 0)
```

Backoff applies only to `recover` and `recover_verify`. For `register`, SEC-30 specifies a simple hard limit with no backoff.

### Integration Points in auth.py

```python
# register() — add request: Request; check first
def register(body: RegisterRequest, request: Request) -> dict:
    client_ip = _get_client_ip(request)
    check_auth_rate_limit(identifier=client_ip, endpoint="register",
                          max_attempts=5, window_minutes=60)
    # ... existing logic unchanged

# verify() — no request needed; check first
def verify(body: VerifyRequest) -> RegisterResponse:
    email = body.email.strip().lower()
    check_auth_rate_limit(identifier=email, endpoint="verify_otp",
                          max_attempts=5, window_minutes=15)
    # ... existing logic unchanged

# recover() — add request: Request; check first (BEFORE get_user_by_email — anti-enumeration)
def recover(body: RegisterRequest, request: Request) -> dict:
    email = str(body.email).strip().lower()
    check_auth_rate_limit(identifier=email, endpoint="recover",
                          max_attempts=5, window_minutes=15)
    # ... existing logic unchanged

# recover_verify() — check first
def recover_verify(body: VerifyRequest) -> RotateKeyResponse:
    email = body.email.strip().lower()
    check_auth_rate_limit(identifier=email, endpoint="recover_verify",
                          max_attempts=5, window_minutes=15)
    # ... existing logic unchanged
```

`check_auth_rate_limit()` raises `HTTPException(429)` directly — no return value to check.

### IP Extraction Utility

Extract the trusted-proxy logic from `rate_limit.py` lines 131–139 into a shared function. The logic is:

```python
# api/middleware/auth_rate_limit.py or api/utils.py
from starlette.requests import Request

def get_client_ip(request: Request) -> str:
    """Extract real client IP. Trusts X-Forwarded-For only from Docker bridge (172.18.x.x)."""
    direct_host = request.client.host if request.client else ""
    if direct_host.startswith("172.18."):
        forwarded = request.headers.get("X-Forwarded-For", "")
        first_ip = forwarded.split(",")[0].strip()
        return first_ip if first_ip else direct_host
    return direct_host or "unknown"
```

### Anti-Patterns to Avoid

- **Rate limit check AFTER `create_email_verification()` or email send:** An attacker who triggered the email before the 429 fires has achieved their goal. The check must be the first line.
- **Keying `/register` on the request body email:** SEC-30 is per IP, not per email. Attackers use random email addresses to rotate keys.
- **In-memory fallback counters:** On DB error, fail OPEN (log and return without raising). Never use in-memory dicts as fallback — that violates SEC-33.
- **Removing auth endpoints from `_EXEMPT_PATHS`:** Auth paths must stay exempt from the daily API-key limiter. The daily limiter is for data endpoints; auth gets its own limits.
- **Using `dt.datetime.now()` (naive):** Comparison with `TIMESTAMPTZ` (`locked_until`) raises `TypeError`. Always use `dt.datetime.now(dt.timezone.utc)`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic increment + window reset | Python read-check-write (three queries) | Single `INSERT … ON CONFLICT … DO UPDATE … RETURNING` | Eliminates TOCTOU; one DB round-trip; exact same pattern as `check_and_set_ip_lock()` |
| `Retry-After` value | Custom timer math | `locked_until` column returned from DB | Precise; no clock drift between app and DB |
| OTP invalidation after 5 guesses | New logic | Existing `verify_email_code()` handles this | Already in `database/queries.py:592`; do not duplicate |
| IP from request | Custom header parsing | Extract `get_client_ip()` from existing `rate_limit.py:131–139` | Already handles Docker bridge trusted-proxy correctly |

---

## Common Pitfalls

### Pitfall 1: Rate Limit Check Placed After Side Effects
**What goes wrong:** `create_email_verification()` or `send_verification_email()` runs before the rate limit check fires — attacker gets the email even on a limited request.
**How to avoid:** Rate limit check is the FIRST statement in every affected handler. No exceptions.
**Warning sign:** Test confirms email service was called even when 429 was expected.

### Pitfall 2: Using Email as Key for `/register`
**What goes wrong:** Attacker sends different email addresses per request, bypassing a per-email limit.
**How to avoid:** `/register` uses IP address as the key (SEC-30 explicitly states "per IP per hour").
**Warning sign:** Test with 6 different email addresses from same IP does not trigger 429.

### Pitfall 3: `%(var)s` Inside INTERVAL Literal
**What goes wrong:** `INTERVAL '%(window)s minutes'` — psycopg2 substitutes `%(window)s` as a SQL parameter only in value positions, not inside string literals. Query fails.
**How to avoid:** Use `sql.replace("WINDOW_INTERVAL", f"{window_minutes} minutes")` before `cur.execute()`. This is the same workaround documented in `queries.py:481`.
**Warning sign:** `psycopg2.errors.SyntaxError` or the interval is treated as a literal string `%(window)s`.

### Pitfall 4: `register()` and `recover()` Missing `request: Request`
**What goes wrong:** `NameError` or `TypeError` when trying to access client IP.
**How to avoid:** Add `request: Request` to both function signatures. FastAPI injects automatically.
**Warning sign:** Function works in tests that mock the DB but fails when hit via HTTP client.

### Pitfall 5: Naive vs Timezone-Aware Datetime Comparison
**What goes wrong:** `locked_until - dt.datetime.now()` raises `TypeError: can't subtract offset-naive and offset-aware datetimes` when `locked_until` is a `TIMESTAMPTZ`-derived value.
**How to avoid:** Always use `dt.datetime.now(dt.timezone.utc)` in `auth_rate_limit.py`.
**Warning sign:** Test passes with mocked datetime but fails in integration against real DB.

### Pitfall 6: `/v1/auth/verify` Left Unprotected
**What goes wrong:** Both registration OTP (`/verify`) and recovery OTP (`/recover/verify`) calls land on `verify_email_code()`. Only covering `/recover/verify` leaves an equivalent attack surface open.
**How to avoid:** Apply `check_auth_rate_limit(endpoint="verify_otp")` to both `verify()` and `recover_verify()`. Add `/v1/auth/verify` to `_EXEMPT_PATHS` so the daily middleware does not interfere.

---

## Code Examples

### Migration 009

```sql
-- database/migrations/009_auth_rate_limits.sql
-- DB-persisted auth endpoint rate limiting. SEC-30, SEC-31, SEC-32, SEC-33.
-- Safe to re-run (all DDL uses IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS auth_rate_limits (
    id             BIGSERIAL    PRIMARY KEY,
    identifier     TEXT         NOT NULL,
    endpoint       TEXT         NOT NULL
                                CHECK (endpoint IN ('register', 'verify_otp', 'recover', 'recover_verify')),
    attempt_count  INT          NOT NULL DEFAULT 0,
    window_start   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    locked_until   TIMESTAMPTZ,
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (identifier, endpoint)
);

CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_identifier_endpoint
    ON auth_rate_limits (identifier, endpoint);
```

### check_and_record_attempt() in database/queries.py

```python
# Source: codebase pattern — mirrors check_and_set_ip_lock() (queries.py:441)
def check_and_record_attempt(
    identifier: str,
    endpoint: str,
    max_attempts: int,
    window_minutes: int,
) -> dict:
    """
    Atomically record an auth attempt and return current state.

    Returns: {"attempt_count": int, "locked_until": datetime|None, "allowed": bool}
    On DB error: raises — caller is responsible for fail-open handling.
    """
    window_interval = f"{window_minutes} minutes"
    sql = """
        INSERT INTO auth_rate_limits (identifier, endpoint, attempt_count, window_start)
        VALUES (%(identifier)s, %(endpoint)s, 1, now())
        ON CONFLICT (identifier, endpoint) DO UPDATE
        SET
            attempt_count = CASE
                WHEN auth_rate_limits.window_start < now() - 'WINDOW_INTERVAL'::interval
                THEN 1
                ELSE auth_rate_limits.attempt_count + 1
            END,
            window_start = CASE
                WHEN auth_rate_limits.window_start < now() - 'WINDOW_INTERVAL'::interval
                THEN now()
                ELSE auth_rate_limits.window_start
            END,
            locked_until = CASE
                WHEN auth_rate_limits.window_start < now() - 'WINDOW_INTERVAL'::interval
                THEN NULL
                WHEN auth_rate_limits.locked_until IS NOT NULL
                  AND auth_rate_limits.locked_until > now()
                THEN auth_rate_limits.locked_until
                ELSE NULL
            END,
            updated_at = now()
        RETURNING attempt_count, locked_until;
    """.replace("WINDOW_INTERVAL", window_interval)

    with get_sync_cursor() as cur:
        cur.execute(sql, {"identifier": identifier, "endpoint": endpoint})
        row = cur.fetchone()

    if not row:
        return {"attempt_count": 1, "locked_until": None, "allowed": True}

    attempt_count = int(row["attempt_count"])
    locked_until = row["locked_until"]
    now_utc = dt.datetime.now(dt.timezone.utc)

    if locked_until and locked_until > now_utc:
        return {"attempt_count": attempt_count, "locked_until": locked_until, "allowed": False}

    if attempt_count > max_attempts:
        return {"attempt_count": attempt_count, "locked_until": locked_until, "allowed": False}

    return {"attempt_count": attempt_count, "locked_until": locked_until, "allowed": True}
```

### check_auth_rate_limit() in api/middleware/auth_rate_limit.py

```python
# Source: codebase pattern — follows api/middleware/rate_limit.py error-handling style
import datetime as dt
import logging
from fastapi import HTTPException, status
from starlette.requests import Request
from database import queries

logger = logging.getLogger(__name__)

_BACKOFF_SCHEDULE = {3: 30, 4: 60, 5: 300}  # attempt_count → lockout seconds

def _set_backoff_if_needed(identifier: str, endpoint: str, attempt_count: int) -> None:
    """Write locked_until for backoff-eligible endpoints (recover, recover_verify)."""
    backoff = _BACKOFF_SCHEDULE.get(attempt_count, 0)
    if backoff == 0:
        return
    try:
        from database.connection import get_sync_cursor
        with get_sync_cursor() as cur:
            cur.execute(
                "UPDATE auth_rate_limits SET locked_until = now() + %s::interval "
                "WHERE identifier = %s AND endpoint = %s;",
                (f"{backoff} seconds", identifier, endpoint),
            )
    except Exception as exc:
        logger.error("Failed to set backoff for %s/%s: %s", endpoint, identifier[:8], exc)


def check_auth_rate_limit(
    identifier: str,
    endpoint: str,
    max_attempts: int,
    window_minutes: int,
    with_backoff: bool = False,
) -> None:
    """
    Raise HTTP 429 if the identifier has exceeded the limit.
    Fails open on DB error (logs, returns without raising).

    identifier   — IP (for register) or email (for OTP endpoints)
    endpoint     — 'register' | 'verify_otp' | 'recover' | 'recover_verify'
    with_backoff — set True for recover/recover_verify (SEC-31)
    """
    try:
        result = queries.check_and_record_attempt(
            identifier=identifier,
            endpoint=endpoint,
            max_attempts=max_attempts,
            window_minutes=window_minutes,
        )
    except Exception as exc:
        logger.error("auth_rate_limit DB error %s/%s: %s", endpoint, identifier[:8], exc)
        return  # fail open

    attempt_count = result["attempt_count"]

    if with_backoff and result["allowed"] and attempt_count >= 3:
        _set_backoff_if_needed(identifier, endpoint, attempt_count)

    if not result["allowed"]:
        locked_until = result.get("locked_until")
        retry_after = 60  # safe default
        if locked_until:
            now_utc = dt.datetime.now(dt.timezone.utc)
            retry_after = max(1, int((locked_until - now_utc).total_seconds()))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "detail": "Too many attempts. Please wait before trying again.",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )


def get_client_ip(request: Request) -> str:
    """Extract real client IP — trusts X-Forwarded-For only from Docker bridge (172.18.x.x)."""
    direct_host = request.client.host if request.client else ""
    if direct_host.startswith("172.18."):
        forwarded = request.headers.get("X-Forwarded-For", "")
        first_ip = forwarded.split(",")[0].strip()
        return first_ip if first_ip else direct_host
    return direct_host or "unknown"
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| No rate limiting on auth endpoints | DB-persisted per-IP and per-email limits | Closes brute-force surface; SEC-33 compliant |
| Generic 400 after OTP exhaustion | 429 with Retry-After + backoff schedule | Clients can implement intelligent retry; abuse is throttled before OTP exhaustion |
| IP lock only for API key sharing (authenticated) | IP-based rate limit for unauthenticated registration | Prevents registration spam / email API abuse |

**Existing infrastructure NOT changed:**
- `verify_email_code()` attempt counter (migration 005) — remains as last-resort OTP exhaustion
- `_EXEMPT_PATHS` exempt `/register`, `/recover`, `/recover/verify` — keep those; add `/verify`
- `RateLimitMiddleware` — not modified
- `check_and_set_ip_lock()` — not modified

---

## Open Questions

1. **Should the `locked_until` update be in the same atomic upsert or a separate UPDATE?**
   - What we know: putting backoff logic in the upsert SQL makes the CASE expression deeply nested and hard to test. The current proposal uses a separate UPDATE after returning from the upsert.
   - Recommendation: Separate UPDATE for backoff — cleaner SQL, easier unit testing. Race window between upsert and backoff UPDATE is acceptable (the attempt_count check is the hard guard; backoff is a soft UX measure).

2. **Should `get_client_ip` be duplicated in `auth_rate_limit.py` or extracted to a shared `api/utils.py`?**
   - What we know: The same 8 lines exist in `rate_limit.py`. Duplication is bad but a new `utils.py` adds a file.
   - Recommendation: Add to `api/middleware/auth_rate_limit.py` in Phase 7. If Phase 8 needs it too, extract then.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pytest.ini` at project root |
| Quick run command | `pytest tests/test_auth_rate_limit.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-30 | 6th registration attempt from same IP within 1h returns 429 | unit (mock DB) | `pytest tests/test_auth_rate_limit.py::test_register_blocks_on_6th_attempt -x` | Wave 0 |
| SEC-30 | Counter resets after window expires | unit (mock DB) | `pytest tests/test_auth_rate_limit.py::test_register_window_reset -x` | Wave 0 |
| SEC-30 | 429 response contains Retry-After header | unit (mock DB) | `pytest tests/test_auth_rate_limit.py::test_register_retry_after_header -x` | Wave 0 |
| SEC-31 | 6th recover attempt for same email returns 429 | unit (mock DB) | `pytest tests/test_auth_rate_limit.py::test_recover_blocks_on_6th_attempt -x` | Wave 0 |
| SEC-31 | Backoff fires at attempt 3 (locked_until set) | unit (mock DB) | `pytest tests/test_auth_rate_limit.py::test_recover_backoff_at_attempt_3 -x` | Wave 0 |
| SEC-32 | verify_otp rate limit blocks after 5 attempts | unit (mock DB) | `pytest tests/test_auth_rate_limit.py::test_verify_otp_blocks_after_5 -x` | Wave 0 |
| SEC-32 | After rate limit, correct OTP still rejected (OTP exhausted by verify_email_code) | unit (mock DB) | `pytest tests/test_auth_rate_limit.py::test_otp_row_exhausted_after_5_wrong -x` | Wave 0 |
| SEC-33 | `check_and_record_attempt` issues DB call — no in-memory fallback | unit (assert queries.check_and_record_attempt called, no dict mutation) | `pytest tests/test_auth_rate_limit.py::test_state_is_db_not_memory -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_auth_rate_limit.py -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_auth_rate_limit.py` — covers SEC-30 through SEC-33 (stub as xfail in Wave 0)
- [ ] `tests/conftest.py` — extend with a `mock_auth_rl_cursor` fixture for `check_and_record_attempt`; no new framework install needed

---

## Sources

### Primary (HIGH confidence)
- `api/routes/auth.py` — complete handler signatures, parameter lists, OTP flow
- `api/middleware/rate_limit.py` — `_EXEMPT_PATHS` list, IP extraction logic lines 130–139, fail-open pattern line 159
- `database/queries.py` — `check_and_set_ip_lock()` upsert pattern, `verify_email_code()` attempt logic, `_OTP_MAX_ATTEMPTS`
- `database/migrations/001–008` — confirmed migration numbering; no existing `auth_rate_limits` table
- `database/connection.py` — `get_sync_cursor()` pattern, psycopg2 sync pool
- `config/settings.py` — no auth rate limit settings present
- `tests/test_security.py` + `tests/conftest.py` — test patterns; all tests use `unittest.mock.patch`
- `.planning/REQUIREMENTS.md` — SEC-30 through SEC-33 verbatim

---

## Metadata

**Confidence breakdown:**
- Existing code structure: HIGH — full codebase read
- DB migration design: HIGH — follows migrations 003–005 exactly
- SQL atomic upsert: HIGH — mirrors `check_and_set_ip_lock()` already in production
- psycopg2 INTERVAL workaround: HIGH — documented in existing code at line 481
- Test approach: HIGH — mirrors `test_security.py` pattern

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable; invalidated if Phase 8 asyncpg migration changes `get_sync_cursor` interface)
