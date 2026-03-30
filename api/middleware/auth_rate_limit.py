"""
Auth endpoint rate-limit helpers — SEC-30, SEC-31, SEC-32, SEC-33.

Provides:
  check_auth_rate_limit() — call at the top of each protected auth handler.
  get_client_ip()         — replicates Docker-bridge-aware IP extraction.
  _set_backoff_if_needed() — internal; writes locked_until after soft limit.

All persistent state lives in the auth_rate_limits table — zero in-memory dicts.
"""
from __future__ import annotations

import datetime as dt
import logging

from fastapi import HTTPException, status
from starlette.requests import Request

from database import queries
from database.connection import get_sync_cursor

logger = logging.getLogger(__name__)

# attempt_count → lockout duration in seconds applied as a progressive backoff.
# Counts below 3 or above 5 use 0 (no backoff) and 300 respectively.
_BACKOFF_SCHEDULE: dict[int, int] = {3: 30, 4: 60, 5: 300}


def get_client_ip(request: Request) -> str:
    """
    Return the real client IP, respecting the Docker bridge proxy trust model.

    X-Forwarded-For is trusted only when the direct TCP connection comes from
    the nginx reverse proxy on the 172.18.0.0/16 Docker bridge network.
    Any other source that includes this header is treated as untrusted and the
    direct connection address is used instead.
    """
    direct_host = request.client.host if request.client else ""
    _trusted_proxy = direct_host.startswith("172.18.")
    if _trusted_proxy:
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        first_ip = forwarded_for.split(",")[0].strip()
        client_ip = first_ip if first_ip else direct_host
    else:
        client_ip = direct_host or "unknown"
    return client_ip


def _set_backoff_if_needed(
    identifier: str,
    endpoint: str,
    attempt_count: int,
) -> None:
    """
    Apply a progressive lockout when the caller is still within the allowed
    window (allowed=True) but is accumulating repeated failures.

    Writes locked_until directly via a targeted UPDATE — does not touch the
    attempt_count so the upsert logic in check_and_record_attempt() remains
    the single source of truth for that column.

    Silently swallows DB errors — backoff is a UX nicety, not a hard limit.
    """
    if attempt_count < 3:
        return

    backoff_seconds = _BACKOFF_SCHEDULE.get(attempt_count, 300)
    if backoff_seconds == 0:
        return

    interval_literal = f"{backoff_seconds} seconds"
    sql = (
        "UPDATE auth_rate_limits "
        "SET locked_until = now() + %s::interval "
        "WHERE identifier = %s AND endpoint = %s"
    )
    try:
        with get_sync_cursor() as cur:
            cur.execute(sql, (interval_literal, identifier, endpoint))
    except Exception as exc:
        logger.error(
            "auth_rate_limit: backoff UPDATE failed for %s/%s: %s",
            identifier,
            endpoint,
            exc,
        )
        # Soft failure — do not re-raise; backoff is UX, not a hard guard


def check_auth_rate_limit(
    identifier: str,
    endpoint: str,
    max_attempts: int,
    window_minutes: int,
    with_backoff: bool = False,
) -> None:
    """
    Record an auth attempt and raise HTTPException(429) if the limit is exceeded.

    Args:
        identifier:    Rate-limit key — typically client IP or hashed email.
        endpoint:      One of 'register', 'verify_otp', 'recover', 'recover_verify'.
        max_attempts:  Number of attempts allowed within the window.
        window_minutes: Rolling window length in minutes.
        with_backoff:  When True, apply progressive lock after attempt_count >= 3
                       even while the request is still technically allowed.

    Raises:
        HTTPException(429) with Retry-After header when limit exceeded.
        Returns None (no raise) on any DB error — fail-open policy.
    """
    try:
        result = queries.check_and_record_attempt(
            identifier=identifier,
            endpoint=endpoint,
            max_attempts=max_attempts,
            window_minutes=window_minutes,
        )
    except Exception as exc:
        logger.error(
            "auth_rate_limit: DB error for %s/%s — failing open: %s",
            identifier,
            endpoint,
            exc,
        )
        return  # fail open — do NOT raise

    attempt_count = result["attempt_count"]
    locked_until: dt.datetime | None = result["locked_until"]
    allowed: bool = result["allowed"]

    # Apply progressive backoff while the request is still allowed
    if with_backoff and allowed and attempt_count >= 3:
        _set_backoff_if_needed(identifier, endpoint, attempt_count)

    if not allowed:
        now_utc = dt.datetime.now(dt.timezone.utc)
        if locked_until is not None and locked_until > now_utc:
            retry_after = max(1, int((locked_until - now_utc).total_seconds()))
        else:
            retry_after = 60  # default when no explicit lock expiry

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "detail": "Too many attempts. Please wait before trying again.",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
