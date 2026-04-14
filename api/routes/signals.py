"""
Unified signal endpoints for MacroPulse.

Implements the /v1/signals surface defined in the Master Build & Launch Manual §5.2:
  GET /v1/signals/latest          — most recent signal package
  GET /v1/signals/history         — regime history (query: days, max 365)
  GET /v1/signals/{date}          — historical lookup by date (YYYY-MM-DD)
  GET /v1/signals/range           — time series (query: start, end; max 365 days)
"""

from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.auth import require_api_key
from api.deps import require_paid
from api.schemas.responses import SignalPackageResponse
from services.signals import build_signal_package, build_signal_range

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/signals", tags=["Signals"])


@router.get(
    "/latest",
    response_model=SignalPackageResponse,
    summary="Latest unified signal package",
)
async def get_latest_signal(
    key_record: dict = Depends(require_paid),
) -> SignalPackageResponse:
    """
    Return the most recent unified macro signal package.

    Combines HMM regime, net liquidity state, PCA factors, and model metadata
    into a single response.  This is the primary integration endpoint for clients.
    """
    pkg = await build_signal_package()
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No regime data available. Run the daily pipeline first.",
        )
    return SignalPackageResponse(**pkg)


@router.get(
    "/history",
    summary="Regime history for charting",
)
async def get_signal_history(
    days: int = Query(default=90, ge=7, le=365, description="Number of calendar days to return"),
    key_record: dict = Depends(require_api_key),
) -> list[dict]:
    """
    Return daily regime rows for the last N days, newest first.

    Lighter than /range — returns only the fields needed for a timeline chart:
    date, regime, risk_score, and the four probability columns.
    Available to all authenticated tiers (free/starter/pro).
    """
    from database.queries import fetch_regime_history
    import datetime as dt

    end   = dt.date.today()
    start = end - dt.timedelta(days=days)
    rows  = await fetch_regime_history(start=start, end=end, limit=days)

    return [
        {
            "date":             str(r["time"])[:10],
            "regime":           r["regime"],
            "risk_score":       float(r.get("risk_score") or 0),
            "prob_expansion":   float(r.get("prob_expansion") or 0),
            "prob_recovery":    float(r.get("prob_recovery") or 0),
            "prob_tightening":  float(r.get("prob_tightening") or 0),
            "prob_risk_off":    float(r.get("prob_risk_off") or 0),
        }
        for r in rows
    ]


@router.get(
    "/range",
    response_model=list[SignalPackageResponse],
    summary="Signal time series over a date range",
)
async def get_signal_range(
    start: dt.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: dt.date = Query(..., description="End date (YYYY-MM-DD)"),
    key_record: dict = Depends(require_paid),
) -> list[SignalPackageResponse]:
    """
    Return signal packages for every trading day in [start, end].

    Capped at 365 days.  Returns an empty list if no data exists for the range.
    """
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end must be >= start.",
        )
    results = await build_signal_range(start=start, end=end)
    return [SignalPackageResponse(**r) for r in results]


@router.get(
    "/{date}",
    response_model=SignalPackageResponse,
    summary="Signal package for a specific date",
)
async def get_signal_by_date(
    date: dt.date,
    key_record: dict = Depends(require_paid),
) -> SignalPackageResponse:
    """
    Return the signal package for a specific date (YYYY-MM-DD).

    Returns 404 if no regime data exists for that date.
    """
    pkg = await build_signal_package(target_date=date)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No signal data found for {date}.",
        )
    return SignalPackageResponse(**pkg)
