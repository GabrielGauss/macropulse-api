"""
MacroPulse Scorecard — 5 normalized macro signals on a -1.0 to +1.0 scale.

Signals are derived entirely from existing macro_features data so no new
data sources are required.  Each value is a z-score of a 20-day rolling
momentum versus a trailing 252-day historical window, clamped to [-1, 1].

Signals:
  growth_momentum    — yield curve slope momentum (steepening = positive)
  inflation_momentum — 10Y yield momentum (rising rates = higher inflation pressure)
  liquidity          — net Fed liquidity level vs 2-year z-score
  financial_stress   — inverted (HY spread + VIX) momentum (calm = positive)
  dollar_strength    — DXY momentum (rising dollar = positive)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from database import queries

logger = logging.getLogger(__name__)

# Window for momentum (trading days)
_MOMENTUM_WINDOW = 20
# Lookback for z-score normalization
_ZSCORE_LOOKBACK = 252


def _rolling_sums(values: list[float], window: int = _MOMENTUM_WINDOW) -> list[float]:
    """Compute rolling sum of fixed window across a chronological list."""
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        result.append(float(sum(values[start : i + 1])))
    return result


def _zscore_to_gauge(series: list[float], lookback: int = _ZSCORE_LOOKBACK) -> float:
    """
    Z-score the last value of `series` vs a trailing window.

    Returns a float clamped to [-1.0, +1.0] (maps raw z of ±2 → ±1).
    """
    if len(series) < 5:
        return 0.0
    window = series[-lookback:] if len(series) > lookback else series
    mean = float(np.mean(window))
    std = float(np.std(window))
    if std < 1e-12:
        return 0.0
    z = (series[-1] - mean) / std
    return float(np.clip(z / 2.0, -1.0, 1.0))


async def build_scorecard() -> dict[str, Any]:
    """
    Compute the 5 normalized gauge signals from the latest macro_features rows.

    Returns:
        {
          "growth_momentum":    float  in [-1, 1],
          "inflation_momentum": float  in [-1, 1],
          "liquidity":          float  in [-1, 1],
          "financial_stress":   float  in [-1, 1],   # positive = calm
          "dollar_strength":    float  in [-1, 1],   # positive = strong USD
          "computed_at":        str    ISO-8601,
        }
    """
    import datetime as dt

    rows = await queries.fetch_latest_features(limit=504)
    if not rows:
        return {
            "growth_momentum": 0.0,
            "inflation_momentum": 0.0,
            "liquidity": 0.0,
            "financial_stress": 0.0,
            "dollar_strength": 0.0,
            "computed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }

    # Rows come DESC (newest first) — reverse to chronological for rolling ops
    rows_asc = list(reversed(rows))

    def _extract(key: str) -> list[float]:
        return [float(r[key]) for r in rows_asc if r.get(key) is not None]

    # ── Yield curve slope momentum (steepening = growth = positive) ──
    d_yc = _extract("d_yield_curve")
    growth_gauge = _zscore_to_gauge(_rolling_sums(d_yc)) if len(d_yc) >= 5 else 0.0

    # ── 10Y yield momentum (rising 10Y = inflation pressure = positive) ──
    d_10y = _extract("d_10y")
    inflation_gauge = _zscore_to_gauge(_rolling_sums(d_10y)) if len(d_10y) >= 5 else 0.0

    # ── Net liquidity level z-score vs 2-year window ──────────────────
    levels = [float(r["net_liquidity"]) for r in rows_asc if r.get("net_liquidity") is not None]
    liquidity_gauge = _zscore_to_gauge(levels) if len(levels) >= 5 else 0.0

    # ── Financial stress — inverted (HY spread + VIX momentum) ───────
    # Positive = low stress = calm markets
    d_hy = _extract("d_hy_spread")
    d_vix = _extract("d_vix")
    # Use whichever is longer; align by truncating to min length
    n = min(len(d_hy), len(d_vix))
    if n >= 5:
        combined = [(d_hy[i] + d_vix[i]) / 2.0 for i in range(n)]
        stress_gauge = -_zscore_to_gauge(_rolling_sums(combined))
    elif len(d_hy) >= 5:
        stress_gauge = -_zscore_to_gauge(_rolling_sums(d_hy))
    elif len(d_vix) >= 5:
        stress_gauge = -_zscore_to_gauge(_rolling_sums(d_vix))
    else:
        stress_gauge = 0.0

    # ── Dollar strength — DXY momentum ────────────────────────────────
    d_dxy = _extract("d_dxy")
    dollar_gauge = _zscore_to_gauge(_rolling_sums(d_dxy)) if len(d_dxy) >= 5 else 0.0

    return {
        "growth_momentum":    round(growth_gauge, 3),
        "inflation_momentum": round(inflation_gauge, 3),
        "liquidity":          round(liquidity_gauge, 3),
        "financial_stress":   round(stress_gauge, 3),
        "dollar_strength":    round(dollar_gauge, 3),
        "computed_at":        dt.datetime.now(dt.timezone.utc).isoformat(),
    }
