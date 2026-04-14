---
phase: 11-gdpr-deletion
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - database/migrations/011_gdpr_deletion.sql
  - database/queries.py
  - api/routes/auth.py
  - tests/test_gdpr_deletion.py
autonomous: true
requirements:
  - GDPR-01
  - GDPR-02
  - GDPR-03
  - GDPR-04

must_haves:
  truths:
    - "Calling DELETE /v1/auth/me with a valid user API key returns HTTP 204 and leaves no callable keys"
    - "The users row retains its id but email becomes deleted_<uuid>@deleted.invalid and deleted_at is set"
    - "All thirteen PII columns on users (name, paddle/LS IDs, webhook_url, etc.) are NULL after deletion"
    - "All api_keys rows for the user have is_active=FALSE, revoked_at set, last_ip=NULL"
    - "webhook_deliveries rows for the user have user_id=NULL and payload=NULL"
    - "api_key_audit_log rows for the user have user_id=NULL, ip_addr=NULL, user_agent=NULL"
    - "newsletter_subscribers row for the user's real email is deleted inside the same transaction"
    - "Calling DELETE /v1/auth/me with user_id=0 (owner/env key) returns HTTP 403 before any DB call"
    - "All 28 existing tests continue to pass after the change"
  artifacts:
    - path: "database/migrations/011_gdpr_deletion.sql"
      provides: "deleted_at TIMESTAMPTZ column on users + partial index"
      contains: "ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at"
    - path: "database/queries.py"
      provides: "anonymise_user(user_id) atomic transaction function"
      exports: ["anonymise_user"]
    - path: "api/routes/auth.py"
      provides: "DELETE /v1/auth/me handler"
      contains: "router.delete"
    - path: "tests/test_gdpr_deletion.py"
      provides: "4 unit tests covering all GDPR requirements"
      contains: "test_delete_me_returns_204"
  key_links:
    - from: "api/routes/auth.py (delete_me handler)"
      to: "database/queries.py (anonymise_user)"
      via: "await queries.anonymise_user(user_id)"
      pattern: "await queries\\.anonymise_user"
    - from: "database/queries.py (anonymise_user)"
      to: "asyncpg conn.transaction()"
      via: "async with conn.transaction():"
      pattern: "conn\\.transaction"
    - from: "database/queries.py"
      to: "newsletter_subscribers DELETE"
      via: "SELECT email before UPDATE, DELETE inside same transaction"
      pattern: "DELETE FROM newsletter_subscribers"
---

<objective>
Implement the GDPR right-to-erasure endpoint for MacroPulse: a single authenticated
DELETE /v1/auth/me route that irrevocably anonymises a user's account in one atomic
database transaction.

Purpose: GDPR Article 17 compliance — registered users can permanently erase their
personal data without manual operator intervention.

Output:
- Migration 011 adding deleted_at to users
- anonymise_user() query function performing all four table writes atomically
- DELETE /v1/auth/me route handler with user_id=0 guard
- 4 unit tests (no live DB) covering all GDPR requirements
</objective>

<execution_context>
@C:/Users/gabri/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/gabri/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse/.planning/phases/11-gdpr-deletion/11-RESEARCH.md

# Key source files
@c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse/database/queries.py
@c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse/database/connection.py
@c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse/api/routes/auth.py
@c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse/api/schemas/responses.py
@c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse/api/auth.py
@c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse/tests/conftest.py
@c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse/tests/test_auth_rate_limit.py

<interfaces>
<!-- Key contracts the executor needs. Extracted from codebase. -->

From database/connection.py:
```python
# Context manager — asyncpg connection from pool
get_db_conn() -> AsyncContextManager[asyncpg.Connection]
# Usage: async with get_db_conn() as conn:
```

From database/queries.py (transaction pattern already in use):
```python
async with get_db_conn() as conn:
    async with conn.transaction():
        await conn.execute(sql, *params)
        result = await conn.fetchrow(sql, *params)
```

From api/auth.py:
```python
# FastAPI dependency — validates X-MacroPulse-Key header
# Returns dict with keys: user_id (int), email (str), tier (str), key_prefix (str)
# user_id == 0 for owner key and legacy env keys — these have no users row
async def require_api_key(...) -> dict: ...
```

From api/routes/auth.py (rotate_key handler pattern):
```python
@router.post("/rotate", response_model=RotateKeyResponse, status_code=status.HTTP_200_OK)
async def rotate_key(key_record: dict = Depends(require_api_key)) -> RotateKeyResponse:
    user_id: int = key_record["user_id"]
    try:
        await queries.revoke_api_keys_for_user(user_id)
    except Exception as exc:
        logger.error("Failed to revoke keys user_id=%d: %s", user_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, ...)
```

From tests/conftest.py (asyncpg mock pattern):
```python
mock_conn = MagicMock()
mock_conn.fetchrow = AsyncMock(return_value=mock_row)
mock_conn.execute = AsyncMock(return_value=None)
mock_cm = AsyncMock()
mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
mock_cm.__aexit__ = AsyncMock(return_value=False)
with patch("database.connection.get_db_conn", return_value=mock_cm):
    yield mock_conn
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Migration 011 + anonymise_user() query function</name>
  <files>
    database/migrations/011_gdpr_deletion.sql
    database/queries.py
    tests/test_gdpr_deletion.py
  </files>
  <behavior>
    - test_anonymise_user_wipes_pii: mock asyncpg conn; call anonymise_user(42); assert return value is True; assert conn.execute call_count == 5 (users UPDATE, api_keys UPDATE, webhook_deliveries UPDATE, api_key_audit_log UPDATE, newsletter_subscribers DELETE); assert first execute call passes a string containing "@deleted.invalid" as the second argument; assert users UPDATE sets deleted_at (the SQL contains "deleted_at")
    - test_anonymise_user_nullifies_audit_pii: mock conn where first execute returns "UPDATE 1"; verify the webhook_deliveries UPDATE SQL contains "payload = NULL"; verify the api_key_audit_log UPDATE SQL contains "user_agent = NULL"; verify the newsletter_subscribers DELETE SQL contains "newsletter_subscribers"
    - test_anonymise_user_not_found: mock conn where first execute returns "UPDATE 0"; assert anonymise_user(999) returns False; assert conn.execute call_count == 1 (early return — remaining tables not touched)
  </behavior>
  <action>
    WRITE database/migrations/011_gdpr_deletion.sql:
    ```sql
    -- Migration 011: Add deleted_at to users for GDPR erasure tracking.
    -- Safe to re-run (IF NOT EXISTS).
    -- Note: auth_rate_limits rows keyed on email/IP expire naturally (<1h window)
    -- and are intentionally NOT wiped during deletion to avoid race conditions.

    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

    CREATE INDEX IF NOT EXISTS idx_users_deleted_at
        ON users (deleted_at) WHERE deleted_at IS NOT NULL;
    ```

    ADD to database/queries.py (after the existing imports, add `import uuid` to the
    import block; then append anonymise_user() at the bottom of the file):

    ```python
    import uuid  # add to existing imports at top of file

    async def anonymise_user(user_id: int) -> bool:
        """
        GDPR right-to-erasure (Article 17). Anonymise the user row, deactivate all
        API keys, nullify PII in audit tables, and remove the newsletter subscription.
        All five operations run in one atomic transaction.

        Authentication note: deletion is authorised by possession of a valid API key
        (the X-MacroPulse-Key header). No email OTP re-verification is required —
        API key auth is not susceptible to CSRF (no browser cookies involved).

        Re-registration note: after anonymisation get_user_by_email() returns None
        for the original address, so the same email may register a new account.
        This is correct GDPR behaviour — data is erased, not just hidden.

        Subscription note: if ls_status = 'active', we proceed with erasure and log
        a warning. The user is expected to cancel via the billing portal beforehand.
        Subscription management is out of scope for Phase 11.

        Returns True if a users row was found and anonymised, False if user_id not found.
        """
        anon_email = f"deleted_{uuid.uuid4()}@deleted.invalid"
        async with get_db_conn() as conn:
            async with conn.transaction():
                # Step 1: Capture real email BEFORE overwriting (needed for newsletter DELETE)
                row = await conn.fetchrow("SELECT email, ls_status FROM users WHERE id = $1", user_id)
                if row is None:
                    return False
                real_email = row["email"]
                if row["ls_status"] == "active":
                    logger.warning(
                        "GDPR deletion for user_id=%d with active LS subscription. "
                        "Subscription was not cancelled automatically.",
                        user_id,
                    )

                # Step 2: Anonymise the users row
                result = await conn.execute(
                    """
                    UPDATE users
                    SET
                        email                      = $1,
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
                        deleted_at                 = now()
                    WHERE id = $2
                    """,
                    anon_email,
                    user_id,
                )
                if result == "UPDATE 0":
                    return False

                # Step 3: Deactivate all API keys and wipe historical IP data
                await conn.execute(
                    """
                    UPDATE api_keys
                    SET
                        is_active    = FALSE,
                        revoked_at   = now(),
                        last_ip      = NULL,
                        ip_locked_at = NULL
                    WHERE user_id = $1
                    """,
                    user_id,
                )

                # Step 4: Nullify PII in webhook_deliveries
                # payload JSONB commonly contains raw Paddle/LS event bodies with customer email
                await conn.execute(
                    """
                    UPDATE webhook_deliveries
                    SET user_id = NULL,
                        payload  = NULL
                    WHERE user_id = $1
                    """,
                    user_id,
                )

                # Step 5: Nullify PII in api_key_audit_log
                # Neither webhook_deliveries nor api_key_audit_log has a FK on user_id
                # (confirmed migration 008) — explicit nullification required
                await conn.execute(
                    """
                    UPDATE api_key_audit_log
                    SET user_id    = NULL,
                        ip_addr    = NULL,
                        user_agent = NULL
                    WHERE user_id = $1
                    """,
                    user_id,
                )

                # Step 6: Remove newsletter subscription using real email (captured above)
                await conn.execute(
                    "DELETE FROM newsletter_subscribers WHERE email = $1",
                    real_email,
                )

        return True
    ```

    CREATE tests/test_gdpr_deletion.py with the three behavior tests described above.
    Follow the exact mock pattern from conftest.py (MagicMock conn, AsyncMock execute,
    AsyncMock __aenter__/__aexit__, patch "database.connection.get_db_conn").
    For the transaction context manager, use:
    ```python
    mock_txn = MagicMock()
    mock_txn.__aenter__ = AsyncMock(return_value=None)
    mock_txn.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=mock_txn)
    ```
    For test_anonymise_user_not_found, set mock_conn.fetchrow to return None.
    For the other tests, set mock_conn.fetchrow to return
    {"email": "user@example.com", "ls_status": "inactive"} and
    mock_conn.execute to return "UPDATE 1".
    Include the call_count assertions from the behavior block.
  </action>
  <verify>
    <automated>cd c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse && pytest tests/test_gdpr_deletion.py -q 2>&1 | tail -5</automated>
  </verify>
  <done>
    3 new tests pass: test_anonymise_user_wipes_pii, test_anonymise_user_nullifies_audit_pii,
    test_anonymise_user_not_found. Migration file exists with correct DDL.
    anonymise_user() is importable from database.queries.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: DELETE /v1/auth/me route handler + endpoint tests</name>
  <files>
    api/routes/auth.py
    tests/test_gdpr_deletion.py
  </files>
  <behavior>
    - test_delete_me_returns_204: build key_record = {"user_id": 42, "tier": "free", "email": "u@example.com", "key_prefix": "mp_abc"}; patch "database.queries.anonymise_user" as AsyncMock(return_value=True); call await delete_me(key_record=key_record); assert result is None (204 no body)
    - test_delete_me_rejects_owner_key: build key_record = {"user_id": 0, "tier": "owner", ...}; call await delete_me(key_record=key_record); assert HTTPException raised with status_code==403; assert anonymise_user was NOT called (patch still present, call_count==0)
  </behavior>
  <action>
    ADD the following handler to api/routes/auth.py, appended after the last existing
    route (rotate_key or recover_verify — check the file end). Do NOT import any new
    modules; `status`, `HTTPException`, `Depends`, `require_api_key`, `queries`, and
    `logger` are already imported.

    ```python
    @router.delete(
        "/me",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Permanently delete your account (GDPR right to erasure)",
    )
    async def delete_me(
        key_record: dict = Depends(require_api_key),
    ) -> None:
        """
        Irrevocably anonymise the authenticated user's account.

        The users row is retained (preserving audit trail FK integrity) but all
        PII columns are overwritten with NULL or a non-reversible placeholder email.
        All API keys for the account are deactivated in the same transaction, making
        this request the last one any of them can authorise.

        CSRF note: API key auth (header-based) is not susceptible to CSRF — no
        browser session cookie is involved. No OTP re-verification is required.

        Subscription note: if the user has an active LemonSqueezy subscription, a
        warning is logged but deletion proceeds. The user should cancel via the
        billing portal first.
        """
        user_id: int = key_record["user_id"]

        # Reject synthetic records: owner key and legacy env-key paths both return
        # user_id=0, which has no corresponding row in the users table.
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
                detail="Could not process deletion request. Please try again.",
            )

        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        logger.info("GDPR account deletion completed: user_id=%d", user_id)
        # Returns HTTP 204 No Content — no response body
    ```

    ADD to tests/test_gdpr_deletion.py the two endpoint tests described in the behavior
    block. Import `delete_me` from `api.routes.auth` at the top of the test file
    (alongside the existing imports). Do not import from `api.main` — this avoids
    triggering the FastAPI lifespan and DB pool at test collection time.
  </action>
  <verify>
    <automated>cd c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse && pytest tests/test_gdpr_deletion.py -q 2>&1 | tail -5</automated>
  </verify>
  <done>
    5 tests pass in test_gdpr_deletion.py (3 from Task 1 + 2 new).
    DELETE /v1/auth/me handler is importable and returns 204 for valid keys, 403 for
    user_id=0, 404 for not-found, 503 on DB error.
  </done>
</task>

<task type="auto">
  <name>Task 3: Full suite regression check</name>
  <files></files>
  <action>
    Run the full test suite to confirm all 28 existing tests still pass alongside the
    5 new GDPR tests (total 33). No code changes in this task — verification only.

    If any pre-existing test fails:
    - Inspect the failure traceback
    - Check whether a new import (uuid) or the new anonymise_user function broke an
      existing mock that patches database.queries at module level
    - Fix the breakage in database/queries.py or the affected test without altering
      the test's assertions
  </action>
  <verify>
    <automated>cd c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse && pytest tests/ -q 2>&1 | tail -10</automated>
  </verify>
  <done>
    pytest tests/ reports 33 passed, 0 failed, 0 errors.
    Output line: "33 passed" (or higher if tests were added by concurrent work).
    No existing test regressed.
  </done>
</task>

</tasks>

<verification>
Manual spot-checks after Task 2 completes (no live DB needed):

1. Import smoke test — confirm no import errors:
   ```
   cd c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse
   python -c "from database.queries import anonymise_user; from api.routes.auth import delete_me; print('OK')"
   ```

2. Migration file sanity:
   ```
   grep -c "ADD COLUMN IF NOT EXISTS deleted_at" database/migrations/011_gdpr_deletion.sql
   ```
   Expected output: 1

3. Transaction completeness — confirm all five execute calls are present in anonymise_user:
   ```
   grep -c "await conn.execute" database/queries.py
   ```
   Count should be >= 5 within the anonymise_user function body (4 UPDATEs + 1 DELETE).
</verification>

<success_criteria>
Phase 11 is complete when:

1. pytest tests/ reports 33 passed (28 existing + 5 new), 0 failed
2. database/migrations/011_gdpr_deletion.sql exists and contains the deleted_at ALTER TABLE
3. anonymise_user() in database/queries.py wraps all five SQL statements in one conn.transaction() block
4. DELETE /v1/auth/me returns 403 for user_id=0, 204 on success (confirmed by unit tests)
5. The users UPDATE SQL covers all 13 PII columns listed in the research (email, name, paddle_customer_id, paddle_subscription_id, paddle_subscription_status, webhook_url, alerts_enabled, ls_customer_id, ls_subscription_id, ls_variant_id, ls_status, ls_portal_url, deleted_at)
6. webhook_deliveries UPDATE includes payload = NULL (GDPR-04 pitfall 4 guard)
7. newsletter_subscribers DELETE executes inside the same transaction using the pre-anonymisation email
</success_criteria>

<output>
After all tasks complete, create:
  c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse/.planning/phases/11-gdpr-deletion/11-01-SUMMARY.md

Include:
- Files created/modified with line counts
- SQL statements written (summary, not full text)
- Test names and which GDPR requirement each covers
- Any deviations from the research recommendations (e.g., if anonymise_user() structure differs)
- Final pytest output line (N passed)
</output>
