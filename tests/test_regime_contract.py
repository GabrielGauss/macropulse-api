"""
Contract tests for GET /v1/regime/current — TEST-08.

This endpoint is the IRL Engine's primary data source. Its response shape is
load-bearing: any missing field or type change silently breaks downstream
mta_ref verification and heartbeat signing. These tests pin the exact contract.

No live DB required — all DB and signer calls are mocked.
"""
from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException


def _regime_row(
    regime: str = "expansion",
    risk_score: float = 22.5,
    time: dt.datetime | None = None,
) -> dict:
    if time is None:
        time = dt.datetime(2026, 4, 14, 2, 0, 0, tzinfo=dt.timezone.utc)
    return {
        "regime": regime,
        "risk_score": risk_score,
        "time": time,
        "prob_expansion": 0.72,
        "prob_tightening": 0.10,
        "prob_risk_off": 0.05,
        "prob_recovery": 0.13,
        "volatility_state": "low",
        "model_version": "v2.0",
    }


# ── Field presence ────────────────────────────────────────────────────────────


async def test_regime_current_required_fields_present():
    """Response contains every field the IRL Engine expects."""
    from api.routes.regime import get_current_regime

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=_regime_row())), \
         patch("api.routes.regime.sign_regime_payload", return_value="sig=="):
        result = await get_current_regime()

    # Core fields
    assert hasattr(result, "timestamp")
    assert hasattr(result, "macro_regime")
    assert hasattr(result, "risk_score")
    assert hasattr(result, "probabilities")
    # IRL-specific fields
    assert hasattr(result, "regime_id")
    assert hasattr(result, "broadcast_time")
    assert hasattr(result, "signature")


async def test_regime_current_probabilities_shape():
    """Probabilities sub-object has all four regime keys as floats."""
    from api.routes.regime import get_current_regime

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=_regime_row())), \
         patch("api.routes.regime.sign_regime_payload", return_value="sig=="):
        result = await get_current_regime()

    p = result.probabilities
    assert isinstance(p.expansion, float)
    assert isinstance(p.tightening, float)
    assert isinstance(p.risk_off, float)
    assert isinstance(p.recovery, float)
    assert abs(p.expansion + p.tightening + p.risk_off + p.recovery - 1.0) < 0.01


# ── Regime ID mapping ─────────────────────────────────────────────────────────


async def test_regime_id_expansion_is_zero():
    """Expansion maps to regime_id=0 (IRL Engine policy index)."""
    from api.routes.regime import get_current_regime

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=_regime_row("expansion"))), \
         patch("api.routes.regime.sign_regime_payload", return_value="sig=="):
        result = await get_current_regime()
    assert result.regime_id == 0


async def test_regime_id_recovery_is_one():
    from api.routes.regime import get_current_regime

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=_regime_row("recovery"))), \
         patch("api.routes.regime.sign_regime_payload", return_value="sig=="):
        result = await get_current_regime()
    assert result.regime_id == 1


async def test_regime_id_tightening_is_two():
    from api.routes.regime import get_current_regime

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=_regime_row("tightening"))), \
         patch("api.routes.regime.sign_regime_payload", return_value="sig=="):
        result = await get_current_regime()
    assert result.regime_id == 2


async def test_regime_id_risk_off_is_three():
    from api.routes.regime import get_current_regime

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=_regime_row("risk_off"))), \
         patch("api.routes.regime.sign_regime_payload", return_value="sig=="):
        result = await get_current_regime()
    assert result.regime_id == 3


async def test_regime_id_unknown_defaults_to_risk_off():
    """Unknown regime string defaults to 3 (risk_off) — the conservative fallback."""
    from api.routes.regime import get_current_regime

    row = _regime_row("mystery_regime")
    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=row)), \
         patch("api.routes.regime.sign_regime_payload", return_value="sig=="):
        result = await get_current_regime()
    assert result.regime_id == 3


# ── broadcast_time stability ──────────────────────────────────────────────────


async def test_broadcast_time_is_derived_from_db_timestamp():
    """broadcast_time is the DB row's timestamp in ms — not wall-clock time.

    IRL Engine verifies mta_ref by independently fetching this endpoint and
    hashing the response. If broadcast_time were time.time(), two calls in the
    same second would hash differently, breaking verification.
    """
    from api.routes.regime import get_current_regime

    fixed_time = dt.datetime(2026, 4, 14, 2, 0, 0, tzinfo=dt.timezone.utc)
    expected_ms = int(fixed_time.timestamp() * 1000)

    row = _regime_row(time=fixed_time)
    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=row)), \
         patch("api.routes.regime.sign_regime_payload", return_value="sig=="):
        result = await get_current_regime()

    assert result.broadcast_time == expected_ms


# ── Signature ────────────────────────────────────────────────────────────────


async def test_signature_is_attached_to_response():
    """sign_regime_payload output is stored in response.signature."""
    from api.routes.regime import get_current_regime

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=_regime_row())), \
         patch("api.routes.regime.sign_regime_payload", return_value="abc123=") as sign_mock:
        result = await get_current_regime()

    assert result.signature == "abc123="
    sign_mock.assert_called_once()


async def test_signature_payload_excludes_signature_field():
    """Payload passed to sign_regime_payload must not contain the 'signature' key.

    Including 'signature' in the signed payload would create a chicken-and-egg
    problem — the IRL Engine can't reproduce the exact bytes before signing.
    """
    from api.routes.regime import get_current_regime

    captured_payload = {}

    def capture_sign(payload: dict) -> str:
        captured_payload.update(payload)
        return "captured_sig=="

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=_regime_row())), \
         patch("api.routes.regime.sign_regime_payload", side_effect=capture_sign):
        await get_current_regime()

    assert "signature" not in captured_payload


# ── Error paths ───────────────────────────────────────────────────────────────


async def test_regime_current_returns_404_when_no_data():
    """Empty DB → 404, not 500."""
    from api.routes.regime import get_current_regime

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await get_current_regime()
    assert exc.value.status_code == 404


async def test_regime_current_passes_through_all_regime_values():
    """macro_regime, risk_score, and model_version are faithfully passed through."""
    from api.routes.regime import get_current_regime

    row = _regime_row("tightening", risk_score=61.3)
    row["model_version"] = "v2.1"

    with patch("database.queries.fetch_current_regime", new=AsyncMock(return_value=row)), \
         patch("api.routes.regime.sign_regime_payload", return_value="sig=="):
        result = await get_current_regime()

    assert result.macro_regime == "tightening"
    assert result.risk_score == pytest.approx(61.3)
    assert result.model_version == "v2.1"
