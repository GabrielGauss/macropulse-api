"""
Prometheus metrics endpoint tests — Phase 9 (OBS-01, OBS-02).

Tests verify that /metrics/ is reachable, exposes the correct metric names,
and that the metrics module handles repeated imports without raising ValueError.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_mock_lifespan_patches():
    """
    Return context-manager patches that suppress the app's lifespan side-effects:
    DB pool init, migrations, signer init, scheduler start/stop, and
    startup security guards (which require env vars not set in CI).
    """
    return [
        patch("database.connection.init_pool", new_callable=AsyncMock),
        patch("database.connection.close_pool", new_callable=AsyncMock),
        patch("api.main._run_migrations", new_callable=AsyncMock),
        patch("services.mta_signer.init_signer"),
        patch("api.main._validate_webhook_secrets"),
        patch("api.main._validate_cors_origins"),
        patch("services.scheduler.start_scheduler"),
        patch("services.scheduler.stop_scheduler"),
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200():
    """GET /metrics/ must return 200 with text/plain content type."""
    from api.main import app

    patches = _make_mock_lifespan_patches()
    started = [p.start() for p in patches]
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/metrics/")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
    finally:
        for p in patches:
            p.stop()


@pytest.mark.asyncio
async def test_metrics_contains_pipeline_counter():
    """After incrementing the counter, /metrics/ body must contain the metric name."""
    from api.main import app
    from api.metrics import PIPELINE_RUNS_TOTAL

    PIPELINE_RUNS_TOTAL.labels(status="success").inc()

    patches = _make_mock_lifespan_patches()
    for p in patches:
        p.start()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/metrics/")
        assert "macropulse_pipeline_runs_total" in resp.text
    finally:
        for p in patches:
            p.stop()


def test_metrics_module_no_duplicate_registration():
    """Importing api.metrics twice (via importlib.reload) must not raise ValueError."""
    import importlib
    import api.metrics

    # reload() re-executes the module body; the module must handle this gracefully
    # (prometheus_client raises ValueError on duplicate timeseries name if not guarded)
    try:
        importlib.reload(api.metrics)
    except ValueError as exc:
        pytest.fail(f"Reloading api.metrics raised ValueError: {exc}")
