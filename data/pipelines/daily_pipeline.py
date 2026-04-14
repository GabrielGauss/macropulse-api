"""
MacroPulse daily pipeline.

Orchestrates the end-to-end flow:
  1. Fetch FRED + market data
  2. Validate raw data
  3. Compute engineered features
  4. Validate features
  5. Store features → TimescaleDB
  6. Data-lag guard
  7. Load frozen models → PCA transform
  8. HMM inference → regime probabilities
  9. Store regime results → TimescaleDB
  10. Detect regime change → fire alerts
  11. Compute & store drift metrics
  12. Broadcast via WebSocket
  13. Log pipeline run
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import time
from typing import Any

import numpy as np
import pandas as pd

from config.settings import get_settings
from data.ingestion.fred_client import fetch_all_fred
from data.ingestion.market_client import fetch_market_data
from data.processing.feature_engineering import (
    MODEL_FEATURE_COLS,
    MODEL_FEATURE_COLS_V1,
    build_features,
)
from database import queries
from models.garch_model import GARCHModel
from models.hmm_model import HMMModel
from models.pca_model import PCAModel
from models.regime_classifier import RegimeClassifier
from services.alerts import alert_drift_warning
from services.drift_monitor import (
    compute_feature_shift,
    compute_pca_variance_drift,
    compute_regime_persistence,
)
from services.validation import validate_features, validate_market_data, validate_raw_fred

logger = logging.getLogger(__name__)

# Critical series — pipeline halts if any are missing or all-NaN.
_CRITICAL_FRED_COLS: frozenset[str] = frozenset({"WALCL", "DGS10", "DGS2"})
_CRITICAL_MARKET_COLS: frozenset[str] = frozenset({"vix"})


def _missing_or_all_nan(df: pd.DataFrame, cols: frozenset[str]) -> set[str]:
    """Return the subset of cols that are absent from df or contain only NaN values."""
    missing: set[str] = set(cols) - set(df.columns)
    for col in cols - missing:
        if df[col].isna().all():
            missing.add(col)
    return missing


async def _log_run(
    status: str,
    data_lag: bool,
    duration: float,
    error: str | None = None,
    model_version: str | None = None,
) -> None:
    """Log a pipeline run to the database (async — must be awaited from async context)."""
    await queries.insert_pipeline_run(
        {
            "run_ts": dt.datetime.now(dt.timezone.utc),
            "status": status,
            "data_lag": data_lag,
            "duration_sec": round(duration, 2),
            "error_message": error,
            "model_version": model_version,
        }
    )


async def _run_daily_pipeline_async(
    target_date: dt.date | None = None,
    model_version: str | None = None,
) -> dict[str, Any]:
    """Async implementation of the daily pipeline. Called via asyncio.run() from sync callers.

    All database query functions are async (asyncpg); this function awaits them directly.
    The public sync entry point run_daily_pipeline() wraps this with asyncio.run().
    """
    settings = get_settings()
    version = model_version or settings.default_model_version
    today = target_date or dt.date.today()
    start = today - dt.timedelta(days=settings.data_lookback_days)
    t0 = time.monotonic()
    data_lag = False

    logger.info("═══ MacroPulse pipeline start (%s) ═══", today)

    # ── 1. Fetch data ────────────────────────────────────────────
    try:
        fred_df = fetch_all_fred(start=start, end=today)
        market_df = fetch_market_data(start=start, end=today)
    except Exception as exc:
        duration = time.monotonic() - t0
        logger.error("Data fetch failed: %s", exc)
        await _log_run("failed", data_lag=False, duration=duration, error=str(exc), model_version=version)
        raise

    # ── 2. Validate raw data ─────────────────────────────────────
    fred_report = validate_raw_fred(fred_df)
    market_report = validate_market_data(market_df)

    if not fred_report.passed or not market_report.passed:
        errors = fred_report.errors + market_report.errors
        duration = time.monotonic() - t0
        msg = f"Raw data validation failed: {errors}"
        await _log_run("failed", data_lag=False, duration=duration, error=msg, model_version=version)
        raise RuntimeError(msg)

    # ── 2b. Critical series guard ────────────────────────────────
    missing_fred = _missing_or_all_nan(fred_df, _CRITICAL_FRED_COLS)
    missing_market = _missing_or_all_nan(market_df, _CRITICAL_MARKET_COLS)

    if missing_fred or missing_market:
        duration = time.monotonic() - t0
        msg = (
            f"Critical series missing or all-NaN: "
            f"FRED={missing_fred or 'none'} market={missing_market or 'none'}"
        )
        logger.error("PIPELINE HALT — %s", msg)
        await _log_run("halted", data_lag=False, duration=duration, error=msg, model_version=version)
        alert_drift_warning("pipeline_halt_critical_data", 1.0, 0.0, today.isoformat())
        return {"status": "halted", "stale_data": True, "reason": msg, "timestamp": today.isoformat()}

    # ── 3. Feature engineering ───────────────────────────────────
    features = build_features(fred_df, market_df)

    # ── 4. Validate features ─────────────────────────────────────
    feat_report = validate_features(features)
    if not feat_report.passed:
        duration = time.monotonic() - t0
        msg = f"Feature validation failed: {feat_report.errors}"
        await _log_run("failed", data_lag=False, duration=duration, error=msg, model_version=version)
        raise RuntimeError(msg)

    # ── 5. Store features ────────────────────────────────────────
    latest_row = features.iloc[-1]
    await queries.upsert_macro_features(
        {
            "time": features.index[-1].to_pydatetime(),
            **{col: float(latest_row[col]) if pd.notna(latest_row[col]) else None for col in features.columns},
        }
    )

    # ── 6. Data-lag guard ────────────────────────────────────────
    latest_fred_date = fred_df.index.max().date() if len(fred_df) else None
    if latest_fred_date and (today - latest_fred_date).days >= 3:
        data_lag = True
        logger.warning("FRED data lag: latest=%s, target=%s", latest_fred_date, today)
        duration = time.monotonic() - t0
        await _log_run("partial", data_lag=True, duration=duration, model_version=version)
        return {"status": "data_lag", "timestamp": today.isoformat()}

    # ── 7. Load frozen models + PCA ──────────────────────────────
    pca_model = PCAModel.load(version)
    hmm_model = HMMModel.load(version)
    classifier = RegimeClassifier.load(version)

    # v1 artifacts were trained on 8 features; v2 uses all 10.
    feature_cols = MODEL_FEATURE_COLS_V1 if version == "v1" else MODEL_FEATURE_COLS
    # Filter to columns actually present — optional commodity columns may be excluded
    # when data was unavailable. For v1, this is a no-op (no commodity cols in V1 set).
    # For v2, a missing commodity column will cause PCA ValueError — intentional (surfaces
    # incompatibility loudly; fix requires model retrain, tracked as tech debt).
    available_cols = [c for c in feature_cols if c in features.columns]
    if len(available_cols) < len(feature_cols):
        excluded = set(feature_cols) - set(available_cols)
        logger.warning("Optional feature columns excluded from PCA input: %s", excluded)
    X = features[available_cols].values
    factors = pca_model.transform(X)

    # ── 7a. GARCH volatility state (replaces simple VIX threshold) ────
    garch_vol_state: str | None = None
    try:
        garch_model = GARCHModel.load(series_name="d_sp500", version=version)
        cond_vol = garch_model.forecast_vol(features["d_sp500"])
        garch_vol_state = garch_model.classify_vol_state(cond_vol)
        logger.info("GARCH vol state: %s (cond_vol=%.4f)", garch_vol_state, cond_vol)
    except Exception as exc:
        logger.warning(
            "GARCH model not found for version=%s; falling back to VIX threshold. (%s)",
            version, exc,
        )

    # Store latest factor row
    lf = factors[-1]
    await queries.upsert_macro_factors(
        {
            "time": features.index[-1].to_pydatetime(),
            "factor_1": float(lf[0]),
            "factor_2": float(lf[1]),
            "factor_3": float(lf[2]) if len(lf) > 2 else None,
            "factor_4": float(lf[3]) if len(lf) > 3 else None,
            "model_version": version,
        }
    )

    # ── 8. HMM inference ─────────────────────────────────────────
    state_probs = hmm_model.predict_proba(factors)
    latest_probs = state_probs[-1]

    # Use GARCH vol state when available; fall back to VIX-diff threshold.
    if garch_vol_state is not None:
        # Override the volatility_state returned by classify() with the
        # GARCH-derived classification.
        result = classifier.classify(latest_probs, vix_diff=None)
        result["volatility_state"] = garch_vol_state
    else:
        vix_diff = float(latest_row["d_vix"]) if pd.notna(latest_row.get("d_vix")) else None
        result = classifier.classify(latest_probs, vix_diff=vix_diff)

    # ── 9. Store regime ──────────────────────────────────────────
    ts_dt = features.index[-1].to_pydatetime()
    ts_iso = features.index[-1].isoformat()
    regime_row = {
        "time": ts_dt,
        "regime": result["regime"],
        "prob_expansion": result["probabilities"].get("expansion", 0),
        "prob_tightening": result["probabilities"].get("tightening", 0),
        "prob_risk_off": result["probabilities"].get("risk_off", 0),
        "prob_recovery": result["probabilities"].get("recovery", 0),
        "risk_score": result["risk_score"],
        "volatility_state": result["volatility_state"],
        "model_version": version,
    }
    await queries.upsert_macro_regime(regime_row)

    # ── 10. Regime change detection + alerting ───────────────────
    # Regime change alert (email + webhook delivery to subscribers)
    try:
        from services.alerts import send_regime_change_alerts
        history = await queries.fetch_regime_history(limit=2)
        if len(history) >= 2 and history[0]["regime"] != history[1]["regime"]:
            await send_regime_change_alerts(
                prev_regime=history[1]["regime"],
                new_regime=history[0]["regime"],
                risk_score=float(history[0].get("risk_score", 0)),
                date=str(history[0].get("time", ""))[:10],
            )
    except Exception as exc:
        logger.warning("regime alert dispatch failed: %s", exc)

    # ── 11. Drift metrics ────────────────────────────────────────
    # X is already filtered to the correct feature_cols above.
    pca_drift = compute_pca_variance_drift(pca_model, X[-60:])
    regimes_seq = hmm_model.predict(factors[-60:])
    persistence = compute_regime_persistence(regimes_seq)
    mean_shift, std_shift = compute_feature_shift(X[:-60], X[-60:])

    await queries.upsert_drift_metrics(
        {
            "time": ts_dt,
            "pca_explained_variance": float(pca_drift),
            "regime_persistence": float(persistence),
            "feature_mean_shift": float(mean_shift),
            "feature_std_shift": float(std_shift),
            "model_version": version,
        }
    )

    # Fire drift alerts if thresholds exceeded
    if pca_drift > settings.pipeline_drift_variance_warn:
        alert_drift_warning("pca_variance_drift", pca_drift, settings.pipeline_drift_variance_warn, ts_iso)
    if persistence > settings.pipeline_drift_persistence_warn:
        alert_drift_warning("regime_persistence", persistence, settings.pipeline_drift_persistence_warn, ts_iso)
    if mean_shift > settings.pipeline_drift_feature_shift_warn:
        alert_drift_warning("feature_mean_shift", mean_shift, settings.pipeline_drift_feature_shift_warn, ts_iso)

    # ── 12. WebSocket broadcast ──────────────────────────────────
    output = {
        "timestamp": ts_iso,
        "macro_regime": result["regime"],
        "risk_score": result["risk_score"],
        "probabilities": result["probabilities"],
        "volatility_state": result["volatility_state"],
        "model_version": version,
    }
    try:
        from api.routes.websocket import notify_regime_update
        notify_regime_update(output)
    except Exception:
        pass  # CLI mode — no event loop

    # ── 13. Log success ──────────────────────────────────────────
    duration = time.monotonic() - t0
    await _log_run("success", data_lag=False, duration=duration, model_version=version)

    logger.info("═══ Pipeline complete in %.1fs ═══  %s", duration, output)

    # ── 14. Daily brief — narrative + X + Discord signal post ────
    try:
        from services.scorecard import build_scorecard
        from services.narrative import generate_narrative
        from services.twitter import post_daily_tweet
        from services.discord import post_daily_signal
        scorecard = await build_scorecard()
        narrative = generate_narrative(regime_row, scorecard)
        post_daily_tweet(regime_row, scorecard)
        post_daily_signal(regime_row, scorecard, narrative=narrative)
        logger.info("Daily brief dispatched (narrative: %d chars)", len(narrative))
    except Exception as exc:
        logger.warning("daily signal broadcast failed: %s", exc)

    return output


def run_daily_pipeline(
    target_date: dt.date | None = None,
    model_version: str | None = None,
) -> dict[str, Any]:
    """
    Execute the daily macro regime pipeline (sync entry point).

    This wrapper exists because APScheduler BackgroundScheduler runs jobs in
    threads where no event loop is active. It delegates to the async
    implementation via asyncio.run().

    Parameters
    ----------
    target_date   : override for the pipeline date (default: today).
    model_version : which frozen model artifacts to use.

    Returns
    -------
    dict – The regime output for the target date, or a partial result
           if data lag is detected.
    """
    return asyncio.run(_run_daily_pipeline_async(target_date=target_date, model_version=model_version))
