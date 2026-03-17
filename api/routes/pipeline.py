"""
Pipeline status endpoint.

GET /v1/pipeline/status  — returns last run timestamp, status, and data_lag flag.
Public (no auth required) — this is confidence/transparency infrastructure for users.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

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
