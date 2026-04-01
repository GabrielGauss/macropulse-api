"""
Prometheus metric singletons for MacroPulse.

All metrics are defined at module level to prevent ValueError: Duplicated
timeseries on import (e.g., during hot reload or test runs with multiple
imports). Import from this module to instrument code.

Each metric is registered inside a try/except so that importlib.reload()
and hot-reload environments never raise ValueError for already-registered names.

Usage::

    from api.metrics import PIPELINE_RUNS_TOTAL, PIPELINE_DURATION_SECONDS

    PIPELINE_RUNS_TOTAL.labels(status="success").inc()
    PIPELINE_DURATION_SECONDS.observe(elapsed)
"""

from __future__ import annotations

from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
)


def _get_or_create_counter(name: str, documentation: str, labelnames: list[str]) -> Counter:
    """Return existing counter by name if already registered, else create it."""
    if name in REGISTRY._names_to_collectors:  # type: ignore[attr-defined]
        return REGISTRY._names_to_collectors[name]  # type: ignore[attr-defined]
    return Counter(name, documentation, labelnames)


def _get_or_create_histogram(
    name: str, documentation: str, buckets: list[float]
) -> Histogram:
    """Return existing histogram by name if already registered, else create it."""
    if name in REGISTRY._names_to_collectors:  # type: ignore[attr-defined]
        return REGISTRY._names_to_collectors[name]  # type: ignore[attr-defined]
    return Histogram(name, documentation, buckets=buckets)


def _get_or_create_gauge(name: str, documentation: str) -> Gauge:
    """Return existing gauge by name if already registered, else create it."""
    if name in REGISTRY._names_to_collectors:  # type: ignore[attr-defined]
        return REGISTRY._names_to_collectors[name]  # type: ignore[attr-defined]
    return Gauge(name, documentation)


# ── Pipeline run counters ────────────────────────────────────────────

PIPELINE_RUNS_TOTAL = _get_or_create_counter(
    "macropulse_pipeline_runs_total",
    "Total pipeline runs by status",
    ["status"],  # label values: success, failure
)

PIPELINE_DURATION_SECONDS = _get_or_create_histogram(
    "macropulse_pipeline_duration_seconds",
    "Pipeline run duration in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

PIPELINE_LAST_SUCCESS_TIMESTAMP = _get_or_create_gauge(
    "macropulse_pipeline_last_success_timestamp",
    "Unix timestamp of the last successful pipeline run",
)

# ── Database pool gauges ─────────────────────────────────────────────

DB_POOL_SIZE = _get_or_create_gauge(
    "macropulse_db_pool_size",
    "Total asyncpg connection pool size (max connections)",
)

DB_POOL_IDLE = _get_or_create_gauge(
    "macropulse_db_pool_idle",
    "Number of idle (available) asyncpg pool connections",
)
