"""
Prometheus metric singletons for MacroPulse.

All metrics are defined at module level to prevent ValueError: Duplicated
timeseries on import (e.g., during hot reload or test runs with multiple
imports). Import from this module to instrument code.

Usage::

    from api.metrics import PIPELINE_RUNS_TOTAL, PIPELINE_DURATION_SECONDS

    PIPELINE_RUNS_TOTAL.labels(status="success").inc()
    PIPELINE_DURATION_SECONDS.observe(elapsed)
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── Pipeline run counters ────────────────────────────────────────────

PIPELINE_RUNS_TOTAL = Counter(
    "macropulse_pipeline_runs_total",
    "Total pipeline runs by status",
    ["status"],  # label values: success, failure
)

PIPELINE_DURATION_SECONDS = Histogram(
    "macropulse_pipeline_duration_seconds",
    "Pipeline run duration in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

PIPELINE_LAST_SUCCESS_TIMESTAMP = Gauge(
    "macropulse_pipeline_last_success_timestamp",
    "Unix timestamp of the last successful pipeline run",
)

# ── Database pool gauges ─────────────────────────────────────────────

DB_POOL_SIZE = Gauge(
    "macropulse_db_pool_size",
    "Total asyncpg connection pool size (max connections)",
)

DB_POOL_IDLE = Gauge(
    "macropulse_db_pool_idle",
    "Number of idle (available) asyncpg pool connections",
)
