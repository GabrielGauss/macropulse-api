"""Shared pytest fixtures for Phase 5 pipeline quality tests."""
from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def mock_fred_df() -> pd.DataFrame:
    """A minimal FRED DataFrame with all critical columns present and non-NaN."""
    idx = pd.date_range(end=dt.date.today(), periods=60, freq="B")
    return pd.DataFrame(
        {
            "WALCL": np.random.uniform(7_000_000, 8_000_000, 60),
            "DGS10": np.random.uniform(3.5, 5.0, 60),
            "DGS2": np.random.uniform(3.0, 4.5, 60),
            "RRPONTSYD": np.random.uniform(500_000, 700_000, 60),
            "WTREGEN": np.random.uniform(400_000, 600_000, 60),
            "BAMLH0A0HYM2": np.random.uniform(3.0, 5.0, 60),
        },
        index=idx,
    )


@pytest.fixture()
def mock_market_df() -> pd.DataFrame:
    """A minimal market DataFrame with VIX and SP500 present."""
    idx = pd.date_range(end=dt.date.today(), periods=60, freq="B")
    return pd.DataFrame(
        {
            "vix": np.random.uniform(15, 25, 60),
            "sp500": np.random.uniform(4000, 5000, 60),
            "dxy": np.random.uniform(100, 110, 60),
        },
        index=idx,
    )


@pytest.fixture()
def mock_hmm_model_converged() -> MagicMock:
    """A mock HMMModel whose HMM has converged."""
    model = MagicMock()
    model.hmm = MagicMock()
    model.hmm.monitor_ = MagicMock()
    model.hmm.monitor_.converged = True
    model.predict_proba.return_value = np.array([[0.6, 0.2, 0.1, 0.1]] * 60)
    model.predict.return_value = np.zeros(60, dtype=int)
    return model


@pytest.fixture()
def mock_hmm_model_not_converged() -> MagicMock:
    """A mock HMMModel whose HMM did NOT converge."""
    model = MagicMock()
    model.hmm = MagicMock()
    model.hmm.monitor_ = MagicMock()
    model.hmm.monitor_.converged = False
    return model


@pytest.fixture()
def mock_garch_model() -> MagicMock:
    """A mock GARCHModel with a pre-fitted _arch_result."""
    model = MagicMock()
    mock_result = MagicMock()
    mock_forecast = MagicMock()
    mock_forecast.variance.iloc.__getitem__ = MagicMock(return_value=0.25)
    mock_result.forecast.return_value = mock_forecast
    model._arch_result = mock_result
    model._long_run_vol = 1.0
    return model
