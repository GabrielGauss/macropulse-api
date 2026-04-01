# Phase 10: Paddle Billing Completion - Research

**Researched:** 2026-04-01
**Domain:** Paddle Billing API, FastAPI webhook handling, asyncpg, Python billing integration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BILL-01 | Paddle checkout session created via `POST /v1/billing/paddle/checkout` for starter and pro tiers | Route exists at `/v1/billing/checkout`; `create_checkout_url()` in `services/paddle.py` is implemented. Need to verify the route path matches spec, add `paddle/` prefix if required, and ensure async I/O. |
| BILL-02 | Paddle webhook handler processes `subscription.activated`, `subscription.cancelled`, `subscription.updated` and updates `users.paddle_subscription_status` and `api_keys.tier` | Handler exists in `services/paddle.py` and route in `api/routes/billing.py`. Critical gap: `users` table has no `paddle_subscription_status` column; `handle_webhook_event` calls sync DB functions; webhook service uses `hmac.new` (should be `hmac.new` — already correct). |
| BILL-03 | Paddle webhook idempotency: duplicate event IDs deduplicated via `webhook_idempotency` table | Table exists (migration 007). Route already does the check/insert. Fully implemented. |
| BILL-04 | `GET /v1/billing/paddle/portal` returns Paddle customer portal URL | Route exists at `POST /v1/billing/portal`. Requirement says `GET` and path `paddle/portal`. Need to verify path and method, and that `create_portal_url()` uses correct API endpoint. |
| BILL-05 | Tier downgrade on `subscription.cancelled`: user API key tier reverted to `free` within one webhook processing cycle | `handle_webhook_event` already calls `upgrade_user_tier(user_id, "free")` on `subscription.canceled`. Gap: function is not awaited (sync call to async function). |
</phase_requirements>

---

## Summary

Phase 10 completes Paddle Billing integration that was started in earlier phases but never fully wired up or made production-safe. The good news: a substantial amount of code already exists — `services/paddle.py`, `api/routes/billing.py` (Paddle section), `database/migrations/002_paddle_billing.sql`, `007_webhook_idempotency.sql`, and matching `config/settings.py` keys are all present.

The bad news: several critical gaps block production use. First, `services/paddle.py::handle_webhook_event()` calls `get_user_by_paddle_customer()`, `update_paddle_customer()`, and `upgrade_user_tier()` without `await` — these are now `async def` functions (Phase 8 migration), making the current service code silently broken at runtime. Second, the `users` table lacks a `paddle_subscription_status` column (BILL-02 requirement). Third, the checkout and portal route paths do not match the REQUIREMENTS.md spec (`/v1/billing/paddle/checkout` vs `/v1/billing/checkout`). Fourth, `services/paddle.py` uses synchronous `httpx.post()` — blocking FastAPI's event loop; it should use `httpx.AsyncClient`.

The architectural decision to keep Lemon Squeezy alongside Paddle is already implemented: both webhook handlers coexist in `billing.py`. No feature flag or database migration is needed for coexistence — they use separate column sets (`ls_*` vs `paddle_*`).

**Primary recommendation:** Fix the async/await gap in `services/paddle.py`, add the missing `paddle_subscription_status` column via migration 010, correct the route URL paths, convert `httpx.post()` to `await httpx.AsyncClient`, and wire up the two new `TEST-02` test cases.

---

## Existing Code Inventory

This section documents what is already built vs what is missing or broken.

### Already Implemented (do NOT rebuild)

| Component | File | Status |
|-----------|------|--------|
| Checkout URL generation | `services/paddle.py::create_checkout_url()` | Implemented, but uses sync httpx |
| Portal URL generation | `services/paddle.py::create_portal_url()` | Implemented, but uses sync httpx |
| Webhook HMAC-SHA256 verification | `services/paddle.py::verify_webhook()` | Correct — `ts=...;h1=...` format, 5-min replay window |
| Webhook event dispatcher | `services/paddle.py::handle_webhook_event()` | Implemented, but all DB calls missing `await` |
| Tier extraction from event | `services/paddle.py::_tier_from_event()` | Correct — checks `custom_data.tier` first, then product_id map |
| User extraction from event | `services/paddle.py::_user_id_from_event()` | Correct |
| Billing route (checkout) | `api/routes/billing.py` | Implemented; path is `/v1/billing/checkout` (spec wants `/v1/billing/paddle/checkout`) |
| Billing route (portal) | `api/routes/billing.py` | Implemented as `POST /v1/billing/portal`; spec says `GET /v1/billing/paddle/portal` |
| Billing route (webhook) | `api/routes/billing.py` | Implemented at `POST /v1/billing/webhook`; idempotency check present |
| Idempotency table | `database/migrations/007_webhook_idempotency.sql` | Exists, `(event_id, provider, processed_at)` |
| Paddle DB columns | `database/migrations/002_paddle_billing.sql` | `paddle_customer_id`, `paddle_subscription_id` on `users` |
| Settings keys | `config/settings.py` | `paddle_api_key`, `paddle_webhook_secret`, `paddle_environment`, `paddle_starter_price_id`, `paddle_pro_price_id`, `paddle_client_token` all present |
| DB query: get by paddle customer | `database/queries.py::get_user_by_paddle_customer()` | Async — correct |
| DB query: update paddle customer | `database/queries.py::update_paddle_customer()` | Async — correct |
| DB query: upgrade tier | `database/queries.py::upgrade_user_tier()` | Async — correct |
| Product ID → tier map | `services/paddle.py::_PRODUCT_TIER_MAP` | Has `pro_01kkhzzr1c1f1fta693c6p6nzv` → starter, `pro_01kkj01cx467jt6v4c5g2hakrd` → pro |

### Gaps and Bugs to Fix

| Gap | File | Fix |
|-----|------|-----|
| `handle_webhook_event()` is sync, calls async DB functions without `await` | `services/paddle.py` | Convert to `async def`, add `await` before all DB calls |
| `httpx.post()` / `httpx.post()` block event loop | `services/paddle.py` | Replace with `async with httpx.AsyncClient() as client: await client.post(...)` |
| Missing `paddle_subscription_status` column on `users` | Schema | Add via migration `010_paddle_subscription_status.sql` |
| Route path mismatch | `api/routes/billing.py` | Change `prefix` or add `paddle/` sub-prefix to match BILL-01/BILL-04 spec |
| Portal endpoint is `POST`, spec wants `GET` | `api/routes/billing.py` | Change method decorator to `@router.get` |
| `handle_webhook_event` result never awaited in route | `api/routes/billing.py` | Change `handle_webhook_event(event)` to `await handle_webhook_event(event)` |

---

## Standard Stack

### Core (all already in `requirements.txt`)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `httpx` | `>=0.27,<1.0` | Async HTTP calls to Paddle REST API | Use `httpx.AsyncClient` — already in requirements |
| `asyncpg` | `>=0.29,<1.0` | Async database | Already in requirements |
| `fastapi` | `>=0.110,<1.0` | API framework | Already in requirements |
| `pydantic` | `>=2.6,<3.0` | Request/response validation | Already in requirements |

### Paddle SDK Decision: Do NOT Add

The official `paddle-python-sdk` v1.14.0 (Python 3.11–3.13 compatible) uses `requests` (synchronous only). The `Verifier` class targets Flask/Django request protocols, not FastAPI's `Request`. Adding it would introduce a synchronous dependency for a codebase that already has:

1. A working HMAC verifier in `services/paddle.py` (already correct — MEDIUM confidence)
2. A working `httpx.AsyncClient` pattern everywhere else

**Decision: Do not add `paddle-python-sdk`.** Maintain the hand-rolled approach; it follows Paddle's documented algorithm exactly.

**Confidence:** HIGH — The HMAC algorithm (`ts=...;h1=...`, `f"{ts}:{raw_body}"`, SHA-256 hexdigest) is confirmed by [Paddle docs](https://developer.paddle.com/webhooks/signature-verification) and multiple independent sources.

---

## Architecture Patterns

### Recommended Structure (matches current codebase — no reorganization needed)

```
services/
└── paddle.py           # Paddle API calls + webhook business logic (async)
api/routes/
└── billing.py          # HTTP layer: checkout, portal, webhook, LS webhook
database/migrations/
└── 010_paddle_subscription_status.sql   # NEW: add paddle_subscription_status
database/
└── queries.py          # DB functions: already has get/update_paddle_customer, upgrade_tier
config/
└── settings.py         # Already has all Paddle keys
tests/
└── test_billing.py     # Extend with BILL-02 tests (TEST-02)
```

### Pattern 1: Async Paddle Service Calls

The current `services/paddle.py` uses synchronous `httpx`. In FastAPI async handlers this blocks the event loop. Pattern to use:

```python
# Source: https://www.python-httpx.org/async/
import httpx

async def create_checkout_url(price_id: str, user_id: int, email: str, tier: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_api_base()}/transactions",
            json=payload,
            headers=_headers(),
        )
    resp.raise_for_status()
    return resp.json()["data"]["checkout"]["url"]
```

### Pattern 2: Webhook Event Handler (Async)

```python
async def handle_webhook_event(event: dict[str, Any]) -> str:
    from database.queries import (
        get_user_by_paddle_customer,
        update_paddle_customer,
        upgrade_user_tier,
    )
    event_type = event.get("event_type", "")
    data = event.get("data", {})

    if event_type in ("subscription.activated", "subscription.updated"):
        tier = _tier_from_event(event)
        user_id = _user_id_from_event(event)
        customer_id = data.get("customer_id", "")
        subscription_id = data.get("id", "")
        status = data.get("status", "")

        if not tier:
            return "no_tier"

        if user_id:
            await update_paddle_customer(user_id, customer_id, subscription_id)
            await upgrade_user_tier(user_id, tier)
            await update_paddle_subscription_status(user_id, status)
            return f"upgraded:{tier}"

        existing = await get_user_by_paddle_customer(customer_id)
        if existing:
            await upgrade_user_tier(existing["id"], tier)
            await update_paddle_subscription_status(existing["id"], status)
            return f"upgraded:{tier}"
        return "user_not_found"

    if event_type in ("subscription.canceled", "subscription.paused"):
        customer_id = data.get("customer_id", "")
        user = await get_user_by_paddle_customer(customer_id)
        if user:
            await upgrade_user_tier(user["id"], "free")
            await update_paddle_subscription_status(user["id"], data.get("status", "canceled"))
            return "downgraded:free"
        return "user_not_found"

    return f"ignored:{event_type}"
```

### Pattern 3: Route Path Correction

REQUIREMENTS.md specifies `/v1/billing/paddle/checkout` and `GET /v1/billing/paddle/portal`. Current implementation uses `/v1/billing/checkout` and `POST /v1/billing/portal`. Two options:

**Option A (minimal change):** Add a `paddle/` sub-router prefix. Change `router = APIRouter(prefix="/v1/billing")` to keep the base, then add `/paddle/checkout` and `GET /paddle/portal` route decorators. This is the cleanest fix.

**Option B (alias):** Keep existing routes for backward compatibility and add new routes at the spec paths. Risky — duplicated logic.

**Recommendation:** Option A. No external clients are using these endpoints yet (Paddle approval still pending), so no backward-compatibility concern.

### Pattern 4: Webhook Status → Tier Mapping

| Paddle event_type | Paddle `data.status` | Action |
|-------------------|----------------------|--------|
| `subscription.activated` | `active` | Upgrade tier to `custom_data.tier` or product map |
| `subscription.updated` | `active` | Upgrade or downgrade based on new tier |
| `subscription.canceled` | `canceled` | Downgrade tier to `free` |
| `subscription.paused` | `paused` | Downgrade tier to `free` |
| `transaction.completed` | — | No tier change needed (already handled by subscription events) |

**Note on `subscription.updated`:** Paddle fires this for plan changes (upgrade/downgrade). The `custom_data.tier` embedded at checkout creation is the source of truth for the target tier. If a user upgrades from Starter to Pro, a new checkout session is created, embedding the new tier. On `subscription.updated`, the tier in `custom_data` reflects the current active plan.

### Anti-Patterns to Avoid

- **Parsing webhook JSON before signature verification:** The raw body used for HMAC must be the unmodified bytes. Never parse JSON first, then re-serialize — this can alter whitespace and break verification.
- **Calling sync DB functions in async handlers:** Phase 8 converted all DB queries to async. Calling them without `await` returns a coroutine object (truthy) — it silently does nothing. This is the critical bug in the current `handle_webhook_event`.
- **Caching portal URLs:** Paddle portal session tokens expire. Always generate a fresh one per request.
- **Using `hmac.new` with non-bytes inputs:** asyncpg returns strings; always `.encode()` before HMAC.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMAC webhook verification | Custom crypto | Already in `services/paddle.py` — keep it | Correct algorithm confirmed by Paddle docs |
| HTTP client | `urllib` / `aiohttp` | `httpx.AsyncClient` (already in requirements) | Consistent with rest of codebase |
| Idempotency dedup | In-memory dict | `webhook_idempotency` DB table (already exists) | Survives restarts, same pattern as Lemon Squeezy |
| Tier resolution | Hardcoded email lookup | `custom_data.user_id` embedded at checkout | More reliable than email matching (emails can change) |

---

## Common Pitfalls

### Pitfall 1: Sync DB Calls in Async Handler (Critical — Already Present)

**What goes wrong:** `handle_webhook_event()` in `services/paddle.py` is a regular `def` function that calls `async def` DB functions like `get_user_by_paddle_customer()` without `await`. In Python, calling an async function without `await` returns a coroutine object — it never executes. The code runs silently, appears to succeed, but nothing is written to the database.

**Why it happens:** The service was written before Phase 8 converted all DB queries to async. The service file was not updated.

**How to avoid:** Convert `handle_webhook_event` to `async def` and add `await` to all internal DB calls. Also update the route to `await handle_webhook_event(event)`.

**Warning signs:** Paddle webhook returns 200 but `api_keys.tier` never updates; `paddle_customer_id` stays NULL.

### Pitfall 2: Synchronous httpx in Async FastAPI Routes

**What goes wrong:** `services/paddle.py::create_checkout_url()` and `create_portal_url()` use `httpx.post(...)` (synchronous). When called from an `async def` FastAPI route, this blocks the event loop for the 100–500ms Paddle API response time.

**Why it happens:** httpx has both sync and async APIs. `httpx.post()` is the sync variant.

**How to avoid:** Use `async with httpx.AsyncClient() as client: await client.post(...)`.

**Warning signs:** API latency spikes during billing calls; event loop warnings in logs.

### Pitfall 3: Paddle Event Name Casing

**What goes wrong:** Paddle uses `subscription.canceled` (American English, one "l"), not `subscription.cancelled` (British English, two "l"s). The current code has both: `services/paddle.py` correctly handles `"subscription.canceled"` but the REQUIREMENTS.md uses `"subscription.cancelled"`.

**Confirmed:** Paddle's official docs use `subscription.canceled`. The existing code is correct on this point. The requirements doc has a typo.

**How to avoid:** Always test against sandbox events. Don't fix the service code to match the requirements typo.

### Pitfall 4: Raw Body Must Remain Unmodified for HMAC

**What goes wrong:** FastAPI's `await request.body()` returns raw bytes — correct. But if the webhook route parses JSON and then verifies, or if any middleware compresses/modifies the body, signature verification fails.

**How to avoid:** Call `raw_body = await request.body()` before any other processing. Pass `raw_body` directly to `verify_webhook()`. The current `billing.py` already does this correctly.

### Pitfall 5: Missing `paddle_subscription_status` Column

**What goes wrong:** BILL-02 requires updating `users.paddle_subscription_status`. This column does not exist in the current schema (confirmed by reading `schema.sql`, `002_paddle_billing.sql`, and `006_lemonsqueezy_billing.sql`). Any INSERT/UPDATE referencing it will raise a `PostgresError` at runtime.

**How to avoid:** Create migration `010_paddle_subscription_status.sql` with `ALTER TABLE users ADD COLUMN IF NOT EXISTS paddle_subscription_status TEXT`.

### Pitfall 6: Portal Session Not Found Without `customer_portal_session.write` Permission

**What goes wrong:** The `POST /customers/{id}/portal-sessions` endpoint requires the API key to have `customer_portal_session.write` permission. Standard read-only API keys will get a 403.

**Confirmed by:** [Paddle API reference — permissions](https://developer.paddle.com/api-reference/about/permissions).

**How to avoid:** In the Paddle dashboard, confirm the API key used for `PADDLE_API_KEY` has this permission scope. Document in `.env.example`.

---

## Code Examples

### Webhook Signature Verification (current implementation — confirmed correct)

```python
# Source: services/paddle.py (existing), algorithm confirmed by
# https://developer.paddle.com/webhooks/signature-verification
import hashlib
import hmac
import time

def verify_webhook(raw_body: bytes, signature_header: str) -> bool:
    """
    Header format:  ts=<timestamp>;h1=<hex_digest>
    Signed content: <timestamp>:<raw_body_as_utf8>
    """
    try:
        parts = dict(p.split("=", 1) for p in signature_header.split(";"))
        ts = parts["ts"]
        h1 = parts["h1"]
    except (KeyError, ValueError):
        return False

    # Replay attack guard: reject webhooks older than 5 minutes
    if abs(time.time() - int(ts)) > 300:
        return False

    signed_payload = f"{ts}:{raw_body.decode('utf-8')}".encode()
    expected = hmac.new(
        settings.paddle_webhook_secret.encode(),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, h1)
```

### Async Checkout URL (fix for current sync implementation)

```python
# Source: https://www.python-httpx.org/async/
async def create_checkout_url(price_id: str, user_id: int, email: str, tier: str) -> str:
    payload = {
        "items": [{"price_id": price_id, "quantity": 1}],
        "customer": {"email": email},
        "checkout": {"url": settings.paddle_success_url},
        "custom_data": {"user_id": str(user_id), "tier": tier},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_api_base()}/transactions",
            json=payload,
            headers=_headers(),
        )
    resp.raise_for_status()
    return resp.json()["data"]["checkout"]["url"]
```

### New DB Query: update_paddle_subscription_status

```python
# Add to database/queries.py — no ORM, matches existing asyncpg pattern
async def update_paddle_subscription_status(user_id: int, status: str) -> None:
    async with get_db_conn() as conn:
        await conn.execute(
            "UPDATE users SET paddle_subscription_status = $1 WHERE id = $2",
            status, user_id,
        )
```

### Migration 010

```sql
-- database/migrations/010_paddle_subscription_status.sql
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS paddle_subscription_status TEXT;

CREATE INDEX IF NOT EXISTS idx_users_paddle_customer
    ON users (paddle_customer_id) WHERE paddle_customer_id IS NOT NULL;
```

### Test: BILL-02 Paddle subscription.activated with valid signature

```python
# Source: tests/test_billing.py pattern (existing), matches conftest.py mock style
import hashlib
import hmac
import json
import time
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from api.main import app

def _make_paddle_signature(body: bytes, secret: str) -> str:
    ts = str(int(time.time()))
    payload = f"{ts}:{body.decode('utf-8')}".encode()
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={digest}"

def test_paddle_webhook_subscription_activated():
    client = TestClient(app)
    secret = "test-paddle-secret"
    event = {
        "event_id": "evt_test_001",
        "event_type": "subscription.activated",
        "data": {
            "id": "sub_001",
            "customer_id": "ctm_001",
            "status": "active",
            "custom_data": {"user_id": "42", "tier": "starter"},
            "items": [],
        },
    }
    body = json.dumps(event).encode()
    sig = _make_paddle_signature(body, secret)

    with patch.dict(os.environ, {"PADDLE_WEBHOOK_SECRET": secret}):
        with patch("database.queries.update_paddle_customer", new=AsyncMock()):
            with patch("database.queries.upgrade_user_tier", new=AsyncMock()):
                resp = client.post(
                    "/v1/billing/paddle/webhook",
                    content=body,
                    headers={"Paddle-Signature": sig, "Content-Type": "application/json"},
                )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
```

---

## Database Schema — Complete Billing Picture

After all migrations applied, the `users` table billing columns are:

| Column | Type | Source Migration | Purpose |
|--------|------|-----------------|---------|
| `paddle_customer_id` | TEXT | 002 | Paddle customer ID (ctm_...) |
| `paddle_subscription_id` | TEXT | 002 | Paddle subscription ID (sub_...) |
| `paddle_subscription_status` | TEXT | **010 (new)** | `active`, `canceled`, `paused`, `past_due` |
| `ls_customer_id` | TEXT | 006 | Lemon Squeezy customer ID |
| `ls_subscription_id` | TEXT | 006 | Lemon Squeezy subscription ID |
| `ls_variant_id` | TEXT | 006 | LS variant ID |
| `ls_status` | TEXT | 006 | LS subscription status |
| `ls_portal_url` | TEXT | 006 | LS customer portal URL |

**Coexistence with Lemon Squeezy:** Both column sets exist independently on the `users` table. `upgrade_user_tier()` updates `api_keys.tier` regardless of billing provider. No feature flag is needed — the billing route handles both providers in separate endpoints. A user could theoretically have both an LS and a Paddle subscription; `api_keys.tier` reflects whichever was updated last (last-write-wins). For v1.1 this is acceptable.

---

## Paddle Webhook Event Reference

**Confirmed event names** (from [Paddle developer docs](https://developer.paddle.com/webhooks/subscriptions/subscription-canceled)):

| Event | When Fired | Action Required |
|-------|-----------|-----------------|
| `subscription.created` | Subscription created (before payment) | None — wait for `activated` |
| `subscription.activated` | First payment succeeds, subscription goes active | Upgrade tier |
| `subscription.updated` | Plan change, billing cycle change | Update tier if changed |
| `subscription.canceled` | User cancels (effective immediately or at period end) | Downgrade to free |
| `subscription.paused` | Subscription paused | Downgrade to free |
| `subscription.resumed` | Subscription resumed after pause | Upgrade tier |
| `subscription.past_due` | Payment failed, dunning begins | No immediate downgrade; Paddle retries |
| `transaction.completed` | One-time payment or renewal invoice paid | Not needed for subscription tier management |

**Recommendation for Phase 10:** Handle `subscription.activated`, `subscription.updated`, `subscription.canceled`, `subscription.paused`, `subscription.resumed`. Ignore `subscription.past_due` (Paddle handles dunning; downgrade only on `canceled`).

---

## Lemon Squeezy Coexistence Strategy

**Current state:** Both providers live in `api/routes/billing.py`. Lemon Squeezy handler is complete and tested. Paddle handler has the async bugs noted above.

**Strategy for Phase 10:** Fix Paddle, do not touch Lemon Squeezy. Lemon Squeezy webhook at `/v1/billing/lemonsqueezy` stays unchanged.

**No feature flag needed.** Paddle approval is pending; once approved and `PADDLE_API_KEY`/`PADDLE_WEBHOOK_SECRET` are set, Paddle becomes active. If keys are not set, the checkout endpoint returns a config error (already implemented in `_price_id_for_tier`). The two providers do not conflict.

---

## Environment Variables Required

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `PADDLE_API_KEY` | Bearer token for Paddle REST API | `pdl_sbox_apikey_...` |
| `PADDLE_WEBHOOK_SECRET` | HMAC secret from Paddle Notifications dashboard | `pdl_ntfset_...` |
| `PADDLE_ENVIRONMENT` | `sandbox` or `production` | `sandbox` |
| `PADDLE_STARTER_PRICE_ID` | `pri_...` for Starter plan ($49/mo) | `pri_01...` |
| `PADDLE_PRO_PRICE_ID` | `pri_...` for Pro plan ($199/mo) | `pri_01...` |
| `PADDLE_SUCCESS_URL` | Redirect after checkout | `https://macropulse.live/welcome` |
| `PADDLE_CLIENT_TOKEN` | For Paddle.js client-side (not needed server-side) | `live_...` |

All keys are already in `config/settings.py`. Add descriptions to `.env.example` (Phase 6 SEC-12 scope, but worth noting here).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio 0.23 |
| Config file | `pytest.ini` (at project root) |
| Quick run command | `pytest tests/test_billing.py -q` |
| Full suite command | `pytest tests/ -q` |
| Async mode | `asyncio_mode = auto` (set in pytest.ini) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BILL-01 | Checkout endpoint returns `checkout_url` for valid tier | unit (mock Paddle API) | `pytest tests/test_billing.py::test_paddle_checkout_creates_url -x` | ❌ Wave 0 |
| BILL-02 | `subscription.activated` webhook upgrades `api_keys.tier` | unit (mock DB + valid signature) | `pytest tests/test_billing.py::test_paddle_webhook_subscription_activated -x` | ❌ Wave 0 |
| BILL-02 | `subscription.cancelled` webhook downgrades tier to free | unit (mock DB + valid signature) | `pytest tests/test_billing.py::test_paddle_webhook_subscription_cancelled -x` | ❌ Wave 0 |
| BILL-02 | Invalid signature returns 401 | unit | `pytest tests/test_billing.py::test_paddle_webhook_invalid_signature -x` | ✅ (existing `test_paddle_replay_window` covers partial — need explicit sig mismatch test) |
| BILL-03 | Duplicate event_id returns 200 with `duplicate: true` | unit (mock DB) | `pytest tests/test_billing.py::test_paddle_webhook_idempotent -x` | ❌ Wave 0 |
| BILL-04 | Portal endpoint returns URL for user with paddle_customer_id | unit (mock Paddle API) | `pytest tests/test_billing.py::test_paddle_portal_returns_url -x` | ❌ Wave 0 |
| BILL-05 | Tier reverts to `free` within one webhook cycle on cancellation | covered by BILL-02 cancelled test above | same | ❌ Wave 0 |

### Wave 0 Gaps

- [ ] `tests/test_billing.py` — extend with 5 new Paddle test cases (BILL-01 through BILL-05). Existing file has 3 tests covering SEC-20, SEC-21, SEC-22. New tests go in the same file.
- [ ] No new framework install needed — pytest-asyncio already in requirements.
- [ ] `conftest.py` — add `mock_paddle_conn` fixture (AsyncMock for asyncpg, same pattern as `mock_auth_rl_cursor`).

### Sampling Rate

- **Per task commit:** `pytest tests/test_billing.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Synchronous httpx in service | `httpx.AsyncClient` with `await` | Phase 10 (fix) | Prevents event loop blocking |
| `def handle_webhook_event` (sync) | `async def handle_webhook_event` | Phase 10 (fix) | DB writes actually execute |
| `/v1/billing/checkout` | `/v1/billing/paddle/checkout` | Phase 10 (fix) | Matches REQUIREMENTS.md spec |
| `POST /v1/billing/portal` | `GET /v1/billing/paddle/portal` | Phase 10 (fix) | Matches REST semantics + spec |
| No `paddle_subscription_status` column | `users.paddle_subscription_status TEXT` | Migration 010 | BILL-02 persists subscription status |

---

## Open Questions

1. **Route path backward compatibility**
   - What we know: Current routes are `/v1/billing/checkout` and `POST /v1/billing/portal`. Dashboard frontend may reference these.
   - What's unclear: Does the frontend call these endpoints? (Paddle not live yet, so probably not.)
   - Recommendation: Check `frontend/src/` for fetch calls to `/v1/billing/` before renaming. If found, update both.

2. **`subscription.updated` tier extraction reliability**
   - What we know: `custom_data.tier` is set at checkout creation. If a user upgrades from starter to pro via the Paddle portal (not our checkout), `custom_data` may be absent.
   - What's unclear: Does Paddle preserve `custom_data` across plan changes initiated from the customer portal?
   - Recommendation: Always fall back to `_PRODUCT_TIER_MAP` (product_id lookup). Keep both resolution paths.

3. **Paddle product IDs in `_PRODUCT_TIER_MAP`**
   - What we know: `services/paddle.py` has hardcoded product IDs (`pro_01kkhzzr1c1f1fta693c6p6nzv` → starter, `pro_01kkj01cx467jt6v4c5g2hakrd` → pro).
   - What's unclear: Are these the real production product IDs or placeholders from when Paddle was first configured?
   - Recommendation: Verify in Paddle sandbox dashboard before going live. Move to `config/settings.py` as `paddle_starter_product_id` / `paddle_pro_product_id` (keys already exist there — just use them in `_PRODUCT_TIER_MAP` instead of hardcoding).

---

## Sources

### Primary (HIGH confidence)

- Codebase: `services/paddle.py`, `api/routes/billing.py`, `database/queries.py`, `database/schema.sql`, `database/migrations/` — read directly
- Codebase: `config/settings.py`, `requirements.txt`, `pytest.ini` — read directly
- [Paddle webhook signature verification](https://developer.paddle.com/webhooks/signature-verification) — algorithm confirmed (`ts=...;h1=...`, `{ts}:{raw_body}` signed payload)
- [paddle-python-sdk PyPI](https://pypi.org/project/paddle-python-sdk/) — v1.14.0, Python 3.13 support confirmed, uses `requests` (sync only)
- [httpx async docs](https://www.python-httpx.org/async/) — `AsyncClient` pattern

### Secondary (MEDIUM confidence)

- [Paddle subscription webhook events](https://developer.paddle.com/webhooks/subscriptions/subscription-canceled) — event names `subscription.activated`, `subscription.canceled` confirmed
- [Paddle customer portal sessions API](https://developer.paddle.com/api-reference/customer-portals/create-customer-portal-session) — `POST /customers/{id}/portal-sessions`, requires `customer_portal_session.write` permission
- [Josh Karamuth — verify Paddle webhooks Python](https://joshkaramuth.com/blog/verify-paddle-billing-webhooks-python/) — corroborates HMAC algorithm

### Tertiary (LOW confidence — flag for validation)

- Paddle SDK `Verifier` class time drift tolerance defaults: stated as 5 seconds by PyPI page; existing code uses 300 seconds (5 minutes). The existing code's 5-minute window matches Paddle's own documentation on replay attacks.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt; no new dependencies needed
- Architecture: HIGH — full codebase read; gaps identified from source, not inference
- Pitfalls: HIGH — async bug confirmed by direct code reading; event name casing confirmed by official docs
- Webhook algorithm: HIGH — confirmed by Paddle docs and independent blog verification
- Test patterns: HIGH — existing test suite and conftest.py read directly

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (Paddle API is stable; SDK v1.14 just released 2026-03-30)
