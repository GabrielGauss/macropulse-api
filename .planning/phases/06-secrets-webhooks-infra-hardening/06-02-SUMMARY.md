---
phase: 06-secrets-webhooks-infra-hardening
plan: "02"
subsystem: infra
tags: [webhook, hmac, security, fastapi, pydantic-settings, lemon-squeezy, paddle]

# Dependency graph
requires:
  - phase: 06-00
    provides: "Wave 0 scaffolding — xfail test stubs in test_billing.py, webhook route skeleton"
provides:
  - "_validate_webhook_secrets() startup guard in api/main.py lifespan()"
  - "_ls_verify_signature() fail-closed — returns False when LS_WEBHOOK_SECRET absent"
  - "Settings.env field for production/development detection"
  - "3 passing billing security tests (SEC-20, SEC-21, SEC-22)"
affects: [06-03, 06-04, future-billing-plans]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fail-closed webhooks: reject (return False) rather than silently accept when secret missing"
    - "Startup guard pattern: validate required secrets in lifespan() before accepting requests"
    - "Settings.env field with AliasChoices for environment-aware production guards"

key-files:
  created:
    - tests/test_billing.py
  modified:
    - api/routes/billing.py
    - api/main.py
    - config/settings.py

key-decisions:
  - "_ls_verify_signature logs error (not warning) when rejecting — distinguishes severity from dev-mode warning"
  - "test_paddle_replay_window patches PADDLE_WEBHOOK_SECRET to reach timestamp check — Paddle secret guard comes before timestamp check in verify_webhook()"
  - "Settings.env uses AliasChoices('ENV', 'env') consistent with all 27 existing threshold fields"

patterns-established:
  - "All startup security guards go in lifespan() after init_signer() — single entry point"
  - "Tests must patch PADDLE_WEBHOOK_SECRET to test replay window (early-return bypasses timestamp check otherwise)"

requirements-completed: [SEC-20, SEC-21, SEC-22]

# Metrics
duration: 6min
completed: 2026-03-29
---

# Phase 6 Plan 02: Webhook Security Hardening Summary

**LS webhook silent-accept vulnerability patched via fail-closed HMAC check and production startup guard; Paddle replay protection confirmed and tested**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-29T05:52:13Z
- **Completed:** 2026-03-29T05:58:31Z
- **Tasks:** 2
- **Files modified:** 4 (api/routes/billing.py, api/main.py, config/settings.py, tests/test_billing.py)

## Accomplishments

- `_ls_verify_signature()` now fails closed — returns `False` (not `True`) when `LS_WEBHOOK_SECRET` is unset, eliminating the billing bypass vulnerability
- `_validate_webhook_secrets()` startup guard in `lifespan()` raises `RuntimeError` in production if `LS_WEBHOOK_SECRET` is missing, preventing silently broken deployments
- `Settings.env` field added to `config/settings.py` for production/development detection via `AliasChoices("ENV", "env")`
- All 3 billing tests converted from xfail stubs to real passing assertions (SEC-20, SEC-21, SEC-22)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Settings.env field and _ls_verify_signature fail-closed fix** - `b6f4eb3` (feat)
2. **Task 2: Add startup guards and implement billing tests** - `7fb5ad2` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD tasks had RED phase (xfail stubs already existed from Wave 0 scaffold; converted to failing real assertions) then GREEN phase (implementation)._

## Files Created/Modified

- `api/routes/billing.py` — `_ls_verify_signature()` returns `False` when secret absent (was `True`)
- `api/main.py` — `_validate_webhook_secrets()` function + call in `lifespan()` after `init_signer()`
- `config/settings.py` — `env: str` field with `AliasChoices("ENV", "env")`, default `"development"`
- `tests/test_billing.py` — All 3 tests converted from xfail stubs to real assertions (3 PASSED)

## Decisions Made

- `_ls_verify_signature` logs at ERROR level (not WARNING) when failing closed — distinguishes security-relevant rejection from the dev-mode warning
- `test_paddle_replay_window` patches `PADDLE_WEBHOOK_SECRET` so the code reaches the timestamp check; without a secret, `verify_webhook` returns `True` early (dev-mode bypass) before the timestamp guard fires
- `Settings.env` uses same `AliasChoices` pattern as all 27 existing threshold fields — consistent with established config conventions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_paddle_replay_window test spec**
- **Found during:** Task 2 (billing tests)
- **Issue:** Plan's test spec called `verify_webhook()` without a Paddle secret set. `verify_webhook()` returns `True` early when `paddle_webhook_secret` is empty (dev-mode skip), so the timestamp check was never reached and the test would assert `True is False`
- **Fix:** Updated test to `patch.dict(os.environ, {"PADDLE_WEBHOOK_SECRET": "test-paddle-secret"})` + `get_settings.cache_clear()` so code proceeds past the secret guard and hits the replay timestamp check
- **Files modified:** tests/test_billing.py
- **Verification:** `test_paddle_replay_window` passes with assertion `result is False`
- **Committed in:** b6f4eb3 (Task 1 commit — test was written in same commit)

**2. [Rule 3 - Blocking] Installed missing email-validator dependency**
- **Found during:** Task 2 (`test_ls_webhook_missing_secret` RED phase)
- **Issue:** Importing `api.main` pulled in `api.routes.auth` → `api.schemas.responses` which uses pydantic `EmailStr`, requiring `email-validator` package not installed in environment
- **Fix:** `pip install "email-validator>=2.1,<3.0"` (already in requirements.txt, just not installed)
- **Files modified:** None (environment install only)
- **Verification:** Test import succeeds, all 3 tests pass

---

**Total deviations:** 2 auto-fixed (1 bug in test spec, 1 missing dep)
**Impact on plan:** Both necessary for tests to pass. No scope creep.

## Issues Encountered

- Linter reverted `test_billing.py` after first Edit during Task 1 RED phase — used Write tool for second attempt, which persisted correctly

## User Setup Required

None — no external service configuration required beyond setting `LS_WEBHOOK_SECRET` in `.env` (already documented in existing setup guides).

## Next Phase Readiness

- SEC-20, SEC-21, SEC-22 complete — webhook security hardening for LS done
- Paddle `verify_webhook()` already had replay protection confirmed (no code change needed)
- Ready for 06-03 (CORS hardening using the new `Settings.env` field)

---
*Phase: 06-secrets-webhooks-infra-hardening*
*Completed: 2026-03-29*
