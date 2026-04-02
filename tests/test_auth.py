"""
Tests for auth route handlers — TEST-01.

Covers: POST /register, POST /verify, POST /recover, POST /recover/verify,
        POST /rotate, GET /me, GET /usage.

All DB calls are mocked — no live database required.
Handlers are called directly (not via TestClient) so require_api_key is
bypassed by passing key_record dicts directly.
"""
from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.routes.auth import (
    get_me,
    get_usage,
    recover,
    recover_verify,
    register,
    rotate_key,
    verify,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_request(ip: str = "1.2.3.4") -> MagicMock:
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock()
    req.client.host = ip
    return req


def _key_record(user_id: int = 42, tier: str = "free") -> dict:
    return {
        "user_id": user_id,
        "tier": tier,
        "email": "user@example.com",
        "key_prefix": "mp_abc123def",
        "created_at": dt.datetime.now(dt.timezone.utc),
        "last_used_at": None,
    }


def _verify_body(email: str = "user@example.com", code: str = "123456") -> MagicMock:
    body = MagicMock()
    body.email = email
    body.code = code
    return body


def _register_body(email: str = "new@example.com") -> MagicMock:
    body = MagicMock()
    body.email = email
    return body


# ── POST /v1/auth/register ────────────────────────────────────────────────────


async def test_register_sends_verification_code():
    """Happy path: new email → returns verification_sent."""
    with patch("api.routes.auth.get_client_ip", return_value="1.2.3.4"), \
         patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.get_user_by_email", new=AsyncMock(return_value=None)), \
         patch("database.queries.create_email_verification", new=AsyncMock(return_value=None)), \
         patch("services.email.send_verification_email"):
        result = await register(body=_register_body("new@example.com"), request=_mock_request())

    assert result["status"] == "verification_sent"
    assert result["email"] == "new@example.com"


async def test_register_duplicate_email_raises_409():
    """Duplicate email → 409 Conflict before calling create_email_verification."""
    existing_user = {"id": 99, "email": "dup@example.com"}
    mock_create = AsyncMock()

    with patch("api.routes.auth.get_client_ip", return_value="1.2.3.4"), \
         patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.get_user_by_email", new=AsyncMock(return_value=existing_user)), \
         patch("database.queries.create_email_verification", new=mock_create):
        with pytest.raises(HTTPException) as exc_info:
            await register(body=_register_body("dup@example.com"), request=_mock_request())

    assert exc_info.value.status_code == 409
    mock_create.assert_not_called()


async def test_register_db_failure_raises_503():
    """DB error on create_email_verification → 503."""
    with patch("api.routes.auth.get_client_ip", return_value="1.2.3.4"), \
         patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.get_user_by_email", new=AsyncMock(return_value=None)), \
         patch("database.queries.create_email_verification",
               new=AsyncMock(side_effect=Exception("DB down"))):
        with pytest.raises(HTTPException) as exc_info:
            await register(body=_register_body(), request=_mock_request())

    assert exc_info.value.status_code == 503


# ── POST /v1/auth/verify ──────────────────────────────────────────────────────


async def test_verify_happy_path_returns_api_key():
    """Valid OTP → creates user and returns API key with 201."""
    new_user = {"id": 42}

    with patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.verify_email_code", new=AsyncMock(return_value=True)), \
         patch("database.queries.get_user_by_email", new=AsyncMock(return_value=None)), \
         patch("database.queries.create_user", new=AsyncMock(return_value=new_user)), \
         patch("database.queries.create_api_key", new=AsyncMock(return_value=None)), \
         patch("services.email.send_welcome_email"):
        result = await verify(body=_verify_body())

    assert result.user_id == 42
    assert result.tier == "free"
    assert len(result.api_key) > 12
    assert result.api_key.startswith(result.key_prefix)


async def test_verify_invalid_code_raises_400():
    """Invalid OTP → 400."""
    with patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.verify_email_code", new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc_info:
            await verify(body=_verify_body(code="000000"))

    assert exc_info.value.status_code == 400


async def test_verify_race_condition_raises_409():
    """If user already exists when verify runs (race/double-submit) → 409."""
    existing_user = {"id": 7, "email": "user@example.com"}

    with patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.verify_email_code", new=AsyncMock(return_value=True)), \
         patch("database.queries.get_user_by_email", new=AsyncMock(return_value=existing_user)):
        with pytest.raises(HTTPException) as exc_info:
            await verify(body=_verify_body())

    assert exc_info.value.status_code == 409


# ── POST /v1/auth/recover ─────────────────────────────────────────────────────


async def test_recover_known_email_sends_code():
    """Email with account → sends recovery code and returns recovery_code_sent."""
    existing_user = {"id": 5, "email": "known@example.com"}

    with patch("api.routes.auth.get_client_ip", return_value="1.2.3.4"), \
         patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.get_user_by_email", new=AsyncMock(return_value=existing_user)), \
         patch("database.queries.create_email_verification", new=AsyncMock(return_value=None)), \
         patch("services.email.send_verification_email"):
        result = await recover(body=_register_body("known@example.com"), request=_mock_request())

    assert result["status"] == "recovery_code_sent"


async def test_recover_unknown_email_returns_same_response():
    """Unknown email → same response (no account enumeration)."""
    with patch("api.routes.auth.get_client_ip", return_value="1.2.3.4"), \
         patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.get_user_by_email", new=AsyncMock(return_value=None)):
        result = await recover(body=_register_body("ghost@example.com"), request=_mock_request())

    # Must return success regardless — prevents account enumeration
    assert result["status"] == "recovery_code_sent"
    assert result["email"] == "ghost@example.com"


# ── POST /v1/auth/recover/verify ──────────────────────────────────────────────


async def test_recover_verify_issues_new_key():
    """Valid recovery code → revokes old key, issues new key."""
    existing_user = {"id": 10, "email": "user@example.com"}
    existing_keys = [{"tier": "starter", "key_prefix": "mp_old123456"}]

    with patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.verify_email_code", new=AsyncMock(return_value=True)), \
         patch("database.queries.get_user_by_email", new=AsyncMock(return_value=existing_user)), \
         patch("database.queries.get_active_keys_for_user", new=AsyncMock(return_value=existing_keys)), \
         patch("database.queries.revoke_api_keys_for_user", new=AsyncMock(return_value=None)), \
         patch("database.queries.create_api_key", new=AsyncMock(return_value=None)), \
         patch("services.email.send_key_recovery_email"):
        result = await recover_verify(body=_verify_body())

    assert result.tier == "starter"
    assert len(result.api_key) > 12


async def test_recover_verify_invalid_code_raises_400():
    """Invalid recovery code → 400."""
    with patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.verify_email_code", new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc_info:
            await recover_verify(body=_verify_body(code="bad"))

    assert exc_info.value.status_code == 400


async def test_recover_verify_user_not_found_raises_404():
    """Code valid but user gone → 404."""
    with patch("api.routes.auth.check_auth_rate_limit", new=AsyncMock(return_value=None)), \
         patch("database.queries.verify_email_code", new=AsyncMock(return_value=True)), \
         patch("database.queries.get_user_by_email", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc_info:
            await recover_verify(body=_verify_body())

    assert exc_info.value.status_code == 404


# ── POST /v1/auth/rotate ──────────────────────────────────────────────────────


async def test_rotate_key_returns_new_key():
    """rotate_key revokes old key and issues a new one at same tier."""
    with patch("database.queries.revoke_api_keys_for_user", new=AsyncMock(return_value=None)), \
         patch("database.queries.create_api_key", new=AsyncMock(return_value=None)):
        result = await rotate_key(key_record=_key_record(tier="pro"))

    assert result.tier == "pro"
    assert len(result.api_key) > 12


async def test_rotate_key_db_failure_raises_503():
    """DB failure on revoke → 503."""
    with patch("database.queries.revoke_api_keys_for_user",
               new=AsyncMock(side_effect=Exception("DB error"))):
        with pytest.raises(HTTPException) as exc_info:
            await rotate_key(key_record=_key_record())

    assert exc_info.value.status_code == 503


# ── GET /v1/auth/me ───────────────────────────────────────────────────────────


async def test_get_me_returns_profile():
    """get_me returns a KeyInfoResponse with fields from key_record."""
    record = _key_record(user_id=77, tier="starter")
    result = await get_me(key_record=record)

    assert result.user_id == 77
    assert result.tier == "starter"
    assert result.email == "user@example.com"
    assert result.key_prefix == "mp_abc123def"


# ── GET /v1/auth/usage ────────────────────────────────────────────────────────


async def test_get_usage_free_tier():
    """Free tier: used=3, limit=50, remaining=47."""
    with patch("api.routes.auth.get_usage_today", new=AsyncMock(return_value=3)):
        result = await get_usage(key_record=_key_record(tier="free"))

    assert result.tier == "free"
    assert result.used_today == 3
    assert result.remaining == 47


async def test_get_usage_pro_tier_unlimited():
    """Pro tier: limit=0 → remaining=-1 (unlimited)."""
    with patch("api.routes.auth.get_usage_today", new=AsyncMock(return_value=500)):
        result = await get_usage(key_record=_key_record(tier="pro"))

    assert result.tier == "pro"
    assert result.remaining == -1
