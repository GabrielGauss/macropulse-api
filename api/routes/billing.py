"""
Billing endpoints for MacroPulse.

  POST /v1/billing/checkout          — create a Paddle checkout session (auth required)
  POST /v1/billing/portal            — get Paddle customer portal URL (auth required)
  POST /v1/billing/webhook           — Paddle webhook receiver (no auth, signature verified)
  POST /v1/billing/lemonsqueezy      — Lemon Squeezy webhook receiver (no auth, HMAC verified)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from api.auth import require_api_key
from config.settings import get_settings
from database import queries
from services.paddle import (
    create_checkout_url,
    create_portal_url,
    handle_webhook_event,
    verify_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/billing", tags=["Billing"])


class CheckoutRequest(BaseModel):
    tier: str  # "starter" | "pro"


class CheckoutResponse(BaseModel):
    checkout_url: str
    tier: str


class PortalResponse(BaseModel):
    portal_url: str


def _price_id_for_tier(tier: str) -> str:
    settings = get_settings()
    mapping = {
        "starter": settings.paddle_starter_price_id,
        "pro":     settings.paddle_pro_price_id,
    }
    price_id = mapping.get(tier, "")
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Price ID for tier '{tier}' is not configured. Contact support.",
        )
    return price_id


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create a Paddle checkout session",
)
def create_checkout(
    body: CheckoutRequest,
    key_record: dict = Depends(require_api_key),
) -> CheckoutResponse:
    """
    Returns a Paddle hosted checkout URL for upgrading to Starter or Pro.

    Redirect the user (or open in browser) to `checkout_url`.
    After payment, Paddle fires a webhook that upgrades the tier automatically.
    """
    tier = body.tier.lower()
    if tier not in ("starter", "pro"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tier must be 'starter' or 'pro'.",
        )

    current_tier = key_record.get("tier", "free")
    if current_tier == tier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You are already on the {tier} plan.",
        )

    user_id: int = key_record["user_id"]
    email: str = key_record.get("email", "")
    price_id = _price_id_for_tier(tier)

    try:
        checkout_url = create_checkout_url(
            price_id=price_id,
            user_id=user_id,
            email=email,
            tier=tier,
        )
    except Exception as exc:
        logger.error("Paddle checkout error for user_id=%d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create checkout session. Please try again.",
        )

    return CheckoutResponse(checkout_url=checkout_url, tier=tier)


@router.post(
    "/portal",
    response_model=PortalResponse,
    summary="Get Paddle customer portal URL",
)
def get_portal(
    key_record: dict = Depends(require_api_key),
) -> PortalResponse:
    """
    Returns the Paddle customer portal URL so the user can manage or cancel
    their subscription directly.
    """
    user_id: int = key_record["user_id"]
    user = queries.get_user_by_id(user_id)

    if not user or not user.get("paddle_customer_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Paddle subscription found for this account.",
        )

    try:
        portal_url = create_portal_url(user["paddle_customer_id"])
    except Exception as exc:
        logger.error("Paddle portal error for user_id=%d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not generate portal URL. Please try again.",
        )

    return PortalResponse(portal_url=portal_url)


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Paddle webhook receiver",
    include_in_schema=False,   # hide from public docs
)
async def paddle_webhook(
    request: Request,
    paddle_signature: str | None = Header(None, alias="Paddle-Signature"),
) -> dict:
    """
    Receives and processes Paddle billing events.

    Verifies the HMAC-SHA256 signature before processing.
    Always returns 200 so Paddle doesn't retry valid deliveries.
    """
    raw_body = await request.body()

    if paddle_signature is None:
        logger.warning("Paddle webhook received without signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Paddle-Signature header.",
        )

    if not verify_webhook(raw_body, paddle_signature):
        logger.warning("Paddle webhook signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature.",
        )

    try:
        import json
        event = json.loads(raw_body)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body.",
        )

    try:
        result = handle_webhook_event(event)
        logger.info("Webhook processed: %s → %s", event.get("event_type"), result)
    except Exception as exc:
        # Log but return 200 — don't let Paddle retry on our DB errors
        logger.error("Webhook handler error: %s", exc, exc_info=True)

    return {"ok": True}


# ── Lemon Squeezy webhook ────────────────────────────────────────────────────

# Variant ID (integer) → MacroPulse tier.
# Set LS_VARIANT_ID_STARTER and LS_VARIANT_ID_PRO env vars from the LS dashboard.
def _ls_variant_map() -> dict[str, str]:
    m: dict[str, str] = {}
    for env_key, tier in (("LS_VARIANT_ID_STARTER", "starter"), ("LS_VARIANT_ID_PRO", "pro")):
        v = os.getenv(env_key, "").strip()
        if v:
            m[v] = tier
    return m


def _ls_verify_signature(raw_body: bytes, signature: str) -> bool:
    secret = os.getenv("LS_WEBHOOK_SECRET", "").strip()
    if not secret:
        logger.warning("LS_WEBHOOK_SECRET not set — skipping signature check")
        return True
    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def _ls_resolve_tier(variant_id: int | str | None, variant_name: str) -> str | None:
    """Return 'starter' or 'pro' from variant_id env map, falling back to name."""
    vmap = _ls_variant_map()
    if variant_id is not None:
        t = vmap.get(str(variant_id))
        if t:
            return t
    name = (variant_name or "").lower()
    if "pro" in name:
        return "pro"
    if "starter" in name:
        return "starter"
    return None


@router.post(
    "/lemonsqueezy",
    status_code=200,
    summary="Lemon Squeezy webhook receiver",
    include_in_schema=False,
)
async def lemonsqueezy_webhook(request: Request) -> dict:
    """
    Processes Lemon Squeezy subscription lifecycle events.

    Configure in LS dashboard:
      Webhooks → Add endpoint → https://api.macropulse.live/v1/billing/lemonsqueezy
      Events: subscription_created, subscription_updated, subscription_cancelled,
              subscription_expired, subscription_payment_success, subscription_payment_failed
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Signature", "")

    if not _ls_verify_signature(raw_body, signature):
        logger.warning("LS webhook: invalid signature rejected")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature.")

    try:
        import json
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    event: str = payload.get("meta", {}).get("event_name", "")
    data: dict = payload.get("data", {})
    attrs: dict = data.get("attributes", {})
    if "id" in data:
        attrs.setdefault("subscription_id", data["id"])

    logger.info("LS webhook event=%s", event)

    try:
        result = _ls_handle(event, attrs)
    except Exception as exc:
        # Always return 200 so LS doesn't retry on our internal errors
        logger.error("LS webhook handler error: %s", exc, exc_info=True)
        result = {"result": "internal_error_logged"}

    return {"ok": True, **result}


def _ls_handle(event: str, attrs: dict) -> dict:
    email    = (attrs.get("user_email") or "").lower().strip()
    cid      = str(attrs.get("customer_id") or "")
    sid      = str(attrs.get("subscription_id") or attrs.get("id") or "")
    vid      = attrs.get("variant_id")
    vname    = attrs.get("variant_name") or attrs.get("product_name") or ""
    ls_status = attrs.get("status") or "unknown"

    # Resolve user
    user = queries.get_user_by_email(email) if email else None
    if user is None and cid:
        user = queries.get_user_by_ls_customer(cid)
    if user is None:
        logger.warning("LS %s: no user for email=%s cid=%s", event, email, cid)
        return {"result": "user_not_found", "email": email}

    uid: int = user["id"]

    if event in ("subscription_created", "subscription_updated", "subscription_resumed"):
        tier = _ls_resolve_tier(vid, vname)
        active = ls_status in ("active", "trialing", "past_due")
        if active and tier:
            queries.upgrade_user_tier(uid, tier)
            action = f"upgraded_to_{tier}"
        elif ls_status in ("expired", "unpaid", "paused"):
            queries.upgrade_user_tier(uid, "free")
            action = "downgraded_to_free"
        else:
            action = f"no_change_status={ls_status}"
        queries.upsert_ls_subscription(uid, cid, sid, str(vid or ""), ls_status)
        return {"result": action, "user_id": uid}

    elif event == "subscription_cancelled":
        # Access continues until period end; just record the cancellation
        queries.upsert_ls_subscription(uid, cid, sid, str(vid or ""), "cancelled")
        return {"result": "cancelled_access_retained", "user_id": uid}

    elif event == "subscription_expired":
        queries.upgrade_user_tier(uid, "free")
        queries.upsert_ls_subscription(uid, cid, sid, str(vid or ""), "expired")
        return {"result": "expired_downgraded_to_free", "user_id": uid}

    elif event in ("subscription_payment_success",):
        return {"result": "payment_ok_no_action"}

    elif event in ("subscription_payment_failed", "subscription_payment_recovered"):
        logger.warning("LS payment event %s for user_id=%s — LS handles dunning", event, uid)
        return {"result": f"payment_event_{event}_logged"}

    else:
        return {"result": "ignored", "event": event}
