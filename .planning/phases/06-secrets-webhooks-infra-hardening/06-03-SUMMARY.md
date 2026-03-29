---
plan: "06-03"
status: complete
completed: 2026-03-28
requirements: SEC-40, SEC-41, SEC-42
---

# Plan 06-03 — Summary

## What was built

**Task 1: Read-only model artifacts volume + CSP header**
- `docker-compose.yml`: `model_artifacts:/app/models/artifacts:ro` — API container can no longer write to the volume. A successful RCE exploit cannot overwrite model files to inject false trading signals. Added retraining path comment for ops clarity.
- `nginx/nginx.conf`: `Content-Security-Policy` header added to HTTPS server block with strict directives: `default-src 'self'`, `frame-ancestors 'none'` (clickjacking prevention), `connect-src` restricted to macropulse.live origins and WebSocket. Future Paddle iframe noted.

**Task 2: CORS wildcard startup guard**
- `api/main.py`: `_validate_cors_origins()` raises `RuntimeError` at startup when `ENV=production` and `CORS_ORIGINS` contains `*`. Warning-only in development. Called in `lifespan()` after `_validate_webhook_secrets()`.
- `tests/test_security.py`: xfail stub replaced with real assertion — verifies both the production raise and the development pass-through. **1 PASSED**.

## Commits
- `19c25b4`: feat(06-03): add :ro volume mount and CSP header (SEC-40, SEC-41)
- `506b2c9`: feat(06-03): add CORS wildcard startup guard + security test (SEC-42)

## Verification
```
pytest tests/test_billing.py tests/test_security.py -v → 4 passed
grep "model_artifacts.*:ro" docker-compose.yml → OK
grep "Content-Security-Policy" nginx/nginx.conf → OK
```

## Requirements covered
- SEC-40 ✓ — model_artifacts:ro prevents model substitution
- SEC-41 ✓ — CSP header in nginx HTTPS block
- SEC-42 ✓ — CORS wildcard blocked at startup in production
