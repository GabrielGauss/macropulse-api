---
phase: 6
slug: secrets-webhooks-infra-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pytest.ini` |
| **Quick run command** | `cd api && pytest tests/test_billing.py tests/test_security.py -v --tb=short -x` |
| **Full suite command** | `cd api && pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd api && pytest tests/test_billing.py tests/test_security.py -v --tb=short -x`
- **After every plan wave:** Run `cd api && pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 1 | SEC-10 | git scan | `git log --all --oneline \| head -5` | ✅ | ⬜ pending |
| 6-01-02 | 01 | 1 | SEC-11 | manual | Key rotation confirmation | N/A | ⬜ pending |
| 6-01-03 | 01 | 1 | SEC-12 | file check | `grep -c "MISSING\|TODO\|PLACEHOLDER" .env.example` | ✅ | ⬜ pending |
| 6-01-04 | 01 | 1 | SEC-13 | doc review | `cat docs/deployment.md \| grep secrets` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | SEC-20 | unit | `pytest tests/test_billing.py::test_ls_webhook_missing_secret -v` | ❌ W0 | ⬜ pending |
| 6-02-02 | 02 | 1 | SEC-21 | unit | `pytest tests/test_billing.py::test_ls_webhook_invalid_signature -v` | ❌ W0 | ⬜ pending |
| 6-02-03 | 02 | 1 | SEC-22 | unit | `pytest tests/test_billing.py::test_paddle_replay_window -v` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 2 | SEC-40 | manual | `docker exec macropulse-api touch /app/model_artifacts/test.txt 2>&1` | N/A | ⬜ pending |
| 6-03-02 | 03 | 2 | SEC-41 | integration | `curl -s -I https://macropulse.live \| grep content-security` | N/A | ⬜ pending |
| 6-03-03 | 03 | 2 | SEC-42 | unit | `pytest tests/test_security.py::test_cors_wildcard_blocked_in_prod -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_billing.py` — stubs for SEC-20, SEC-21, SEC-22 (LS webhook tests)
- [ ] `tests/test_security.py` — stubs for SEC-42 (CORS wildcard startup guard)
- [ ] Both files must import `fastapi.testclient.TestClient` and `app` from `api.main`

*Existing infrastructure: pytest installed, `tests/conftest.py` exists with fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Git history contains no committed secrets | SEC-10 | Requires `git filter-repo` run on local clone; CI cannot verify history purge automatically | Run `git log --all -p -- .env \| grep -E 'BREVO\|MTA_SIGNING\|FRED_API'` — must return empty |
| All secrets rotated | SEC-11 | Rotation requires out-of-band action in provider dashboards (Brevo, IRL Engine) | Confirm new BREVO key functional, new MTA public key deployed to IRL Engine |
| `model_artifacts` write rejected | SEC-40 | Requires running Docker container | `docker exec macropulse-api touch /app/model_artifacts/test.txt` must fail with "Read-only file system" |
| CSP header visible on production | SEC-41 | Requires deployed nginx config | `curl -I https://macropulse.live` must include `Content-Security-Policy` header |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING (❌ W0) references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
