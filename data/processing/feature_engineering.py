"""
Feature engineering for MacroPulse.

Transforms raw macro and market series into stationary features
suitable for PCA / HMM consumption.

Core feature set (8 columns, always present when data is valid):
    d_liquidity, d_sp500, d_vix, d_dxy, d_hy_spread,
    d_yield_curve, d_10y, d_2y

Optional commodity features (absent from output when data is unavailable):
    d_gold, d_oil, d_btc, d_eth
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_net_liquidity(fred_df: pd.DataFrame) -> pd.Series:
    """
    Compute the Net Liquidity Proxy:

        NetLiquidity = WALCL − WTREGEN − RRPONTSYD

    All inputs are in millions of USD (FRED native units).
    """
    required = {"WALCL", "WTREGEN", "RRPONTSYD"}
    missing = required - set(fred_df.columns)
    if missing:
        raise KeyError(f"Missing FRED columns for liquidity calc: {missing}")

    net_liq = fred_df["WALCL"] - fred_df["WTREGEN"] - fred_df["RRPONTSYD"]
    net_liq.name = "net_liquidity"
    return net_liq


def build_features(
    fred_df: pd.DataFrame,
    market_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine FRED and market data, then produce stationary features.

    Returns a DataFrame with core columns:
        net_liquidity, d_liquidity, d_sp500, d_vix, d_dxy,
        d_hy_spread, d_yield_curve, d_10y, d_2y

    Optional commodity columns (d_gold, d_oil, d_btc, d_eth) are included
    only when source data is available. When unavailable, the column is
    absent from the output entirely — not zero-filled.
    """
    # ── Normalise both indices to tz-naive date-only DatetimeIndex ───
    fred_df = fred_df.copy()
    fred_df.index = pd.to_datetime(fred_df.index.date if hasattr(fred_df.index, "date") else fred_df.index)

    market_df = market_df.copy()
    market_df.index = pd.to_datetime(market_df.index)

    # ── Merge on date ────────────────────────────────────────────
    combined = fred_df.join(market_df, how="outer").sort_index().ffill()

    # ── Net Liquidity ────────────────────────────────────────────
    combined["net_liquidity"] = compute_net_liquidity(combined)

    # ── Yield curve spread ───────────────────────────────────────
    combined["yield_curve"] = combined["DGS10"] - combined["DGS2"]

    # ── Stationary transformations ───────────────────────────────
    features = pd.DataFrame(index=combined.index)
    features["net_liquidity"] = combined["net_liquidity"]

    # Log returns for price-like series
    features["d_sp500"] = np.log(combined["sp500"]).diff()

    # First differences for level / spread series
    features["d_liquidity"] = combined["net_liquidity"].diff()
    features["d_vix"] = combined["vix"].diff() if "vix" in combined.columns else pd.Series(0.0, index=combined.index)
    if "dxy" in combined.columns and combined["dxy"].notna().any():
        features["d_dxy"] = combined["dxy"].diff().fillna(0.0)
    else:
        logger.warning("DXY data unavailable; d_dxy set to 0.")
        features["d_dxy"] = pd.Series(0.0, index=combined.index)
    features["d_hy_spread"] = combined["BAMLH0A0HYM2"].diff()
    features["d_yield_curve"] = combined["yield_curve"].diff()
    features["d_10y"] = combined["DGS10"].diff()
    features["d_2y"] = combined["DGS2"].diff()

    # Optional commodity features — column is absent from output when data is unavailable.
    # Do NOT zero-fill: a missing column is preferable to a signal-corrupting zero series.
    if "gold" in combined.columns and combined["gold"].notna().any():
        features["d_gold"] = np.log(combined["gold"].replace(0, np.nan)).diff()
    else:
        logger.warning("Gold data unavailable; d_gold excluded from features.")

    if "oil" in combined.columns and combined["oil"].notna().any():
        features["d_oil"] = np.log(combined["oil"].replace(0, np.nan)).diff()
    else:
        logger.warning("Oil data unavailable; d_oil excluded from features.")

    if "btc" in combined.columns and combined["btc"].notna().any():
        features["d_btc"] = np.log(combined["btc"].replace(0, np.nan)).diff()
    else:
        logger.warning("BTC data unavailable; d_btc excluded from features.")

    if "eth" in combined.columns and combined["eth"].notna().any():
        features["d_eth"] = np.log(combined["eth"].replace(0, np.nan)).diff()
    else:
        logger.warning("ETH data unavailable; d_eth excluded from features.")

    features = features.dropna()
    logger.info("Built feature matrix: %s", features.shape)
    return features


# Feature columns used for model input (excludes raw net_liquidity).
# v1 models were trained on the first 8 features only; v2 models use
# all 10 (including d_gold and d_oil).
MODEL_FEATURE_COLS: list[str] = [
    "d_liquidity",
    "d_sp500",
    "d_vix",
    "d_dxy",
    "d_hy_spread",
    "d_yield_curve",
    "d_10y",
    "d_2y",
    "d_gold",
    "d_oil",
]

# Legacy 8-feature set for backward compatibility with v1 artifacts.
MODEL_FEATURE_COLS_V1: list[str] = [
    "d_liquidity",
    "d_sp500",
    "d_vix",
    "d_dxy",
    "d_hy_spread",
    "d_yield_curve",
    "d_10y",
    "d_2y",
]
