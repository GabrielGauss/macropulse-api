"""
Tests for Stripe webhook handling — TEST-07.

Covers: _stripe_tier_from_price, _stripe_handle (all 6 event types),
        and the stripe_webhook endpoint (signature + dispatch + idempotency).

No live DB or network required — all external calls mocked.
"""
from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ───────────────────────────────────────────────────────────────────


def _settings(
    starter_price: str = "price_starter",
    pro_price: str = "price_pro",
    irl_sidecar_price: str = "price_irl_sidecar",
    irl_audit_price: str = "price_irl_audit",
    stripe_secret: str = "sk_test_secret",
    stripe_webhook_secret: str = "whsec_test",
):
    s = MagicMock()
    s.stripe_starter_price_id      = starter_price
    s.stripe_pro_price_id          = pro_price
    s.stripe_irl_sidecar_price_id  = irl_sidecar_price
    s.stripe_irl_audit_price_id    = irl_audit_price
    s.stripe_secret_key            = stripe_secret
    s.stripe_webhook_secret        = stripe_webhook_secret
    return s


def _fake_event(event_type: str, obj: dict, event_id: str = "evt_test001") -> dict:
    return {"id": event_id, "type": event_type, "data": {"object": obj}}


def _existing_user(uid: int = 42) -> dict:
    return {"id": uid, "email": "user@example.com"}


# ── _stripe_tier_from_price ───────────────────────────────────────────────────


def test_tier_from_price_starter():
    from api.routes.billing import _stripe_tier_from_price
    from config.settings import get_settings

    get_settings.cache_clear()
    with patch.dict(os.environ, {"STRIPE_STARTER_PRICE_ID": "price_starter_123"}):
        get_settings.cache_clear()
        result = _stripe_tier_from_price("price_starter_123")
    get_settings.cache_clear()
    assert result == "starter"


def test_tier_from_price_pro():
    from api.routes.billing import _stripe_tier_from_price
    from config.settings import get_settings

    get_settings.cache_clear()
    with patch.dict(os.environ, {"STRIPE_PRO_PRICE_ID": "price_pro_123"}):
        get_settings.cache_clear()
        result = _stripe_tier_from_price("price_pro_123")
    get_settings.cache_clear()
    assert result == "pro"


def test_tier_from_price_irl_audit():
    from api.routes.billing import _stripe_tier_from_price
    from config.settings import get_settings

    get_settings.cache_clear()
    with patch.dict(os.environ, {"STRIPE_IRL_AUDIT_PRICE_ID": "price_irl_audit_123"}):
        get_settings.cache_clear()
        result = _stripe_tier_from_price("price_irl_audit_123")
    get_settings.cache_clear()
    assert result == "irl_audit"


def test_tier_from_price_unknown_returns_none():
    from api.routes.billing import _stripe_tier_from_price
    from config.settings import get_settings

    get_settings.cache_clear()
    result = _stripe_tier_from_price("price_unknown_xyz")
    get_settings.cache_clear()
    assert result is None


# ── checkout.session.completed — MacroPulse ───────────────────────────────────


async def test_checkout_completed_new_macropulse_user():
    """checkout.session.completed provisions new user and returns created_to_<tier>."""
    from api.routes.billing import _stripe_handle

    obj = {
        "customer": "cus_new01",
        "subscription": "sub_new01",
        "customer_email": "newuser@example.com",
        "metadata": {"tier": "starter"},
    }
    event = _fake_event("checkout.session.completed", obj)
    settings = _settings()

    with patch("api.routes.billing._ls_provision", new=AsyncMock(return_value=(99, "mp_test123", True))), \
         patch("database.queries.upsert_stripe_subscription", new=AsyncMock()):
        result = await _stripe_handle(event, settings)

    assert "created_to_starter" in result["result"]
    assert result["user_id"] == 99


async def test_checkout_completed_existing_macropulse_user_upgrades():
    """checkout.session.completed for existing user shows upgraded_to_<tier>."""
    from api.routes.billing import _stripe_handle

    obj = {
        "customer": "cus_exist01",
        "subscription": "sub_exist01",
        "customer_email": "existing@example.com",
        "metadata": {"tier": "pro"},
    }
    event = _fake_event("checkout.session.completed", obj)
    settings = _settings()

    with patch("api.routes.billing._ls_provision", new=AsyncMock(return_value=(42, "mp_old12345", False))), \
         patch("database.queries.upsert_stripe_subscription", new=AsyncMock()):
        result = await _stripe_handle(event, settings)

    assert "upgraded_to_pro" in result["result"]


async def test_checkout_completed_irl_tier_routes_to_irl_provision():
    """IRL tiers use _irl_provision, not _ls_provision."""
    from api.routes.billing import _stripe_handle

    obj = {
        "customer": "cus_irl01",
        "subscription": "sub_irl01",
        "customer_email": "irl@example.com",
        "metadata": {"tier": "irl_audit", "agent_count": "3"},
    }
    event = _fake_event("checkout.session.completed", obj)
    settings = _settings()

    irl_mock = AsyncMock(return_value=(77, "mp_irl1234", True))
    with patch("api.routes.billing._irl_provision", new=irl_mock), \
         patch("database.queries.upsert_stripe_subscription", new=AsyncMock()):
        result = await _stripe_handle(event, settings)

    irl_mock.assert_awaited_once_with("irl@example.com", "irl_audit", 3)
    assert "created_to_irl_audit" in result["result"]


async def test_checkout_completed_missing_tier_or_email_no_action():
    """Missing tier or email → result=missing_tier_or_email, no provisioning."""
    from api.routes.billing import _stripe_handle

    obj = {
        "customer": "cus_bad01",
        "subscription": "sub_bad01",
        "customer_email": "",
        "metadata": {"tier": ""},
    }
    event = _fake_event("checkout.session.completed", obj)
    settings = _settings()

    result = await _stripe_handle(event, settings)
    assert result["result"] == "missing_tier_or_email"


# ── customer.subscription.updated ────────────────────────────────────────────


async def test_subscription_updated_active_upgrades_tier():
    """subscription.updated with active status upgrades tier and reactivates keys."""
    from api.routes.billing import _stripe_handle

    obj = {
        "id": "sub_upd01",
        "customer": "cus_upd01",
        "status": "active",
        "items": {"data": [{"price": {"id": "price_pro"}, "quantity": 1}]},
    }
    event = _fake_event("customer.subscription.updated", obj)
    settings = _settings(pro_price="price_pro")

    reactivate = AsyncMock()
    upgrade = AsyncMock()
    upsert = AsyncMock()

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=_existing_user())), \
         patch("api.routes.billing._stripe_tier_from_price", return_value="pro"), \
         patch("database.queries.reactivate_user_keys", new=reactivate), \
         patch("database.queries.upgrade_user_tier", new=upgrade), \
         patch("database.queries.upsert_stripe_subscription", new=upsert):
        result = await _stripe_handle(event, settings)

    assert "updated_to_pro" in result["result"]
    reactivate.assert_awaited_once_with(42, product_line="macropulse")
    upgrade.assert_awaited_once_with(42, "pro", product_line="macropulse")


async def test_subscription_updated_past_due_suspends_keys():
    """subscription.updated with past_due status suspends user keys."""
    from api.routes.billing import _stripe_handle

    obj = {
        "id": "sub_pastdue01",
        "customer": "cus_pastdue01",
        "status": "past_due",
        "items": {"data": [{"price": {"id": "price_starter"}, "quantity": 1}]},
    }
    event = _fake_event("customer.subscription.updated", obj)
    settings = _settings(starter_price="price_starter")

    suspend_mock = AsyncMock()

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=_existing_user())), \
         patch("database.queries.suspend_user_keys", new=suspend_mock), \
         patch("database.queries.upsert_stripe_subscription", new=AsyncMock()):
        result = await _stripe_handle(event, settings)

    assert result["result"] == "suspended_past_due"
    suspend_mock.assert_awaited_once_with(42, product_line="macropulse")


async def test_subscription_updated_canceled_downgrades_to_free():
    """subscription.updated with canceled status downgrades to free."""
    from api.routes.billing import _stripe_handle

    obj = {
        "id": "sub_can01",
        "customer": "cus_can01",
        "status": "canceled",
        "items": {"data": [{"price": {"id": "price_pro"}, "quantity": 1}]},
    }
    event = _fake_event("customer.subscription.updated", obj)
    settings = _settings(pro_price="price_pro")

    upgrade_mock = AsyncMock()

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=_existing_user())), \
         patch("database.queries.upgrade_user_tier", new=upgrade_mock), \
         patch("database.queries.upsert_stripe_subscription", new=AsyncMock()):
        result = await _stripe_handle(event, settings)

    assert result["result"] == "downgraded_to_free"
    upgrade_mock.assert_awaited_once_with(42, "free", product_line="macropulse")


async def test_subscription_updated_irl_syncs_agent_count():
    """IRL subscription.updated syncs the agent count from subscription quantity."""
    from api.routes.billing import _stripe_handle

    obj = {
        "id": "sub_irl_upd01",
        "customer": "cus_irl_upd01",
        "status": "active",
        "items": {"data": [{"price": {"id": "price_irl_sidecar"}, "quantity": 5}]},
    }
    event = _fake_event("customer.subscription.updated", obj)
    settings = _settings(irl_sidecar_price="price_irl_sidecar")

    agent_count_mock = AsyncMock()

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=_existing_user())), \
         patch("api.routes.billing._stripe_tier_from_price", return_value="irl_sidecar"), \
         patch("database.queries.reactivate_user_keys", new=AsyncMock()), \
         patch("database.queries.upgrade_user_tier", new=AsyncMock()), \
         patch("database.queries.update_agent_count", new=agent_count_mock), \
         patch("database.queries.upsert_stripe_subscription", new=AsyncMock()):
        result = await _stripe_handle(event, settings)

    agent_count_mock.assert_awaited_once_with(42, 5, product_line="irl")


async def test_subscription_updated_user_not_found():
    """subscription.updated with unknown customer → user_not_found result."""
    from api.routes.billing import _stripe_handle

    obj = {
        "id": "sub_ghost01",
        "customer": "cus_ghost01",
        "status": "active",
        "items": {"data": [{"price": {"id": "price_pro"}, "quantity": 1}]},
    }
    event = _fake_event("customer.subscription.updated", obj)
    settings = _settings(pro_price="price_pro")

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=None)):
        result = await _stripe_handle(event, settings)

    assert result["result"] == "user_not_found"
    assert result["customer_id"] == "cus_ghost01"


# ── customer.subscription.deleted ────────────────────────────────────────────


async def test_subscription_deleted_downgrades_to_free():
    """subscription.deleted downgrades user to free and records canceled status."""
    from api.routes.billing import _stripe_handle

    obj = {
        "id": "sub_del01",
        "customer": "cus_del01",
        "items": {"data": [{"price": {"id": "price_starter"}, "quantity": 1}]},
    }
    event = _fake_event("customer.subscription.deleted", obj)
    settings = _settings(starter_price="price_starter")

    upgrade_mock = AsyncMock()
    upsert_mock = AsyncMock()

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=_existing_user())), \
         patch("database.queries.upgrade_user_tier", new=upgrade_mock), \
         patch("database.queries.upsert_stripe_subscription", new=upsert_mock):
        result = await _stripe_handle(event, settings)

    assert result["result"] == "deleted_downgraded_to_free"
    upgrade_mock.assert_awaited_once_with(42, "free", product_line="macropulse")
    call_args = upsert_mock.call_args[0]
    assert call_args[4] == "canceled"


async def test_subscription_deleted_user_not_found():
    """subscription.deleted with unknown customer → user_not_found, no DB writes."""
    from api.routes.billing import _stripe_handle

    obj = {
        "id": "sub_del_ghost",
        "customer": "cus_del_ghost",
        "items": {"data": []},
    }
    event = _fake_event("customer.subscription.deleted", obj)
    settings = _settings()

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=None)):
        result = await _stripe_handle(event, settings)

    assert result["result"] == "user_not_found"


# ── invoice.paid ──────────────────────────────────────────────────────────────


async def test_invoice_paid_restores_access():
    """invoice.paid reactivates suspended keys and ensures correct tier."""
    from api.routes.billing import _stripe_handle

    obj = {
        "customer": "cus_inv01",
        "subscription": "sub_inv01",
        "lines": {"data": [{"price": {"id": "price_pro"}}]},
    }
    event = _fake_event("invoice.paid", obj)
    settings = _settings(pro_price="price_pro")

    reactivate = AsyncMock()
    upgrade = AsyncMock()
    upsert = AsyncMock()

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=_existing_user())), \
         patch("api.routes.billing._stripe_tier_from_price", return_value="pro"), \
         patch("database.queries.reactivate_user_keys", new=reactivate), \
         patch("database.queries.upgrade_user_tier", new=upgrade), \
         patch("database.queries.upsert_stripe_subscription", new=upsert):
        result = await _stripe_handle(event, settings)

    assert result["result"] == "payment_confirmed_access_restored"
    reactivate.assert_awaited_once_with(42, product_line="macropulse")
    upgrade.assert_awaited_once_with(42, "pro", product_line="macropulse")


async def test_invoice_paid_user_not_found_logs_only():
    """invoice.paid with no matching customer → invoice_paid_logged, no writes."""
    from api.routes.billing import _stripe_handle

    obj = {
        "customer": "cus_ghost_inv",
        "subscription": "sub_ghost_inv",
        "lines": {"data": [{"price": {"id": "price_pro"}}]},
    }
    event = _fake_event("invoice.paid", obj)
    settings = _settings(pro_price="price_pro")

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=None)):
        result = await _stripe_handle(event, settings)

    assert result["result"] == "invoice_paid_logged"


# ── invoice.payment_failed ────────────────────────────────────────────────────


async def test_invoice_payment_failed_suspends_keys():
    """invoice.payment_failed suspends user keys and records past_due status."""
    from api.routes.billing import _stripe_handle

    obj = {
        "customer": "cus_fail01",
        "subscription": "sub_fail01",
        "lines": {"data": [{"price": {"id": "price_starter"}}]},
    }
    event = _fake_event("invoice.payment_failed", obj)
    settings = _settings(starter_price="price_starter")

    suspend_mock = AsyncMock()
    upsert_mock = AsyncMock()

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=_existing_user())), \
         patch("database.queries.suspend_user_keys", new=suspend_mock), \
         patch("database.queries.upsert_stripe_subscription", new=upsert_mock):
        result = await _stripe_handle(event, settings)

    assert result["result"] == "payment_failed_keys_suspended"
    suspend_mock.assert_awaited_once_with(42, product_line="macropulse")
    # upsert recorded past_due status
    call_args = upsert_mock.call_args[0]
    assert call_args[4] == "past_due"


async def test_invoice_payment_failed_irl_suspends_irl_keys():
    """invoice.payment_failed for IRL customer suspends only IRL product_line keys."""
    from api.routes.billing import _stripe_handle

    obj = {
        "customer": "cus_irl_fail01",
        "subscription": "sub_irl_fail01",
        "lines": {"data": [{"price": {"id": "price_irl_sidecar"}}]},
    }
    event = _fake_event("invoice.payment_failed", obj)
    settings = _settings(irl_sidecar_price="price_irl_sidecar")

    suspend_mock = AsyncMock()

    with patch("database.queries.get_user_by_stripe_customer", new=AsyncMock(return_value=_existing_user())), \
         patch("api.routes.billing._stripe_tier_from_price", return_value="irl_sidecar"), \
         patch("database.queries.suspend_user_keys", new=suspend_mock), \
         patch("database.queries.upsert_stripe_subscription", new=AsyncMock()):
        await _stripe_handle(event, settings)

    suspend_mock.assert_awaited_once_with(42, product_line="irl")


# ── Unknown / action_required events ─────────────────────────────────────────


async def test_unknown_event_is_ignored():
    """Unrecognized event type → ignored, no DB calls."""
    from api.routes.billing import _stripe_handle

    event = _fake_event("customer.created", {"id": "cus_new"})
    result = await _stripe_handle(event, _settings())
    assert result["result"] == "ignored"


async def test_action_required_event_logged():
    """invoice.payment_action_required → action_required_logged."""
    from api.routes.billing import _stripe_handle

    event = _fake_event("invoice.payment_action_required", {"customer": "cus_3ds"})
    result = await _stripe_handle(event, _settings())
    assert result["result"] == "action_required_logged"


# ── stripe_webhook endpoint ───────────────────────────────────────────────────


async def test_stripe_webhook_missing_signature_returns_400():
    """Missing Stripe-Signature header → 400."""
    from api.routes.billing import stripe_webhook

    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=b'{"type": "invoice.paid"}')
    mock_request.headers = {}

    with pytest.raises(HTTPException) as exc:
        await stripe_webhook(request=mock_request, stripe_signature=None)

    assert exc.value.status_code == 400


async def test_stripe_webhook_invalid_signature_returns_401():
    """Invalid HMAC signature → 401."""
    import stripe as stripe_lib
    from stripe import SignatureVerificationError
    from api.routes.billing import stripe_webhook

    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=b'{"type": "invoice.paid"}')
    mock_request.headers = {"Stripe-Signature": "bad-sig"}

    with patch.object(stripe_lib.Webhook, "construct_event",
                      side_effect=SignatureVerificationError("bad sig", "bad-sig")):
        with pytest.raises(HTTPException) as exc:
            await stripe_webhook(request=mock_request, stripe_signature="bad-sig")

    assert exc.value.status_code == 401


async def test_stripe_webhook_duplicate_event_returns_200_with_duplicate_flag():
    """Duplicate event_id → {ok: true, duplicate: true} without calling _stripe_handle."""
    import stripe as stripe_lib
    from api.routes.billing import stripe_webhook

    payload = json.dumps({"type": "invoice.paid", "data": {"object": {}}}).encode()
    fake_event = {"id": "evt_dup_stripe_01", "type": "invoice.paid", "data": {"object": {}}}

    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=payload)
    mock_request.headers = {"Stripe-Signature": "valid-sig"}

    mock_conn = MagicMock()
    mock_conn.fetchrow = AsyncMock(return_value={"event_id": "evt_dup_stripe_01"})
    mock_conn.execute = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch.object(stripe_lib.Webhook, "construct_event", return_value=fake_event), \
         patch("database.connection.get_db_conn", return_value=mock_cm):
        result = await stripe_webhook(request=mock_request, stripe_signature="valid-sig")

    assert result["ok"] is True
    assert result.get("duplicate") is True


async def test_stripe_webhook_valid_event_dispatches_and_returns_200():
    """Valid signature + new event → _stripe_handle called, {ok: true} returned."""
    import stripe as stripe_lib
    from api.routes.billing import stripe_webhook

    payload = json.dumps({"type": "invoice.paid", "data": {"object": {}}}).encode()
    fake_event = {"id": "evt_new_stripe_01", "type": "invoice.paid", "data": {"object": {}}}

    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=payload)
    mock_request.headers = {"Stripe-Signature": "valid-sig"}

    mock_conn = MagicMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)   # not a duplicate
    mock_conn.execute = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    handle_mock = AsyncMock(return_value={"result": "payment_confirmed_access_restored"})

    with patch.object(stripe_lib.Webhook, "construct_event", return_value=fake_event), \
         patch("database.connection.get_db_conn", return_value=mock_cm), \
         patch("api.routes.billing._stripe_handle", new=handle_mock):
        result = await stripe_webhook(request=mock_request, stripe_signature="valid-sig")

    assert result["ok"] is True
    handle_mock.assert_awaited_once()


async def test_stripe_webhook_handler_error_still_returns_200():
    """Internal handler exception → logged but 200 returned so Stripe doesn't retry."""
    import stripe as stripe_lib
    from api.routes.billing import stripe_webhook

    payload = json.dumps({"type": "invoice.paid", "data": {"object": {}}}).encode()
    fake_event = {"id": "evt_crash_01", "type": "invoice.paid", "data": {"object": {}}}

    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=payload)
    mock_request.headers = {"Stripe-Signature": "valid-sig"}

    mock_conn = MagicMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch.object(stripe_lib.Webhook, "construct_event", return_value=fake_event), \
         patch("database.connection.get_db_conn", return_value=mock_cm), \
         patch("api.routes.billing._stripe_handle",
               new=AsyncMock(side_effect=Exception("DB exploded"))):
        result = await stripe_webhook(request=mock_request, stripe_signature="valid-sig")

    # Must return 200 — webhook acknowledged even on internal errors
    assert result["ok"] is True
