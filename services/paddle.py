"""
Paddle Billing integration for MacroPulse.

Handles:
  - Checkout URL generation (server-side transaction creation)
  - Webhook signature verification
  - Subscription lifecycle events → tier upgrades/downgrades
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any

import httpx

from config.settings import get_settings

logger = logging.getLogger(__name__)

_PADDLE_API = {
    "sandbox":    "https://sandbox-api.paddle.com",
    "production": "https://api.paddle.com",
}

# Paddle product_id → tier name
_PRODUCT_TIER_MAP: dict[str, str] = {
    "pro_01kkhzzr1c1f1fta693c6p6nzv": "starter",
    "pro_01kkj01cx467jt6v4c5g2hakrd": "pro",
}


def _api_base() -> str:
    settings = get_settings()
    return _PADDLE_API.get(settings.paddle_environment, _PADDLE_API["sandbox"])


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.paddle_api_key}",
        "Content-Type": "application/json",
    }


# ── Checkout ─────────────────────────────────────────────────────────


async def create_checkout_url(
    price_id: str,
    user_id: int,
    email: str,
    tier: str,
) -> str:
    """
    Create a Paddle transaction and return the hosted checkout URL.

    Embeds user_id and tier in custom_data so the webhook handler can
    identify the user without needing to match emails.
    """
    settings = get_settings()
    payload: dict[str, Any] = {
        "items": [{"price_id": price_id, "quantity": 1}],
        "customer": {"email": email},
        "checkout": {"url": settings.paddle_success_url},
        "custom_data": {
            "user_id": str(user_id),
            "tier": tier,
        },
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_api_base()}/transactions",
            json=payload,
            headers=_headers(),
        )
    resp.raise_for_status()
    data = resp.json()
    checkout_url: str = data["data"]["checkout"]["url"]
    logger.info("Created Paddle checkout for user_id=%d tier=%s", user_id, tier)
    return checkout_url


async def create_portal_url(paddle_customer_id: str) -> str:
    """Generate a Paddle customer portal URL for subscription management."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_api_base()}/customers/{paddle_customer_id}/portal-sessions",
            json={},
            headers=_headers(),
        )
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["urls"]["general"]["overview"]


# ── Webhook verification ──────────────────────────────────────────────


def verify_webhook(raw_body: bytes, signature_header: str) -> bool:
    """
    Verify the Paddle-Signature header using HMAC-SHA256.

    Header format:  ts=<timestamp>;h1=<hex_digest>
    Signed content: <timestamp>:<raw_body>
    """
    settings = get_settings()
    if not settings.paddle_webhook_secret:
        logger.warning("PADDLE_WEBHOOK_SECRET not set — skipping signature check (dev mode)")
        return True

    try:
        parts = dict(p.split("=", 1) for p in signature_header.split(";"))
        ts = parts["ts"]
        h1 = parts["h1"]
    except (KeyError, ValueError):
        logger.warning("Malformed Paddle-Signature header: %s", signature_header)
        return False

    # Replay attack guard: reject webhooks older than 5 minutes
    try:
        if abs(time.time() - int(ts)) > 300:
            logger.warning("Paddle webhook timestamp too old: ts=%s", ts)
            return False
    except ValueError:
        return False

    signed_payload = f"{ts}:{raw_body.decode('utf-8')}".encode()
    expected = hmac.new(
        settings.paddle_webhook_secret.encode(),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, h1)


# ── Event handlers ────────────────────────────────────────────────────


def _tier_from_event(event: dict[str, Any]) -> str | None:
    """
    Extract the target tier from a Paddle subscription event.

    Priority order:
      1. custom_data.tier  (set during checkout creation)
      2. product_id → _PRODUCT_TIER_MAP lookup
    """
    # Try custom_data first (most reliable)
    custom_data = event.get("data", {}).get("custom_data") or {}
    if isinstance(custom_data, dict) and custom_data.get("tier"):
        return custom_data["tier"]

    # Fall back to product_id lookup
    items = event.get("data", {}).get("items", [])
    for item in items:
        product_id = item.get("price", {}).get("product_id", "")
        tier = _PRODUCT_TIER_MAP.get(product_id)
        if tier:
            return tier

    return None


def _user_id_from_event(event: dict[str, Any]) -> int | None:
    """Extract user_id from custom_data (set during checkout)."""
    custom_data = event.get("data", {}).get("custom_data") or {}
    if isinstance(custom_data, dict):
        try:
            return int(custom_data["user_id"])
        except (KeyError, ValueError, TypeError):
            pass
    return None


async def handle_webhook_event(event: dict[str, Any]) -> str:
    """
    Process a verified Paddle webhook event.

    Returns a short status string for logging.
    """
    from database.queries import (
        get_user_by_paddle_customer,
        update_paddle_customer,
        update_paddle_subscription_status,
        upgrade_user_tier,
    )

    event_type: str = event.get("event_type", "")
    data: dict = event.get("data", {})

    logger.info("Paddle webhook: event_type=%s", event_type)

    # ── subscription.activated / subscription.updated / subscription.resumed ──
    if event_type in ("subscription.activated", "subscription.updated", "subscription.resumed"):
        tier = _tier_from_event(event)
        user_id = _user_id_from_event(event)
        customer_id: str = data.get("customer_id", "")
        subscription_id: str = data.get("id", "")
        status: str = data.get("status", "")

        if not tier:
            logger.warning("Could not determine tier from event: %s", event_type)
            return "no_tier"

        if user_id:
            await update_paddle_customer(user_id, customer_id, subscription_id)
            await upgrade_user_tier(user_id, tier)
            await update_paddle_subscription_status(user_id, status)
            logger.info("Upgraded user_id=%d to tier=%s", user_id, tier)
            return f"upgraded:{tier}"

        existing = await get_user_by_paddle_customer(customer_id)
        if existing:
            await upgrade_user_tier(existing["id"], tier)
            await update_paddle_subscription_status(existing["id"], status)
            logger.info("Upgraded user email=%s to tier=%s", existing["email"], tier)
            return f"upgraded:{tier}"

        logger.warning("No user found for paddle_customer_id=%s", customer_id)
        return "user_not_found"

    # ── subscription.canceled / subscription.paused ───────────────────────────
    if event_type in ("subscription.canceled", "subscription.paused"):
        customer_id = data.get("customer_id", "")
        status = data.get("status", event_type.split(".")[1])
        user = await get_user_by_paddle_customer(customer_id)
        if user:
            await upgrade_user_tier(user["id"], "free")
            await update_paddle_subscription_status(user["id"], status)
            logger.info(
                "Downgraded user email=%s to free (event=%s)", user["email"], event_type
            )
            return "downgraded:free"
        return "user_not_found"

    return f"ignored:{event_type}"
