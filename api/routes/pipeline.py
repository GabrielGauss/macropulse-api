"""
Pipeline endpoints.

GET  /v1/pipeline/status   — last run timestamp, status, data_lag flag. Public.
POST /v1/pipeline/trigger  — kick off an immediate run. Owner key required.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException

from config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/pipeline", tags=["System"])


@router.get("/status")
def get_pipeline_status() -> dict:
    """
    Return the most recent pipeline run metadata.

    Used by the dashboard header to display data freshness.
    No API key required — public transparency endpoint.
    """
    try:
        from database.queries import fetch_latest_pipeline_run
        row = fetch_latest_pipeline_run()
    except Exception as exc:
        logger.error("pipeline/status DB error: %s", exc)
        raise HTTPException(status_code=503, detail="Status temporarily unavailable")

    if row is None:
        return {"last_run_at": None, "status": "never", "data_lag": False, "model_version": None}

    return {
        "last_run_at": row["run_ts"].isoformat() if row.get("run_ts") else None,
        "status": row.get("status", "unknown"),
        "data_lag": bool(row.get("data_lag", False)),
        "model_version": row.get("model_version"),
    }


@router.post("/trigger")
def trigger_pipeline(x_api_key: str = Header(...)) -> dict:
    """
    Trigger an immediate pipeline run outside the normal schedule.

    Requires the owner API key in the X-Api-Key header.
    Runs asynchronously in the background — returns immediately.
    """
    settings = get_settings()
    if not settings.owner_api_key or x_api_key != settings.owner_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    import threading
    from services.scheduler import _loop, _run_pipeline_with_alert

    if _loop is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialised")

    t = threading.Thread(target=_run_pipeline_with_alert, daemon=True, name="manual-pipeline-trigger")
    t.start()
    logger.info("Pipeline triggered manually via API")
    return {"status": "triggered"}
