"""
Tests for new v1.9 endpoints — TEST-06.

Covers:
  GET /v1/account
  GET /v1/public/regime
  GET /v1/forecast
  GET /v1/signals/history
  GET /v1/irl/heartbeat
  GET /v1/irl/audit

All DB and service calls are mocked — no live database or network required.
Handlers are called directly so require_api_key / require_paid is bypassed
by passing key_record dicts as arguments.
"""
from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ───────────────────────────────────────────────────────────────────


def _key(tier: str = "pro", product_line: str = "macropulse", **kwargs) -> dict:
    return {
        "user_id": 42,
        "email": "test@example.com",
        "tier": tier,
        "product_line": product_line,
        "key_prefix": "mp_test123",
        "agent_count": 1,
        "payment_status": "active",
        "is_active": True,
        **kwargs,
    }


# ── GET /v1/account ───────────────────────────────────────────────────────────


async def test_account_returns_expected_fields():
    """get_account returns tier, product, usage, billing_portal for a valid key."""
    from api.routes.account import get_account

    with patch("database.queries.get_daily_usage_by_prefix", new=AsyncMock(return_value=5)):
        result = await get_account(key_record=_key(tier="pro"))

    assert result["tier"] == "pro"
    assert result["tier_label"] == "Pro"
    assert result["product"] == "MacroPulse"
    assert result["usage"]["daily_requests"] == 5
    assert "billing_portal" in result
    assert "features" in result
    assert isinstance(result["features"], list)


async def test_account_irl_product_billing_url():
    """IRL product_line returns the IRL pricing URL, not the dashboard URL."""
    from api.routes.account import get_account

    with patch("database.queries.get_daily_usage_by_prefix", new=AsyncMock(return_value=0)):
        result = await get_account(key_record=_key(tier="irl_audit", product_line="irl"))

    assert "irl" in result["billing_portal"]


async def test_account_usage_db_error_falls_back_to_zero():
    """If the usage DB call raises, daily_requests silently defaults to 0."""
    from api.routes.account import get_account

    with patch("database.queries.get_daily_usage_by_prefix", new=AsyncMock(side_effect=Exception("db down"))):
        result = await get_account(key_record=_key())

    assert result["usage"]["daily_requests"] == 0


async def test_account_unknown_tier_label_is_titlecased():
    """Unknown tier gets a human-readable fallback label."""
    from api.routes.account import get_account

    with patch("database.queries.get_daily_usage_by_prefix", new=AsyncMock(return_value=0)):
        result = await get_account(key_record=_key(tier="future_tier"))

    assert result["tier_label"] == "Future Tier"


# ── GET /v1/public/regime ─────────────────────────────────────────────────────


async def test_public_regime_returns_regime_data():
    """Returns current regime, risk score, and interpretation — no auth required."""
    from api.routes.public import get_public_regime

    fake_row = {"regime": "expansion", "risk_score": 25.5, "time": "2026-01-15"}

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=fake_row)):
        result = await get_public_regime()

    assert result["regime"] == "expansion"
    assert result["regime_label"] == "Expansion"
    assert result["risk_score"] == 25.5
    assert result["equity_exposure"] == "100%"
    assert "interpretation" in result
    assert len(result["interpretation"]) > 0
    assert "upgrade" in result


async def test_public_regime_returns_503_when_no_data():
    """Returns HTTP 503 when the DB has no regime row."""
    from api.routes.public import get_public_regime

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await get_public_regime()
    assert exc.value.status_code == 503


async def test_public_regime_returns_503_on_db_error():
    """DB exception → 503 (not 500 — masked gracefully)."""
    from api.routes.public import get_public_regime

    with patch("database.queries.fetch_current_regime", new=AsyncMock(side_effect=Exception("db error"))):
        with pytest.raises(HTTPException) as exc:
            await get_public_regime()
    assert exc.value.status_code == 503


async def test_public_regime_risk_off_exposure_zero():
    """risk_off regime maps to 0% equity exposure."""
    from api.routes.public import get_public_regime

    fake_row = {"regime": "risk_off", "risk_score": 88.0, "time": "2026-01-15"}

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=fake_row)):
        result = await get_public_regime()

    assert result["equity_exposure"] == "0%"
    assert result["emoji"] == "🔴"


# ── GET /v1/forecast ──────────────────────────────────────────────────────────


async def test_forecast_returns_503_when_no_history():
    """Empty regime history → 503 with a helpful message."""
    from api.routes.forecast import get_forecast

    with patch("database.queries.fetch_regime_history", new=AsyncMock(return_value=[])):
        with pytest.raises(HTTPException) as exc:
            await get_forecast(horizon=5, key_record=_key(tier="starter"))
    assert exc.value.status_code == 503
    assert "pipeline" in exc.value.detail.lower()


async def test_forecast_returns_503_when_insufficient_history():
    """Fewer than 10 history rows → 503 with count in message."""
    from api.routes.forecast import get_forecast

    few_rows = [{"time": dt.date(2026, 1, i), "regime": "expansion",
                 "prob_expansion": 0.8, "prob_recovery": 0.1,
                 "prob_tightening": 0.05, "prob_risk_off": 0.05,
                 "risk_score": 20.0} for i in range(1, 6)]

    with patch("database.queries.fetch_regime_history", new=AsyncMock(return_value=few_rows)):
        with pytest.raises(HTTPException) as exc:
            await get_forecast(horizon=5, key_record=_key(tier="starter"))
    assert exc.value.status_code == 503
    assert "Insufficient" in exc.value.detail


async def test_forecast_returns_500_when_missing_columns():
    """History rows missing required prob columns → 500."""
    from api.routes.forecast import get_forecast

    # 15 rows but without the probability columns
    rows = [{"time": dt.date(2026, 1, (i % 28) + 1), "regime": "expansion",
             "risk_score": 20.0} for i in range(15)]

    with patch("database.queries.fetch_regime_history", new=AsyncMock(return_value=rows)):
        with pytest.raises(HTTPException) as exc:
            await get_forecast(horizon=5, key_record=_key(tier="starter"))
    assert exc.value.status_code == 500
    assert "missing columns" in exc.value.detail


async def test_forecast_returns_forecast_rows():
    """Happy path: valid history + working forecaster → ForecastResponse returned."""
    from api.routes.forecast import get_forecast

    rows = [
        {
            "time": dt.date(2026, 1, (i % 28) + 1),
            "regime": "expansion",
            "prob_expansion": 0.7,
            "prob_recovery": 0.15,
            "prob_tightening": 0.1,
            "prob_risk_off": 0.05,
            "risk_score": float(20 + i),
        }
        for i in range(20)
    ]

    # ForecastRow fields: date, prob_expansion, prob_tightening, prob_risk_off,
    # prob_recovery, risk_score, confidence — all required
    fake_forecast = [
        {
            "date": dt.date(2026, 2, i + 1),
            "prob_expansion": 0.65,
            "prob_recovery": 0.20,
            "prob_tightening": 0.10,
            "prob_risk_off": 0.05,
            "confidence": 0.75,
            "risk_score": 22.0,
        }
        for i in range(5)
    ]

    with patch("database.queries.fetch_regime_history", new=AsyncMock(return_value=rows)), \
         patch("api.routes.forecast.forecast_regime_probabilities", return_value=fake_forecast):
        result = await get_forecast(horizon=5, key_record=_key(tier="starter"))

    assert result.horizon == 5
    assert len(result.forecast) == 5
    assert result.forecast[0].prob_expansion == pytest.approx(0.65)


# ── GET /v1/signals/history ───────────────────────────────────────────────────


async def test_signals_history_returns_list_of_rows():
    """Returns a list of date/regime/risk_score rows for valid auth."""
    from api.routes.signals import get_signal_history

    fake_rows = [
        {
            "time": dt.date(2026, 1, 15),
            "regime": "expansion",
            "risk_score": 22.5,
            "prob_expansion": 0.7,
            "prob_recovery": 0.15,
            "prob_tightening": 0.1,
            "prob_risk_off": 0.05,
        },
        {
            "time": dt.date(2026, 1, 14),
            "regime": "expansion",
            "risk_score": 21.0,
            "prob_expansion": 0.68,
            "prob_recovery": 0.17,
            "prob_tightening": 0.1,
            "prob_risk_off": 0.05,
        },
    ]

    with patch("database.queries.fetch_regime_history", new=AsyncMock(return_value=fake_rows)):
        result = await get_signal_history(days=90, key_record=_key(tier="free"))

    assert len(result) == 2
    assert result[0]["regime"] == "expansion"
    assert result[0]["risk_score"] == 22.5
    assert "prob_expansion" in result[0]
    assert result[0]["date"] == "2026-01-15"


async def test_signals_history_returns_empty_list_when_no_data():
    """Empty DB result → empty list, not an error."""
    from api.routes.signals import get_signal_history

    with patch("database.queries.fetch_regime_history", new=AsyncMock(return_value=[])):
        result = await get_signal_history(days=30, key_record=_key(tier="starter"))

    assert result == []


# ── GET /v1/irl/heartbeat ─────────────────────────────────────────────────────
# The tier check lives in _require_irl (a FastAPI dependency), not the handler body.
# We test the guard function directly and test the handler with appropriate mocks.


def test_irl_guard_blocks_macropulse_tier():
    """_require_irl raises 403 for non-IRL tiers (pro, starter, free)."""
    from api.routes.irl import _require_irl

    for tier in ("pro", "starter", "free"):
        with pytest.raises(HTTPException) as exc:
            _require_irl(key_record=_key(tier=tier))
        assert exc.value.status_code == 403
        assert "IRL Engine" in exc.value.detail


def test_irl_guard_allows_irl_tiers():
    """_require_irl passes irl_sidecar, irl_audit, and owner through."""
    from api.routes.irl import _require_irl

    for tier in ("irl_sidecar", "irl_audit", "owner"):
        result = _require_irl(key_record=_key(tier=tier))
        assert result["tier"] == tier


def test_irl_audit_guard_blocks_sidecar():
    """_require_irl_audit raises 403 for irl_sidecar — L2 requires irl_audit tier."""
    from api.routes.irl import _require_irl_audit

    with pytest.raises(HTTPException) as exc:
        _require_irl_audit(key_record=_key(tier="irl_sidecar"))
    assert exc.value.status_code == 403
    assert "L2" in exc.value.detail or "Audit" in exc.value.detail


def test_irl_audit_guard_allows_audit_and_owner():
    """_require_irl_audit passes irl_audit and owner tiers."""
    from api.routes.irl import _require_irl_audit

    for tier in ("irl_audit", "owner"):
        result = _require_irl_audit(key_record=_key(tier=tier))
        assert result["tier"] == tier


async def test_irl_heartbeat_returns_heartbeat_for_irl_sidecar():
    """irl_sidecar tier can call /heartbeat successfully."""
    from api.routes.irl import get_heartbeat
    from services.heartbeat_service import Heartbeat

    fake_hb = Heartbeat(
        sequence_id=1001,
        timestamp_ms=1700000000000,
        regime_id=2,
        mta_ref="abc123def456",
        signature="sig==",
    )

    # Patch the name in the irl module's namespace (imported at top of irl.py)
    with patch("api.routes.irl.issue_heartbeat", new=AsyncMock(return_value=fake_hb)):
        result = await get_heartbeat(key_record=_key(tier="irl_sidecar"))

    assert result.sequence_id == 1001
    assert result.regime_id == 2
    assert result.signature == "sig=="


async def test_irl_heartbeat_returns_503_on_service_error():
    """RuntimeError from issue_heartbeat → 503."""
    from api.routes.irl import get_heartbeat

    with patch("api.routes.irl.issue_heartbeat",
               new=AsyncMock(side_effect=RuntimeError("MTA signing key not set"))):
        with pytest.raises(HTTPException) as exc:
            await get_heartbeat(key_record=_key(tier="irl_audit"))
    assert exc.value.status_code == 503


async def test_irl_heartbeat_owner_key_allowed():
    """Owner key passes the IRL guard and gets a heartbeat."""
    from api.routes.irl import get_heartbeat
    from services.heartbeat_service import Heartbeat

    fake_hb = Heartbeat(sequence_id=1, timestamp_ms=1700000000000,
                        regime_id=1, mta_ref="ref", signature="sig")

    with patch("api.routes.irl.issue_heartbeat", new=AsyncMock(return_value=fake_hb)):
        result = await get_heartbeat(key_record=_key(tier="owner"))
    assert result.sequence_id == 1


# ── GET /v1/irl/audit ─────────────────────────────────────────────────────────
# Tier guard is tested via _require_irl_audit directly (above).
# Here we test the handler body: DB errors and model load failures.


async def test_irl_audit_returns_503_when_no_regime_data():
    """irl_audit key but no regime row in DB → 503."""
    from api.routes.irl import get_audit

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=None)), \
         patch("database.queries.fetch_latest_factors", new=AsyncMock(return_value=[])), \
         patch("database.queries.fetch_latest_liquidity", new=AsyncMock(return_value=[])), \
         patch("database.queries.fetch_latest_drift", new=AsyncMock(return_value=[])), \
         patch("database.queries.fetch_latest_features", new=AsyncMock(return_value=[])):
        with pytest.raises(HTTPException) as exc:
            await get_audit(key_record=_key(tier="irl_audit"))
    assert exc.value.status_code == 503


async def test_irl_audit_returns_503_when_models_unavailable():
    """Model artifacts missing → 503 with helpful detail."""
    from api.routes.irl import get_audit

    fake_regime = {"regime": "expansion", "risk_score": 25.0, "time": "2026-01-15"}

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=fake_regime)), \
         patch("database.queries.fetch_latest_factors", new=AsyncMock(return_value=[])), \
         patch("database.queries.fetch_latest_liquidity", new=AsyncMock(return_value=[])), \
         patch("database.queries.fetch_latest_drift", new=AsyncMock(return_value=[])), \
         patch("database.queries.fetch_latest_features", new=AsyncMock(return_value=[])), \
         patch("models.pca_model.PCAModel.load", side_effect=FileNotFoundError("model not found")):
        with pytest.raises(HTTPException) as exc:
            await get_audit(key_record=_key(tier="irl_audit"))
    assert exc.value.status_code == 503
    assert "artifacts" in exc.value.detail.lower()
