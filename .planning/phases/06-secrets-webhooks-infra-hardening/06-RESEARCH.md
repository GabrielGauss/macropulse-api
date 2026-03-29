# Phase 6: Secrets, Webhooks, and Infrastructure Hardening — Research

**Researched:** 2026-03-29
**Domain:** Git history rewriting, webhook HMAC hardening, Docker security, Nginx CSP, FastAPI startup validation
**Confidence:** HIGH (all findings verified against official documentation or direct codebase inspection)

---

## Summary

Phase 6 addresses the three highest-severity security issues in MacroPulse: live secrets committed to git history, a webhook handler that silently accepts unauthenticated events, and infrastructure misconfigurations that allow model substitution and missing HTTP security headers.

The git history rewrite (SEC-10) is the most operationally disruptive task. `git filter-repo` is the current standard tool — it is faster and safer than the deprecated `git filter-branch`. Because the repository is currently not a remote-tracking repo (per env metadata), the force-push coordination concern is limited to Gabriel's own machines, but the MTA Ed25519 key rotation requires coordinating the new public key with the IRL Engine service, which holds the public key for MTA signature verification.

The Lemon Squeezy webhook vulnerability (SEC-20, SEC-21) is a one-function fix: the `_ls_verify_signature` function in `api/routes/billing.py` (line 257–263) must fail closed when `LS_WEBHOOK_SECRET` is absent. A startup guard in `api/main.py`'s lifespan function is the correct place for the environment check, consistent with how `init_signer(settings.mta_signing_key_hex)` already raises at startup if the MTA key is invalid.

The infrastructure hardening tasks (SEC-40, SEC-41, SEC-42) are isolated, low-risk changes: one flag in `docker-compose.yml`, one `add_header` directive in `nginx/nginx.conf`, and one startup assertion in `api/main.py`.

**Primary recommendation:** Execute in order — SEC-10/11/12/13 first (secrets purge), then SEC-20/21/22 (webhook hardening), then SEC-40/41/42 (infra). This ordering ensures secrets are out of history before any code is pushed to fix the other issues, preventing a repeat commit of sensitive data.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEC-10 | All secrets removed from git history via `git filter-repo`; `.env` added to `.gitignore` | git filter-repo is the canonical tool; `.env` already in `.gitignore` but the tracked file object must be purged from history |
| SEC-11 | All previously committed secrets rotated: new Brevo API key, new MTA Ed25519 key pair, new owner API key | Rotation commands documented; MTA key requires coordinating new public key with IRL Engine |
| SEC-12 | `.env.example` documents every required env var with description and format; no real values | `.env.example` already exists but is missing `LS_WEBHOOK_SECRET`, `LS_VARIANT_ID_STARTER`, `LS_VARIANT_ID_PRO`, and `ENV` variable; needs audit |
| SEC-13 | Production secrets managed via environment injection (not committed files); deployment guide updated | Docker Compose `env_file: .env` pattern is correct; deployment guide must document how to provision `.env` on server |
| SEC-20 | LS webhook rejects all events and returns 500 at startup if `LS_WEBHOOK_SECRET` is not set | Startup guard in `lifespan()` context manager; consistent with existing `init_signer()` pattern |
| SEC-21 | LS webhook signature verification fails closed: any HMAC mismatch → 401, request logged, no event processed | Already implemented for mismatch case; the gap is only the missing-secret branch |
| SEC-22 | Paddle webhook logs and rejects events with timestamp outside 5-minute replay window (existing guard verified and tested) | `services/paddle.py verify_webhook()` already implements replay protection; task is to verify and document, not rewrite |
| SEC-40 | `model_artifacts` Docker volume mounted read-only in the API container | One-line change: `model_artifacts:/app/models/artifacts:ro` in `docker-compose.yml` line 45 |
| SEC-41 | Nginx CSP header configured: blocks inline scripts, restricts sources to macropulse.live origin | `add_header Content-Security-Policy "..."` in `nginx/nginx.conf`; existing security headers section at line 34 |
| SEC-42 | `CORS_ORIGINS` validated at startup — app refuses to start if wildcard `*` is set in production (`ENV=production`) | Startup assertion in `lifespan()` function; requires new `ENV` setting in `Settings` class |
</phase_requirements>

---

## Standard Stack

### Core — Already Present in Codebase
| Tool/Library | Version/Source | Purpose | Confidence |
|---|---|---|---|
| `git filter-repo` | Install via `pip install git-filter-repo` | Purge secrets from git history | HIGH — official Git project recommendation |
| `hmac` (stdlib) | Python 3.12 stdlib | HMAC-SHA256 for LS webhook verification | HIGH — already used in `billing.py` line 262 |
| `fastapi` lifespan | Already in `api/main.py` | Startup guards for missing secrets | HIGH — pattern already used for `init_signer()` |
| `pydantic-settings` | Already in `config/settings.py` | Add `ENV` field for production detection | HIGH — already the config mechanism |

### No New Dependencies Required
All ten requirements in Phase 6 are achievable with existing installed packages and standard tooling. No new `pip install` needed.

---

## Architecture Patterns

### Pattern 1: Startup Fail-Fast Guard (SEC-20, SEC-42)

The codebase already uses this pattern in `api/main.py` `lifespan()`:

```python
# api/main.py — lifespan() — existing pattern
init_signer(settings.mta_signing_key_hex)  # raises ValueError if key is invalid
```

SEC-20 and SEC-42 follow the same approach — add validation calls early in `lifespan()` so the app refuses to start with an insecure configuration.

**For SEC-20 (LS webhook secret):**
```python
# In lifespan(), after init_signer()
_validate_webhook_secrets()  # new function — raises RuntimeError if LS_WEBHOOK_SECRET unset
```

**For SEC-42 (CORS wildcard):**
```python
# In lifespan(), after _validate_webhook_secrets()
_validate_cors_origins()  # raises RuntimeError if ENV=production and "*" in cors_origins
```

The fail-fast location is the lifespan context manager — not a module-level check — because `get_settings()` is cached and must be called after the environment is loaded.

### Pattern 2: Webhook HMAC Fail-Closed (SEC-20, SEC-21)

Current buggy behavior in `api/routes/billing.py`:

```python
def _ls_verify_signature(raw_body: bytes, signature: str) -> bool:
    secret = os.getenv("LS_WEBHOOK_SECRET", "").strip()
    if not secret:
        logger.warning("LS_WEBHOOK_SECRET not set — skipping signature check")
        return True   # BUG: silently accepts all events
    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
```

Fix: remove the `return True` branch. The missing-secret condition becomes unreachable at runtime because the startup guard (SEC-20) prevents the app from starting without `LS_WEBHOOK_SECRET`. The function body simplifies to pure HMAC comparison.

**Note:** The Paddle webhook handler (`services/paddle.py verify_webhook()`) already implements correct fail-closed behavior and has replay protection. SEC-22 is a verification task, not a rewrite.

### Pattern 3: Docker Volume Read-Only Mount (SEC-40)

Single-character change in `docker-compose.yml`:

```yaml
# Before (line 45):
- model_artifacts:/app/models/artifacts

# After:
- model_artifacts:/app/models/artifacts:ro
```

**Consequence to document:** The pipeline retraining process writes to `/app/models/artifacts`. With `:ro` on the API container, retraining must either run in a separate container (correct long-term) or temporarily remount. For v1.1, the pipeline runs inside the same API container (via APScheduler). This creates a conflict.

**Resolution:** The `:ro` mount makes sense for the API container ONLY IF retraining is separated from serving. Current architecture has both in the same container. The correct v1.1 approach is to keep the volume writable for the API container but document the risk, OR accept that retraining must use a separate `docker-compose run` command against the volume directly. Given the SEC-40 requirement text states the API container should be `:ro`, the plan must explicitly address what happens to the daily retraining path.

**Options for the planner:**
1. Add `:ro` flag AND move retraining to a one-off container invocation (breaks in-process APScheduler retraining)
2. Add `:ro` flag AND disable in-process retraining (make it a manual `docker-compose run` step)
3. Add `:ro` flag with a note that retraining requires a separate container — acceptable because retraining is infrequent

Option 3 is the lowest-risk v1.1 approach: add the flag, document that `docker-compose run api python -m data.pipelines.retrain` is the retraining path.

### Pattern 4: Nginx CSP Header (SEC-41)

Existing security headers in `nginx/nginx.conf` (lines 34–36):
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options    nosniff always;
add_header X-Frame-Options           SAMEORIGIN always;
```

Add CSP in the same block:
```nginx
add_header Content-Security-Policy "default-src 'self' https://macropulse.live; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' wss://api.macropulse.live; frame-ancestors 'none'" always;
```

MacroPulse is a React SPA with no inline scripts (Vite builds to hashed bundles). `unsafe-inline` for styles is typically needed by React component libraries. The `connect-src` must include `wss://` for WebSocket at `/ws/regime`. Paddle Checkout embeds may need additional `frame-src` allowance when billing integration is active (Phase 10) — the planner should note this as a future concern.

### Pattern 5: git filter-repo Workflow (SEC-10)

```bash
# 1. Install
pip install git-filter-repo

# 2. Purge .env from all history
git filter-repo --path .env --invert-paths --force

# 3. Verify .env is gone
git log --all --full-history -- .env   # should return nothing

# 4. Force-push all branches and tags (if remote exists)
git push --force --all
git push --force --tags
```

**Critical side effects:**
- All commit SHAs change — any existing clones will diverge
- Because this is a single-developer project (per project profile), the "team re-clone" concern is just Gabriel's other machines
- The deployment server will need `git fetch --all && git reset --hard origin/main` after the force-push

**`.gitignore` audit:** `.env` is already in `.gitignore` (line 4). However, the file was tracked before the gitignore entry took effect, which is why it persists in history. After `filter-repo`, `.env` will never appear in `git status` again.

---

## What Needs to Be Built vs. What Already Exists

| Requirement | Existing Code | What Needs Changing |
|---|---|---|
| SEC-10: Purge .env from history | `.env` in `.gitignore` | Run `git filter-repo`; update deployment docs |
| SEC-11: Rotate all secrets | — | External: rotate Brevo key, generate new Ed25519 pair, regenerate OWNER_API_KEY; coordinate MTA pubkey with IRL Engine |
| SEC-12: `.env.example` audit | `.env.example` exists (104 lines) | Add missing vars: `LS_WEBHOOK_SECRET`, `LS_VARIANT_ID_STARTER`, `LS_VARIANT_ID_PRO`, `ENV` |
| SEC-13: Deployment guide | No dedicated deployment guide found | Create `DEPLOYMENT.md` or update existing docs with env injection instructions |
| SEC-20: LS startup guard | `lifespan()` in `main.py` | Add `_validate_webhook_secrets()` call in `lifespan()` |
| SEC-21: LS fail-closed fix | `_ls_verify_signature()` in `billing.py` | Remove the `return True` branch from missing-secret case |
| SEC-22: Paddle replay protection | `services/paddle.py verify_webhook()` | Verify and add a test — code change unlikely needed |
| SEC-40: Volume read-only | `docker-compose.yml` line 45 | Add `:ro` suffix; document retraining impact |
| SEC-41: CSP header | `nginx/nginx.conf` lines 34–36 | Add `Content-Security-Policy` header |
| SEC-42: CORS startup guard | `config/settings.py` | Add `env: str = "development"` field; add `_validate_cors_origins()` in `lifespan()` |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Purging secrets from git | Manual blob deletion | `git filter-repo` | Handles all refs, tags, reflogs; BFG alternative also acceptable |
| HMAC comparison | Custom string equality | `hmac.compare_digest()` | Prevents timing attacks; already used in billing.py |
| Ed25519 key generation | Custom crypto | `cryptography` stdlib (already installed) | Already documented in `.env.example` and `settings.py` comment |
| CSP policy generation | Trial and error | Use the existing header pattern in nginx.conf | Existing headers show the pattern; extend, don't rewrite |

---

## Common Pitfalls

### Pitfall 1: `git filter-repo` Changes All Commit SHAs
**What goes wrong:** After running `filter-repo`, the local repo history diverges from any remote. If a force-push is done against a production server's tracked branch, the server's `git pull` will fail with "refusing to merge unrelated histories."
**Why it happens:** `filter-repo` rewrites the entire DAG, changing every commit object.
**How to avoid:** On the production server, use `git fetch --all && git reset --hard origin/main` after the force-push. Document this in the deployment guide.
**Warning signs:** `git status` shows "branch diverged" on any machine that had an old clone.

### Pitfall 2: Rotating MTA Ed25519 Key Breaks IRL Engine
**What goes wrong:** IRL Engine holds MacroPulse's Ed25519 PUBLIC key in its own `.env` as `MACROPULSE_PUBKEY_HEX`. When the private key is rotated (SEC-11), the IRL Engine will reject all regime signatures until its public key is updated.
**Why it happens:** The key pair is asymmetric — the verifier holds the public key independently.
**How to avoid:** Generate new key pair first, update IRL Engine's `MACROPULSE_PUBKEY_HEX` before deploying the new MacroPulse private key. Deploy both atomically, or accept a brief window where regime signatures are invalid.
**Warning signs:** IRL Engine returns signature verification errors after MacroPulse redeploys.

### Pitfall 3: CSP Header Breaks Paddle Checkout (Future Phase 10)
**What goes wrong:** The Paddle hosted checkout uses an iframe. A strict `frame-src 'none'` or no `frame-src` directive in the CSP will block the checkout overlay.
**Why it happens:** Paddle Billing's checkout embeds an iframe from `checkout.paddle.com`.
**How to avoid:** Either leave `frame-src` absent from the CSP now (it defaults to `default-src 'self'`, which will block Paddle) or add `frame-src https://checkout.paddle.com` proactively.
**Warning signs:** Paddle checkout overlay fails to render; browser console shows CSP violation.

### Pitfall 4: `:ro` Volume Breaks In-Process Model Retraining
**What goes wrong:** APScheduler inside the API container triggers the retraining pipeline, which writes to `/app/models/artifacts`. With `:ro`, this write raises `PermissionError`.
**Why it happens:** The API container can no longer write to the mounted volume.
**How to avoid:** Document that retraining must be run as a separate one-off container: `docker-compose run --rm api python -m data.pipelines.retrain`. The daily APScheduler job should only run inference, not retraining. Review whether `services/scheduler.py` invokes retraining — if so, that code path must be conditional on the volume being writable, or the retraining scheduler must be removed from the API container.
**Warning signs:** `PermissionError` or `OSError` in logs when pipeline attempts to save artifacts.

### Pitfall 5: `LS_WEBHOOK_SECRET` Missing Causes API Startup Failure in Dev
**What goes wrong:** The startup guard for SEC-20 will prevent the API from starting in development environments where `LS_WEBHOOK_SECRET` is not set in `.env`.
**Why it happens:** Startup guards are intentionally strict.
**How to avoid:** The guard should only enforce in `ENV=production`. In `ENV=development`, log a warning instead of raising. This is consistent with how the existing code handles `BREVO_API_KEY` (optional, fails silently in dev).
**Warning signs:** Local dev environment fails to start with `RuntimeError: LS_WEBHOOK_SECRET not set`.

### Pitfall 6: `.env.example` Missing LS Variables
**What goes wrong:** A new deployer follows `.env.example` exactly but has no `LS_WEBHOOK_SECRET`, `LS_VARIANT_ID_STARTER`, `LS_VARIANT_ID_PRO` entries because they are not in the current `.env.example`. After the startup guard lands, the app will fail to start.
**Why it happens:** These variables are read via `os.getenv()` directly in `billing.py`, bypassing the `Settings` class, so they are not auto-documented.
**How to avoid:** SEC-12 must add all three LS variables to `.env.example`. Also add `ENV=development` to make the production/dev distinction explicit.

---

## Code Examples

### Startup Guard Pattern (SEC-20, SEC-42)

```python
# api/main.py — add to lifespan(), after init_signer()

def _validate_webhook_secrets() -> None:
    """Raise at startup if LS_WEBHOOK_SECRET is not set in production."""
    import os
    env = get_settings().env  # new field: Settings.env: str = "development"
    secret = os.getenv("LS_WEBHOOK_SECRET", "").strip()
    if not secret:
        if env == "production":
            raise RuntimeError(
                "LS_WEBHOOK_SECRET must be set in production. "
                "Set it in .env or via environment injection."
            )
        else:
            logger.warning(
                "LS_WEBHOOK_SECRET not set — Lemon Squeezy webhook validation disabled. "
                "Set this before deploying to production."
            )


def _validate_cors_origins() -> None:
    """Raise at startup if CORS wildcard is configured in production."""
    settings = get_settings()
    if settings.env == "production" and "*" in settings.cors_origins:
        raise RuntimeError(
            "CORS wildcard '*' is not allowed in production. "
            "Set CORS_ORIGINS to explicit allowed origins in .env."
        )
```

### LS Webhook Fail-Closed Fix (SEC-21)

```python
# api/routes/billing.py — replace _ls_verify_signature()

def _ls_verify_signature(raw_body: bytes, signature: str) -> bool:
    """Verify Lemon Squeezy HMAC-SHA256 signature. Fails closed if secret missing."""
    import os
    secret = os.getenv("LS_WEBHOOK_SECRET", "").strip()
    if not secret:
        # Startup guard (SEC-20) prevents reaching here in production.
        # In dev, treat as failed verification (not silent accept).
        logger.error("LS_WEBHOOK_SECRET not set — rejecting webhook event")
        return False
    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
```

Note: `hmac.new` in the original code is actually `hmac.new` — this should be `hmac.new(key, msg, digestmod)`. The stdlib function is `hmac.new()`. Verify the exact call matches stdlib signature (`hmac.new(key: bytes, msg: bytes, digestmod) -> HMAC`).

### Settings.env Field (SEC-42)

```python
# config/settings.py — add to Settings class

# ── Deployment environment ───────────────────────────────────────
env: str = Field(default="development", validation_alias=AliasChoices("ENV", "env"))
```

This follows the existing `Field(validation_alias=AliasChoices(...))` pattern already used throughout `settings.py`.

### Docker Compose Volume Fix (SEC-40)

```yaml
# docker-compose.yml — api service volumes section

volumes:
  - model_artifacts:/app/models/artifacts:ro   # read-only: prevents model substitution via API compromise
```

### Nginx CSP Header (SEC-41)

```nginx
# nginx/nginx.conf — add to existing security headers block

add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' wss://api.macropulse.live https://api.macropulse.live; font-src 'self'; frame-ancestors 'none'; base-uri 'self'" always;
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|---|---|---|
| `git filter-branch` (deprecated) | `git filter-repo` | `filter-repo` is 10-100x faster; officially recommended by Git project since 2019 |
| BFG Repo Cleaner (Java, separate tool) | `git filter-repo` (Python, pip-installable) | Either works; `filter-repo` is the Git project's own recommendation |
| Hardcoded secret fallback to `True` | Startup guard + fail closed | Eliminates entire class of misconfiguration vulnerability |

**Deprecated/outdated:**
- `git filter-branch`: Deprecated by Git project. Do not use. `git filter-repo` is the replacement.
- `hmac.new()`: The stdlib function name is correct. The `hashlib.sha256` digestmod argument is correct. No deprecation here — just verify the call site in `billing.py` line 262 uses the right argument order.

---

## Open Questions

1. **Does the daily APScheduler pipeline trigger model retraining (not just inference)?**
   - What we know: `services/scheduler.py` triggers the daily pipeline. The pipeline in `data/pipelines/daily_pipeline.py` is known to write HMM/PCA artifacts during training.
   - What's unclear: Whether the daily scheduled run RETRAINS or only INFERS using existing artifacts.
   - Recommendation: Read `services/scheduler.py` and `data/pipelines/daily_pipeline.py` to determine if `save()` is called during the nightly run. If yes, `:ro` will break the daily pipeline and the task plan must address this explicitly.

2. **Does the repository have a remote (GitHub/GitLab)?**
   - What we know: The env metadata shows "Is directory a git repo: No" — the project directory itself may not be a tracked repo at the current working directory.
   - What's unclear: Whether there is a remote that needs force-push coordination after `filter-repo`.
   - Recommendation: The planner should include a step to check `git remote -v` before the filter-repo task.

3. **What is the current `.env` file content in production?**
   - What we know: The `.env` file contains live `BREVO_API_KEY` and `MTA_SIGNING_KEY_HEX` values based on CONCERNS.md.
   - What's unclear: Whether these keys have already been used in production requests and whether rotating them will break any live sessions.
   - Recommendation: Rotation is always safe for API keys (old key stops working, new key issued). For MTA Ed25519, plan a coordinated rotation with IRL Engine.

---

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | pytest 9.0.2 |
| Config file | `tests/conftest.py` (fixtures); no `pytest.ini` detected — runs via `pytest` from project root |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map

| ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| SEC-20 | API startup raises RuntimeError if `LS_WEBHOOK_SECRET` unset and `ENV=production` | unit | `pytest tests/test_webhook_hardening.py::test_ls_startup_guard -x` | Wave 0 |
| SEC-21 | LS webhook returns 401 on HMAC mismatch; returns 500 if secret missing in production | unit | `pytest tests/test_webhook_hardening.py::test_ls_signature_verification -x` | Wave 0 |
| SEC-22 | Paddle webhook rejects events with timestamp > 5 minutes old | unit | `pytest tests/test_webhook_hardening.py::test_paddle_replay_protection -x` | Wave 0 |
| SEC-42 | API startup raises RuntimeError if `ENV=production` and `CORS_ORIGINS=["*"]` | unit | `pytest tests/test_startup_guards.py::test_cors_wildcard_rejected -x` | Wave 0 |
| SEC-10 | `.env` absent from git log after filter-repo | manual | `git log --all --full-history -- .env` returns no output | N/A — git operation |
| SEC-11 | Secrets rotated | manual | Verify new keys work in external services | N/A — external |
| SEC-12 | `.env.example` contains all required vars | manual/review | Diff `.env.example` against `Settings` fields and `os.getenv()` calls in `billing.py` | N/A — file review |
| SEC-40 | Volume mount is `:ro` in `docker-compose.yml` | manual | `grep 'model_artifacts' docker-compose.yml` | N/A — config review |
| SEC-41 | CSP header present in nginx response | integration | `curl -sI https://api.macropulse.live | grep -i content-security` | N/A — live check |
| SEC-13 | Deployment guide updated | manual/review | Review `DEPLOYMENT.md` | N/A — doc review |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before verify-work

### Wave 0 Gaps
- [ ] `tests/test_webhook_hardening.py` — covers SEC-20, SEC-21, SEC-22
- [ ] `tests/test_startup_guards.py` — covers SEC-42

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `api/routes/billing.py`, `api/main.py`, `docker-compose.yml`, `nginx/nginx.conf`, `config/settings.py`, `.env.example`, `.gitignore`
- `.planning/REQUIREMENTS.md` — authoritative requirement definitions for SEC-10 through SEC-42
- `.planning/codebase/CONCERNS.md` — root cause analysis of each vulnerability

### Secondary (MEDIUM confidence)
- git-filter-repo official documentation (https://github.com/newren/git-filter-repo) — confirmed as the Git project's recommended replacement for `git filter-branch`
- Python stdlib `hmac` module documentation — `hmac.compare_digest()` is the correct constant-time comparison function
- Mozilla MDN Content-Security-Policy documentation — CSP directive syntax and browser support

### Tertiary (LOW confidence — not required, patterns are standard)
- Nginx CSP header patterns from community references — standard `add_header` directive syntax

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already in the codebase; no new dependencies
- Architecture: HIGH — all patterns derived from direct code inspection; no speculation
- Pitfalls: HIGH for items 1, 2, 4 (derived from code); MEDIUM for item 3 (Paddle CSP — Paddle docs not fetched, but iframe embed is well-known behavior)

**Research date:** 2026-03-29
**Valid until:** 2026-05-01 (stable domain — git filter-repo, Python stdlib hmac, Docker Compose syntax are not fast-moving)
