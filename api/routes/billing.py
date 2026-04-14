"""
Billing endpoints for MacroPulse.

  POST /v1/billing/stripe/checkout   — create a Stripe checkout session (auth required)
  GET  /v1/billing/stripe/portal     — get Stripe customer portal URL (auth required)
  POST /v1/billing/stripe/webhook    — Stripe webhook receiver (no auth, signature verified)
  POST /v1/billing/paddle/webhook    — Paddle webhook receiver (legacy, no auth, signature verified)
  POST /v1/billing/lemonsqueezy      — Lemon Squeezy webhook receiver (legacy)
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
    Ensure a paid user has a MacroPulse account and an active API key at the given tier.

    Scoped to product_line='macropulse' so IRL keys are never touched.
    Returns (user_id, key_prefix, key_is_new).
    """
    from api.auth import generate_api_key, hash_key
    from services.email import send_welcome_email, send_upgrade_email

    user = await queries.get_user_by_email(email)
    if user is None:
        user = await queries.create_user(email)

    uid: int = user["id"]

    # Scope to MacroPulse product line — prevents cross-product key collision
    existing_keys = await queries.get_active_keys_for_user(uid, product_line="macropulse")

    if not existing_keys:
        raw_key = generate_api_key()
        await queries.create_api_key(
            user_id=uid,
            key_hash=hash_key(raw_key),
            key_prefix=raw_key[:12],
            tier=tier,
            product_line="macropulse",
            agent_count=1,
        )
        try:
            send_welcome_email(email, raw_key, tier)
        except Exception as exc:
            logger.error("send_welcome_email failed for %s: %s", email, exc)
        return uid, raw_key[:12], True
    else:
        # Re-activate if suspended, then upgrade tier
        await queries.reactivate_user_keys(uid, product_line="macropulse")
        await queries.upgrade_user_tier(uid, tier, product_line="macropulse")
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


# ── IRL Engine provisioning ──────────────────────────────────────────────────

async def _irl_provision(email: str, tier: str, agent_count: int = 1) -> tuple[int, str, bool]:
    """
    Ensure an IRL customer has an account and a license key at the given tier.

    Scoped to product_line='irl' — one IRL key per customer, independent from
    any MacroPulse key they may hold. L2 Audit requires minimum 3 agents;
    this is enforced at checkout and stored on the key for billing reconciliation.
    Returns (user_id, license_key_prefix, key_is_new).
    """
    from api.auth import generate_api_key, hash_key
    from services.email import send_irl_welcome_email

    user = await queries.get_user_by_email(email)
    if user is None:
        user = await queries.create_user(email)

    uid: int = user["id"]

    # Scope to IRL product line only
    existing_keys = await queries.get_active_keys_for_user(uid, product_line="irl")

    if not existing_keys:
        raw_key = generate_api_key()
        await queries.create_api_key(
            user_id=uid,
            key_hash=hash_key(raw_key),
            key_prefix=raw_key[:12],
            tier=tier,
            product_line="irl",
            agent_count=agent_count,
        )
        try:
            send_irl_welcome_email(email, raw_key, tier, agent_count)
        except Exception as exc:
            logger.error("send_irl_welcome_email failed for %s: %s", email, exc)
        return uid, raw_key[:12], True
    else:
        # Existing IRL customer — re-activate if suspended, upgrade tier, update agent count
        await queries.reactivate_user_keys(uid, product_line="irl")
        await queries.upgrade_user_tier(uid, tier, product_line="irl")
        await queries.update_agent_count(uid, agent_count, product_line="irl")
        key_prefix = existing_keys[0]["key_prefix"]
        try:
            send_irl_welcome_email(email, key_prefix + "...", tier, agent_count, is_upgrade=True)
        except Exception as exc:
            logger.error("send_irl_welcome_email (upgrade) failed for %s: %s", email, exc)
        return uid, key_prefix, False


# ── Stripe ───────────────────────────────────────────────────────────────────

class StripeCheckoutRequest(BaseModel):
    tier: str  # "starter" | "pro"


@router.post(
    "/stripe/public-checkout",
    summary="Create a Stripe checkout session (no auth — for pricing page)",
)
async def stripe_public_checkout(body: StripeCheckoutRequest) -> dict:
    """
    Creates a Stripe hosted checkout session without requiring an API key.
    Used by the public pricing page. Stripe collects the email; the webhook
    provisions the MacroPulse account and emails the API key on success.
    """
    import stripe as stripe_lib

    settings = get_settings()
    tier = body.tier.lower()
    if tier not in ("starter", "pro"):
        raise HTTPException(status_code=400, detail="tier must be 'starter' or 'pro'.")

    price_id = settings.stripe_starter_price_id if tier == "starter" else settings.stripe_pro_price_id
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Stripe price ID for '{tier}' not configured.")

    stripe_lib.api_key = settings.stripe_secret_key

    try:
        session = stripe_lib.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=settings.stripe_success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.stripe_cancel_url,
            metadata={"tier": tier},
        )
    except Exception as exc:
        logger.error("Stripe public checkout error: %s", exc)
        raise HTTPException(status_code=502, detail="Could not create checkout session.")

    return {"checkout_url": session.url, "tier": tier}


class IrlCheckoutRequest(BaseModel):
    tier: str         # "irl_sidecar" | "irl_audit"
    agent_count: int  # number of agents — min 1 for Sidecar, min 3 for Audit


@router.post(
    "/stripe/irl-checkout",
    summary="Create a Stripe checkout session for IRL Engine products",
)
async def stripe_irl_public_checkout(body: IrlCheckoutRequest) -> dict:
    """
    Creates a Stripe hosted checkout for IRL Sidecar L1 or IRL Audit Platform L2.
    Uses per-unit pricing — quantity = agent_count.
    No auth required; Stripe collects the email; webhook provisions the IRL license.
    """
    import stripe as stripe_lib

    settings = get_settings()
    tier = body.tier.lower()

    if tier == "irl_sidecar":
        price_id = settings.stripe_irl_sidecar_price_id
        min_agents = 1
    elif tier == "irl_audit":
        price_id = settings.stripe_irl_audit_price_id
        min_agents = 3
    else:
        raise HTTPException(status_code=400, detail="tier must be 'irl_sidecar' or 'irl_audit'.")

    agent_count = max(body.agent_count, min_agents)

    if not price_id:
        raise HTTPException(status_code=503, detail=f"IRL price ID for '{tier}' not configured yet.")

    stripe_lib.api_key = settings.stripe_secret_key

    try:
        session = stripe_lib.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": agent_count}],
            success_url=settings.stripe_irl_success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.stripe_irl_cancel_url,
            metadata={"tier": tier, "agent_count": str(agent_count)},
        )
    except Exception as exc:
        logger.error("Stripe IRL checkout error: %s", exc)
        raise HTTPException(status_code=502, detail="Could not create IRL checkout session.")

    return {"checkout_url": session.url, "tier": tier, "agent_count": agent_count}


@router.get(
    "/stripe/session-info",
    summary="Get IRL tier + agent count from a completed checkout session",
    include_in_schema=False,  # internal use by irl-welcome page only
)
async def stripe_session_info(session_id: str) -> dict:
    """
    Returns { tier, agent_count } from a Stripe checkout session.
    Used by irl-welcome.html to populate the onboarding UI without requiring auth.
    Only exposes non-sensitive metadata; never returns email or customer data.
    """
    import stripe as stripe_lib
    settings = get_settings()

    if not session_id or not session_id.startswith("cs_"):
        raise HTTPException(status_code=400, detail="Invalid session_id.")

    stripe_lib.api_key = settings.stripe_secret_key
    try:
        session = stripe_lib.checkout.Session.retrieve(session_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found.")

    meta = session.get("metadata") or {}
    return {
        "tier": meta.get("tier", ""),
        "agent_count": int(meta.get("agent_count", 1)),
    }


@router.post(
    "/stripe/checkout",
    summary="Create a Stripe checkout session",
)
async def stripe_checkout(
    body: StripeCheckoutRequest,
    key_record: dict = Depends(require_api_key),
) -> dict:
    """
    Returns a Stripe hosted checkout URL for the given tier.
    Redirect the user to `checkout_url`. After payment Stripe fires a webhook
    that upgrades the tier automatically.
    """
    import stripe as stripe_lib

    settings = get_settings()
    tier = body.tier.lower()
    if tier not in ("starter", "pro"):
        raise HTTPException(status_code=400, detail="tier must be 'starter' or 'pro'.")

    price_id = settings.stripe_starter_price_id if tier == "starter" else settings.stripe_pro_price_id
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Stripe price ID for '{tier}' not configured.")

    stripe_lib.api_key = settings.stripe_secret_key
    user_id: int = key_record["user_id"]
    email: str = key_record.get("email", "")

    try:
        session = stripe_lib.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=email or None,
            success_url=settings.stripe_success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.stripe_cancel_url,
            metadata={"user_id": str(user_id), "tier": tier},
        )
    except Exception as exc:
        logger.error("Stripe checkout error for user_id=%d: %s", user_id, exc)
        raise HTTPException(status_code=502, detail="Could not create checkout session.")

    return {"checkout_url": session.url, "tier": tier}


@router.get(
    "/stripe/portal",
    summary="Get Stripe customer portal URL",
)
async def stripe_portal(key_record: dict = Depends(require_api_key)) -> dict:
    """Returns the Stripe billing portal URL so the user can manage or cancel."""
    import stripe as stripe_lib

    settings = get_settings()
    stripe_lib.api_key = settings.stripe_secret_key

    user_id: int = key_record["user_id"]
    user = await queries.get_user_by_id(user_id)

    if not user or not user.get("stripe_customer_id"):
        raise HTTPException(status_code=404, detail="No active Stripe subscription found.")

    try:
        session = stripe_lib.billing_portal.Session.create(
            customer=user["stripe_customer_id"],
            return_url="https://api.macropulse.live/portal",
        )
    except Exception as exc:
        logger.error("Stripe portal error for user_id=%d: %s", user_id, exc)
        raise HTTPException(status_code=502, detail="Could not generate portal URL.")

    return {"portal_url": session.url}


@router.post(
    "/stripe/webhook",
    status_code=200,
    summary="Stripe webhook receiver",
    include_in_schema=False,
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
) -> dict:
    """
    Receives and processes Stripe billing events.
    Verifies the webhook signature before processing.
    Always returns 200 so Stripe doesn't retry valid deliveries.
    """
    import stripe as stripe_lib

    settings = get_settings()
    raw_body = await request.body()

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")

    try:
        event = stripe_lib.Webhook.construct_event(
            raw_body, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe_lib.errors.SignatureVerificationError:
        logger.warning("Stripe webhook: invalid signature rejected")
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Webhook parse error: {exc}")

    # Idempotency check
    event_id: str = event["id"]
    from database.connection import get_db_conn
    try:
        async with get_db_conn() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM webhook_idempotency WHERE event_id = $1", event_id
            )
            if row is not None:
                logger.info("Stripe webhook duplicate skipped: event_id=%s", event_id)
                return {"ok": True, "duplicate": True}
            await conn.execute(
                "INSERT INTO webhook_idempotency (event_id, provider) VALUES ($1, 'stripe') ON CONFLICT DO NOTHING",
                event_id,
            )
    except Exception as exc:
        logger.error("Stripe webhook idempotency check failed: %s", exc)

    try:
        result = await _stripe_handle(event, settings)
        logger.info("Stripe webhook processed: %s → %s", event["type"], result)
    except Exception as exc:
        logger.error("Stripe webhook handler error: %s", exc, exc_info=True)

    return {"ok": True}


def _stripe_tier_from_price(price_id: str) -> str | None:
    """Map a Stripe price ID to a MacroPulse or IRL tier."""
    settings = get_settings()
    if price_id == settings.stripe_starter_price_id:
        return "starter"
    if price_id == settings.stripe_pro_price_id:
        return "pro"
    if price_id == settings.stripe_irl_sidecar_price_id:
        return "irl_sidecar"
    if price_id == settings.stripe_irl_audit_price_id:
        return "irl_audit"
    return None


async def _stripe_handle(event: dict, settings) -> dict:
    import stripe as stripe_lib
    stripe_lib.api_key = settings.stripe_secret_key

    event_type: str = event["type"]
    obj: dict = event["data"]["object"]

    # ── checkout.session.completed ───────────────────────────────────
    if event_type == "checkout.session.completed":
        customer_id: str = obj.get("customer", "")
        subscription_id: str = obj.get("subscription", "")
        email: str = (obj.get("customer_email") or obj.get("customer_details", {}).get("email") or "").lower().strip()
        tier: str = obj.get("metadata", {}).get("tier", "")
        user_id_meta: str = obj.get("metadata", {}).get("user_id", "")

        if not tier or not email:
            logger.warning("Stripe checkout.session.completed missing tier/email: %s", obj.get("id"))
            return {"result": "missing_tier_or_email"}

        if tier in ("irl_sidecar", "irl_audit"):
            agent_count = int(obj.get("metadata", {}).get("agent_count", "1"))
            uid, key_prefix, is_new = await _irl_provision(email, tier, agent_count)
        else:
            uid, key_prefix, is_new = await _ls_provision(email, tier)

        await queries.upsert_stripe_subscription(uid, customer_id, subscription_id, tier, "active")
        action = f"{'created' if is_new else 'upgraded'}_to_{tier}"
        logger.info("Stripe checkout: uid=%s email=%s action=%s", uid, email, action)
        return {"result": action, "user_id": uid}

    # ── customer.subscription.updated ───────────────────────────────
    elif event_type == "customer.subscription.updated":
        customer_id = obj.get("customer", "")
        subscription_id = obj.get("id", "")
        sub_status: str = obj.get("status", "")
        price_id: str = (obj.get("items", {}).get("data") or [{}])[0].get("price", {}).get("id", "")
        tier = _stripe_tier_from_price(price_id)

        user = await queries.get_user_by_stripe_customer(customer_id)
        if not user:
            return {"result": "user_not_found", "customer_id": customer_id}

        uid = user["id"]
        product_line = "irl" if (tier or "").startswith("irl_") else "macropulse"

        if sub_status in ("active", "trialing") and tier:
            await queries.reactivate_user_keys(uid, product_line=product_line)
            await queries.upgrade_user_tier(uid, tier, product_line=product_line)
            # For IRL: sync agent count from subscription quantity
            if product_line == "irl":
                qty = (obj.get("items", {}).get("data") or [{}])[0].get("quantity", 1)
                await queries.update_agent_count(uid, int(qty), product_line="irl")
            await queries.upsert_stripe_subscription(uid, customer_id, subscription_id, price_id, sub_status)
            return {"result": f"updated_to_{tier}", "status": sub_status}
        elif sub_status in ("canceled", "unpaid", "past_due"):
            await queries.upsert_stripe_subscription(uid, customer_id, subscription_id, price_id or "", sub_status)
            if sub_status == "past_due":
                await queries.suspend_user_keys(uid, product_line=product_line)
                return {"result": "suspended_past_due", "status": sub_status}
            elif sub_status in ("canceled", "unpaid"):
                await queries.upgrade_user_tier(uid, "free", product_line=product_line)
                return {"result": "downgraded_to_free", "status": sub_status}
        return {"result": f"no_tier_change_status={sub_status}"}

    # ── customer.subscription.deleted ───────────────────────────────
    elif event_type == "customer.subscription.deleted":
        customer_id = obj.get("customer", "")
        subscription_id = obj.get("id", "")
        price_id = (obj.get("items", {}).get("data") or [{}])[0].get("price", {}).get("id", "")
        tier = _stripe_tier_from_price(price_id)
        product_line = "irl" if (tier or "").startswith("irl_") else "macropulse"

        user = await queries.get_user_by_stripe_customer(customer_id)
        if user:
            await queries.upgrade_user_tier(user["id"], "free", product_line=product_line)
            await queries.upsert_stripe_subscription(user["id"], customer_id, subscription_id, "", "canceled")
            return {"result": "deleted_downgraded_to_free"}
        return {"result": "user_not_found"}

    # ── invoice.paid ─────────────────────────────────────────────────
    elif event_type == "invoice.paid":
        # Payment confirmed — lift suspension and ensure correct tier (handles recovery from past_due)
        customer_id = obj.get("customer", "")
        subscription_id = obj.get("subscription", "")
        price_id = (obj.get("lines", {}).get("data") or [{}])[0].get("price", {}).get("id", "")
        tier = _stripe_tier_from_price(price_id)
        product_line = "irl" if (tier or "").startswith("irl_") else "macropulse"

        user = await queries.get_user_by_stripe_customer(customer_id)
        if user and tier:
            await queries.reactivate_user_keys(user["id"], product_line=product_line)
            await queries.upgrade_user_tier(user["id"], tier, product_line=product_line)
            await queries.upsert_stripe_subscription(user["id"], customer_id, subscription_id, price_id, "active")
            return {"result": "payment_confirmed_access_restored"}
        return {"result": "invoice_paid_logged"}

    # ── invoice.payment_failed ───────────────────────────────────────
    elif event_type == "invoice.payment_failed":
        customer_id = obj.get("customer", "")
        subscription_id = obj.get("subscription", "")
        price_id = (obj.get("lines", {}).get("data") or [{}])[0].get("price", {}).get("id", "")
        tier = _stripe_tier_from_price(price_id)
        product_line = "irl" if (tier or "").startswith("irl_") else "macropulse"

        logger.warning(
            "Stripe invoice.payment_failed for customer=%s product_line=%s — suspending keys",
            customer_id, product_line,
        )
        user = await queries.get_user_by_stripe_customer(customer_id)
        if user:
            await queries.suspend_user_keys(user["id"], product_line=product_line)
            await queries.upsert_stripe_subscription(
                user["id"], customer_id, subscription_id, price_id or "", "past_due"
            )
        return {"result": "payment_failed_keys_suspended"}

    # ── invoice.payment_action_required ─────────────────────────────
    elif event_type == "invoice.payment_action_required":
        logger.warning("Stripe 3DS required for customer=%s", obj.get("customer"))
        return {"result": "action_required_logged"}

    else:
        return {"result": "ignored", "event": event_type}
