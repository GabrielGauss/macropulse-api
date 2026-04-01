---
phase: 09-prometheus-metrics
plan: "00"
subsystem: observability
tags: [prometheus, metrics, async-fix, scheduler, rate-limiting]
dependency_graph:
  requires: [database/connection.py, database/queries.py, services/scheduler.py]
  provides: [api/metrics.py, GET /metrics]
  affects: [data/pipelines/daily_pipeline.py, api/main.py, api/middleware/rate_limit.py]
tech_stack:
  added: [prometheus-client>=0.20,<1.0]
  patterns: [module-level metric singletons, asyncio.run() sync wrapper, ASGI sub-app mount]
key_files:
  created: [api/metrics.py]
  modified:
    - requirements.txt
    - api/main.py
    - api/middleware/rate_limit.py
    - data/pipelines/daily_pipeline.py
    - services/scheduler.py
decisions:
  - "Converted run_daily_pipeline to async inner function (_run_daily_pipeline_async) with a sync wrapper — avoids nested asyncio.run() and keeps all DB awaits in one async context"
  - "Module-level metric singletons in api/metrics.py prevent ValueError on duplicate registration during hot reload or multi-import test runs"
  - "_update_pool_metrics deferred-imports _pool from database.connection to avoid circular import at module load time"
metrics:
  duration: ~8min
  completed: "2026-03-31T16:48:42Z"
  tasks_completed: 4
  files_modified: 6
---

# Phase 9 Plan 00: Prometheus Metrics + Pipeline Instrumentation Summary

Prometheus `/metrics` endpoint live with pipeline run counters, duration histogram, last-success timestamp, and DB pool gauges. Fixed the async/sync mismatch introduced by Phase 8's asyncpg migration.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Fix async/sync mismatch in daily_pipeline.py | 3586c48 | data/pipelines/daily_pipeline.py |
| 2 | Create api/metrics.py + add prometheus-client to requirements | 3586c48 | api/metrics.py, requirements.txt |
| 3 | Mount /metrics endpoint + exempt from rate limiting | 3586c48 | api/main.py, api/middleware/rate_limit.py |
| 4 | Instrument scheduler pipeline wrapper + pool metrics job | 3586c48 | services/scheduler.py |

## What Was Built

### Async/Sync Fix (Task 1)

`data/pipelines/daily_pipeline.py` had a critical bug introduced by Phase 8: all `database/queries.py` functions are `async def` but `run_daily_pipeline` and `_log_run` were sync, calling them without `await`. This caused coroutines to be created and immediately garbage-collected — zero DB writes during pipeline execution.

Fix applied:
- `_log_run` converted to `async def`, awaits `queries.insert_pipeline_run()`
- `run_daily_pipeline` body extracted to `async def _run_daily_pipeline_async()` with all `queries.*` calls properly awaited
- Sync `run_daily_pipeline()` wrapper added: calls `asyncio.run(_run_daily_pipeline_async(...))` — safe because APScheduler BackgroundScheduler runs jobs in threads (no running event loop)

### Prometheus Metrics (Task 2)

`api/metrics.py` — 5 module-level singletons:

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `macropulse_pipeline_runs_total` | Counter | `status` (success/failure) | Pipeline run count by outcome |
| `macropulse_pipeline_duration_seconds` | Histogram | — | Duration buckets: 1,5,10,30,60,120,300,600s |
| `macropulse_pipeline_last_success_timestamp` | Gauge | — | Unix epoch of last successful run |
| `macropulse_db_pool_size` | Gauge | — | asyncpg pool max connections |
| `macropulse_db_pool_idle` | Gauge | — | asyncpg pool idle connections |

### /metrics Endpoint (Task 3)

- `make_asgi_app()` mounted at `/metrics` in `api/main.py`, after all route registrations
- `/metrics` and `/metrics/` added to `_EXEMPT_PATHS` in `api/middleware/rate_limit.py` — Prometheus scrapers are never rate-limited

### Scheduler Instrumentation (Task 4)

`services/scheduler.py` — `_run_pipeline_with_alert`:
- Increments `PIPELINE_RUNS_TOTAL.labels(status="success"/"failure")` on each run
- Observes `PIPELINE_DURATION_SECONDS` in `finally` block (always recorded, even on failure)
- Sets `PIPELINE_LAST_SUCCESS_TIMESTAMP` on success only

`_update_pool_metrics()` — new 60s interval APScheduler job:
- Reads `_pool.get_size()` and `_pool.get_idle_size()` from the asyncpg pool
- Updates `DB_POOL_SIZE` and `DB_POOL_IDLE` gauges
- Deferred import of `database.connection._pool` to avoid circular imports at module load

## Verification

```
python -c "from api.main import app; print('OK')"           # OK
python -c "from api.metrics import PIPELINE_RUNS_TOTAL; ..."  # OK (twice, no dup error)
python -c "from data.pipelines.daily_pipeline import run_daily_pipeline; print('OK')"  # OK
grep -c "prometheus" requirements.txt                        # 1
grep "/metrics" api/main.py                                  # app.mount("/metrics", _metrics_app)
grep "/metrics" api/middleware/rate_limit.py                 # "/metrics", "/metrics/"
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] All query calls in run_daily_pipeline were unawaited**
- **Found during:** Task 1
- **Issue:** The plan described `_log_run()` as the only async/sync mismatch. In reality, `_run_daily_pipeline_async` calls `queries.upsert_macro_features`, `queries.upsert_macro_factors`, `queries.upsert_macro_regime`, `queries.fetch_regime_history`, and `queries.upsert_drift_metrics` — all async — without `await`. These were silent no-ops (coroutines returned but never run).
- **Fix:** Converted the entire pipeline body to `async def _run_daily_pipeline_async()`, added `await` to all 6 query call sites, added `await` to all 5 `_log_run()` call sites. Kept `run_daily_pipeline()` as a sync wrapper using `asyncio.run()`.
- **Files modified:** data/pipelines/daily_pipeline.py
- **Commit:** 3586c48

## Self-Check: PASSED

- `api/metrics.py` — exists
- `requirements.txt` — contains `prometheus-client>=0.20,<1.0`
- `api/main.py` — contains `app.mount("/metrics", _metrics_app)`
- `api/middleware/rate_limit.py` — contains `"/metrics", "/metrics/"`
- `services/scheduler.py` — contains `PIPELINE_RUNS_TOTAL`, `PIPELINE_DURATION_SECONDS`, `_update_pool_metrics`
- `data/pipelines/daily_pipeline.py` — contains `asyncio.run()` wrapper and awaited query calls
- Commit 3586c48 — verified in git log
