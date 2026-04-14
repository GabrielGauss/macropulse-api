"""
Public (unauthenticated) API endpoints for the MacroPulse marketing site.

These routes are exempt from API key authentication and rate limiting.
They expose minimal read-only data to power the live regime chart and
the email subscribe form at macropulse.live.
"""

from __future__ import annotations

import datetime as dt
import logging
import math

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/public", tags=["Public"])

def _compute_stats(series: list[dict]) -> dict:
    """Compute Sharpe proxy, max drawdown, and win-rate from the strategy series."""
    if len(series) < 2:
        return {"sharpe_proxy": None, "max_drawdown": None, "avg_persistence_days": None,
                "strategy_annual_return": None, "bh_annual_return": None}

    # Daily simple returns
    strat_vals = [s["strategy"] for s in series]
    bh_vals    = [s["sp500"]    for s in series]
    strat_rets = [(strat_vals[i] / strat_vals[i-1] - 1) for i in range(1, len(strat_vals))]
    bh_rets    = [(bh_vals[i]   / bh_vals[i-1]    - 1) for i in range(1, len(bh_vals))]

    n = len(strat_rets)

    # Annualised return (CAGR)
    total_days = len(series)
    years = total_days / 365.25
    strat_annual = (strat_vals[-1] / strat_vals[0]) ** (1 / years) - 1 if years > 0 else 0
    bh_annual    = (bh_vals[-1]    / bh_vals[0])    ** (1 / years) - 1 if years > 0 else 0

    # Annualised volatility
    mean_r = sum(strat_rets) / n
    variance = sum((r - mean_r) ** 2 for r in strat_rets) / (n - 1)
    daily_vol = variance ** 0.5
    annual_vol = daily_vol * (252 ** 0.5)

    sharpe = round(strat_annual / annual_vol, 2) if annual_vol > 0 else None

    # Max drawdown (strategy)
    peak, max_dd = strat_vals[0], 0.0
    for v in strat_vals:
        if v > peak:
            peak = v
        dd = (v - peak) / peak
        if dd < max_dd:
            max_dd = dd

    # Avg regime persistence
    transitions, run = 0, 1
    total_run = 0
    for i in range(1, len(series)):
        if series[i]["regime"] == series[i-1]["regime"]:
            run += 1
        else:
            total_run += run
            transitions += 1
            run = 1
    total_run += run
    avg_persist = round(total_run / (transitions + 1), 1) if transitions >= 0 else None

    return {
        "sharpe_proxy":          sharpe,
        "max_drawdown":          round(max_dd * 100, 1),
        "avg_persistence_days":  avg_persist,
        "strategy_annual_return": round(strat_annual * 100, 1),
        "bh_annual_return":       round(bh_annual * 100, 1),
    }


@router.get("/chart-data")
async def get_chart_data():
    """
    Last 730 days of regime history for the marketing-site interactive chart.
    No API key required.
    """
    try:
        from database.queries import fetch_public_chart_data
        rows = await fetch_public_chart_data(limit=730)
    except Exception as exc:
        logger.error("public chart-data DB error: %s", exc)
        raise HTTPException(status_code=503, detail="Data temporarily unavailable")

    # rows are newest-first; reverse so we compute cumulative correctly
    rows_asc = list(reversed(rows))

    # Regime → equity allocation (the strategy being demonstrated)
    _EXPOSURE = {"expansion": 1.00, "recovery": 0.75, "tightening": 0.25, "risk_off": 0.00}

    # Compute cumulative returns (base 100) from daily log-returns
    sp500_cum    = 100.0
    gold_cum     = 100.0
    strategy_cum = 100.0
    series = []
    for row in rows_asc:
        d_sp    = float(row.get("d_sp500") or 0)
        d_gd    = float(row.get("d_gold")  or 0)
        regime  = row.get("regime", "recovery")
        weight  = _EXPOSURE.get(regime, 0.75)
        # Convert log-returns to simple returns, then blend with cash (0%) at weight
        sp500_ret    = math.exp(d_sp) - 1
        gold_ret     = math.exp(d_gd) - 1
        sp500_cum    *= (1 + sp500_ret)
        gold_cum     *= (1 + gold_ret)
        strategy_cum *= (1 + weight * sp500_ret)
        series.append({
            "date": (
                row["time"].strftime("%Y-%m-%d")
                if hasattr(row.get("time"), "strftime")
                else str(row["time"])[:10]
            ),
            "regime": regime,
            "risk_score": round(float(row["risk_score"]), 2) if row.get("risk_score") is not None else 0.0,
            "sp500":    round(sp500_cum, 2),
            "gold":     round(gold_cum, 2),
            "strategy": round(strategy_cum, 2),
        })

    # Compute regime distribution from returned rows
    dist: dict[str, int] = {}
    for row in series:
        dist[row["regime"]] = dist.get(row["regime"], 0) + 1
    total = len(series) or 1
    regime_distribution = {k: round(v / total, 3) for k, v in sorted(dist.items())}

    computed = _compute_stats(series)

    return {
        "days": len(series),
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "series": series,
        "stats": {
            **computed,
            "total_days": len(series),
            "regime_distribution": regime_distribution,
        },
    }


@router.get("/latest")
async def get_public_latest():
    """
    Current regime snapshot for the marketing site terminal display.
    Returns a subset of the full signal package — no API key required.
    """
    try:
        from services.signals import build_signal_package
        pkg = await build_signal_package()
    except Exception as exc:
        logger.error("public latest DB error: %s", exc)
        raise HTTPException(status_code=503, detail="Data temporarily unavailable")

    if pkg is None:
        raise HTTPException(status_code=503, detail="No regime data available yet")

    return {
        "date": pkg["date"],
        "regime": {
            "most_likely": pkg["regime"]["most_likely"],
            "confidence": pkg["regime"]["confidence"],
            "persistence_days": pkg["regime"]["persistence_days"],
            "risk_score": pkg["regime"]["risk_score"],
        },
        "net_liquidity": {
            "zscore": pkg["net_liquidity"]["zscore"],
            "trend": pkg["net_liquidity"]["trend"],
        },
        "equity_exposure": {
            "expansion": 1.0,
            "recovery": 0.75,
            "tightening": 0.25,
            "risk_off": 0.0,
        }.get(pkg["regime"]["most_likely"], 0.0),
    }


@router.get("/regime")
async def get_public_regime():
    """
    Current macro regime — no API key required.

    Returns the live regime, risk score, equity exposure recommendation,
    and a plain-English interpretation. Designed as the free-tier entry point:
    gives enough signal to be useful, links to upgrade for the full package
    (scorecard, factors, forecast, webhook alerts).
    """
    _EXPOSURE = {"expansion": "100%", "recovery": "75%", "tightening": "25%", "risk_off": "0%"}
    _LABEL    = {"expansion": "Expansion", "recovery": "Recovery",
                 "tightening": "Tightening", "risk_off": "Risk-Off"}
    _EMOJI    = {"expansion": "🟢", "recovery": "🔵", "tightening": "🟡", "risk_off": "🔴"}
    _WHAT     = {
        "expansion":  "Fed liquidity is ample, credit spreads are tight, volatility suppressed. Full risk-on positioning is warranted.",
        "recovery":   "Liquidity re-injecting after stress. Risk appetite healing but not fully restored. Positive bias with elevated caution.",
        "tightening": "Fed draining liquidity or hiking. Credit spreads widening. Defensive positioning appropriate — reduce duration and leveraged exposure.",
        "risk_off":   "Acute stress conditions. Spiking spreads and volatility. Capital preservation is the only objective.",
    }

    try:
        from database.queries import fetch_current_regime
        row = await fetch_current_regime()
    except Exception as exc:
        logger.error("public regime DB error: %s", exc)
        raise HTTPException(status_code=503, detail="Data temporarily unavailable")

    if row is None:
        raise HTTPException(status_code=503, detail="No regime data available yet")

    regime = str(row.get("regime", "recovery")).lower()
    risk_score = float(row.get("risk_score") or 0)
    date = str(row.get("time", ""))[:10]

    return {
        "date": date,
        "regime": regime,
        "regime_label": _LABEL.get(regime, regime.title()),
        "emoji": _EMOJI.get(regime, "⚪"),
        "risk_score": round(risk_score, 1),
        "equity_exposure": _EXPOSURE.get(regime, "—"),
        "interpretation": _WHAT.get(regime, ""),
        "upgrade": {
            "message": "Get the full signal package — scorecard, 5-day forecast, webhook alerts, and factor decomposition.",
            "url": "https://macropulse.live/#pricing",
        },
    }


class SubscribeRequest(BaseModel):
    email: EmailStr


@router.post("/subscribe", status_code=202)
async def subscribe(body: SubscribeRequest):
    """
    Newsletter subscribe — captures email for the weekly macro brief.
    No API key required.
    """
    email = str(body.email).strip().lower()  # EmailStr already validated by pydantic

    try:
        from database.queries import create_newsletter_subscriber
        await create_newsletter_subscriber(email)
    except Exception as exc:
        logger.error("newsletter subscribe DB error: %s", exc)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    try:
        from services.email import send_newsletter_confirmation
        send_newsletter_confirmation(email)
    except Exception:
        pass  # email is fire-and-forget

    return {"status": "subscribed"}
