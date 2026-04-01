---
phase: 09-prometheus-metrics
plan: "01"
subsystem: observability
tags: [prometheus, alerting, staleness, brevo, tests, requirements]
dependency_graph:
  requires: [api/metrics.py, services/scheduler.py, services/email.py, database/queries.py]
  provides: [alerts/pipeline_alerts.yml, tests/test_metrics.py, staleness check job]
  affects: [services/scheduler.py, api/metrics.py, .planning/REQUIREMENTS.md]
tech_stack:
  added: []
  patterns: [asyncio.run() in BackgroundScheduler thread, _get_or_create_* reload-safe metric helpers, ASGI test client with mocked lifespan]
key_files:
  created:
    - alerts/pipeline_alerts.yml
    - tests/test_metrics.py
  modified:
    - services/scheduler.py
    - api/metrics.py
    - .planning/REQUIREMENTS.md
decisions:
  - "Used asyncio.run() inside BackgroundScheduler job for staleness check — BackgroundScheduler runs jobs in threads (no running event loop), so asyncio.run() is the correct pattern"
  - "Made api/metrics.py reload-safe with _get_or_create_* helpers that check REGISTRY._names_to_collectors before registering — prevents ValueError on importlib.reload() in tests"
  - "Test lifespan mocking: patch all lifespan side-effects (init_pool, close_pool, migrations, scheduler, security guards) rather than disabling lifespan — preserves app structure while keeping tests isolated"
  - "Staleness check queries fetch_latest_pipeline_run() which returns the most recent row regardless of status, then filters for status='success' — avoids needing a separate DB query"
metrics:
  duration: ~12min
  completed: "2026-04-01T00:00:00Z"
  tasks_completed: 4
  files_modified: 5
---

# Phase 9 Plan 01: OBS-04 Staleness Alerting + Tests + OBS Requirements Complete Summary

Staleness alerting job added to scheduler (30-min interval, Brevo email when last successful run is >26h old), Prometheus alerting rules YAML created, metrics endpoint tests written and passing, OBS-01 through OBS-04 marked complete in REQUIREMENTS.md.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | OBS-04 staleness alerting job | 651f6c0 | services/scheduler.py |
| 2 | Prometheus alerting rules YAML | 651f6c0 | alerts/pipeline_alerts.yml |
| 3 | Tests for metrics endpoint | 651f6c0 | tests/test_metrics.py, api/metrics.py |
| 4 | Mark OBS-01 through OBS-04 complete | 651f6c0 | .planning/REQUIREMENTS.md |

## What Was Built

### Staleness Alerting Job (Task 1)

`services/scheduler.py` — new `_check_pipeline_staleness()` job:

- Runs every 30 minutes via `IntervalTrigger(minutes=30)`, job ID `pipeline_staleness_check`
- Calls `asyncio.run(_fetch_last_successful_run_ts())` — uses async DB query inside BackgroundScheduler's thread context
- `_fetch_last_successful_run_ts()` queries `fetch_latest_pipeline_run()`, filters for `status='success'`, normalises `run_ts` to naive UTC datetime
- If age > 26 hours (`_STALENESS_THRESHOLD_HOURS = 26`), sends Brevo email to `settings.pipeline_alert_email` via `services.email.send_email()`
- Full exception guard: DB errors, email errors, and None/no-runs cases all handled gracefully without crashing the scheduler

### Prometheus Alerting Rules (Task 2)

`alerts/pipeline_alerts.yml` — two Prometheus alerting rules:

| Alert | Expression | For | Severity |
|-------|-----------|-----|---------|
| `PipelineNotRunRecently` | `time() - macropulse_pipeline_last_success_timestamp > 93600` | 5m | warning |
| `PipelineHighFailureRate` | `rate(macropulse_pipeline_runs_total{status="failure"}[1h]) > 0.5` | 10m | critical |

### Metrics Tests (Task 3)

`tests/test_metrics.py` — 3 tests:

- `test_metrics_endpoint_returns_200`: patches all lifespan side-effects, hits `GET /metrics/` via AsyncClient+ASGITransport, verifies 200 + `text/plain` content-type
- `test_metrics_contains_pipeline_counter`: increments `PIPELINE_RUNS_TOTAL.labels(status="success")`, then checks `/metrics/` body contains `macropulse_pipeline_runs_total`
- `test_metrics_module_no_duplicate_registration`: calls `importlib.reload(api.metrics)` and asserts no `ValueError` is raised

All 3 tests pass. Broader suite (test_metrics + test_security + test_billing) — 7/7 pass.

### OBS Requirements Completion (Task 4)

Marked `[x]` in `.planning/REQUIREMENTS.md`:
- OBS-01: `/metrics` endpoint — Complete (09-00)
- OBS-02: Key metrics exposed — Complete (09-00)
- OBS-03: Pipeline failure alerting — Complete (09-00)
- OBS-04: Pipeline staleness alert — Complete (09-01)

Traceability table updated with phase/plan references for all four.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] api/metrics.py raised ValueError on importlib.reload()**
- **Found during:** Task 3 (test design)
- **Issue:** The plan's test `test_metrics_module_no_duplicate_registration` calls `importlib.reload(api.metrics)`. The original module-level `Counter(...)` / `Gauge(...)` / `Histogram(...)` calls unconditionally register new collectors, raising `ValueError: Duplicated timeseries` when the same name already exists in the Prometheus REGISTRY.
- **Fix:** Replaced direct metric constructors with `_get_or_create_counter/histogram/gauge` helpers that check `REGISTRY._names_to_collectors` before creating. If the name is already registered, returns the existing collector. Reload-safe and hot-reload-safe.
- **Files modified:** api/metrics.py
- **Commit:** 651f6c0

**2. [Rule 1 - Bug] fetch_latest_pipeline_run() returns most recent row regardless of status**
- **Found during:** Task 1 (code reading)
- **Issue:** The plan assumed a `completed_at` column and a query filtered to `status='success'`. The actual `queries.fetch_latest_pipeline_run()` returns the single most recent row (any status) with column `run_ts` (not `completed_at`).
- **Fix:** Added `_fetch_last_successful_run_ts()` async helper that calls the existing function and filters for `status='success'` in Python, normalises `run_ts` to naive UTC datetime. No DB schema changes needed.
- **Files modified:** services/scheduler.py
- **Commit:** 651f6c0

**3. [Rule 2 - Missing functionality] Test lifespan mocking**
- **Found during:** Task 3
- **Issue:** The plan's test template imported `app` and used `AsyncClient(transport=ASGITransport(app=app))` directly. The lifespan calls `init_pool()`, `_run_migrations()`, `start_scheduler()`, and two security guard functions — all of which fail or have side effects in test environment.
- **Fix:** Added `_make_mock_lifespan_patches()` helper that patches all lifespan side-effects so tests run in isolation. Tests use `p.start()/p.stop()` pattern (not pytest fixtures) for compatibility with the async test bodies.
- **Files modified:** tests/test_metrics.py
- **Commit:** 651f6c0

## Self-Check: PASSED

- `alerts/pipeline_alerts.yml` — exists
- `tests/test_metrics.py` — exists
- `services/scheduler.py` — contains `_check_pipeline_staleness`, `pipeline_staleness_check`, `IntervalTrigger(minutes=30)`
- `api/metrics.py` — contains `_get_or_create_counter`, `_get_or_create_gauge`, `_get_or_create_histogram`
- `.planning/REQUIREMENTS.md` — 4 OBS requirements marked [x], traceability table updated
- Commit 651f6c0 — verified in git log
