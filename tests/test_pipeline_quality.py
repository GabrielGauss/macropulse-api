"""
Tests for pipeline quality requirements (PIPE-01 through PIPE-05).

Phase 5: Pipeline Quality and Noise Reduction
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────


def _base_fred_df():
    idx = pd.date_range(end=dt.date.today(), periods=60, freq="B")
    return pd.DataFrame({
        "WALCL": [7e6] * 60,
        "DGS10": [4.0] * 60,
        "DGS2": [3.5] * 60,
        "RRPONTSYD": [5e5] * 60,
        "WTREGEN": [4e5] * 60,
        "BAMLH0A0HYM2": [3.5] * 60,
    }, index=idx)


def _base_market_df():
    idx = pd.date_range(end=dt.date.today(), periods=60, freq="B")
    return pd.DataFrame({
        "vix": [20.0] * 60,
        "sp500": [4500.0] * 60,
        "dxy": [105.0] * 60,
    }, index=idx)


# ── PIPE-01: Critical series halt ─────────────────────────────────────────────


def test_critical_fred_failure_halts():
    """When WALCL is all-NaN, run_daily_pipeline() must return status='halted'."""
    fred_df = _base_fred_df()
    fred_df["WALCL"] = np.nan  # all-NaN critical series
    mkt_df = _base_market_df()

    with patch("data.pipelines.daily_pipeline.fetch_all_fred", return_value=fred_df), \
         patch("data.pipelines.daily_pipeline.fetch_market_data", return_value=mkt_df), \
         patch("data.pipelines.daily_pipeline.validate_raw_fred") as mock_val_fred, \
         patch("data.pipelines.daily_pipeline.validate_market_data") as mock_val_mkt, \
         patch("data.pipelines.daily_pipeline.queries.insert_pipeline_run"), \
         patch("data.pipelines.daily_pipeline.alert_drift_warning"):
        mock_val_fred.return_value = MagicMock(passed=True, errors=[])
        mock_val_mkt.return_value = MagicMock(passed=True, errors=[])
        from data.pipelines.daily_pipeline import run_daily_pipeline
        result = run_daily_pipeline()

    assert result["status"] == "halted"
    assert result.get("stale_data") is True


def test_vix_failure_halts_pipeline():
    """When VIX is all-NaN, run_daily_pipeline() must return status='halted'."""
    fred_df = _base_fred_df()
    mkt_df = _base_market_df()
    mkt_df["vix"] = np.nan  # all-NaN VIX

    with patch("data.pipelines.daily_pipeline.fetch_all_fred", return_value=fred_df), \
         patch("data.pipelines.daily_pipeline.fetch_market_data", return_value=mkt_df), \
         patch("data.pipelines.daily_pipeline.validate_raw_fred") as mock_val_fred, \
         patch("data.pipelines.daily_pipeline.validate_market_data") as mock_val_mkt, \
         patch("data.pipelines.daily_pipeline.queries.insert_pipeline_run"), \
         patch("data.pipelines.daily_pipeline.alert_drift_warning"):
        mock_val_fred.return_value = MagicMock(passed=True, errors=[])
        mock_val_mkt.return_value = MagicMock(passed=True, errors=[])
        from data.pipelines.daily_pipeline import run_daily_pipeline
        result = run_daily_pipeline()

    assert result["status"] == "halted"
    assert result.get("stale_data") is True


# ── PIPE-02: Optional column exclusion ────────────────────────────────────────


def test_optional_series_excluded_not_zeroed():
    """build_features() must exclude d_gold/d_oil columns when source data is absent."""
    from data.processing.feature_engineering import build_features

    idx = pd.date_range(end=dt.date.today(), periods=60, freq="B")
    fred = pd.DataFrame({
        "WALCL": [7e6] * 60,
        "DGS10": [4.0] * 60,
        "DGS2": [3.5] * 60,
        "RRPONTSYD": [5e5] * 60,
        "WTREGEN": [4e5] * 60,
        "BAMLH0A0HYM2": [3.5] * 60,
    }, index=idx)
    mkt = pd.DataFrame({
        "vix": [20.0] * 60,
        "sp500": [4500.0] * 60,  # no gold, no oil
    }, index=idx)

    features = build_features(fred, mkt)
    assert "d_gold" not in features.columns, "d_gold must be excluded, not zero-filled"
    assert "d_oil" not in features.columns, "d_oil must be excluded, not zero-filled"


# ── PIPE-03: HMM convergence guard ────────────────────────────────────────────


def test_hmm_convergence_check():
    """HMMModel.predict_proba raises RuntimeError when monitor_.converged is False."""
    from models.hmm_model import HMMModel

    model = object.__new__(HMMModel)
    model.hmm = MagicMock()
    model.hmm.monitor_ = MagicMock()
    model.hmm.monitor_.converged = False

    with pytest.raises(RuntimeError, match="did not converge"):
        model.predict_proba(np.zeros((5, 4)))


# ── PIPE-04: GARCH no refit on inference ──────────────────────────────────────


def test_garch_no_refit_on_inference():
    """GARCHModel.forecast_vol() must use stored _arch_result, not re-fit."""
    from models.garch_model import GARCHModel

    model = object.__new__(GARCHModel)
    model.series_name = "test"
    model._long_run_vol = 1.0
    mock_result = MagicMock()
    mock_forecast = MagicMock()
    mock_forecast.variance.iloc.__getitem__ = MagicMock(return_value=0.25)
    mock_result.forecast.return_value = mock_forecast
    model._arch_result = mock_result

    idx = pd.date_range(end=dt.date.today(), periods=60, freq="B")
    returns = pd.Series(np.random.normal(0, 0.01, 60), index=idx)

    with patch("models.garch_model.arch_model") as mock_arch:
        model.forecast_vol(returns)
        assert not mock_arch.called, "arch_model() must NOT be called — use stored result"
        assert mock_result.forecast.called, "_arch_result.forecast() must be called"


# ── Stubs for future plans ─────────────────────────────────────────────────────


@pytest.mark.xfail(reason="PIPE-05: threshold settings not yet implemented", strict=False)
def test_thresholds_in_settings():
    """All magic-number thresholds are accessible as settings attributes."""
    from config.settings import get_settings

    s = get_settings()
    assert hasattr(s, "regime_confidence_high"), "missing regime_confidence_high"
    assert hasattr(s, "regime_confidence_low"), "missing regime_confidence_low"


@pytest.mark.xfail(reason="PIPE-05: env-override for thresholds not yet implemented", strict=False)
def test_settings_env_override():
    """Threshold settings can be overridden via environment variable."""
    import os

    os.environ["REGIME_CONFIDENCE_HIGH"] = "0.80"
    try:
        from config.settings import get_settings

        s = get_settings()
        assert float(s.regime_confidence_high) == 0.80
    finally:
        os.environ.pop("REGIME_CONFIDENCE_HIGH", None)
