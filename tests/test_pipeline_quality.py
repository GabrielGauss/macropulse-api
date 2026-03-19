"""
Phase 5 — Pipeline Quality and Noise Reduction.

Verification tests for PIPE-01 through PIPE-05.
Each test starts as an xfail stub; implementation plans convert them to
passing tests by adding the production code.
"""
from __future__ import annotations

import os
import pytest
import numpy as np
import pandas as pd


# ── PIPE-01: Critical FRED failure halts pipeline ─────────────────────

@pytest.mark.xfail(strict=False, reason="stub — implementation pending")
def test_critical_fred_failure_halts(mock_fred_df, mock_market_df):
    """Pipeline returns status='halted' with stale_data=True when WALCL is all-NaN."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=False, reason="stub — implementation pending")
def test_optional_series_excluded_not_zeroed(mock_fred_df, mock_market_df):
    """d_gold column is absent from build_features() output when gold data unavailable."""
    pytest.fail("not implemented")


# ── PIPE-02: VIX failure halts pipeline ───────────────────────────────

@pytest.mark.xfail(strict=False, reason="stub — implementation pending")
def test_vix_failure_halts_pipeline(mock_fred_df, mock_market_df):
    """Pipeline returns status='halted' when VIX column is all-NaN."""
    pytest.fail("not implemented")


# ── PIPE-03: HMM convergence guard ────────────────────────────────────

@pytest.mark.xfail(strict=False, reason="stub — implementation pending")
def test_hmm_convergence_check(mock_hmm_model_not_converged):
    """HMMModel.predict_proba raises RuntimeError when monitor_.converged is False."""
    pytest.fail("not implemented")


# ── PIPE-04: GARCH no-refit on inference ──────────────────────────────

@pytest.mark.xfail(strict=False, reason="stub — implementation pending")
def test_garch_no_refit_on_inference(mock_garch_model):
    """GARCHModel.forecast_vol() uses stored _arch_result.forecast(), not arch_model().fit()."""
    pytest.fail("not implemented")


# ── PIPE-05: Thresholds in settings ──────────────────────────────────

@pytest.mark.xfail(strict=False, reason="stub — implementation pending")
def test_thresholds_in_settings():
    """All phase-5 threshold fields exist on Settings with correct defaults."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=False, reason="stub — implementation pending")
def test_settings_env_override():
    """GARCH_VOL_LOW env var overrides the garch_vol_low setting value."""
    pytest.fail("not implemented")
