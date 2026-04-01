"""
Billing endpoints for MacroPulse.

  POST /v1/billing/paddle/checkout   — create a Paddle checkout session (auth required)
  GET  /v1/billing/paddle/portal     — get Paddle customer portal URL (auth required)
  POST /v1/billing/paddle/webhook    — Paddle webhook receiver (no auth, signature verified)
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
    "/paddle/checkout",
    response_model=CheckoutResponse,
    summary="Create a Paddle checkout session",
)
async def create_checkout(
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
        checkout_url = await create_checkout_url(
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


@router.get(
    "/paddle/portal",
    response_model=PortalResponse,
    summary="Get Paddle customer portal URL",
)
async def get_portal(
    key_record: dict = Depends(require_api_key),
) -> PortalResponse:
    """
    Returns the Paddle customer portal URL so the user can manage or cancel
    their subscription directly.
    """
    user_id: int = key_record["user_id"]
    user = await queries.get_user_by_id(user_id)

    if not user or not user.get("paddle_customer_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Paddle subscription found for this account.",
        )

    try:
        portal_url = await create_portal_url(user["paddle_customer_id"])
    except Exception as exc:
        logger.error("Paddle portal error for user_id=%d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not generate portal URL. Please try again.",
        )

    return PortalResponse(portal_url=portal_url)


@router.get(
    "/ls-portal",
    summary="Get Lemon Squeezy customer portal URL",
)
async def get_ls_portal(key_record: dict = Depends(require_api_key)) -> dict:
    """
    Returns the Lemon Squeezy customer portal URL for the authenticated user.
    Used by the dashboard to render a 'Manage subscription' link.
    Returns null if the user has no LS subscription on file.
    """
    user_id: int = key_record["user_id"]
    try:
        user = await queries.get_user_by_id(user_id)
    except Exception as exc:
        logger.error("ls-portal lookup error for user_id=%d: %s", user_id, exc)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    portal_url = user.get("ls_portal_url") if user else None
    tier = key_record.get("tier", "free")
    return {"portal_url": portal_url, "tier": tier, "has_subscription": bool(portal_url)}


@router.post(
    "/paddle/webhook",
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

    # Idempotency check — Paddle may retry on network errors
    event_id: str | None = (
        event.get("event_id")
        or request.headers.get("paddle-event-id")
    )
    if event_id:
        from database.connection import get_db_conn
        try:
            async with get_db_conn() as conn:
                row = await conn.fetchrow(
                    "SELECT 1 FROM webhook_idempotency WHERE event_id = $1",
                    event_id,
                )
                if row is not None:
                    logger.info("Paddle webhook duplicate skipped: event_id=%s", event_id)
                    return {"ok": True, "duplicate": True}
                await conn.execute(
                    "INSERT INTO webhook_idempotency (event_id, provider) VALUES ($1, 'paddle') ON CONFLICT DO NOTHING",
                    event_id,
                )
        except Exception as exc:
            logger.error("Webhook idempotency check failed: %s", exc)
            # Fall through and process anyway — better to double-process than reject

    try:
        result = await handle_webhook_event(event)
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
    """Verify Lemon Squeezy HMAC-SHA256 signature. Fails closed if secret missing."""
    secret = os.getenv("LS_WEBHOOK_SECRET", "").strip()
    if not secret:
        # Startup guard (SEC-20) prevents reaching here in production.
        # In dev/test, reject rather than silently accept.
        logger.error("LS_WEBHOOK_SECRET not set — rejecting webhook event (fail closed)")
        return False
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
        result = await _ls_handle(event, attrs)
    except Exception as exc:
        # Always return 200 so LS doesn't retry on our internal errors
        logger.error("LS webhook handler error: %s", exc, exc_info=True)
        result = {"result": "internal_error_logged"}

    return {"ok": True, **result}


async def _ls_provision(email: str, tier: str) -> tuple[int, str, bool]:
    """
    Ensure a paid user has an account and an active API key at the given tier.

    Returns (user_id, key_prefix, key_is_new).
    key_is_new=True  → a new plaintext key was just generated and emailed.
    key_is_new=False → user already had a key; tier was upgraded in place.
    """
    from api.auth import generate_api_key, hash_key
    from services.email import send_welcome_email, send_upgrade_email

    # Get or create user
    user = await queries.get_user_by_email(email)
    if user is None:
        user = await queries.create_user(email)

    uid: int = user["id"]

    # Check for an existing active key
    existing_keys = await queries.get_active_keys_for_user(uid)

    if not existing_keys:
        # New user (or one without a key) — generate and deliver a key
        raw_key = generate_api_key()
        await queries.create_api_key(
            user_id=uid,
            key_hash=hash_key(raw_key),
            key_prefix=raw_key[:12],
            tier=tier,
        )
        try:
            send_welcome_email(email, raw_key, tier)
        except Exception as exc:
            logger.error("send_welcome_email failed for %s: %s", email, exc)
        return uid, raw_key[:12], True
    else:
        # Existing user — upgrade tier on all active keys and notify
        await queries.upgrade_user_tier(uid, tier)
        key_prefix = existing_keys[0]["key_prefix"]
        try:
            send_upgrade_email(email, tier, key_prefix)
        except Exception as exc:
            logger.error("send_upgrade_email failed for %s: %s", email, exc)
        return uid, key_prefix, False


async def _ls_handle(event: str, attrs: dict) -> dict:
    email     = (attrs.get("user_email") or "").lower().strip()
    cid       = str(attrs.get("customer_id") or "")
    sid       = str(attrs.get("subscription_id") or attrs.get("id") or "")
    vid       = attrs.get("variant_id")
    vname     = attrs.get("variant_name") or attrs.get("product_name") or ""
    ls_status = attrs.get("status") or "unknown"
    portal_url: str | None = (attrs.get("urls") or {}).get("customer_portal") or None

    if event in ("subscription_created", "subscription_updated", "subscription_resumed"):
        tier = _ls_resolve_tier(vid, vname)
        active = ls_status in ("active", "trialing", "past_due")

        if active and tier:
            if not email:
                logger.warning("LS %s: no email in payload, cid=%s", event, cid)
                return {"result": "no_email", "cid": cid}
            uid, key_prefix, key_is_new = await _ls_provision(email, tier)
            await queries.upsert_ls_subscription(uid, cid, sid, str(vid or ""), ls_status, portal_url)
            action = f"{'created' if key_is_new else 'upgraded'}_to_{tier}"
            logger.info("LS %s: uid=%s email=%s action=%s", event, uid, email, action)
            return {"result": action, "user_id": uid}

        elif ls_status in ("expired", "unpaid", "paused"):
            # Downgrade path — user must already exist
            user = await queries.get_user_by_email(email) if email else None
            if user is None and cid:
                user = await queries.get_user_by_ls_customer(cid)
            if user:
                await queries.upgrade_user_tier(user["id"], "free")
                await queries.upsert_ls_subscription(user["id"], cid, sid, str(vid or ""), ls_status)
            return {"result": f"downgraded_to_free_status={ls_status}"}

        else:
            return {"result": f"no_change_status={ls_status}"}

    elif event == "subscription_cancelled":
        # Access continues until period end — record cancellation, don't downgrade yet
        user = await queries.get_user_by_email(email) if email else None
        if user is None and cid:
            user = await queries.get_user_by_ls_customer(cid)
        if user:
            await queries.upsert_ls_subscription(user["id"], cid, sid, str(vid or ""), "cancelled")
        return {"result": "cancelled_access_retained"}

    elif event == "subscription_expired":
        user = await queries.get_user_by_email(email) if email else None
        if user is None and cid:
            user = await queries.get_user_by_ls_customer(cid)
        if user:
            await queries.upgrade_user_tier(user["id"], "free")
            await queries.upsert_ls_subscription(user["id"], cid, sid, str(vid or ""), "expired")
        return {"result": "expired_downgraded_to_free"}

    elif event == "subscription_payment_success":
        return {"result": "payment_ok_no_action"}

    elif event in ("subscription_payment_failed", "subscription_payment_recovered"):
        logger.warning("LS payment event %s email=%s — LS handles dunning", event, email)
        return {"result": f"payment_event_{event}_logged"}

    else:
        return {"result": "ignored", "event": event}
