"""
Account endpoint — returns the authenticated user's subscription details.

GET /v1/account
  → tier, product_line, agent_count, key_prefix, payment_status,
    daily usage, billing portal link
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from api.auth import require_api_key
from config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/account", tags=["Account"])

_TIER_LABEL = {
    "free":       "Free",
    "starter":    "Starter",
    "pro":        "Pro",
    "owner":      "Owner",
    "irl_sidecar": "IRL Engine — Sidecar (L1)",
    "irl_audit":   "IRL Engine — Audit (L2)",
}

_PRODUCT_LABEL = {
    "macropulse": "MacroPulse",
    "irl":        "IRL Engine",
}

_TIER_FEATURES = {
    "free": ["Regime signal (delayed 24h)", "Public endpoints only"],
    "starter": ["Daily regime signal (real-time)", "Email alerts on regime change", "REST API access"],
    "pro": [
        "All Starter features",
        "Webhook delivery on regime change",
        "Full scorecard + factor data",
        "Priority support",
    ],
    "irl_sidecar": [
        "L1 Sidecar API access",
        "Real-time regime + liquidity signal",
        "Per-agent licensing",
        "Email + webhook alerts",
    ],
    "irl_audit": [
        "All Sidecar features",
        "L2 Audit endpoints (min 3 agents)",
        "Deep factor + stress attribution",
        "Quarterly review access",
    ],
    "owner": ["Full access — all features, no rate limit"],
}


@router.get("", summary="Get account details")
async def get_account(key_record: dict[str, Any] = Depends(require_api_key)) -> dict[str, Any]:
    """
    Return subscription + usage details for the authenticated key.

    Does not expose the key hash or any sensitive credential material.
    """
    from database.queries import get_daily_usage

    settings = get_settings()
    tier         = key_record.get("tier", "free")
    product_line = key_record.get("product_line", "macropulse")
    key_prefix   = key_record.get("key_prefix", "")
    agent_count  = key_record.get("agent_count", 1)
    payment_status = key_record.get("payment_status", "active")

    # Daily usage — best effort (dev/owner keys won't have a hash-based row)
    daily_requests = 0
    raw_key = None  # we only have the record here; usage is tracked by hash
    try:
        # usage is keyed by the raw key's hash; we don't have the raw key here
        # so we look up the key record directly by prefix via a dedicated query
        from database.queries import get_daily_usage_by_prefix
        daily_requests = await get_daily_usage_by_prefix(key_prefix) or 0
    except Exception:
        daily_requests = 0

    billing_portal_url = "https://macropulse.live/dashboard"
    if product_line == "irl":
        billing_portal_url = "https://macropulse.live/irl#pricing"

    return {
        "key_prefix": key_prefix,
        "tier": tier,
        "tier_label": _TIER_LABEL.get(tier, tier.replace("_", " ").title()),
        "product": _PRODUCT_LABEL.get(product_line, product_line),
        "product_line": product_line,
        "agent_count": agent_count,
        "payment_status": payment_status,
        "features": _TIER_FEATURES.get(tier, []),
        "usage": {
            "daily_requests": daily_requests,
            "daily_limit": settings.rate_limit_per_day,
        },
        "billing_portal": billing_portal_url,
        "docs": "https://macropulse.live/api-docs",
    }
