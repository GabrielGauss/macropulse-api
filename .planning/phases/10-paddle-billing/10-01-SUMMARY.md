---
phase: 10-paddle-billing
plan: "01"
type: summary
status: complete
commit: 6d363ac
---

# Phase 10-01 Summary — Paddle Billing Tests

## What was done

Added 6 Paddle billing tests to `tests/test_billing.py` and the `mock_paddle_conn` fixture to `tests/conftest.py`. Marked BILL-01–05 and TEST-02 complete in REQUIREMENTS.md.

## Artifacts produced

- `tests/conftest.py` — `mock_paddle_conn` fixture (AsyncMock asyncpg connection, same pattern as `mock_auth_rl_cursor`)
- `tests/test_billing.py` — 6 new test cases:
  - `test_paddle_checkout_creates_url` (BILL-01)
  - `test_paddle_webhook_subscription_activated` (BILL-02)
  - `test_paddle_webhook_subscription_cancelled` (BILL-02 / BILL-05)
  - `test_paddle_webhook_invalid_signature` (BILL-02)
  - `test_paddle_webhook_idempotent` (BILL-03)
  - `test_paddle_portal_returns_url` (BILL-04)
  - `_make_paddle_signature` helper (reproduces Paddle ts=...;h1=... HMAC-SHA256)
- `.planning/REQUIREMENTS.md` — BILL-01–05 and TEST-02 marked `[x]`, traceability updated to `Complete (10-00, 10-01)`

## Test results

28 passed, 0 failed (full suite)

## Notes

- Patch paths must target `api.routes.billing.create_checkout_url` / `api.routes.billing.create_portal_url` (not `services.paddle.*`) because billing.py imports them directly
- `PADDLE_STARTER_PRICE_ID` / `PADDLE_PRO_PRICE_ID` env vars must be patched in the checkout test so `_price_id_for_tier` doesn't 503 before reaching the mocked service function
