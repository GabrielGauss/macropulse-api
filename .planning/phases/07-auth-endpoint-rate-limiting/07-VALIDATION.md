# Phase 7 Validation: Auth Endpoint Rate Limiting

**Phase:** 07-auth-endpoint-rate-limiting
**Requirements covered:** SEC-30, SEC-31, SEC-32, SEC-33
**Run after:** 07-01-PLAN.md completes

---

## Pre-flight

Before running any checks, verify the API container is running with the latest code and migration 009 has been applied:

```bash
# Confirm migration ran
docker exec macropulse-api python -c "
from database.connection import get_sync_cursor
with get_sync_cursor() as cur:
    cur.execute(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'auth_rate_limits'\")
    print('table exists:', cur.fetchone()[0] == 1)
"
```

---

## Automated Checks

Run after each plan completes. All must exit 0.

```bash
# After 07-00: stubs present
pytest tests/test_auth_rate_limit.py -q
# Expected: 8 xfailed, exit 0

# After 07-01: real tests pass
pytest tests/test_auth_rate_limit.py -v
# Expected: 8 passed, exit 0

# Full suite unbroken
pytest tests/ -q
# Expected: exit 0
```

---

## SEC-30: Registration Rate Limit (per IP, max 5 per hour)

### Check 1 — Rate limit check is first in register()
```bash
grep -n "check_auth_rate_limit\|get_user_by_email\|create_email_verification" api/routes/auth.py | head -10
```
Expected: check_auth_rate_limit line number < get_user_by_email line number in the register() block.

### Check 2 — Identifier is IP, not email
```bash
grep -A3 "def register" api/routes/auth.py | grep "check_auth_rate_limit"
```
Expected output contains `get_client_ip(request)` as the identifier argument, not `email`.

### Check 3 — register() accepts Request parameter
```bash
grep "def register" api/routes/auth.py
```
Expected: `def register(body: RegisterRequest, request: Request) -> dict:`

### Check 4 — Endpoint and limit values
```bash
grep "check_auth_rate_limit" api/routes/auth.py
```
Expected lines:
- register handler: `endpoint="register"`, `max_attempts=5`, `window_minutes=60`
- verify handler: `endpoint="verify_otp"`, `max_attempts=5`, `window_minutes=15`
- recover handler: `endpoint="recover"`, `max_attempts=5`, `window_minutes=15`, `with_backoff=True`
- recover_verify handler: `endpoint="recover_verify"`, `max_attempts=5`, `window_minutes=15`, `with_backoff=True`

---

## SEC-31: Recovery Rate Limit (per email, max 5 per 15 min, backoff after attempt 3)

### Check 5 — recover() rate limit precedes anti-enumeration check
```bash
grep -n "check_auth_rate_limit\|get_user_by_email" api/routes/auth.py
```
Expected: In the recover() function block, check_auth_rate_limit line number < get_user_by_email line number. This ensures the attacker cannot learn if an email exists before hitting the rate limit.

### Check 6 — with_backoff=True on recover endpoints
```bash
grep "with_backoff" api/routes/auth.py
```
Expected: 2 lines, both on recover/recover_verify handlers.

### Check 7 — Backoff schedule defined in middleware
```bash
grep "_BACKOFF_SCHEDULE" api/middleware/auth_rate_limit.py
```
Expected: `_BACKOFF_SCHEDULE = {3: 30, 4: 60, 5: 300}`

---

## SEC-32: OTP Verification Lockout (5 attempts per 15 min)

### Check 8 — verify_otp endpoint rate-limited
```bash
grep "verify_otp" api/routes/auth.py api/middleware/auth_rate_limit.py
```
Expected: Present in both files.

### Check 9 — verify() rate limit precedes verify_email_code()
```bash
grep -n "check_auth_rate_limit\|verify_email_code" api/routes/auth.py
```
Expected: In the verify() function block, check_auth_rate_limit line number < verify_email_code line number.

### Check 10 — verify_email_code() OTP exhaustion still works independently
```bash
grep "_OTP_MAX_ATTEMPTS\|attempts.*5\|mark.*used" database/queries.py | head -5
```
Expected: _OTP_MAX_ATTEMPTS = 5 still present (not removed — it's the last-resort OTP exhaustion guard).

---

## SEC-33: DB-Persisted State

### Check 11 — No in-memory dict in auth_rate_limit.py
```bash
grep -n "= {}" api/middleware/auth_rate_limit.py
grep -n "in_memory\|_counter\|_attempts" api/middleware/auth_rate_limit.py
```
Expected: No matches. State lives exclusively in auth_rate_limits DB table.

### Check 12 — check_and_record_attempt issues DB call
```bash
grep "INSERT INTO auth_rate_limits" database/queries.py
```
Expected: 1 match inside check_and_record_attempt().

### Check 13 — WINDOW_INTERVAL workaround present (not %(var)s inside INTERVAL)
```bash
grep "WINDOW_INTERVAL\|window_interval" database/queries.py
```
Expected: str.replace("WINDOW_INTERVAL", ...) pattern present — NO `INTERVAL '%(window_minutes)s minutes'` pattern.

### Check 14 — Timezone-aware datetime comparison
```bash
grep "datetime.now" api/middleware/auth_rate_limit.py database/queries.py
```
Expected: All occurrences use `dt.datetime.now(dt.timezone.utc)` — no bare `dt.datetime.now()`.

---

## Middleware Isolation

### Check 15 — /v1/auth/verify added to _EXEMPT_PATHS
```bash
grep "auth/verify" api/middleware/rate_limit.py
```
Expected: `"/v1/auth/verify"` present in _EXEMPT_PATHS set.

### Check 16 — Existing exempt paths not removed
```bash
grep "_EXEMPT_PATHS" api/middleware/rate_limit.py -A10
```
Expected: /v1/auth/register, /v1/auth/recover, /v1/auth/recover/verify all still present alongside the new /v1/auth/verify entry.

### Check 17 — RateLimitMiddleware not modified
The daily API-key rate limiter must be unchanged. Auth endpoints must stay exempt from it.
```bash
git diff api/middleware/rate_limit.py | grep "^+" | grep -v "_EXEMPT_PATHS\|auth/verify"
```
Expected: No other additions to rate_limit.py beyond the exempt path entry.

---

## Fail-Open Behavior

### Check 18 — DB error does not block requests
```bash
grep "except Exception" api/middleware/auth_rate_limit.py
grep "fail open\|fail_open\|return.*#" api/middleware/auth_rate_limit.py
```
Expected: except Exception handler in check_auth_rate_limit logs and returns (does not re-raise).

---

## REQUIREMENTS.md

### Check 19 — All four requirements marked complete
```bash
grep "SEC-3[0-3]" .planning/REQUIREMENTS.md
```
Expected: All four lines show `- [x]` and traceability table shows "Complete".

---

## Phase Gate

All 19 checks must pass before closing Phase 7. Run full test suite as final gate:

```bash
pytest tests/ -q --tb=short
```

Expected output: all tests pass, exit 0.

Phase 7 is complete when:
- [ ] Check 1–4: SEC-30 registration rate limit wired correctly
- [ ] Check 5–7: SEC-31 recovery rate limit with backoff wired correctly
- [ ] Check 8–10: SEC-32 OTP verification rate limit wired; existing OTP exhaustion intact
- [ ] Check 11–14: SEC-33 all state in DB; no in-memory fallback; INTERVAL workaround present; timezone-aware
- [ ] Check 15–17: /v1/auth/verify in _EXEMPT_PATHS; existing exemptions preserved; RateLimitMiddleware otherwise untouched
- [ ] Check 18: fail-open on DB error confirmed
- [ ] Check 19: REQUIREMENTS.md updated
- [ ] Full pytest suite: exit 0
