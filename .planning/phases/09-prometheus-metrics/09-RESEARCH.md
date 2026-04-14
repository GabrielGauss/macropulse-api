# Phase 9: Prometheus /metrics + Pipeline Failure Alerting — Research

**Researched:** 2026-03-30
**Domain:** Prometheus instrumentation for FastAPI + APScheduler, in-process alerting
**Confidence:** HIGH

---

## Summary

Phase 9 adds a `/metrics` endpoint in Prometheus text exposition format to the existing FastAPI app, instruments the APScheduler daily pipeline job with Counters/Histograms/Gauges, and implements two alerting paths: (1) a Prometheus alerting rules YAML file for Prometheus-server-based alerting, and (2) in-app Brevo email alerting already wired in `services/scheduler.py` that satisfies OBS-03 without requiring a Prometheus server.

The existing codebase already has everything needed as scaffolding: `_run_pipeline_with_alert()` in `scheduler.py` catches exceptions and emails the owner. `database/queries.py` has `insert_pipeline_run` and `fetch_latest_pipeline_run` which record status, duration, and timestamps. The `asyncpg` pool in `database/connection.py` exposes `get_size()`, `get_idle_size()`, `get_min_size()`, and `get_max_size()` — all needed for `macropulse_db_pool_size`.

The cleanest approach for this single-process, single-worker deployment is: `prometheus-client`'s `make_asgi_app()` mounted at `/metrics` in `api/main.py`, with metrics defined in a new `api/metrics.py` module. APScheduler jobs are synchronous (`BackgroundScheduler`), so metric updates happen via plain `counter.inc()` and `histogram.observe()` calls inside `_run_pipeline_with_alert()` — no async complication. A custom Collector class reads the asyncpg pool introspection methods and DB-queried gauge values at scrape time.

**Primary recommendation:** Use `prometheus-client` with `make_asgi_app()` mounted directly in `main.py`. Define all metric objects in a single `api/metrics.py` module. Instrument the scheduler wrapper function and add a custom collector for DB-derived gauges. Deliver the Grafana dashboard JSON at `infrastructure/grafana/macropulse-dashboard.json`.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OBS-01 | `GET /metrics` endpoint in Prometheus text exposition format (no auth required) | `make_asgi_app()` mounted via `app.mount("/metrics", metrics_app)` in `main.py`; add `/metrics` to `_EXEMPT_PATHS` in rate limit middleware |
| OBS-02 | Key metrics: `macropulse_api_requests_total`, `macropulse_pipeline_runs_total`, `macropulse_pipeline_last_success_timestamp`, `macropulse_active_api_keys`, `macropulse_db_pool_size` | prometheus-client Counter/Gauge/Histogram; custom Collector for DB-derived gauges queried at scrape time |
| OBS-03 | Pipeline failure email within 5 minutes via Brevo to `pipeline_alert_email` | Already partially implemented in `scheduler.py::_run_pipeline_with_alert()`; extend to also update `macropulse_pipeline_runs_total{status="failed"}` Counter |
| OBS-04 | Staleness alert if `macropulse_pipeline_last_success_timestamp` is >26 hours old | Prometheus alerting rule `time() - macropulse_pipeline_last_success_timestamp > 93600` OR in-app staleness check job in scheduler |
| OBS-05 | Grafana dashboard JSON committed to `infrastructure/grafana/macropulse-dashboard.json` | Hand-authored JSON referencing the five OBS-02 metrics; importable to any Grafana instance |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| prometheus-client | >=0.20,<1.0 | Metric registry, exposition, ASGI app | Official Prometheus Python client; `make_asgi_app()` for FastAPI integration |

### Not Needed
| Library | Why Skip |
|---------|---------|
| starlette-exporter | Adds per-route request metrics automatically; useful but OBS-02 specifies exact metric names — hand-rolled Counter+Histogram gives precise control with zero naming surprises |
| prometheus-fastapi-instrumentator | Same reasoning; opinionated metric names don't match OBS-02 spec |
| aioprometheus | Only needed for async collection; single-process uvicorn + BackgroundScheduler doesn't require it |

**Installation:**
```bash
pip install "prometheus-client>=0.20,<1.0"
```

Add to `requirements.txt`:
```
prometheus-client>=0.20,<1.0
```

---

## Architecture Patterns

### Recommended Project Structure (additions only)
```
api/
├── metrics.py           # All prometheus-client metric objects + custom collectors
├── routes/
│   └── (existing)
main.py                  # mount /metrics ASGI app; add /metrics to rate-limit exempt list
services/
└── scheduler.py         # instrument _run_pipeline_with_alert() with pipeline metrics
infrastructure/
└── grafana/
    └── macropulse-dashboard.json   # OBS-05
    prometheus/
    └── alerts.yml       # OBS-04 alerting rules (optional — only used if Prometheus server present)
```

### Pattern 1: Mounting `/metrics` with `make_asgi_app()`

**What:** `prometheus-client` ships an ASGI application that serves the default registry in Prometheus text format.
**When to use:** Single process, single worker (this app uses `uvicorn` with one worker).

```python
# api/main.py — inside the existing app setup, after all routes are included

from prometheus_client import make_asgi_app as _make_prom_app

# Mount AFTER all API routes but BEFORE the StaticFiles catchall.
_metrics_app = _make_prom_app()
app.mount("/metrics", _metrics_app)
```

**Important:** Also add `"/metrics"` to `_EXEMPT_PATHS` in `api/middleware/rate_limit.py` so scraping is never rate-limited.

**Redirect note:** FastAPI's mount adds a 307 redirect from `/metrics` to `/metrics/`. The Prometheus scrape config must either use `/metrics/` as the path or set `follow_redirects: true`. Document this in the deployment guide. Alternatively, add a plain `@app.get("/metrics")` route that delegates — but the ASGI mount is simpler and more correct.

### Pattern 2: Centralized Metric Registry in `api/metrics.py`

**What:** Define all `Counter`, `Histogram`, and `Gauge` objects once at module import time. Import them wherever needed.
**Why:** Prometheus-client raises `ValueError: Duplicated timeseries` if the same metric name is registered twice — this happens in tests if metrics are created at function scope. Module-level singletons prevent this.

```python
# api/metrics.py
# Source: https://prometheus.github.io/client_python/instrumenting/counter/
from prometheus_client import Counter, Gauge, Histogram, REGISTRY
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector

# ── Request metrics (OBS-02) ───────────────────────────────────────
API_REQUESTS = Counter(
    "macropulse_api_requests_total",
    "Total API requests by endpoint and HTTP status",
    ["endpoint", "status"],
)

API_REQUEST_DURATION = Histogram(
    "macropulse_api_request_duration_seconds",
    "API request latency in seconds by endpoint",
    ["endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ── Pipeline metrics (OBS-02, OBS-03, OBS-04) ─────────────────────
PIPELINE_RUNS = Counter(
    "macropulse_pipeline_runs_total",
    "Total pipeline executions by status",
    ["status"],  # "success" | "failed" | "partial" | "halted"
)

PIPELINE_DURATION = Histogram(
    "macropulse_pipeline_duration_seconds",
    "Pipeline wall-clock duration in seconds",
    buckets=[10, 30, 60, 120, 300, 600, 1200],
)

PIPELINE_LAST_SUCCESS = Gauge(
    "macropulse_pipeline_last_success_timestamp",
    "Unix timestamp of the last successful pipeline run (0 if never)",
)
```

### Pattern 3: Custom Collector for DB-Derived Gauges

**What:** `macropulse_active_api_keys{tier="free"}` and `macropulse_db_pool_size` cannot be kept in sync via `.inc()/.dec()` — they are state derived from the DB and the asyncpg pool at scrape time. Use a custom Collector that queries them when Prometheus scrapes.
**Why:** Gauges updated by set() drift when the process restarts or when DB state changes externally. A custom collector always reflects ground truth.

**Key constraint:** The custom collector's `collect()` method is called synchronously during a Prometheus scrape (inside the ASGI request). It cannot `await` anything. Solutions:
1. Use a background periodic updater (a second APScheduler job every 60s) that calls `asyncio.run_coroutine_threadsafe()` to update module-level Gauge values.
2. Or expose the asyncpg pool's synchronous introspection methods (`pool.get_size()`, `pool.get_idle_size()`) which are non-async and safe to call from a collector.

**Recommended approach for `macropulse_db_pool_size`:** Use `set_function` with a lambda that reads the module-level `_pool` from `database.connection`:

```python
# api/metrics.py (continued)
from prometheus_client import Gauge

DB_POOL_SIZE = Gauge(
    "macropulse_db_pool_size",
    "Current number of connections in the asyncpg pool",
)

DB_POOL_IDLE = Gauge(
    "macropulse_db_pool_idle",
    "Current number of idle connections in the asyncpg pool",
)

def _update_pool_gauges() -> None:
    """Call once per scheduler tick (e.g., every minute) from a background job."""
    from database.connection import _pool
    if _pool is not None:
        DB_POOL_SIZE.set(_pool.get_size())
        DB_POOL_IDLE.set(_pool.get_idle_size())
```

**For `macropulse_active_api_keys`:** Add a second APScheduler job (cron every 5 min) that runs a DB query to count api_keys by tier and calls `ACTIVE_API_KEYS.labels(tier=tier).set(count)`. This is simpler than a custom Collector for a value that changes rarely.

```python
ACTIVE_API_KEYS = Gauge(
    "macropulse_active_api_keys",
    "Number of active API keys by tier",
    ["tier"],
)
```

### Pattern 4: Instrumenting APScheduler Jobs

The daily pipeline uses `BackgroundScheduler` (runs in a thread, not the asyncio event loop). The wrapper function `_run_pipeline_with_alert()` in `scheduler.py` is the correct instrumentation point — it already catches exceptions.

```python
# services/scheduler.py — updated _run_pipeline_with_alert()
import time as _time

def _run_pipeline_with_alert() -> None:
    from api.metrics import PIPELINE_RUNS, PIPELINE_DURATION, PIPELINE_LAST_SUCCESS
    import time as _time_mod
    t0 = _time_mod.monotonic()
    try:
        run_daily_pipeline()
        duration = _time_mod.monotonic() - t0
        PIPELINE_RUNS.labels(status="success").inc()
        PIPELINE_DURATION.observe(duration)
        PIPELINE_LAST_SUCCESS.set(_time_mod.time())  # Unix timestamp
    except Exception as exc:
        duration = _time_mod.monotonic() - t0
        PIPELINE_RUNS.labels(status="failed").inc()
        PIPELINE_DURATION.observe(duration)
        logger.error("Daily pipeline FAILED: %s", exc, exc_info=True)
        # ... existing email alert logic unchanged ...
        raise
```

Note: `PIPELINE_LAST_SUCCESS.set(time.time())` sets the Unix epoch timestamp. The OBS-04 staleness alert then uses `time() - macropulse_pipeline_last_success_timestamp > 93600` (26 hours = 93,600 seconds).

### Pattern 5: Request Instrumentation via Starlette Middleware

For `macropulse_api_requests_total` by endpoint/status, add a thin middleware class (not the third-party starlette-exporter) to keep full control over metric names:

```python
# api/middleware/metrics.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        # Skip /metrics itself to avoid recursion
        if path.startswith("/metrics"):
            return await call_next(request)
        t0 = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - t0
        from api.metrics import API_REQUESTS, API_REQUEST_DURATION
        API_REQUESTS.labels(endpoint=path, status=str(response.status_code)).inc()
        API_REQUEST_DURATION.labels(endpoint=path).observe(duration)
        return response
```

Register in `main.py` before `RateLimitMiddleware`:
```python
from api.middleware.metrics import MetricsMiddleware
app.add_middleware(MetricsMiddleware)
```

**Anti-pattern warning:** High-cardinality labels. If `endpoint` is set to the raw path including path parameters (e.g., `/v1/regime/2024-01-01`), the metrics cardinality explodes. Normalize dynamic path segments: use the route template (`/v1/regime/{date}`) or group at the prefix level. FastAPI's route matching can be used to extract the route template.

### Pattern 6: Alerting — Two Complementary Approaches

**OBS-03 (pipeline failure within 5 minutes):** Already achievable in-app without a Prometheus server. `_run_pipeline_with_alert()` sends a Brevo email on exception. This satisfies OBS-03 independently of any Prometheus deployment. The metric `macropulse_pipeline_runs_total{status="failed"}` is an additional observable artifact for dashboards.

**OBS-04 (staleness >26 hours):** Two implementation options:

Option A — Prometheus alerting rules (requires Prometheus server):
```yaml
# infrastructure/prometheus/alerts.yml
groups:
  - name: macropulse_pipeline
    rules:
      - alert: MacroPulsePipelineStale
        expr: time() - macropulse_pipeline_last_success_timestamp > 93600
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "MacroPulse pipeline has not succeeded in >26 hours"
          description: "Last success was {{ $value | humanizeDuration }} ago."

      - alert: MacroPulsePipelineFailed
        expr: increase(macropulse_pipeline_runs_total{status="failed"}[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "MacroPulse pipeline run failed"
```

Option B — In-app staleness check (no Prometheus server needed, satisfies OBS-04 for single-VPS deploy):
Add a second APScheduler job that runs every 30 minutes, queries `fetch_latest_pipeline_run()` from the DB, and sends a Brevo alert if `now - last_success_ts > 26h`. This is self-contained.

**Recommendation for this project (single VPS, no Prometheus server in docker-compose):** Implement Option B (in-app staleness check job) for OBS-04 so the alerting works without requiring Prometheus + Alertmanager. Also commit the alerting rules YAML for when a Prometheus server is eventually added.

### Anti-Patterns to Avoid
- **High-cardinality endpoint labels:** Never use raw URL path including path params. Use route template or strip dynamic segments.
- **Creating metrics inside request handlers:** Always define metrics at module import time. Creating inside handlers causes `ValueError: Duplicated timeseries` on second request.
- **Calling async DB queries from `collect()` in a custom Collector:** The ASGI scrape request runs synchronously in the Prometheus exposition path. Use background updater pattern instead.
- **Registering metrics in tests without cleanup:** Use `REGISTRY.unregister()` or create a fresh `CollectorRegistry(auto_describe=False)` per test and pass it to metric constructors.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Prometheus text format serialization | Custom `/metrics` text writer | `prometheus-client make_asgi_app()` | Handles OpenMetrics vs Prometheus text negotiation, gzip, content-type headers |
| Metric counter/histogram bucketing | Custom JSON counters in DB | `prometheus-client Counter/Histogram` | Thread-safe, handles label cardinality, proper `_total` suffix convention |
| asyncpg pool introspection | Custom SQL query for connection count | `_pool.get_size()`, `_pool.get_idle_size()` | asyncpg exposes these directly as synchronous methods — no DB query needed |

---

## Common Pitfalls

### Pitfall 1: Duplicate Metric Registration in Tests
**What goes wrong:** `ValueError: Duplicated timeseries in CollectorRegistry: {'macropulse_pipeline_runs_total'}` when tests import `api/metrics.py` multiple times.
**Why it happens:** Module-level metric objects register themselves with the global `REGISTRY` at import time. pytest imports the module once per session but the registry persists.
**How to avoid:** In tests, pass a fresh `CollectorRegistry()` to each metric constructor, OR use `prometheus_client.REGISTRY.unregister(metric)` in teardown, OR isolate test imports with `importlib.reload()`.
**Warning signs:** Tests pass in isolation but fail when run together.

### Pitfall 2: `/metrics` Redirect 307
**What goes wrong:** Prometheus scraper gets a 307 redirect from `/metrics` to `/metrics/` and may not follow it, causing scrape failures.
**Why it happens:** FastAPI's `app.mount()` mounts the ASGI sub-app at the path prefix, causing trailing-slash normalization.
**How to avoid:** Configure the Prometheus scrape target to use `/metrics/` (with trailing slash) OR add `metrics_path: /metrics/` in `prometheus.yml`. Document this in the ops guide.
**Warning signs:** Prometheus shows scrape target as DOWN or 307 in scrape logs.

### Pitfall 3: APScheduler Thread vs Event Loop
**What goes wrong:** Calling async DB queries (like `await fetch_latest_pipeline_run()`) directly inside `_run_pipeline_with_alert()` fails because BackgroundScheduler runs in a daemon thread outside the asyncio event loop.
**Why it happens:** `BackgroundScheduler` is the synchronous APScheduler scheduler. The app uses `asyncio` for the FastAPI event loop but the scheduler runs independently.
**How to avoid:** `_run_pipeline_with_alert()` already calls the synchronous `run_daily_pipeline()`. Keep all new metric updates in this wrapper as plain synchronous calls (`.inc()`, `.observe()`, `.set()` are all thread-safe).
**Warning signs:** `RuntimeError: no running event loop` in scheduler logs.

### Pitfall 4: Zero Value Before First Pipeline Run
**What goes wrong:** `macropulse_pipeline_last_success_timestamp` starts at 0 (Gauge default), causing the staleness alert to fire immediately on first deploy.
**Why it happens:** Gauge defaults to 0, which is epoch (1970). `time() - 0` is always huge.
**How to avoid:** At app startup in lifespan, query `fetch_latest_pipeline_run()` from the DB and initialize `PIPELINE_LAST_SUCCESS.set(last_run_ts)` if a successful run exists. If no runs exist, leave at 0 and suppress the alert with an `unless` clause or by initializing to `time()` on first startup.
**Warning signs:** Alert fires immediately after deploy even though pipeline ran yesterday.

### Pitfall 5: `queries.py` Uses Sync DB Calls in Daily Pipeline
**What goes wrong:** `_log_run()` in `daily_pipeline.py` calls `queries.insert_pipeline_run()` but `queries.py` is now all-async (Phase 8 migration). The pipeline itself is synchronous (`run_daily_pipeline` is `def`, not `async def`).
**Why it happens:** Phase 8 migrated all queries to async, but the daily pipeline runs in a sync BackgroundScheduler thread.
**How to avoid:** Check whether `queries.insert_pipeline_run()` is already async and whether `_log_run()` correctly awaits it or uses `asyncio.run()`. This is a pre-existing concern — Phase 9 must not break this.
**Warning signs:** Pipeline logs show DB write errors for `pipeline_runs` table.

---

## Code Examples

### Full `api/metrics.py` Module

```python
# Source: https://prometheus.github.io/client_python/instrumenting/counter/
# Source: https://prometheus.github.io/client_python/instrumenting/gauge/
# Source: https://prometheus.github.io/client_python/instrumenting/histogram/
from prometheus_client import Counter, Gauge, Histogram

# ── API request metrics ────────────────────────────────────────────
API_REQUESTS = Counter(
    "macropulse_api_requests_total",
    "Total HTTP requests handled by the API, by endpoint and status code",
    ["endpoint", "status"],
)

API_REQUEST_DURATION = Histogram(
    "macropulse_api_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ── Pipeline metrics ───────────────────────────────────────────────
PIPELINE_RUNS = Counter(
    "macropulse_pipeline_runs_total",
    "Pipeline executions by completion status",
    ["status"],
)

PIPELINE_DURATION = Histogram(
    "macropulse_pipeline_duration_seconds",
    "Pipeline execution wall-clock time in seconds",
    buckets=[10, 30, 60, 120, 300, 600, 1200],
)

PIPELINE_LAST_SUCCESS = Gauge(
    "macropulse_pipeline_last_success_timestamp",
    "Unix timestamp of the most recent successful pipeline run (0 if never run)",
)

# ── Infrastructure gauges ──────────────────────────────────────────
DB_POOL_SIZE = Gauge(
    "macropulse_db_pool_size",
    "Current total connections in the asyncpg pool",
)

DB_POOL_IDLE = Gauge(
    "macropulse_db_pool_idle_size",
    "Current idle connections in the asyncpg pool",
)

ACTIVE_API_KEYS = Gauge(
    "macropulse_active_api_keys",
    "Count of active (non-revoked) API keys by tier",
    ["tier"],
)


def update_pool_gauges() -> None:
    """Refresh pool size gauges from asyncpg pool state. Call from a periodic job."""
    from database.connection import _pool
    if _pool is not None and not _pool.is_closing():
        DB_POOL_SIZE.set(_pool.get_size())
        DB_POOL_IDLE.set(_pool.get_idle_size())


async def refresh_api_key_gauges() -> None:
    """Query DB for active key counts by tier. Call from a periodic async-capable context."""
    from database.connection import get_db_conn
    sql = """
        SELECT tier, COUNT(*) AS cnt
        FROM api_keys
        WHERE is_active = TRUE
        GROUP BY tier;
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql)
    for row in rows:
        ACTIVE_API_KEYS.labels(tier=row["tier"]).set(row["cnt"])
```

### Mounting in `main.py`

```python
# api/main.py — add after all route includes, before StaticFiles mount
from prometheus_client import make_asgi_app as _make_prom_app

_metrics_asgi = _make_prom_app()
app.mount("/metrics", _metrics_asgi)
```

### Adding `/metrics` to Rate Limit Exemptions

```python
# api/middleware/rate_limit.py
_EXEMPT_PATHS = {
    "/health", "/docs", "/openapi.json", "/redoc", "/dashboard",
    "/v1/auth/register", "/v1/auth/recover", "/v1/auth/recover/verify",
    "/v1/auth/verify",
    "/v1/pipeline/status",
    "/metrics", "/metrics/",   # OBS-01: Prometheus scrape endpoint — no auth required
}
```

### Staleness Alert YAML (Prometheus alerting rules)

```yaml
# infrastructure/prometheus/alerts.yml
# Source: https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
groups:
  - name: macropulse_pipeline
    rules:
      - alert: MacroPulsePipelineStale
        expr: time() - macropulse_pipeline_last_success_timestamp > 93600
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "MacroPulse pipeline has not completed successfully in >26 hours"
          description: >
            Last successful run was {{ $value | humanizeDuration }} ago.
            Check server logs and the /v1/pipeline/status endpoint.

      - alert: MacroPulsePipelineFailed
        expr: increase(macropulse_pipeline_runs_total{status="failed"}[10m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "MacroPulse daily pipeline run has failed"
          description: "A pipeline run recorded status=failed. Check scheduler logs immediately."
```

### In-App Staleness Check (OBS-04 without Prometheus server)

```python
# services/scheduler.py — add second job in start_scheduler()
import datetime as dt

async def _check_pipeline_staleness() -> None:
    """Fire a Brevo alert if the last successful pipeline run is >26 hours old."""
    from database.queries import fetch_latest_pipeline_run
    from config.settings import get_settings
    row = await fetch_latest_pipeline_run()
    if row is None:
        return
    if row.get("status") != "success":
        return
    last_ts = row["run_ts"]
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=dt.timezone.utc)
    age_hours = (dt.datetime.now(dt.timezone.utc) - last_ts).total_seconds() / 3600
    if age_hours > 26:
        settings = get_settings()
        if settings.pipeline_alert_email:
            from services.email import send_email
            send_email(
                to=settings.pipeline_alert_email,
                subject="[MacroPulse] Pipeline staleness alert: no success in >26h",
                html=(
                    f"<p>MacroPulse pipeline last succeeded "
                    f"<strong>{age_hours:.1f} hours ago</strong> "
                    f"({last_ts.strftime('%Y-%m-%d %H:%M UTC')}).</p>"
                    f"<p>The daily cron may have been skipped. Check the scheduler.</p>"
                ),
            )
```

Note: Because `_check_pipeline_staleness` is async and `BackgroundScheduler` is synchronous, it must be wrapped with `asyncio.run_coroutine_threadsafe(coro, loop)` where `loop` is the running event loop from the FastAPI lifespan, OR converted to synchronous DB access using `asyncpg`'s `run_until_complete` pattern. The simplest approach is to make it a plain sync function using a direct DB connection (avoids the pool) or to run the check inside the `lifespan` async context using `asyncio.create_task`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | None detected — uses `pytest.ini` or `pyproject.toml` conventions |
| Quick run command | `pytest tests/test_metrics.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBS-01 | `GET /metrics` returns 200 with `text/plain` content-type | integration | `pytest tests/test_metrics.py::test_metrics_endpoint_ok -x` | Wave 0 |
| OBS-01 | `/metrics` is not rate-limited | unit | `pytest tests/test_metrics.py::test_metrics_exempt_from_rate_limit -x` | Wave 0 |
| OBS-02 | `macropulse_pipeline_runs_total` appears in /metrics output after pipeline mock | unit | `pytest tests/test_metrics.py::test_pipeline_counter_increments -x` | Wave 0 |
| OBS-02 | `macropulse_pipeline_last_success_timestamp` is set on success | unit | `pytest tests/test_metrics.py::test_pipeline_last_success_timestamp -x` | Wave 0 |
| OBS-02 | `macropulse_db_pool_size` appears in output | unit | `pytest tests/test_metrics.py::test_db_pool_gauge -x` | Wave 0 |
| OBS-03 | Pipeline failure increments `status="failed"` counter | unit | `pytest tests/test_metrics.py::test_pipeline_failed_counter -x` | Wave 0 |
| OBS-04 | In-app staleness check sends email when age >26h | unit | `pytest tests/test_metrics.py::test_staleness_alert_fires -x` | Wave 0 |
| OBS-04 | In-app staleness check does NOT send email when age <26h | unit | `pytest tests/test_metrics.py::test_staleness_alert_suppressed -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_metrics.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_metrics.py` — covers all OBS-01 through OBS-04 test cases above
- [ ] `tests/conftest.py` update — add `reset_metrics_registry` fixture that unregisters test metrics from `prometheus_client.REGISTRY` between tests to prevent `ValueError: Duplicated timeseries`

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `prometheus-fastapi-instrumentator` (automatic instrumentation) | `prometheus-client` `make_asgi_app()` + hand-rolled middleware | Precise OBS-02 metric names; no third-party dependency on opinionated library |
| `starlette_exporter` middleware | Custom `MetricsMiddleware` | Full control over cardinality and label naming |
| Custom Collector for pool metrics | `Gauge.set_function()` via background updater | Avoids async-in-sync collector pitfall |

**Deprecated/outdated:**
- `prometheus_multiprocess_mode` env var: only relevant for multi-process (Gunicorn with multiple workers). This app uses single uvicorn worker — not needed.
- `push_to_gateway()`: only needed for short-lived batch jobs. Not applicable to this long-running FastAPI service.

---

## Open Questions

1. **Async DB calls from staleness checker in BackgroundScheduler**
   - What we know: BackgroundScheduler is synchronous; staleness check needs to query the DB
   - What's unclear: Whether to use `asyncio.run_coroutine_threadsafe()` (requires passing the event loop reference), or to make the staleness check another APScheduler `AsyncIOScheduler` job, or to use a synchronous DB connection for this check only
   - Recommendation: Add an `AsyncIOScheduler` job (separate from `BackgroundScheduler`) for the staleness check, since the staleness check is async-capable. This keeps the pattern clean. Phase 9 planner should decide.

2. **`_log_run()` sync/async mismatch in `daily_pipeline.py`**
   - What we know: `_log_run()` calls `queries.insert_pipeline_run()` which is now `async def` (Phase 8). The daily pipeline is synchronous (`def run_daily_pipeline`).
   - What's unclear: How this currently works without errors — either there's a sync wrapper somewhere or the pipeline doesn't actually await it
   - Recommendation: Audit `_log_run()` and `queries.insert_pipeline_run()` before Phase 9 ships. Phase 9 metric updates happen in the same synchronous wrapper, so this must be resolved first.

3. **OBS-05 Grafana dashboard JSON format version**
   - What we know: Grafana dashboard JSON is versioned; a dashboard exported from Grafana 10.x may not import cleanly to 9.x
   - What's unclear: Target Grafana version for this project
   - Recommendation: Write the dashboard JSON targeting Grafana 10.x schema (latest stable as of 2026). Include a comment in the file noting the target version.

---

## Sources

### Primary (HIGH confidence)
- [prometheus/client_python — FastAPI+Gunicorn docs](https://prometheus.github.io/client_python/exporting/http/fastapi-gunicorn/) — `make_asgi_app()` mount pattern
- [prometheus/client_python — Counter docs](https://prometheus.github.io/client_python/instrumenting/counter/) — Counter API
- [prometheus/client_python — Gauge docs](https://prometheus.github.io/client_python/instrumenting/gauge/) — Gauge API, `set_function`
- [prometheus/client_python — Histogram docs](https://prometheus.github.io/client_python/instrumenting/histogram/) — Histogram API, `.time()` context manager
- [prometheus/client_python — Custom Collectors docs](https://prometheus.github.io/client_python/collector/custom/) — `Collector.collect()` pattern
- [asyncpg Pool API](https://magicstack.github.io/asyncpg/current/api/index.html#connection-pools) — `get_size()`, `get_idle_size()`, `get_min_size()`, `get_max_size()`, `is_closing()`
- [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) — YAML structure, `for:`, `time()` function for staleness

### Secondary (MEDIUM confidence)
- [starlette_exporter GitHub](https://github.com/stephenhillier/starlette_exporter) — PrometheusMiddleware reference (used to understand what NOT to depend on)
- [prometheus-fastapi-instrumentator PyPI](https://pypi.org/project/prometheus-fastapi-instrumentator/) — Alternative considered, rejected in favor of hand-rolled approach
- [prometheus/client_python Issue #1016](https://github.com/prometheus/client_python/issues/1016) — `/metrics` vs `/metrics/` redirect behavior confirmed

### Tertiary (LOW confidence)
- Community examples of asyncpg+prometheus integration patterns (WebSearch only, not independently verified against official docs)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — prometheus-client is the official Python Prometheus client; make_asgi_app() is documented
- Architecture: HIGH — metric objects, custom collectors, and scheduler instrumentation all verified against official docs
- Pitfalls: HIGH for registry duplication (known issue), MEDIUM for async/sync boundary (verified by code inspection, not official doc)
- Alerting rules YAML: HIGH — verified against prometheus.io documentation
- asyncpg pool methods: HIGH — verified against asyncpg official API docs

**Research date:** 2026-03-30
**Valid until:** 2026-09-30 (prometheus-client is stable; asyncpg API is stable)
