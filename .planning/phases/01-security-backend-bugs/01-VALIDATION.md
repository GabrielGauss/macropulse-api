---
phase: 1
slug: security-backend-bugs
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-18
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — zero automated tests in codebase (known constraint) |
| **Config file** | none |
| **Quick run command** | `grep` / `python -c` spot checks (see per-task map below) |
| **Full suite command** | n/a |
| **Estimated runtime** | ~2 seconds per check |

Zero automated tests exist in this codebase (documented in PROJECT.md). All verifications are grep/static checks or Python syntax validation — no test runner is needed or installed.

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` verify command
- **After every plan wave:** Run the full verification block from each plan's `<verification>` section
- **Before `/gsd:verify-work`:** All verify commands must return expected output
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|------|------|------|-------------|-----------|-------------------|--------|
| Add missing env vars | 01-env-example-audit | 1 | SEC-01 | static | `grep "OWNER_API_KEY" .env.example` | ⬜ pending |
| Remove duplicate alert call | 01-pipeline-fixes | 1 | SEC-02 | static | `grep -c "alert_regime_change" data/pipelines/daily_pipeline.py` (expect 0) | ⬜ pending |
| Fix data-lag threshold | 01-pipeline-fixes | 1 | BUG-01 | static | `grep ">= 3" data/pipelines/daily_pipeline.py` | ⬜ pending |
| Add asyncio.Lock to anon counter | 01-rate-limit-race | 1 | SEC-03 | static + syntax | `grep "_anon_locks" api/middleware/rate_limit.py && python -c "import ast; ast.parse(open('api/middleware/rate_limit.py').read()); print('OK')"` | ⬜ pending |
| Snapshot _connections before broadcast | 01-websocket-disconnect | 1 | BUG-02 | static + syntax | `grep "list(_connections)" api/routes/websocket.py && python -c "import ast; ast.parse(open('api/routes/websocket.py').read()); print('OK')"` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None. All verifications use grep and Python's built-in `ast.parse()` — no test framework installation needed.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Single email received on regime change | SEC-02 | Requires live DB + email delivery | Trigger a test pipeline run with a mocked regime change; confirm exactly one email arrives per subscriber |
| Rate limit holds under concurrent load | SEC-03 | Requires concurrent HTTP clients | Use `ab -n 100 -c 10` against the API with an unauthenticated IP; confirm counter doesn't exceed configured limit |
| WS broadcast continues after client disconnect | BUG-02 | Requires live WebSocket connections | Connect 3 WS clients; disconnect one mid-broadcast; confirm the other 2 receive the message |

---

## Full Verification Commands (run after Wave 1 completes)

```bash
# SEC-01: OWNER_API_KEY documented in .env.example
grep "OWNER_API_KEY" .env.example

# SEC-01: ANTHROPIC_API_KEY documented
grep "ANTHROPIC_API_KEY" .env.example

# SEC-02: alert_regime_change not called for regime change (expect 0 lines)
grep -c "alert_regime_change" data/pipelines/daily_pipeline.py

# SEC-02: send_regime_change_alerts still present
grep "send_regime_change_alerts" data/pipelines/daily_pipeline.py

# SEC-02: drift alerts untouched
grep "alert_drift_warning" data/pipelines/daily_pipeline.py

# BUG-01: data-lag uses >= 3
grep ">= 3" data/pipelines/daily_pipeline.py

# SEC-03: asyncio.Lock present
grep "_anon_locks" api/middleware/rate_limit.py
grep "asyncio.Lock" api/middleware/rate_limit.py
python -c "import ast; ast.parse(open('api/middleware/rate_limit.py').read()); print('syntax OK')"

# BUG-02: set snapshot present
grep "list(_connections)" api/routes/websocket.py
python -c "import ast; ast.parse(open('api/routes/websocket.py').read()); print('syntax OK')"
```

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: each task has immediate feedback (grep/ast.parse)
- [x] Wave 0: not needed (no test framework required)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
