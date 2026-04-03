---
phase: 06-secrets-webhooks-infra-hardening
verified: 2026-04-03T14:24:02Z
status: gaps_found
score: 9/10 must-haves verified
gaps:
  - truth: "All four secret categories confirmed rotated (Brevo API key, MTA Ed25519 key pair, FRED API key, owner API key)"
    status: failed
    reason: "SEC-11 credential rotation was intentionally deferred per owner decision (2026-04-03 checkpoint). Keys are local-only and not on any remote, but the REQUIREMENTS.md requirement has not been satisfied and the checkbox remains unchecked."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "SEC-11 marked [ ] (pending) — rotation deferred, not completed"
    missing:
      - "Owner must rotate Brevo API key in Brevo dashboard and update production .env"
      - "Owner must generate new MTA Ed25519 key pair, update IRL Engine MACROPULSE_PUBKEY_HEX first, then MacroPulse MTA_SIGNING_KEY_HEX"
      - "Owner must request new FRED API key and update production .env"
      - "Owner must generate new OWNER_API_KEY and update production .env"
      - "REQUIREMENTS.md SEC-11 and SEC-10/SEC-12/SEC-13 checkboxes need to be marked [x] once complete"
human_verification:
  - test: "Verify success criterion #2 intent: start API with LS_WEBHOOK_SECRET unset and ENV=production, confirm it refuses to start (RuntimeError in logs, no webhook accepted)"
    expected: "App fails at startup with 'LS_WEBHOOK_SECRET must be set in production' error — no request reaches the LS webhook endpoint"
    why_human: "The ROADMAP says 'return 500 on every request' but the implementation is stricter: the app refuses to start entirely. The security intent is met but the exact HTTP code (500 vs. startup-abort) requires human judgment on whether this satisfies the success criterion"
  - test: "Confirm REQUIREMENTS.md is updated to mark SEC-10, SEC-12, SEC-13 as [x] (they are done in the codebase but still marked [ ])"
    expected: "SEC-10, SEC-12, SEC-13 checkboxes updated to [x]; SEC-11 remains [ ] pending rotation"
    why_human: "REQUIREMENTS.md status markers do not reflect the actual codebase state for SEC-10, SEC-12, SEC-13"
---

# Phase 6: Secrets, Webhooks, and Infrastructure Hardening — Verification Report

**Phase Goal:** The production environment contains no committed secrets and no webhook handler that can silently accept unauthenticated events
**Verified:** 2026-04-03T14:24:02Z
**Status:** gaps_found (1 gap — SEC-11 credential rotation deferred by owner decision)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                 | Status      | Evidence |
|----|---------------------------------------------------------------------------------------|-------------|----------|
| 1  | `git log --all -p -- .env` contains no Brevo, MTA, FRED, or owner API key values     | VERIFIED  | `git log --all -p -- .env | grep -E 'BREVO|MTA_SIGNING|FRED_API|OWNER_API_KEY'` returns empty; `.env` has 0 history entries |
| 2  | `.env` not tracked in git (`git ls-files .env` empty, in `.gitignore`)               | VERIFIED  | `git ls-files .env` = empty; `.gitignore` contains `.env` |
| 3  | `.env.example` documents `LS_WEBHOOK_SECRET`, `LS_VARIANT_ID_STARTER`, `LS_VARIANT_ID_PRO`, `ENV` | VERIFIED  | All 4 vars present with descriptive comments; no real values |
| 4  | `docs/DEPLOYMENT.md` exists with secret rotation procedures for all four credential types | VERIFIED  | File exists; documents Brevo, MTA Ed25519, FRED, Owner key rotation |
| 5  | All four secret categories rotated                                                    | FAILED    | SEC-11 deferred by owner — keys are local-only, rotation intentionally skipped |
| 6  | `LS_WEBHOOK_SECRET` unset causes LS webhook to reject events (no silent accept)      | VERIFIED  | In production: RuntimeError at startup (app never starts). In dev: returns 401 via fail-closed `_ls_verify_signature` |
| 7  | Tampered LS webhook HMAC signature returns 401; event handler never called            | VERIFIED  | `_ls_verify_signature` returns `False` on mismatch → HTTPException 401; confirmed by `test_ls_webhook_invalid_signature` (PASSED) |
| 8  | `model_artifacts` Docker volume mounted `:ro` in `docker-compose.yml`                | VERIFIED  | `docker-compose.yml` line 48: `model_artifacts:/app/models/artifacts:ro` |
| 9  | `nginx/nginx.conf` contains `Content-Security-Policy` header                         | VERIFIED  | Line 38: full CSP header with default-src, script-src, frame-ancestors 'none' |
| 10 | App refuses to start when `ENV=production` and `CORS_ORIGINS` contains `*`           | VERIFIED  | `_validate_cors_origins()` in lifespan raises RuntimeError; confirmed by `test_cors_wildcard_blocked_in_prod` (PASSED) |

**Score:** 9/10 truths verified (1 gap: SEC-11 credential rotation deferred)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.env.example` | Complete env var reference with LS_WEBHOOK_SECRET, ENV | VERIFIED | All required vars present; no real values |
| `docs/DEPLOYMENT.md` | Secret rotation and env injection guide | VERIFIED | Exists; documents all 4 credential rotation procedures |
| `api/routes/billing.py` | `_ls_verify_signature()` fails closed | VERIFIED | Returns `False` when secret absent; returns `False` on HMAC mismatch |
| `api/main.py` | `_validate_webhook_secrets()` and `_validate_cors_origins()` in lifespan | VERIFIED | Both functions defined and called in lifespan() after `init_signer()` |
| `config/settings.py` | `env: str` field with AliasChoices("ENV", "env") | VERIFIED | Line 98: `env: str = Field(default="development", validation_alias=AliasChoices("ENV", "env"))` |
| `docker-compose.yml` | `model_artifacts:/app/models/artifacts:ro` | VERIFIED | Line 48 confirmed |
| `nginx/nginx.conf` | `Content-Security-Policy` header in HTTPS server block | VERIFIED | Line 38 confirmed |
| `tests/test_billing.py` | 3 passing tests (SEC-20, SEC-21, SEC-22) | VERIFIED | All 3 PASSED in pytest run |
| `tests/test_security.py` | 1 passing test (SEC-42) | VERIFIED | PASSED in pytest run |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `api/main.py lifespan()` | `_validate_webhook_secrets()` | direct call after `init_signer()` | WIRED | Line 115: `_validate_webhook_secrets()   # SEC-20` |
| `api/main.py lifespan()` | `_validate_cors_origins()` | direct call after `_validate_webhook_secrets()` | WIRED | Line 116: `_validate_cors_origins()      # SEC-42` |
| `_validate_webhook_secrets()` | `config/settings.py Settings.env` | `get_settings().env` | WIRED | Line 78: `env = get_settings().env` |
| `_validate_cors_origins()` | `Settings.env` and `Settings.cors_origins` | `get_settings().env` and `.cors_origins` | WIRED | Lines 95-96 confirmed |
| `billing.py _ls_verify_signature()` | returns False when secret absent | early return `False` | WIRED | Lines 259-263 confirmed; no `return True` path when secret missing |
| `docker-compose.yml api.volumes` | `model_artifacts` volume | `:ro` suffix | WIRED | `model_artifacts:/app/models/artifacts:ro` confirmed |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SEC-10 | 06-01 | Secrets removed from git history via filter-repo; .env in .gitignore | SATISFIED | `git log --all --full-history -- .env` = 0 lines; `.gitignore` has `.env`; `git ls-files .env` = empty |
| SEC-11 | 06-01 | All previously committed secrets rotated | NOT SATISFIED | Intentionally deferred per owner decision 2026-04-03; keys are local-only, not on remote |
| SEC-12 | 06-01 | `.env.example` documents all required vars; no real values | SATISFIED | All required vars present with comments; no real values committed |
| SEC-13 | 06-01 | Secrets managed via env injection; deployment guide updated | SATISFIED | `docs/DEPLOYMENT.md` exists with full rotation procedures |
| SEC-20 | 06-02 | LS webhook rejects all events at startup if `LS_WEBHOOK_SECRET` not set | SATISFIED | `_validate_webhook_secrets()` raises RuntimeError in production when secret missing |
| SEC-21 | 06-02 | LS HMAC mismatch returns 401; no event processed | SATISFIED | `_ls_verify_signature` returns False → HTTPException 401; event handler not reached |
| SEC-22 | 06-02 | Paddle replay protection tested (timestamp outside 5-min window rejected) | SATISFIED | `test_paddle_replay_window` PASSED; `verify_webhook()` returns False for old timestamps |
| SEC-40 | 06-03 | `model_artifacts` volume mounted `:ro` in API container | SATISFIED | `docker-compose.yml` line 48 confirmed |
| SEC-41 | 06-03 | Nginx CSP header configured | SATISFIED | `nginx/nginx.conf` line 38 confirmed |
| SEC-42 | 06-03 | CORS wildcard blocked at startup in production | SATISFIED | `_validate_cors_origins()` raises RuntimeError; test PASSED |

**Note:** REQUIREMENTS.md checkboxes for SEC-10, SEC-12, SEC-13, SEC-20, SEC-21, SEC-22, SEC-40, SEC-41, SEC-42 remain marked `[ ]` even though the codebase satisfies them. Only SEC-11 is genuinely incomplete (rotation deferred). The REQUIREMENTS.md status table partially reflects this (SEC-20/21/22/40/41/42 marked "Complete") but the checkbox rows do not. This is a documentation consistency gap, not a code gap.

---

### Anti-Patterns Found

No anti-patterns found in the modified files. Specifically:

- No TODO/FIXME/placeholder comments in `api/main.py`, `api/routes/billing.py`, `config/settings.py`, `docker-compose.yml`, or `nginx/nginx.conf`
- No stub implementations (empty handlers, `return null`, `return {}`)
- No hardcoded secret values in any tracked file
- All test functions have real assertions (not `pytest.fail("not implemented")`)

---

### Test Suite Results

```
pytest tests/test_billing.py tests/test_security.py -v --tb=short

tests/test_billing.py::test_ls_webhook_missing_secret           PASSED
tests/test_billing.py::test_ls_webhook_invalid_signature        PASSED
tests/test_billing.py::test_paddle_replay_window                PASSED
tests/test_billing.py::test_paddle_checkout_creates_url         PASSED
tests/test_billing.py::test_paddle_webhook_subscription_activated  PASSED
tests/test_billing.py::test_paddle_webhook_subscription_cancelled  PASSED
tests/test_billing.py::test_paddle_webhook_invalid_signature    PASSED
tests/test_billing.py::test_paddle_webhook_idempotent           PASSED
tests/test_billing.py::test_paddle_portal_returns_url           PASSED
tests/test_security.py::test_cors_wildcard_blocked_in_prod      PASSED

10 passed in 10.44s
```

---

### Human Verification Required

#### 1. Success Criterion #2 — Semantic Gap

**Test:** Start the API with `ENV=production` and `LS_WEBHOOK_SECRET` unset. Check what happens.
**Expected per ROADMAP:** "Lemon Squeezy webhook endpoint returns 500 on every request — no event is processed"
**Actual behavior:** App refuses to start entirely with RuntimeError ("LS_WEBHOOK_SECRET must be set in production"). No request ever reaches the endpoint.
**Why human:** The security goal is fully met (no event is ever processed), but the exact mechanism differs from the ROADMAP wording. The implementation is stricter (startup abort vs. per-request 500). Owner should confirm this satisfies the intent of the success criterion.

#### 2. REQUIREMENTS.md Checkbox Consistency

**Test:** Review `.planning/REQUIREMENTS.md` lines 10-13 (SEC-10 through SEC-13).
**Expected:** SEC-10, SEC-12, SEC-13 should be `[x]` (done in codebase); SEC-11 should remain `[ ]` (rotation deferred).
**Why human:** REQUIREMENTS.md still shows all four as `[ ]` pending. The code satisfies SEC-10, SEC-12, and SEC-13. The checkboxes need a manual update to reflect reality.

---

### Gaps Summary

**One real gap:** SEC-11 (credential rotation) was intentionally deferred by the owner. The PLAN required rotating all four credential types after purging them from history. The owner determined the security risk was acceptable because the keys were local-only and never pushed to a remote repository. This is a deliberate owner decision, not a forgotten task.

The remaining 9/10 truths are fully verified in the codebase with passing tests and correct wiring. The phase goal — "no committed secrets and no webhook handler that can silently accept unauthenticated events" — is achieved for both clauses:
- No committed secrets: `.env` purged from all git history, not tracked, `.gitignore` enforced
- No silent-accept webhook: `_ls_verify_signature` fails closed; startup guard prevents production deployment without the secret

---

_Verified: 2026-04-03T14:24:02Z_
_Verifier: Claude (gsd-verifier)_
