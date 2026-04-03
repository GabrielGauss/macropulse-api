"""
FastAPI route definitions for MacroPulse v1 endpoints.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.auth import require_api_key
from api.deps import require_paid
from api.schemas.responses import (
    DriftResponse,
    DriftRow,
    FactorRow,
    FactorsResponse,
    LiquidityResponse,
    LiquidityRow,
    RegimeProbabilities,
    RegimeResponse,
)
from database import queries
from services.mta_signer import sign_regime_payload
from services.scorecard import build_scorecard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["MacroPulse"])


@router.get("/regime/current", response_model=RegimeResponse)
async def get_current_regime() -> RegimeResponse:
    """Return the most recent macro regime signal."""
    row = await queries.fetch_current_regime()
    if row is None:
        raise HTTPException(status_code=404, detail="No regime data available.")

    broadcast_time = int(time.time() * 1000)  # Unix ms

    # Numeric regime ID — stable key for IRL Engine policy enforcement.
    _REGIME_ID = {"expansion": 0, "recovery": 1, "tightening": 2, "risk_off": 3}
    regime_str = row["regime"]
    regime_id = _REGIME_ID.get(regime_str, 3)  # default to risk_off (conservative)

    # Build the response without signature first so we can sign the exact bytes
    # that will appear in the JSON body.  Using model_dump(mode="json") ensures
    # Pydantic's serialization rules (float precision, ISO-8601 with Z, etc.)
    # produce the same values the IRL Engine will see when it verifies the sig.
    response = RegimeResponse(
        timestamp=row["time"],
        macro_regime=regime_str,
        risk_score=row["risk_score"],
        probabilities=RegimeProbabilities(
            expansion=row["prob_expansion"],
            tightening=row["prob_tightening"],
            risk_off=row["prob_risk_off"],
            recovery=row["prob_recovery"],
        ),
        volatility_state=row.get("volatility_state"),
        model_version=row.get("model_version"),
        regime_id=regime_id,
        broadcast_time=broadcast_time,
        signature=None,
    )
    # Sign the Pydantic-serialized dict (no "signature" key) so the canonical
    # JSON matches the response body byte-for-byte after the sig field is removed.
    payload = response.model_dump(mode="json")
    payload.pop("signature", None)
    signature = sign_regime_payload(payload)

    response.signature = signature
    return response


_FREE_HISTORY_LIMIT = 30
_UPGRADE_URL = "https://macropulse.live/#pricing"


@router.get("/regime/history", response_model=list[RegimeResponse])
async def get_regime_history(
    start: Optional[dt.date] = Query(None, description="Start date (inclusive)"),
    end: Optional[dt.date] = Query(None, description="End date (inclusive)"),
    limit: int = Query(90, ge=1, le=1000),
    key_record: dict = Depends(require_api_key),
) -> list[RegimeResponse]:
    """Return historical regime signals."""
    tier = key_record.get("tier", "free")
    if tier == "free":
        limit = min(limit, _FREE_HISTORY_LIMIT)
    rows = await queries.fetch_regime_history(start=start, end=end, limit=limit)
    return [
        RegimeResponse(
            timestamp=r["time"],
            macro_regime=r["regime"],
            risk_score=r["risk_score"],
            probabilities=RegimeProbabilities(
                expansion=r["prob_expansion"],
                tightening=r["prob_tightening"],
                risk_off=r["prob_risk_off"],
                recovery=r["prob_recovery"],
            ),
            volatility_state=r.get("volatility_state"),
            model_version=r.get("model_version"),
        )
        for r in rows
    ]


_CSV_MAX_ROWS = 10_000


@router.get("/regime/export")
async def export_regime_history(
    limit: int = Query(730, ge=1, le=10_000),
    key_record: dict = Depends(require_api_key),
):
    """
    Download regime history as CSV.
    Free: 30 days. Starter/Pro: up to 730 days. Hard cap: 10,000 rows.
    """
    tier = key_record.get("tier", "free")
    if tier == "free":
        limit = min(limit, 30)

    # Safety cap: never return more than 10,000 rows regardless of tier or query param
    limit = min(limit or _CSV_MAX_ROWS, _CSV_MAX_ROWS)

    rows = await queries.fetch_regime_history(limit=limit)
    rows_asc = list(reversed(rows))

    _EXPOSURE = {"expansion": 1.00, "recovery": 0.75, "tightening": 0.25, "risk_off": 0.00}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "regime", "risk_score", "equity_exposure",
                     "prob_expansion", "prob_recovery", "prob_tightening", "prob_risk_off"])

    for r in rows_asc:
        regime = r.get("regime", "")
        writer.writerow([
            str(r.get("time", ""))[:10],
            regime,
            round(float(r.get("risk_score") or 0), 2),
            _EXPOSURE.get(regime, ""),
            round(float(r.get("prob_expansion") or 0), 4),
            round(float(r.get("prob_recovery") or 0), 4),
            round(float(r.get("prob_tightening") or 0), 4),
            round(float(r.get("prob_risk_off") or 0), 4),
        ])

    output.seek(0)
    filename = f"macropulse_regimes_{str(rows_asc[-1].get('time', ''))[:10]}.csv" if rows_asc else "macropulse_regimes.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/liquidity", response_model=LiquidityResponse)
async def get_liquidity(
    limit: int = Query(30, ge=1, le=500),
) -> LiquidityResponse:
    """Return recent net liquidity values."""
    rows = await queries.fetch_latest_liquidity(limit=limit)
    return LiquidityResponse(
        data=[LiquidityRow(**r) for r in rows]
    )


@router.get("/factors", response_model=FactorsResponse)
async def get_factors(
    limit: int = Query(30, ge=1, le=500),
) -> FactorsResponse:
    """Return recent PCA latent factors."""
    rows = await queries.fetch_latest_factors(limit=limit)
    return FactorsResponse(
        data=[FactorRow(**r) for r in rows]
    )


@router.get("/drift", response_model=DriftResponse)
async def get_drift(
    limit: int = Query(30, ge=1, le=500),
) -> DriftResponse:
    """Return recent model drift metrics."""
    rows = await queries.fetch_latest_drift(limit=limit)
    return DriftResponse(
        data=[DriftRow(**r) for r in rows]
    )


@router.get("/features", tags=["MacroPulse"])
async def get_features(
    limit: int = Query(90, ge=1, le=500),
    key_record: dict = Depends(require_paid),
) -> list[dict]:
    """Return recent macro feature time series (d_10y, d_2y, d_yield_curve, d_sp500, etc.)"""
    rows = await queries.fetch_latest_features(limit=limit)
    # Convert datetime objects to ISO strings for JSON serialisation
    return [
        {**row, "time": row["time"].isoformat() if hasattr(row.get("time"), "isoformat") else row["time"]}
        for row in rows
    ]


@router.get("/scorecard", tags=["MacroPulse"])
def get_scorecard() -> dict:
    """
    Return the MacroPulse Scorecard — 5 normalized macro signals on [-1, 1].

    No authentication required (public endpoint for the dashboard).
    """
    return build_scorecard()
