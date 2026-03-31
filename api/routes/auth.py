"""
User registration, key management, and usage endpoints.

  POST /v1/auth/register    — create user + issue first API key (no auth required)
  POST /v1/auth/rotate      — revoke current key + issue new one (auth required)
  GET  /v1/auth/me          — return user profile + key info (auth required)
  GET  /v1/auth/usage       — return today's request count vs tier limit (auth required)
"""

from __future__ import annotations

import datetime as dt
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request

from api.auth import generate_api_key, hash_key, require_api_key
from api.middleware.auth_rate_limit import check_auth_rate_limit, get_client_ip
from api.middleware.rate_limit import TIER_LIMITS, _reset_ts, get_usage_today
from api.schemas.responses import (
    KeyInfoResponse,
    RegisterRequest,
    RegisterResponse,
    RotateKeyResponse,
    UsageResponse,
    VerifyRequest,
)
from database import queries

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["Auth"])


def _tier_limit(tier: str) -> int:
    return TIER_LIMITS.get(tier, 50)


def _generate_code() -> str:
    return str(secrets.randbelow(1_000_000)).zfill(6)


@router.post(
    "/register",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start registration — sends a verification code to your email",
)
async def register(body: RegisterRequest, request: Request) -> dict:
    """
    Step 1 of 2: validate email format, send a 6-digit verification code.

    On success returns `{"status": "verification_sent", "email": "..."}`.
    Call `POST /v1/auth/verify` with the code to complete registration and
    receive your API key.
    """
    client_ip = get_client_ip(request)
    await check_auth_rate_limit(identifier=client_ip, endpoint="register",
                                max_attempts=5, window_minutes=60)
    email = str(body.email).strip().lower()  # EmailStr already validated by pydantic

    # Prevent duplicate registrations
    existing = await queries.get_user_by_email(email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    code = _generate_code()
    try:
        await queries.create_email_verification(email=email, code=code)
    except Exception as exc:
        logger.error("Failed to create email verification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not initiate verification. Please try again.",
        )

    try:
        from services.email import send_verification_email
        send_verification_email(to=email, code=code)
    except Exception:
        logger.warning("Verification email dispatch error for %s (non-fatal)", email, exc_info=True)

    logger.info("Verification code sent: email=%s", email)
    return {"status": "verification_sent", "email": email}


@router.post(
    "/verify",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Verify email code and receive your API key",
)
async def verify(body: VerifyRequest) -> RegisterResponse:
    """
    Step 2 of 2: submit the 6-digit code received by email.

    On success creates your account and returns your API key **once only**.
    """
    email = body.email.strip().lower()
    await check_auth_rate_limit(identifier=email, endpoint="verify_otp",
                                max_attempts=5, window_minutes=15)
    code  = body.code.strip()

    if not await queries.verify_email_code(email=email, code=code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    # Guard against replay if user submits twice before record is cleaned up
    existing = await queries.get_user_by_email(email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    try:
        user = await queries.create_user(email=email)
    except Exception as exc:
        logger.error("Failed to create user: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create account. Please try again.",
        )

    plaintext_key = generate_api_key()
    key_prefix    = plaintext_key[:12]
    try:
        await queries.create_api_key(
            user_id=user["id"],
            key_hash=hash_key(plaintext_key),
            key_prefix=key_prefix,
            tier="free",
        )
    except Exception as exc:
        logger.error("Failed to create API key: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not issue API key. Please try again.",
        )

    logger.info("New user verified and registered: email=%s tier=free", email)

    try:
        from services.email import send_welcome_email
        send_welcome_email(to=email, api_key=plaintext_key, tier="free")
    except Exception:
        logger.warning("Welcome email dispatch error for %s (non-fatal)", email, exc_info=True)

    return RegisterResponse(
        user_id=user["id"],
        email=email,
        api_key=plaintext_key,
        key_prefix=key_prefix,
        tier="free",
        daily_limit=_tier_limit("free"),
    )


@router.post(
    "/recover",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start key recovery — sends a verification code to your email",
)
async def recover(body: RegisterRequest, request: Request) -> dict:
    """
    Step 1 of 2: if the email has an account, send a 6-digit recovery code.

    Always returns the same response regardless of whether the email exists
    (prevents account enumeration). Call `POST /v1/auth/recover/verify` with
    the code to receive a new API key (old key is revoked on verify).
    """
    email = str(body.email).strip().lower()
    await check_auth_rate_limit(identifier=email, endpoint="recover",
                                max_attempts=5, window_minutes=15, with_backoff=True)

    existing = await queries.get_user_by_email(email)
    if existing:
        code = _generate_code()
        try:
            await queries.create_email_verification(email=email, code=code)
            from services.email import send_verification_email
            send_verification_email(to=email, code=code)
        except Exception as exc:
            logger.error("Key recovery initiation error for %s: %s", email, exc)
            # Still return success — don't reveal DB errors to caller

    logger.info("Key recovery requested: email=%s found=%s", email, bool(existing))
    return {"status": "recovery_code_sent", "email": email}


@router.post(
    "/recover/verify",
    response_model=RotateKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify recovery code and receive a new API key",
)
async def recover_verify(body: VerifyRequest) -> RotateKeyResponse:
    """
    Step 2 of 2: submit the 6-digit code received by email.

    On success revokes the old API key and issues a new one with the same tier.
    The new plaintext `api_key` is shown **once only**.
    """
    email = body.email.strip().lower()
    code  = body.code.strip()
    await check_auth_rate_limit(identifier=email, endpoint="recover_verify",
                                max_attempts=5, window_minutes=15, with_backoff=True)

    if not await queries.verify_email_code(email=email, code=code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired recovery code.",
        )

    user = await queries.get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found for that email.",
        )

    user_id: int = user["id"]

    # Determine current tier before revoking (via async query)
    existing_keys = await queries.get_active_keys_for_user(user_id)
    tier = existing_keys[0]["tier"] if existing_keys else "free"

    # Revoke existing keys
    try:
        await queries.revoke_api_keys_for_user(user_id)
    except Exception as exc:
        logger.error("Failed to revoke keys during recovery user_id=%d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not revoke old key. Please try again.",
        )

    # Issue new key
    plaintext_key = generate_api_key()
    key_prefix = plaintext_key[:12]
    try:
        await queries.create_api_key(
            user_id=user_id,
            key_hash=hash_key(plaintext_key),
            key_prefix=key_prefix,
            tier=tier,
        )
    except Exception as exc:
        logger.error("Failed to issue recovery key user_id=%d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not issue new key. Please try again.",
        )

    logger.info("Key recovered: user_id=%d tier=%s", user_id, tier)

    try:
        from services.email import send_key_recovery_email
        send_key_recovery_email(to=email, api_key=plaintext_key, tier=tier)
    except Exception:
        logger.warning("Recovery email dispatch error for %s (non-fatal)", email, exc_info=True)

    return RotateKeyResponse(
        api_key=plaintext_key,
        key_prefix=key_prefix,
        tier=tier,
        daily_limit=_tier_limit(tier),
    )


@router.post(
    "/rotate",
    response_model=RotateKeyResponse,
    summary="Rotate your API key",
)
async def rotate_key(
    key_record: dict = Depends(require_api_key),
) -> RotateKeyResponse:
    """
    Revoke the current API key and issue a new one with the same tier.

    The new plaintext `api_key` is shown **once only**.
    """
    user_id: int = key_record["user_id"]
    tier: str = key_record.get("tier", "free")

    # Revoke existing keys for this user
    try:
        await queries.revoke_api_keys_for_user(user_id)
    except Exception as exc:
        logger.error("Failed to revoke keys for user_id=%d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not revoke current key. Please try again.",
        )

    # Issue new key
    plaintext_key = generate_api_key()
    key_prefix = plaintext_key[:12]
    try:
        await queries.create_api_key(
            user_id=user_id,
            key_hash=hash_key(plaintext_key),
            key_prefix=key_prefix,
            tier=tier,
        )
    except Exception as exc:
        logger.error("Failed to issue new key for user_id=%d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not issue new key. Please try again.",
        )

    logger.info("Key rotated: user_id=%d tier=%s", user_id, tier)

    return RotateKeyResponse(
        api_key=plaintext_key,
        key_prefix=key_prefix,
        tier=tier,
        daily_limit=_tier_limit(tier),
    )


@router.get(
    "/me",
    response_model=KeyInfoResponse,
    summary="Your account and key info",
)
async def get_me(
    key_record: dict = Depends(require_api_key),
) -> KeyInfoResponse:
    """Return account details and key metadata (no plaintext key)."""
    tier = key_record.get("tier", "free")
    return KeyInfoResponse(
        user_id=key_record["user_id"],
        email=key_record.get("email", ""),
        key_prefix=key_record.get("key_prefix", ""),
        tier=tier,
        daily_limit=_tier_limit(tier),
        created_at=key_record.get("created_at") or dt.datetime.now(dt.timezone.utc),
        last_used_at=key_record.get("last_used_at"),
    )


@router.get(
    "/usage",
    response_model=UsageResponse,
    summary="Today's API usage vs your tier limit",
)
async def get_usage(
    key_record: dict = Depends(require_api_key),
) -> UsageResponse:
    """
    Return today's request count and how many remain before rate limiting.

    `remaining` is -1 for unlimited (Pro tier).
    `reset_at` is the Unix timestamp of next midnight UTC.
    """
    tier = key_record.get("tier", "free")
    limit = _tier_limit(tier)

    # client_id used by the rate limiter is the raw key value
    # We don't have the raw key here — use key_prefix as a proxy identifier
    # (the rate limiter keys on the raw key, but we can expose an approximation)
    key_prefix = key_record.get("key_prefix", "")
    used = await get_usage_today(key_prefix)  # best-effort (may undercount in multi-process)

    if limit == 0:
        remaining = -1
    else:
        remaining = max(0, limit - used)

    return UsageResponse(
        tier=tier,
        daily_limit=limit,
        used_today=used,
        remaining=remaining,
        reset_at=_reset_ts(),
    )
