"""
Shared FastAPI dependencies for MacroPulse route handlers.

Using these instead of inline tier checks keeps route code clean and
ensures gating logic is defined in exactly one place.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from api.auth import require_api_key

_UPGRADE_URL = "https://macropulse.live/pricing"


def require_paid(
    key_record: dict = Depends(require_api_key),
) -> dict:
    """
    Dependency that blocks free-tier users with a clear upgrade message.

    Usage:
        @router.get("/endpoint")
        def handler(key_record: dict = Depends(require_paid)):
            ...
    """
    if key_record.get("tier", "free") == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"This endpoint requires a Starter or Pro plan. "
                f"Upgrade at {_UPGRADE_URL}"
            ),
        )
    return key_record
