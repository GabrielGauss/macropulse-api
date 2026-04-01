---
phase: 11-gdpr-deletion
plan: 01
subsystem: auth/gdpr
tags: [gdpr, erasure, auth, database, asyncpg]
dependency_graph:
  requires: []
  provides: [DELETE /v1/auth/me, anonymise_user()]
  affects: [database/queries.py, api/routes/auth.py]
tech_stack:
  added: []
  patterns: [asyncpg conn.transaction() multi-table atomic write, require_api_key dependency]
key_files:
  created:
    - database/migrations/011_gdpr_deletion.sql (10 lines)
    - tests/test_gdpr_deletion.py (151 lines)
  modified:
    - database/queries.py (741 → 854 lines, +113 lines)
    - api/routes/auth.py (386 → 437 lines, +51 lines)
decisions:
  - anonymise_user() fetches real email via fetchrow before UPDATE (newsletter DELETE needs pre-anonymisation email)
  - patch target is database.queries.get_db_conn (not database.connection.get_db_conn) — module-level import binding
  - execute call_count == 5 (users UPDATE, api_keys UPDATE, webhook_deliveries UPDATE, api_key_audit_log UPDATE, newsletter DELETE)
metrics:
  duration: ~10 minutes
  completed: 2026-04-01T23:45:00Z
  tasks: 3
  files: 4
---

# Phase 11 Plan 01: GDPR User Deletion Endpoint Summary

**One-liner:** Atomic GDPR right-to-erasure via `DELETE /v1/auth/me` — anonymises 13 PII columns, deactivates all API keys, nullifies audit table references, and removes newsletter subscription in one asyncpg transaction.

---

## Files Created / Modified

| File | Action | Lines |
|------|--------|-------|
| `database/migrations/011_gdpr_deletion.sql` | Created | 10 |
| `tests/test_gdpr_deletion.py` | Created | 151 |
| `database/queries.py` | Modified (+113) | 854 |
| `api/routes/auth.py` | Modified (+51) | 437 |

---

## SQL Statements Written

`anonymise_user()` in `database/queries.py` wraps 5 SQL operations in a single `conn.transaction()` block:

1. **SELECT** `email, ls_status FROM users WHERE id = $1` — capture real email before overwriting (needed for newsletter DELETE)
2. **UPDATE users** — sets `email = deleted_<uuid4>@deleted.invalid`, nullifies 12 PII columns (`name`, `paddle_customer_id`, `paddle_subscription_id`, `paddle_subscription_status`, `webhook_url`, `ls_customer_id`, `ls_subscription_id`, `ls_variant_id`, `ls_status`, `ls_portal_url`), sets `alerts_enabled = FALSE`, sets `deleted_at = now()`
3. **UPDATE api_keys** — sets `is_active = FALSE`, `revoked_at = now()`, `last_ip = NULL`, `ip_locked_at = NULL` for all keys of the user (not just active ones — wipes historical IP data)
4. **UPDATE webhook_deliveries** — sets `user_id = NULL`, `payload = NULL` (GDPR-04: payload JSONB contains customer email from Paddle/LS events)
5. **UPDATE api_key_audit_log** — sets `user_id = NULL`, `ip_addr = NULL`, `user_agent = NULL`
6. **DELETE FROM newsletter_subscribers** — removes row by real email (captured in step 1, before the users UPDATE overwrites it)

Migration `011_gdpr_deletion.sql` adds:
- `ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ`
- `CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users (deleted_at) WHERE deleted_at IS NOT NULL`

---

## Test Names and GDPR Requirement Coverage

| Test | Requirement | What it verifies |
|------|-------------|-----------------|
| `test_anonymise_user_wipes_pii` | GDPR-02, GDPR-03 | 5 execute calls, anon email contains `@deleted.invalid`, SQL contains `deleted_at` |
| `test_anonymise_user_nullifies_audit_pii` | GDPR-04 | webhook_deliveries UPDATE contains `payload = NULL`; api_key_audit_log UPDATE contains `user_agent = NULL`; newsletter DELETE targets `newsletter_subscribers` |
| `test_anonymise_user_not_found` | GDPR-02 | Returns `False` immediately with 0 execute calls when user not found |
| `test_delete_me_returns_204` | GDPR-01 | Handler returns `None` (204 No Content) for valid user API key |
| `test_delete_me_rejects_owner_key` | GDPR-01 guard | Raises HTTP 403 for `user_id=0`; `anonymise_user` not called |

---

## Deviations from Plan

**1. [Rule 1 - Bug] Patch target corrected from `database.connection.get_db_conn` to `database.queries.get_db_conn`**

- **Found during:** Task 1 test run (all 3 tests failed with `AssertionError: Pool not initialised`)
- **Issue:** The PLAN.md and RESEARCH.md both specify patching `database.connection.get_db_conn`, but the function is imported at module level into `database/queries.py`. Python resolves the name from the importing module's namespace, not the origin module — so patching `database.connection.get_db_conn` after import has no effect on the already-bound reference.
- **Fix:** Changed all patch targets in the test file to `database.queries.get_db_conn` (matching the pattern in `test_auth_rate_limit.py` line 180: `patch("database.queries.get_db_conn", ...)`)
- **Files modified:** `tests/test_gdpr_deletion.py`

No other deviations — anonymise_user() structure, route handler pattern, and migration DDL implemented exactly as specified.

---

## Final pytest Output

```
33 passed in 4.67s
```

(28 existing + 5 new GDPR tests, 0 failed, 0 errors)

---

## Self-Check

**Files exist:**
- `database/migrations/011_gdpr_deletion.sql` - FOUND
- `database/queries.py` (contains `anonymise_user`) - FOUND
- `api/routes/auth.py` (contains `delete_me`) - FOUND
- `tests/test_gdpr_deletion.py` - FOUND

**Commits exist:**
- `d0b687b` feat(11-01): add anonymise_user() GDPR query function + migration 011 - FOUND
- `76a3bad` feat(11-01): add DELETE /v1/auth/me GDPR erasure endpoint + endpoint tests - FOUND

## Self-Check: PASSED
