# Phase 11: GDPR User Deletion Endpoint - Research

**Researched:** 2026-04-01
**Domain:** GDPR right-to-erasure, FastAPI REST endpoint, asyncpg PostgreSQL
**Confidence:** HIGH

---

## Summary

Phase 11 adds a single authenticated endpoint (`DELETE /v1/auth/me`) that lets a
registered user irrevocably anonymise their own account. The operation is fully
in-place: the `users` row is not deleted, it is overwritten with
`deleted_<uuid>@deleted.invalid` in place of the real email, and all PII
columns are nullified. API keys are cascade-deactivated (not deleted) so that
audit-trail rows that reference `user_id` or `key_prefix` in `api_key_audit_log`
and `webhook_deliveries` remain intact but can no longer be used to authenticate.
Idempotency, rate-limit, and webhook-deduplication tables that do NOT carry PII
are left entirely untouched.

No new Python packages are required. The implementation follows patterns already
present in the codebase: asyncpg `conn.transaction()` blocks, the
`require_api_key` FastAPI dependency for authentication, and the
`database/queries.py` pattern of thin async functions over parameterised SQL.

**Primary recommendation:** Implement as a single atomic DB transaction that (1)
updates `users` to anonymise PII, (2) sets `api_keys.is_active = FALSE` and
`revoked_at = now()` for all keys of that user, then returns HTTP 204. Write
a new migration `011_gdpr_deletion.sql` that adds any needed index and a
`deleted_at` column for operational clarity.

---

<phase_requirements>
## Phase Requirements

| ID       | Description                                                                                                   | Research Support                                                                                      |
|----------|---------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| GDPR-01  | `DELETE /v1/auth/me` — authenticated user can request their own deletion                                      | `require_api_key` dep already provides `user_id`; add DELETE handler to `api/routes/auth.py`         |
| GDPR-02  | Anonymise email as `deleted_<uuid>@deleted.invalid`, wipe `name` and all profile PII fields                  | Full PII column inventory documented below; one UPDATE statement inside a transaction                 |
| GDPR-03  | Cascade deactivate all API keys for the user                                                                  | `revoke_api_keys_for_user()` already exists in `queries.py`; call it inside the same transaction     |
| GDPR-04  | Retain idempotency records; nullify PII references but do not delete rows that other audit trails depend on   | `webhook_deliveries` and `api_key_audit_log` carry `user_id BIGINT` with no FK — nullify, don't delete |
</phase_requirements>

---

## Full Schema Inventory

### `users` table — all columns

Assembled from `database/schema.sql` plus migrations 001–010:

| Column                        | Migration    | PII?          | Anonymisation action                              |
|-------------------------------|--------------|---------------|---------------------------------------------------|
| `id`                          | schema.sql   | No (PK)       | Retain — FK anchor for all child rows             |
| `email`                       | schema.sql   | **YES**       | Replace with `deleted_<uuid4>@deleted.invalid`    |
| `name`                        | schema.sql   | **YES**       | Set `NULL`                                        |
| `created_at`                  | schema.sql   | Low risk      | Retain — operational / aggregate only             |
| `paddle_customer_id`          | 002          | **YES**       | Set `NULL`                                        |
| `paddle_subscription_id`      | 002          | **YES**       | Set `NULL`                                        |
| `webhook_url`                 | 003          | **YES**       | Set `NULL`                                        |
| `alerts_enabled`              | 003          | No            | Set `FALSE` (disables future delivery attempts)   |
| `ls_customer_id`              | 006          | **YES**       | Set `NULL`                                        |
| `ls_subscription_id`          | 006          | **YES**       | Set `NULL`                                        |
| `ls_variant_id`               | 006          | Low risk      | Set `NULL` (safe to wipe, no downstream join)     |
| `ls_status`                   | 006          | No            | Set `NULL` (operational, but clean on deletion)   |
| `ls_portal_url`               | 006          | **YES**       | Set `NULL` (URL contains customer-specific token) |
| `paddle_subscription_status`  | 010          | No            | Set `NULL` (clean on deletion)                    |

**Columns to write in a single UPDATE:**

```sql
UPDATE users
SET
    email                      = $1,   -- 'deleted_<uuid4>@deleted.invalid'
    name                       = NULL,
    paddle_customer_id         = NULL,
    paddle_subscription_id     = NULL,
    paddle_subscription_status = NULL,
    webhook_url                = NULL,
    alerts_enabled             = FALSE,
    ls_customer_id             = NULL,
    ls_subscription_id         = NULL,
    ls_variant_id              = NULL,
    ls_status                  = NULL,
    ls_portal_url              = NULL,
    deleted_at                 = now()   -- added by migration 011
WHERE id = $2;
```

### `api_keys` table — relationship and PII

`api_keys.user_id` is a `BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE`.
The `ON DELETE CASCADE` means if we ever hard-delete a user row, all keys vanish.
We are NOT hard-deleting, so we must explicitly deactivate the keys.

PII in `api_keys`:

| Column        | PII?    | Action                              |
|---------------|---------|-------------------------------------|
| `key_hash`    | **YES** (allows auth if not revoked) | Implicitly neutralised by `is_active = FALSE` |
| `last_ip`     | **YES** | Set `NULL`                          |
| `key_prefix`  | Low     | Retain (display token, not a secret)|
| `is_active`   | No      | Set `FALSE`                         |
| `revoked_at`  | No      | Set `now()`                         |

Extend `revoke_api_keys_for_user()` or call the existing function then do a
second pass to nullify `last_ip` and `ip_locked_at`:

```sql
UPDATE api_keys
SET is_active   = FALSE,
    revoked_at  = now(),
    last_ip     = NULL,
    ip_locked_at = NULL
WHERE user_id = $1;
```

(Applies to ALL rows for the user, not just `is_active = TRUE`, to wipe
historical IP data too.)

### Audit and idempotency tables that reference `user_id`

| Table                   | `user_id` column type | FK?  | PII in row?       | Action                      |
|-------------------------|-----------------------|------|-------------------|-----------------------------|
| `webhook_deliveries`    | `BIGINT`              | None | `payload JSONB`   | Set `user_id = NULL`, `payload = NULL` |
| `api_key_audit_log`     | `BIGINT`              | None | `ip_addr`, `user_agent` | Set `user_id = NULL`, `ip_addr = NULL`, `user_agent = NULL` |

Both tables have no FK constraint on `user_id` (confirmed in migration 008), so
nullification is safe and preserves the row count / aggregate integrity without
exposing PII.

### Tables that do NOT reference `user_id` — leave untouched

| Table                   | Rationale                                         |
|-------------------------|---------------------------------------------------|
| `webhook_idempotency`   | No user reference; keyed on `event_id` only       |
| `auth_rate_limits`      | Keyed on IP or email string — expires naturally   |
| `email_verifications`   | Keyed on email string; short-lived, not linked to user row |
| All `macro_*` tables    | Pipeline / time-series data, no user reference    |
| `newsletter_subscribers`| Separate table, not linked to `users.id`         |

---

## Authentication Pattern (How the Endpoint Identifies the Caller)

The `require_api_key` dependency in `api/auth.py` validates the
`X-MacroPulse-Key` header, hashes it, looks up `api_keys` joined to `users`,
and returns a `dict` that includes `user_id`, `email`, `tier`, and `key_prefix`.

All existing authenticated routes use the pattern:

```python
@router.delete("/me", status_code=204)
async def delete_me(
    key_record: dict = Depends(require_api_key),
) -> None:
    user_id: int = key_record["user_id"]
    ...
```

No JWT, no session cookie — purely API-key auth. The key record provides
`user_id` directly. No additional lookup is needed before executing the
anonymisation.

**Edge case — owner key and legacy env keys:** `require_api_key` returns
`user_id = 0` for the owner and legacy env-key paths. The deletion handler MUST
reject `user_id == 0` with HTTP 403 before touching the database, since
`user_id = 0` does not correspond to a real `users` row.

---

## Architecture Patterns

### Recommended project structure — files to create/modify

```
api/routes/auth.py                  # Add DELETE /v1/auth/me handler (GDPR-01)
database/queries.py                 # Add anonymise_user() query function
database/migrations/011_gdpr_deletion.sql  # Add deleted_at column + index
tests/test_gdpr_deletion.py         # New test file (4 tests, no live DB)
```

No new modules, no new packages.

### Pattern: Atomic transaction wrapping multi-table writes

Existing precedent in `queries.create_email_verification()`:

```python
async with get_db_conn() as conn:
    async with conn.transaction():
        await conn.execute("DELETE FROM email_verifications WHERE email = $1;", email)
        await conn.execute("INSERT INTO email_verifications ...", email, code)
```

The deletion operation MUST use the same `conn.transaction()` pattern so that
the user anonymisation, key deactivation, and audit/webhook nullification are
atomic. A partial failure (e.g., keys deactivated but `users` row not wiped)
would leave the account in an inconsistent state.

### Pattern: Thin query function in `database/queries.py`

All DB access goes through `database/queries.py`. The route handler calls a
single `await queries.anonymise_user(user_id)` function that owns the entire
transaction. The route handler should not build SQL directly.

```python
# database/queries.py
async def anonymise_user(user_id: int) -> bool:
    """
    GDPR right-to-erasure: anonymise user row, deactivate all keys,
    nullify PII in audit tables. All operations run in one transaction.

    Returns True if a user row was found and updated, False if not found.
    """
    anon_email = f"deleted_{uuid.uuid4()}@deleted.invalid"
    async with get_db_conn() as conn:
        async with conn.transaction():
            result = await conn.execute(
                """
                UPDATE users
                SET email = $1, name = NULL,
                    paddle_customer_id = NULL, paddle_subscription_id = NULL,
                    paddle_subscription_status = NULL,
                    webhook_url = NULL, alerts_enabled = FALSE,
                    ls_customer_id = NULL, ls_subscription_id = NULL,
                    ls_variant_id = NULL, ls_status = NULL, ls_portal_url = NULL,
                    deleted_at = now()
                WHERE id = $2
                """,
                anon_email, user_id,
            )
            if result == "UPDATE 0":
                return False
            await conn.execute(
                """
                UPDATE api_keys
                SET is_active = FALSE, revoked_at = now(),
                    last_ip = NULL, ip_locked_at = NULL
                WHERE user_id = $1
                """,
                user_id,
            )
            await conn.execute(
                """
                UPDATE webhook_deliveries
                SET user_id = NULL, payload = NULL
                WHERE user_id = $1
                """,
                user_id,
            )
            await conn.execute(
                """
                UPDATE api_key_audit_log
                SET user_id = NULL, ip_addr = NULL, user_agent = NULL
                WHERE user_id = $1
                """,
                user_id,
            )
    return True
```

### Route handler pattern (matches existing `rotate_key` style)

```python
@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete your account (GDPR right to erasure)",
)
async def delete_me(
    key_record: dict = Depends(require_api_key),
) -> None:
    user_id: int = key_record["user_id"]

    # Reject synthetic records (owner key, legacy env key)
    if user_id == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This key type does not support account deletion.",
        )

    try:
        found = await queries.anonymise_user(user_id)
    except Exception as exc:
        logger.error("GDPR deletion failed for user_id=%d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not process deletion. Please try again.",
        )

    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    logger.info("GDPR account deletion completed: user_id=%d", user_id)
    # HTTP 204 — no response body
```

### Migration 011

```sql
-- database/migrations/011_gdpr_deletion.sql
-- Adds deleted_at column to users for operational monitoring.
-- Safe to re-run (IF NOT EXISTS).

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_users_deleted_at
    ON users (deleted_at) WHERE deleted_at IS NOT NULL;
```

`deleted_at` is intentionally not part of the anonymisation email column.
Its purpose is operational: allows a cron job or admin query to find accounts
that have been anonymised without scanning email values.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Transaction management | Custom rollback logic | `asyncpg conn.transaction()` | Already in codebase, battle-tested |
| Auth identity resolution | Parse headers manually | `Depends(require_api_key)` | Pattern used by all protected routes |
| UUID generation | Custom random string | `import uuid; uuid.uuid4()` | stdlib, guaranteed uniqueness |
| DB connection pooling | Direct `asyncpg.connect()` | `database.connection.get_db_conn` | Reuses the existing pool |

---

## Common Pitfalls

### Pitfall 1: Partial anonymisation due to missing `conn.transaction()`
**What goes wrong:** Each `await conn.execute(...)` runs as its own autocommit
statement. A transient network error after the `users` UPDATE but before the
`api_keys` UPDATE leaves the account in a half-anonymised state where the email
is wiped but keys are still active.
**How to avoid:** Wrap ALL four UPDATE statements inside a single
`async with conn.transaction():` block.
**Warning signs:** Tests that mock `conn.execute` without simulating the
transaction context — check that the mock verifies all four statements ran.

### Pitfall 2: `user_id = 0` bypasses protection
**What goes wrong:** The owner key and legacy env-key paths both return
`user_id = 0`. An anonymisation query `WHERE id = 0` would silently execute
`UPDATE 0` (no rows found) rather than cause harm, but the handler would
incorrectly return 404 rather than 403, leaking that synthetic records exist.
**How to avoid:** Guard `user_id == 0` at the very top of the handler with a
hardcoded 403 before any DB call.

### Pitfall 3: `ON DELETE CASCADE` misread as automatic cleanup
**What goes wrong:** Seeing `REFERENCES users(id) ON DELETE CASCADE` on
`api_keys` and assuming the keys will be cleaned up automatically. They will
only cascade if the `users` row is hard-deleted. Since we keep the row and
only anonymise it, cascade does not fire — keys must be explicitly deactivated.
**How to avoid:** Always deactivate keys inside the same transaction as the
`users` UPDATE.

### Pitfall 4: `webhook_deliveries.payload` retains PII
**What goes wrong:** Forgetting to wipe the `payload JSONB` column on
`webhook_deliveries`. Paddle and LemonSqueezy payloads commonly include the
customer email in their event body, which would survive even after the `users`
row is anonymised.
**How to avoid:** Include `payload = NULL` in the `webhook_deliveries` UPDATE.
Document this in the test (verify the mock receives the `payload = NULL`
parameter).

### Pitfall 5: Re-registration after deletion
**What goes wrong:** After anonymisation, the real email is no longer stored,
so `queries.get_user_by_email(email)` returns `None`. The registration flow
treats this as "no existing account" and allows a fresh registration under the
same email. This is the correct GDPR behaviour (data is erased), but it should
be understood and accepted, not accidental.
**How to avoid:** No special handling needed — this behaviour is correct by
design. Add a comment in the handler and a brief note in test documentation.

### Pitfall 6: `auth_rate_limits` holds email as identifier
**What goes wrong:** The `auth_rate_limits` table stores the raw email string
(or IP) as `identifier`. This is short-lived rate-limit state, not a PII
record that must be erased (the window is 15–60 minutes and holds no linked
personal data beyond the identifier string itself). Attempting to delete it
introduces a race with the rate-limit logic.
**How to avoid:** Do NOT touch `auth_rate_limits` during deletion. The row
expires naturally. Document this decision in the migration comment.

---

## Idempotency Behaviour

A user who calls `DELETE /v1/auth/me` twice (e.g., client retry) will:

1. First call: finds `user_id` in DB, anonymises, returns 204.
2. Second call (using same API key): `require_api_key` looks up the key by
   hash, but the key is now `is_active = FALSE`, so the lookup returns `None`.
   The middleware raises HTTP 403 "Invalid or revoked API key."

This means the endpoint is naturally idempotent from the API consumer's
perspective — a retry with the revoked key cannot double-trigger deletion.
The handler does NOT need to special-case "already deleted" users.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pytest.ini` (asyncio_mode = auto) |
| Quick run command | `pytest tests/test_gdpr_deletion.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID  | Behavior | Test Type | Automated Command | File Exists? |
|---------|----------|-----------|-------------------|-------------|
| GDPR-01 | DELETE /me returns 204 with valid key | unit (mock DB) | `pytest tests/test_gdpr_deletion.py::test_delete_me_returns_204 -q` | Wave 0 |
| GDPR-01 | DELETE /me with `user_id=0` (owner key) returns 403 | unit (mock) | `pytest tests/test_gdpr_deletion.py::test_delete_me_rejects_owner_key -q` | Wave 0 |
| GDPR-02 | anonymise_user() issues UPDATE with anonymised email and NULL PII columns | unit (mock conn) | `pytest tests/test_gdpr_deletion.py::test_anonymise_user_wipes_pii -q` | Wave 0 |
| GDPR-03 | All api_keys rows for the user are deactivated | unit (mock conn) | included in `test_anonymise_user_wipes_pii` | Wave 0 |
| GDPR-04 | webhook_deliveries and api_key_audit_log PII nullified; idempotency rows untouched | unit (mock conn) | `pytest tests/test_gdpr_deletion.py::test_anonymise_user_nullifies_audit_pii -q` | Wave 0 |

### Test file pattern (consistent with `test_auth_rate_limit.py`)

```python
# tests/test_gdpr_deletion.py
from unittest.mock import AsyncMock, MagicMock, call, patch
import pytest
from fastapi import HTTPException
from api.routes.auth import delete_me
from database.queries import anonymise_user

async def test_delete_me_returns_204():
    key_record = {"user_id": 42, "tier": "free", "email": "user@example.com", "key_prefix": "mp_abc"}
    with patch("database.queries.anonymise_user", new=AsyncMock(return_value=True)):
        # FastAPI dependency injection not needed — call handler directly
        result = await delete_me(key_record=key_record)
    assert result is None  # 204 No Content returns None

async def test_delete_me_rejects_owner_key():
    key_record = {"user_id": 0, "tier": "owner", "email": "owner@macropulse.live", "key_prefix": "mp_owner"}
    with pytest.raises(HTTPException) as exc_info:
        await delete_me(key_record=key_record)
    assert exc_info.value.status_code == 403

async def test_anonymise_user_wipes_pii():
    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")
    mock_conn.transaction = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock(return_value=False)))
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    with patch("database.connection.get_db_conn", return_value=mock_cm):
        result = await anonymise_user(42)
    assert result is True
    # Verify users UPDATE was called (first execute call)
    first_call_sql = mock_conn.execute.call_args_list[0][0][0]
    assert "deleted_" in first_call_sql or "@deleted.invalid" in str(mock_conn.execute.call_args_list[0])

async def test_anonymise_user_nullifies_audit_pii():
    # Verify all four tables receive their UPDATE
    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")
    ...
    # Assert execute called 4 times (users, api_keys, webhook_deliveries, api_key_audit_log)
    assert mock_conn.execute.call_count == 4
```

### Sampling Rate
- **Per task commit:** `pytest tests/test_gdpr_deletion.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite (28 existing + 4 new = 32 tests) green before verify

### Wave 0 Gaps
- [ ] `tests/test_gdpr_deletion.py` — covers GDPR-01 through GDPR-04
- [ ] `database/migrations/011_gdpr_deletion.sql` — `deleted_at` column

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hard-delete user row | In-place anonymisation (keep row, wipe PII) | GDPR Article 17 guidance 2018+ | Preserves audit trail integrity |
| DELETE cascades as GDPR compliance | Explicit nullification of non-FK audit columns | Whenever no FK exists | Required for `webhook_deliveries` and `api_key_audit_log` |
| Synchronous deletion | Synchronous is fine here | N/A | No background job needed at current scale |

**Deprecated / not applicable:**
- "Soft delete" with `is_deleted BOOLEAN` flag: not sufficient for GDPR — PII must be wiped, not just hidden.
- Scheduled async deletion job: overkill at current user volume. Synchronous in-request deletion is simpler and correct.

---

## Open Questions

1. **Cancellation of active Paddle / LemonSqueezy subscriptions before deletion**
   - What we know: the `users` row holds `paddle_customer_id`, `ls_customer_id`, and associated subscription IDs that are nullified by deletion.
   - What's unclear: GDPR does not require cancelling a paid subscription before erasure, but it is good practice. Should the endpoint reject deletion if `ls_status = 'active'`, or should it proceed and expect the user to cancel first?
   - Recommendation: For Phase 11, proceed with deletion regardless of subscription status (the user chose erasure). Log a warning if `ls_status = 'active'`. Leave subscription management to the billing portal. Add a comment in the handler.

2. **Email confirmation before deletion**
   - What we know: the current registration and recovery flows use a 2-step OTP email verification.
   - What's unclear: should deletion require a re-verification step (e.g., send OTP, then confirm) to prevent accidental or CSRF-driven deletion?
   - Recommendation: Out of scope for Phase 11. The `X-MacroPulse-Key` in the header is sufficient proof of identity — it is already the authentication credential. A CSRF attack vector does not apply to API key auth (no browser cookies). Document this reasoning in the handler docstring.

3. **Newsletter subscriber cleanup**
   - What we know: `newsletter_subscribers` is a separate table keyed by email, with no FK to `users`.
   - What's unclear: should `DELETE /v1/auth/me` also delete the `newsletter_subscribers` row for the user's email?
   - Recommendation: Yes, add a `DELETE FROM newsletter_subscribers WHERE email = $1` inside the same transaction, using the real email fetched BEFORE the anonymisation UPDATE (since the email is being overwritten).

---

## Sources

### Primary (HIGH confidence)
- Codebase direct read: `database/schema.sql` — complete base schema, `users` and `api_keys` structure
- Codebase direct read: `database/migrations/001–010` — all additive columns on `users` and `api_keys`
- Codebase direct read: `database/migrations/008_schema_hardening.sql` — confirms `webhook_deliveries.user_id` and `api_key_audit_log.user_id` have no FK constraint
- Codebase direct read: `api/auth.py` (`require_api_key`) — auth dependency mechanics and `user_id=0` synthetic records
- Codebase direct read: `api/routes/auth.py` — existing route handler patterns, `Depends(require_api_key)` usage
- Codebase direct read: `database/queries.py` — `conn.transaction()` pattern, query function conventions
- Codebase direct read: `tests/conftest.py`, `tests/test_auth_rate_limit.py` — mock patterns for asyncpg

### Secondary (MEDIUM confidence)
- GDPR Article 17 (Right to erasure) — in-place anonymisation is an accepted implementation of erasure when data integrity requires retaining the row structure; email masking pattern `deleted_<token>@deleted.invalid` is a widely-used convention

### Tertiary (LOW confidence)
- None identified

---

## Metadata

**Confidence breakdown:**
- Schema / PII column inventory: HIGH — read directly from source SQL files
- Auth dependency mechanics: HIGH — read from `api/auth.py` source
- Transaction pattern: HIGH — identical pattern already in `queries.py`
- Audit table FK absence: HIGH — confirmed in migration 008 DDL
- GDPR anonymisation strategy: MEDIUM — based on regulatory guidance and common industry practice; no legal review performed

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (schema is stable; re-verify if new migrations are added before Phase 11 executes)
