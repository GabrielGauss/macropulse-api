"""
Public configuration endpoint — exposes client-safe settings to the
marketing site (Paddle client token + price IDs).
"""

from __future__ import annotations

from fastapi import APIRouter

from config.settings import get_settings

router = APIRouter(prefix="/v1", tags=["Public"])


@router.get("/config", include_in_schema=False)
def get_public_config() -> dict:
    """
    Return client-safe configuration values for the marketing site.

    These values are intentionally public (Paddle client-side tokens).
    Never include server-side secrets here.
    """
    s = get_settings()
    return {
        "paddle_client_token":    s.paddle_client_token,
        "paddle_starter_price_id": s.paddle_starter_price_id,
        "paddle_pro_price_id":     s.paddle_pro_price_id,
        "paddle_environment":      s.paddle_environment,
    }
