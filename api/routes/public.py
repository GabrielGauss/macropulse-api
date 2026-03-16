"""
Public (unauthenticated) API endpoints for the MacroPulse marketing site.

These routes are exempt from API key authentication and rate limiting.
They expose minimal read-only data to power the live regime chart and
the email subscribe form at macropulse.live.
"""

from __future__ import annotations

import datetime as dt
import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/public", tags=["Public"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Static performance stats (computed from 2-year backtest)
_PERF_STATS = {
    "sharpe_proxy": 1.69,
    "max_drawdown": -5.9,
    "avg_persistence_days": 44,
}


@router.get("/chart-data")
def get_chart_data():
    """
    Last 730 days of regime history for the marketing-site interactive chart.
    No API key required.
    """
    try:
        from database.queries import fetch_public_chart_data
        rows = fetch_public_chart_data(limit=730)
    except Exception as exc:
        logger.error("public chart-data DB error: %s", exc)
        raise HTTPException(status_code=503, detail="Data temporarily unavailable")

    series = [
        {
            "date": (
                row["time"].strftime("%Y-%m-%d")
                if hasattr(row.get("time"), "strftime")
                else str(row["time"])[:10]
            ),
            "regime": row["regime"],
            "risk_score": round(float(row["risk_score"]), 2) if row.get("risk_score") is not None else 0.0,
        }
        for row in rows
    ]

    # Compute regime distribution from returned rows
    dist: dict[str, int] = {}
    for row in series:
        dist[row["regime"]] = dist.get(row["regime"], 0) + 1
    total = len(series) or 1
    regime_distribution = {k: round(v / total, 3) for k, v in sorted(dist.items())}

    return {
        "days": len(series),
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "series": series,
        "stats": {
            **_PERF_STATS,
            "total_days": len(series),
            "regime_distribution": regime_distribution,
        },
    }


class SubscribeRequest(BaseModel):
    email: str


@router.post("/subscribe", status_code=202)
def subscribe(body: SubscribeRequest):
    """
    Newsletter subscribe — captures email for the weekly macro brief.
    No API key required.
    """
    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Invalid email address")

    try:
        from database.queries import create_newsletter_subscriber
        create_newsletter_subscriber(email)
    except Exception as exc:
        logger.error("newsletter subscribe DB error: %s", exc)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    try:
        from services.email import send_newsletter_confirmation
        send_newsletter_confirmation(email)
    except Exception:
        pass  # email is fire-and-forget

    return {"status": "subscribed"}
