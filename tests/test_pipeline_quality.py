"""
Phase 5 — Pipeline Quality and Noise Reduction.

Verification tests for PIPE-01 through PIPE-05.
Each test starts as an xfail stub; implementation plans convert them to
passing tests by adding the production code.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ── PIPE-01: Critical FRED failure halts pipeline ─────────────────────


def test_critical_fred_failure_halts(mock_fred_df, mock_market_df):
    """Pipeline returns status='halted' with stale_data=True when WALCL is all-NaN."""
    mock_fred_df["WALCL"] = np.nan  # all-NaN critical series

    with patch("data.pipelines.daily_pipeline.fetch_all_fred", return_value=mock_fred_df), \
         patch("data.pipelines.daily_pipeline.fetch_market_data", return_value=mock_market_df), \
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


def test_optional_series_excluded_not_zeroed(mock_fred_df, mock_market_df):
    """d_gold column is absent from build_features() output when gold data unavailable."""
    from data.processing.feature_engineering import build_features

    # mock_market_df has no gold column — d_gold must not appear in output
    assert "gold" not in mock_market_df.columns
    features = build_features(mock_fred_df, mock_market_df)
    assert "d_gold" not in features.columns, "d_gold must be excluded, not zero-filled"
    assert "d_oil" not in features.columns, "d_oil must be excluded, not zero-filled"


# ── PIPE-02: VIX failure halts pipeline ───────────────────────────────


def test_vix_failure_halts_pipeline(mock_fred_df, mock_market_df):
    """Pipeline returns status='halted' when VIX column is all-NaN."""
    mock_market_df["vix"] = np.nan  # all-NaN VIX

    with patch("data.pipelines.daily_pipeline.fetch_all_fred", return_value=mock_fred_df), \
         patch("data.pipelines.daily_pipeline.fetch_market_data", return_value=mock_market_df), \
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


# ── PIPE-03: HMM convergence guard ────────────────────────────────────


def test_hmm_convergence_check():
    """HMMModel.predict_proba raises RuntimeError when monitor_.converged is False."""
    from models.hmm_model import HMMModel

    model = object.__new__(HMMModel)
    model.hmm = MagicMock()
    model.hmm.monitor_ = MagicMock()
    model.hmm.monitor_.converged = False

    with pytest.raises(RuntimeError, match="did not converge"):
        model.predict_proba(np.zeros((5, 4)))


# ── PIPE-04: GARCH no-refit on inference ──────────────────────────────


def test_garch_no_refit_on_inference():
    """GARCHModel.forecast_vol() uses stored _arch_result.forecast(), not arch_model().fit()."""
    import datetime as dt

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


# ── PIPE-05: Thresholds in settings ──────────────────────────────────

@pytest.mark.xfail(strict=False, reason="stub — implementation pending")
def test_thresholds_in_settings():
    """All phase-5 threshold fields exist on Settings with correct defaults."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=False, reason="stub — implementation pending")
def test_settings_env_override():
    """GARCH_VOL_LOW env var overrides the garch_vol_low setting value."""
    pytest.fail("not implemented")
