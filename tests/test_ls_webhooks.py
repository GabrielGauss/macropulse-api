"""
Tests for Lemon Squeezy webhook handling — TEST-03.

Covers: _ls_resolve_tier, _ls_handle event routing, and the
lemonsqueezy_webhook endpoint (signature + dispatch).

No live DB or network required — all external calls mocked.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.routes.billing import (
    _ls_handle,
    _ls_resolve_tier,
    _ls_verify_signature,
    lemonsqueezy_webhook,
)


# ── _ls_resolve_tier ──────────────────────────────────────────────────────────


def test_resolve_tier_by_variant_id_env(monkeypatch):
    """LS_VARIANT_ID_PRO env var maps to 'pro'."""
    monkeypatch.setenv("LS_VARIANT_ID_PRO", "99999")
    monkeypatch.setenv("LS_VARIANT_ID_STARTER", "11111")
    assert _ls_resolve_tier(99999, "") == "pro"
    assert _ls_resolve_tier(11111, "") == "starter"


def test_resolve_tier_fallback_to_name():
    """Unmapped variant_id falls back to variant_name matching."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("LS_VARIANT_ID_PRO", None)
        os.environ.pop("LS_VARIANT_ID_STARTER", None)
        assert _ls_resolve_tier(None, "Pro Monthly") == "pro"
        assert _ls_resolve_tier(None, "Starter Plan") == "starter"
        assert _ls_resolve_tier(None, "Unknown Plan") is None


def test_resolve_tier_string_variant_id():
    """Variant ID passed as string (from JSON) still matches env var."""
    with patch.dict(os.environ, {"LS_VARIANT_ID_PRO": "55555"}):
        assert _ls_resolve_tier("55555", "") == "pro"


# ── _ls_verify_signature ──────────────────────────────────────────────────────


def test_verify_signature_valid():
    """Correct HMAC-SHA256 signature is accepted."""
    secret = "test-secret-key"
    body = b'{"meta":{"event_name":"subscription_created"}}'
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    with patch.dict(os.environ, {"LS_WEBHOOK_SECRET": secret}):
        assert _ls_verify_signature(body, digest) is True


def test_verify_signature_wrong_secret_rejected():
    """Signature generated with a different secret is rejected."""
    body = b'{"event": "test"}'
    wrong_sig = hmac.new(b"wrong-secret", body, hashlib.sha256).hexdigest()

    with patch.dict(os.environ, {"LS_WEBHOOK_SECRET": "correct-secret"}):
        assert _ls_verify_signature(body, wrong_sig) is False


def test_verify_signature_no_secret_rejects():
    """Missing LS_WEBHOOK_SECRET → fail closed (return False)."""
    env = {k: v for k, v in os.environ.items() if k != "LS_WEBHOOK_SECRET"}
    with patch.dict(os.environ, env, clear=True):
        assert _ls_verify_signature(b"body", "any-sig") is False


# ── _ls_handle: subscription_created ─────────────────────────────────────────


async def test_ls_handle_subscription_created_new_user():
    """subscription_created with active status and new email provisions user."""
    attrs = {
        "user_email": "newpro@example.com",
        "customer_id": "cust_1",
        "subscription_id": "sub_1",
        "variant_id": 9,
        "variant_name": "Pro",
        "status": "active",
        "urls": {"customer_portal": "https://ls.example.com/portal"},
    }
    new_user = {"id": 55}

    with patch("database.queries.get_user_by_email", new=AsyncMock(return_value=None)), \
         patch("database.queries.create_user", new=AsyncMock(return_value=new_user)), \
         patch("database.queries.get_active_keys_for_user", new=AsyncMock(return_value=[])), \
         patch("database.queries.create_api_key", new=AsyncMock(return_value=None)), \
         patch("database.queries.upsert_ls_subscription", new=AsyncMock(return_value=None)), \
         patch("services.email.send_welcome_email"), \
         patch.dict(os.environ, {"LS_VARIANT_ID_PRO": "9"}):
        result = await _ls_handle("subscription_created", attrs)

    assert "created_to_pro" in result["result"]
    assert result["user_id"] == 55


async def test_ls_handle_subscription_created_existing_user_upgrades():
    """subscription_created for existing user upgrades tier in place."""
    attrs = {
        "user_email": "existing@example.com",
        "customer_id": "cust_2",
        "subscription_id": "sub_2",
        "variant_id": 9,
        "variant_name": "Pro",
        "status": "active",
        "urls": {},
    }
    existing_user = {"id": 10}
    existing_keys = [{"tier": "starter", "key_prefix": "mp_old123456"}]

    with patch("database.queries.get_user_by_email", new=AsyncMock(return_value=existing_user)), \
         patch("database.queries.get_active_keys_for_user", new=AsyncMock(return_value=existing_keys)), \
         patch("database.queries.upgrade_user_tier", new=AsyncMock(return_value=None)), \
         patch("database.queries.upsert_ls_subscription", new=AsyncMock(return_value=None)), \
         patch("services.email.send_upgrade_email"), \
         patch.dict(os.environ, {"LS_VARIANT_ID_PRO": "9"}):
        result = await _ls_handle("subscription_created", attrs)

    assert "upgraded_to_pro" in result["result"]


async def test_ls_handle_subscription_created_no_email():
    """subscription_created without email → no_email result, no provisioning."""
    attrs = {
        "user_email": "",
        "customer_id": "cust_99",
        "subscription_id": "sub_99",
        "variant_id": 9,
        "variant_name": "Pro",
        "status": "active",
        "urls": {},
    }

    with patch.dict(os.environ, {"LS_VARIANT_ID_PRO": "9"}):
        result = await _ls_handle("subscription_created", attrs)

    assert result["result"] == "no_email"


# ── _ls_handle: subscription_updated ─────────────────────────────────────────


async def test_ls_handle_subscription_updated_downgrade():
    """subscription_updated with expired status → downgrade to free."""
    attrs = {
        "user_email": "user@example.com",
        "customer_id": "cust_3",
        "subscription_id": "sub_3",
        "variant_id": 9,
        "variant_name": "Pro",
        "status": "expired",
        "urls": {},
    }
    existing_user = {"id": 20}

    with patch("database.queries.get_user_by_email", new=AsyncMock(return_value=existing_user)), \
         patch("database.queries.upgrade_user_tier", new=AsyncMock(return_value=None)), \
         patch("database.queries.upsert_ls_subscription", new=AsyncMock(return_value=None)), \
         patch.dict(os.environ, {"LS_VARIANT_ID_PRO": "9"}):
        result = await _ls_handle("subscription_updated", attrs)

    assert "downgraded_to_free" in result["result"]


# ── _ls_handle: subscription_cancelled ───────────────────────────────────────


async def test_ls_handle_subscription_cancelled_retains_access():
    """Cancellation retains access until period end — tier not downgraded."""
    attrs = {
        "user_email": "cancel@example.com",
        "customer_id": "cust_4",
        "subscription_id": "sub_4",
        "variant_id": None,
        "variant_name": "",
        "status": "cancelled",
        "urls": {},
    }
    existing_user = {"id": 30}

    with patch("database.queries.get_user_by_email", new=AsyncMock(return_value=existing_user)), \
         patch("database.queries.upsert_ls_subscription", new=AsyncMock(return_value=None)) as mock_upsert:
        result = await _ls_handle("subscription_cancelled", attrs)

    assert result["result"] == "cancelled_access_retained"
    # upsert called with "cancelled" status — tier NOT downgraded
    mock_upsert.assert_awaited_once()
    call_kwargs = mock_upsert.call_args[0]
    assert call_kwargs[4] == "cancelled"


# ── _ls_handle: subscription_expired ─────────────────────────────────────────


async def test_ls_handle_subscription_expired_downgrades():
    """Expiry downgrades user to free tier."""
    attrs = {
        "user_email": "expired@example.com",
        "customer_id": "cust_5",
        "subscription_id": "sub_5",
        "variant_id": None,
        "variant_name": "",
        "status": "expired",
        "urls": {},
    }
    existing_user = {"id": 40}

    with patch("database.queries.get_user_by_email", new=AsyncMock(return_value=existing_user)), \
         patch("database.queries.upgrade_user_tier", new=AsyncMock(return_value=None)) as mock_upgrade, \
         patch("database.queries.upsert_ls_subscription", new=AsyncMock(return_value=None)):
        result = await _ls_handle("subscription_expired", attrs)

    assert result["result"] == "expired_downgraded_to_free"
    mock_upgrade.assert_awaited_once_with(40, "free")


# ── _ls_handle: payment events ────────────────────────────────────────────────


async def test_ls_handle_payment_success_no_action():
    """subscription_payment_success → no DB changes, just ack."""
    result = await _ls_handle("subscription_payment_success", {})
    assert result["result"] == "payment_ok_no_action"


async def test_ls_handle_payment_failed_logged():
    """subscription_payment_failed → logged, no action (LS handles dunning)."""
    result = await _ls_handle("subscription_payment_failed", {"user_email": "u@e.com"})
    assert "payment_event" in result["result"]


# ── _ls_handle: unknown event ─────────────────────────────────────────────────


async def test_ls_handle_unknown_event_ignored():
    """Unrecognized event is silently ignored."""
    result = await _ls_handle("some_future_event", {})
    assert result["result"] == "ignored"
    assert result["event"] == "some_future_event"


# ── lemonsqueezy_webhook endpoint ─────────────────────────────────────────────


async def test_lemonsqueezy_webhook_invalid_signature_returns_401():
    """Invalid HMAC → 401, _ls_handle is never called."""
    raw_body = json.dumps({"meta": {"event_name": "subscription_created"}}).encode()

    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=raw_body)
    mock_request.headers = {"X-Signature": "bad-signature"}

    with patch("api.routes.billing._ls_verify_signature", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await lemonsqueezy_webhook(request=mock_request)

    assert exc_info.value.status_code == 401


async def test_lemonsqueezy_webhook_valid_signature_dispatches():
    """Valid signature → _ls_handle is called and result is returned."""
    payload = {"meta": {"event_name": "subscription_payment_success"}, "data": {}}
    raw_body = json.dumps(payload).encode()

    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=raw_body)
    mock_request.headers = {"X-Signature": "valid-sig"}

    with patch("api.routes.billing._ls_verify_signature", return_value=True), \
         patch("api.routes.billing._ls_handle",
               new=AsyncMock(return_value={"result": "payment_ok_no_action"})):
        result = await lemonsqueezy_webhook(request=mock_request)

    assert result["ok"] is True
    assert result["result"] == "payment_ok_no_action"


async def test_lemonsqueezy_webhook_handler_error_still_returns_200():
    """Internal handler error → logged but 200 returned so LS doesn't retry."""
    payload = {"meta": {"event_name": "subscription_created"}, "data": {}}
    raw_body = json.dumps(payload).encode()

    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=raw_body)
    mock_request.headers = {"X-Signature": "valid-sig"}

    with patch("api.routes.billing._ls_verify_signature", return_value=True), \
         patch("api.routes.billing._ls_handle",
               new=AsyncMock(side_effect=Exception("DB exploded"))):
        result = await lemonsqueezy_webhook(request=mock_request)

    # Must return 200 — webhook acknowledged even on internal errors
    assert result["ok"] is True
    assert "internal_error_logged" in result["result"]
