# Phase 10: Paddle Billing Completion — Validation Checklist

**Phase:** 10-paddle-billing
**Validated after:** 10-01-PLAN.md completes (Wave 2)
**Run command:** `pytest tests/ -q` from project root

---

## Pre-Validation Gate

Before running `/gsd:verify-work`, confirm all items below:

- [ ] `pytest tests/test_billing.py -q` shows 8 passed, 0 failed
- [ ] `pytest tests/ -q` shows no regressions from any prior phase
- [ ] `10-00-SUMMARY.md` and `10-01-SUMMARY.md` both exist

---

## Requirement Coverage

| Requirement | Verification Command | Pass Criteria |
|-------------|----------------------|---------------|
| BILL-01 | `pytest tests/test_billing.py::test_paddle_checkout_creates_url -x` | 200 response with `checkout_url` field |
| BILL-02 | `pytest tests/test_billing.py::test_paddle_webhook_subscription_activated -x` | 200 + `{ok: true}`; DB mock called |
| BILL-02 | `pytest tests/test_billing.py::test_paddle_webhook_invalid_signature -x` | 401 on HMAC mismatch |
| BILL-03 | `pytest tests/test_billing.py::test_paddle_webhook_idempotent -x` | 200 + `{ok: true, duplicate: true}` |
| BILL-04 | `pytest tests/test_billing.py::test_paddle_portal_returns_url -x` | 200 + `portal_url` field present |
| BILL-05 | `pytest tests/test_billing.py::test_paddle_webhook_subscription_cancelled -x` | `upgrade_user_tier(42, "free")` called |
| TEST-02 | `pytest tests/test_billing.py -q` | All 8 tests pass |

---

## Code Integrity Checks

Run these after both plans execute to confirm no structural regressions:

```bash
cd C:/Users/gabri/OneDrive/Documentos/code/claude/macropulse

# 1. All modified files parse cleanly
python -c "
import ast
for f in ['services/paddle.py', 'api/routes/billing.py', 'database/queries.py', 'tests/test_billing.py', 'tests/conftest.py']:
    ast.parse(open(f).read())
    print(f, 'OK')
"

# 2. Route paths match spec
python -c "
from api.main import app
routes = {r.path: getattr(r, 'methods', set()) for r in app.routes if hasattr(r, 'path')}
assert '/v1/billing/paddle/checkout' in routes, 'FAIL: checkout path missing'
assert '/v1/billing/paddle/portal' in routes, 'FAIL: portal path missing'
assert '/v1/billing/paddle/webhook' in routes, 'FAIL: webhook path missing'
assert 'GET' in routes.get('/v1/billing/paddle/portal', set()), 'FAIL: portal must be GET'
assert 'POST' in routes.get('/v1/billing/paddle/checkout', set()), 'FAIL: checkout must be POST'
assert 'POST' in routes.get('/v1/billing/paddle/webhook', set()), 'FAIL: webhook must be POST'
print('Route paths and methods OK')
"

# 3. Paddle service functions are async
python -c "
import inspect
import services.paddle as p
assert inspect.iscoroutinefunction(p.create_checkout_url), 'FAIL: create_checkout_url not async'
assert inspect.iscoroutinefunction(p.create_portal_url), 'FAIL: create_portal_url not async'
assert inspect.iscoroutinefunction(p.handle_webhook_event), 'FAIL: handle_webhook_event not async'
print('Async signatures OK')
"

# 4. AsyncClient is used (not sync httpx.post)
python -c "
src = open('services/paddle.py').read()
assert 'httpx.post(' not in src, 'FAIL: sync httpx.post still present'
assert 'AsyncClient' in src, 'FAIL: AsyncClient not found'
print('httpx async pattern OK')
"

# 5. Migration 010 exists and contains the column
python -c "
import os
path = 'database/migrations/010_paddle_subscription_status.sql'
assert os.path.exists(path), 'FAIL: migration 010 missing'
content = open(path).read()
assert 'paddle_subscription_status' in content, 'FAIL: column not in migration'
assert 'ADD COLUMN IF NOT EXISTS' in content, 'FAIL: idempotent ADD COLUMN missing'
print('Migration 010 OK')
"

# 6. update_paddle_subscription_status is in queries.py
python -c "
src = open('database/queries.py').read()
assert 'async def update_paddle_subscription_status' in src, 'FAIL: function missing from queries.py'
print('update_paddle_subscription_status OK')
"

# 7. handle_webhook_event awaits its DB calls (no bare function calls on async fns)
python -c "
src = open('services/paddle.py').read()
# Ensure 'await' precedes each DB call in the async handler
assert 'await update_paddle_customer' in src, 'FAIL: missing await on update_paddle_customer'
assert 'await upgrade_user_tier' in src, 'FAIL: missing await on upgrade_user_tier'
assert 'await update_paddle_subscription_status' in src, 'FAIL: missing await on update_paddle_subscription_status'
assert 'await get_user_by_paddle_customer' in src, 'FAIL: missing await on get_user_by_paddle_customer'
print('DB call awaits OK')
"

# 8. Lemon Squeezy routes are untouched
python -c "
from api.main import app
routes = {r.path for r in app.routes if hasattr(r, 'path')}
assert '/v1/billing/lemonsqueezy' in routes, 'FAIL: LS webhook route removed'
assert '/v1/billing/ls-portal' in routes, 'FAIL: ls-portal route removed'
print('Lemon Squeezy routes intact OK')
"

# 9. REQUIREMENTS.md completeness
python -c "
content = open('.planning/REQUIREMENTS.md').read()
for req in ['BILL-01', 'BILL-02', 'BILL-03', 'BILL-04', 'BILL-05', 'TEST-02']:
    assert '[x] **' + req + '**' in content, 'FAIL: ' + req + ' not marked complete'
print('REQUIREMENTS.md completeness OK')
"
```

---

## Known Non-Issues (Do Not Flag)

| Item | Why it's OK |
|------|-------------|
| `subscription.cancelled` (two "l"s) in REQUIREMENTS.md | Typo in the spec; Paddle uses `subscription.canceled` (one "l"). Service code is correct. |
| `_PRODUCT_TIER_MAP` has hardcoded product IDs | Acceptable for Phase 10; move to settings in a future cleanup |
| `verify_webhook` returns `True` when `PADDLE_WEBHOOK_SECRET` unset | Dev-mode bypass, same as existing Phase 6 design. Only matters with secret set. |
| Portal route queries `get_user_by_id` which may not include `paddle_subscription_status` in SELECT | Fixed by Task 1 of 10-00 (column added to SELECT). Verify the SELECT was updated. |

---

## Phase Gate

Phase 10 is complete when:

- [ ] All 9 code integrity checks above pass
- [ ] All 7 requirement verification tests pass
- [ ] `pytest tests/ -q` shows 0 failures across entire suite
- [ ] `10-00-SUMMARY.md` documents: async fixes applied, migration 010 created, routes renamed
- [ ] `10-01-SUMMARY.md` documents: 5 new tests added, BILL-XX requirements marked complete
