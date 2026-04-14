"""
Webhook management endpoints.

POST /v1/webhook/set    — set or clear webhook URL (Pro tier required)
GET  /v1/webhook/test   — send a test payload to the configured webhook (Pro tier)
GET  /v1/webhook/info   — return current webhook URL (masked)
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/webhook", tags=["Webhook"])


class WebhookRequest(BaseModel):
    url: HttpUrl | None = None  # None = clear webhook


@router.post("/set", status_code=200)
async def set_webhook(
    body: WebhookRequest,
    key_record: dict = Depends(require_api_key),
):
    """Set or clear a webhook URL. Pro tier only."""
    tier = key_record.get("tier", "free")
    if tier not in ("pro", "owner"):
        raise HTTPException(status_code=403, detail="Webhook delivery requires Pro plan.")

    url = str(body.url) if body.url else None

    try:
        from database.queries import update_webhook_url
        await update_webhook_url(key_record["user_id"], url)
    except Exception as exc:
        logger.error("webhook set error: %s", exc)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    return {"status": "ok", "webhook_url": url}


@router.get("/test")
async def test_webhook(key_record: dict = Depends(require_api_key)):
    """Send a test payload to the configured webhook."""
    tier = key_record.get("tier", "free")
    if tier not in ("pro", "owner"):
        raise HTTPException(status_code=403, detail="Webhook delivery requires Pro plan.")

    try:
        from database import queries
        user = await queries.get_user_by_id(key_record["user_id"])
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    if not user or not user.get("webhook_url"):
        raise HTTPException(status_code=400, detail="No webhook URL configured. Call POST /v1/webhook/set first.")

    test_payload = {
        "regime_change": {
            "from": "recovery",
            "to": "tightening",
            "from_label": "Recovery",
            "to_label": "Tightening",
            "equity_exposure": "25%",
            "risk_score": -1.4,
            "date": "2026-03-17",
        },
        "test": True,
    }

    try:
        resp = httpx.post(user["webhook_url"], json=test_payload, timeout=10.0)
        return {"status": "delivered", "http_status": resp.status_code}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Webhook delivery failed: {exc}")


@router.get("/info")
async def get_webhook_info(key_record: dict = Depends(require_api_key)):
    """Return current webhook configuration."""
    tier = key_record.get("tier", "free")
    if tier not in ("pro", "owner"):
        raise HTTPException(status_code=403, detail="Webhook delivery requires Pro plan.")

    try:
        from database import queries
        user = await queries.get_user_by_id(key_record["user_id"])
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    url = user.get("webhook_url") if user else None
    masked = (url[:20] + "…" + url[-10:]) if url and len(url) > 32 else url
    return {"webhook_url": masked, "configured": bool(url)}
