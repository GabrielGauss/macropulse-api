"""
Billing webhook hardening tests — Phase 6 (SEC-20, SEC-21, SEC-22).

Stubs created in Wave 0. Implementations filled in by 06-02-PLAN.md.
"""
import hashlib
import hmac as _hmac
import json
import os
import time as _time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


def test_ls_webhook_missing_secret():
    """API raises RuntimeError at startup when ENV=production and LS_WEBHOOK_SECRET unset."""
    from config.settings import get_settings
    from api.main import _validate_webhook_secrets

    get_settings.cache_clear()
    with patch.dict(os.environ, {"ENV": "production"}, clear=False):
        # Ensure LS_WEBHOOK_SECRET is absent
        os.environ.pop("LS_WEBHOOK_SECRET", None)
        get_settings.cache_clear()
        with pytest.raises(RuntimeError, match="LS_WEBHOOK_SECRET must be set"):
            _validate_webhook_secrets()
    get_settings.cache_clear()


def test_ls_webhook_invalid_signature():
    """LS webhook returns 401 on HMAC mismatch; rejects without calling event handler."""
    from api.routes.billing import _ls_verify_signature

    # With correct secret set but wrong signature — must return False
    with patch.dict(os.environ, {"LS_WEBHOOK_SECRET": "test-secret"}, clear=False):
        result = _ls_verify_signature(b"test body", "wrong-signature")
    assert result is False

    # With no secret set — must also return False (fail closed, not True)
    os.environ.pop("LS_WEBHOOK_SECRET", None)
    result = _ls_verify_signature(b"test body", "any-signature")
    assert result is False


def test_paddle_replay_window():
    """Paddle verify_webhook() rejects events with timestamp outside 5-minute window."""
    import time
    from config.settings import get_settings
    from services.paddle import verify_webhook

    # Build a fake Paddle-Signature header with old timestamp
    old_ts = int(time.time()) - 400  # 400 seconds ago — outside 5-min window
    fake_sig_header = f"ts={old_ts};h1=fakehash"

    # Set a Paddle secret so verify_webhook proceeds past the "secret not set" early-return
    # and reaches the timestamp check. Timestamp check fires before HMAC verification.
    get_settings.cache_clear()
    with patch.dict(os.environ, {"PADDLE_WEBHOOK_SECRET": "test-paddle-secret"}, clear=False):
        get_settings.cache_clear()
        result = verify_webhook(b'{"event_type": "test"}', fake_sig_header)
    get_settings.cache_clear()
    assert result is False


# ── Paddle billing tests (Phase 10 — BILL-01 through BILL-05, TEST-02) ─────────

def _make_paddle_signature(body: bytes, secret: str) -> str:
    """Reproduce Paddle's ts=...;h1=... HMAC-SHA256 header for tests."""
    ts = str(int(_time.time()))
    payload = f"{ts}:{body.decode('utf-8')}".encode()
    digest = _hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={digest}"


def _fake_key_record(tier: str = "free", user_id: int = 42, email: str = "test@example.com") -> dict:
    return {"user_id": user_id, "tier": tier, "email": email, "key_prefix": "test_prefix"}


def test_paddle_checkout_creates_url():
    """BILL-01: POST /v1/billing/paddle/checkout returns checkout_url for valid tier."""
    from api.main import app
    from api.auth import require_api_key
    from config.settings import get_settings

    client = TestClient(app)
    app.dependency_overrides[require_api_key] = lambda: _fake_key_record(tier="free")

    env_patch = {
        "PADDLE_STARTER_PRICE_ID": "pri_starter_test",
        "PADDLE_PRO_PRICE_ID": "pri_pro_test",
    }
    with patch.dict(os.environ, env_patch, clear=False):
        get_settings.cache_clear()
        with patch(
            "api.routes.billing.create_checkout_url",
            new=AsyncMock(return_value="https://checkout.paddle.com/checkout/test123"),
        ):
            resp = client.post(
                "/v1/billing/paddle/checkout",
                json={"tier": "starter"},
                headers={"Content-Type": "application/json"},
            )
        get_settings.cache_clear()

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert "checkout_url" in data
    assert data["tier"] == "starter"


def test_paddle_webhook_subscription_activated():
    """BILL-02: subscription.activated with valid signature upgrades tier via DB."""
    from api.main import app
    from config.settings import get_settings

    client = TestClient(app)
    secret = "test-paddle-secret"
    event = {
        "event_id": "evt_activated_001",
        "event_type": "subscription.activated",
        "data": {
            "id": "sub_001",
            "customer_id": "ctm_001",
            "status": "active",
            "custom_data": {"user_id": "42", "tier": "starter"},
            "items": [],
        },
    }
    body = json.dumps(event).encode()
    sig = _make_paddle_signature(body, secret)

    mock_conn = MagicMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock(return_value=None)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch.dict(os.environ, {"PADDLE_WEBHOOK_SECRET": secret}, clear=False):
        get_settings.cache_clear()
        with patch("database.queries.update_paddle_customer", new=AsyncMock()):
            with patch("database.queries.upgrade_user_tier", new=AsyncMock()):
                with patch("database.queries.update_paddle_subscription_status", new=AsyncMock()):
                    with patch("database.connection.get_db_conn", return_value=mock_cm):
                        resp = client.post(
                            "/v1/billing/paddle/webhook",
                            content=body,
                            headers={
                                "Paddle-Signature": sig,
                                "Content-Type": "application/json",
                            },
                        )
        get_settings.cache_clear()

    assert resp.status_code == 200
    assert resp.json().get("ok") is True


def test_paddle_webhook_subscription_cancelled():
    """BILL-02 / BILL-05: subscription.canceled with valid signature downgrades to free."""
    from api.main import app
    from config.settings import get_settings

    client = TestClient(app)
    secret = "test-paddle-secret"
    event = {
        "event_id": "evt_canceled_001",
        "event_type": "subscription.canceled",
        "data": {
            "id": "sub_001",
            "customer_id": "ctm_001",
            "status": "canceled",
        },
    }
    body = json.dumps(event).encode()
    sig = _make_paddle_signature(body, secret)

    mock_user = {"id": 42, "email": "test@example.com"}
    mock_conn = MagicMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock(return_value=None)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch.dict(os.environ, {"PADDLE_WEBHOOK_SECRET": secret}, clear=False):
        get_settings.cache_clear()
        with patch("database.queries.get_user_by_paddle_customer", new=AsyncMock(return_value=mock_user)):
            with patch("database.queries.upgrade_user_tier", new=AsyncMock()) as mock_upgrade:
                with patch("database.queries.update_paddle_subscription_status", new=AsyncMock()):
                    with patch("database.connection.get_db_conn", return_value=mock_cm):
                        resp = client.post(
                            "/v1/billing/paddle/webhook",
                            content=body,
                            headers={
                                "Paddle-Signature": sig,
                                "Content-Type": "application/json",
                            },
                        )
                    mock_upgrade.assert_called_once_with(42, "free")
        get_settings.cache_clear()

    assert resp.status_code == 200
    assert resp.json().get("ok") is True


def test_paddle_webhook_invalid_signature():
    """BILL-02: webhook with mismatched HMAC returns 401."""
    from api.main import app
    from config.settings import get_settings

    client = TestClient(app)
    event = {"event_id": "evt_bad", "event_type": "subscription.activated", "data": {}}
    body = json.dumps(event).encode()
    bad_sig = "ts=9999999999;h1=badhash"

    with patch.dict(os.environ, {"PADDLE_WEBHOOK_SECRET": "real-secret"}, clear=False):
        get_settings.cache_clear()
        resp = client.post(
            "/v1/billing/paddle/webhook",
            content=body,
            headers={
                "Paddle-Signature": bad_sig,
                "Content-Type": "application/json",
            },
        )
        get_settings.cache_clear()

    assert resp.status_code == 401


def test_paddle_webhook_idempotent():
    """BILL-03: duplicate event_id returns {ok: true, duplicate: true}."""
    from api.main import app
    from config.settings import get_settings

    client = TestClient(app)
    secret = "test-paddle-secret"
    event = {
        "event_id": "evt_dup_001",
        "event_type": "subscription.activated",
        "data": {"id": "sub_001", "customer_id": "ctm_001", "status": "active"},
    }
    body = json.dumps(event).encode()
    sig = _make_paddle_signature(body, secret)

    # fetchrow returns a row (non-None) → idempotency short-circuit
    mock_conn = MagicMock()
    mock_conn.fetchrow = AsyncMock(return_value={"event_id": "evt_dup_001"})
    mock_conn.execute = AsyncMock(return_value=None)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch.dict(os.environ, {"PADDLE_WEBHOOK_SECRET": secret}, clear=False):
        get_settings.cache_clear()
        with patch("database.connection.get_db_conn", return_value=mock_cm):
            resp = client.post(
                "/v1/billing/paddle/webhook",
                content=body,
                headers={
                    "Paddle-Signature": sig,
                    "Content-Type": "application/json",
                },
            )
        get_settings.cache_clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("duplicate") is True


def test_paddle_portal_returns_url():
    """BILL-04: GET /v1/billing/paddle/portal returns portal_url for user with paddle_customer_id."""
    from api.main import app
    from api.auth import require_api_key

    client = TestClient(app)
    app.dependency_overrides[require_api_key] = lambda: _fake_key_record(tier="starter")

    mock_user = {
        "id": 42,
        "email": "test@example.com",
        "paddle_customer_id": "ctm_001",
        "paddle_subscription_id": "sub_001",
        "paddle_subscription_status": "active",
    }

    with patch("database.queries.get_user_by_id", new=AsyncMock(return_value=mock_user)):
        with patch(
            "api.routes.billing.create_portal_url",
            new=AsyncMock(return_value="https://portal.paddle.com/overview"),
        ):
            resp = client.get("/v1/billing/paddle/portal")

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert "portal_url" in data
    assert data["portal_url"] == "https://portal.paddle.com/overview"
