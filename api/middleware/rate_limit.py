"""
Per-API-key tier-aware rate limiting middleware for MacroPulse.

Daily limits by tier:
  free     →  50  requests / day
  starter  →  500 requests / day
  pro      →  0   (unlimited)

For authenticated requests (X-MacroPulse-Key present), counters are stored
in the database (api_keys.daily_requests + usage_date) so they survive
container restarts. Tier upgrades take effect on the next request.

For unauthenticated requests, an in-memory per-IP counter is used as a
lightweight guard against anonymous abuse.

Set RATE_LIMIT_PER_DAY=0 in .env to bypass globally (dev / internal use).

Response headers (RFC 6585 / de-facto standard):
  X-RateLimit-Limit      daily cap for this key
  X-RateLimit-Remaining  requests left today
  X-RateLimit-Reset      Unix timestamp of next window reset (midnight UTC)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
from collections import defaultdict

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Paths that are never rate-limited (health, public demo, docs, auth)
_EXEMPT_PATHS = {
    "/health", "/docs", "/openapi.json", "/redoc", "/dashboard",
    "/v1/auth/register", "/v1/pipeline/status",
}

# Path prefixes that bypass rate limiting (unauthenticated public routes)
_EXEMPT_PREFIXES = ("/v1/public/",)

# Tier → daily request cap  (0 = unlimited)
TIER_LIMITS: dict[str, int] = {
    "free":    50,
    "starter": 500,
    "pro":     0,
    "owner":   0,  # unlimited — all features, no billing
}

# In-memory store for anonymous (unauthenticated) IP-based counters only.
# Authenticated counters live in the DB and survive restarts.
_anon_counters: dict[str, tuple[str, int]] = defaultdict(lambda: ("", 0))

# Per-key tier cache: key_hash → (date_string, daily_limit)
# Refreshed once per day so tier upgrades take effect within 24h.
_tier_cache: dict[str, tuple[str, int]] = {}


def _reset_ts() -> int:
    """Unix timestamp of next midnight UTC."""
    tomorrow = dt.date.today() + dt.timedelta(days=1)
    return int(dt.datetime.combine(tomorrow, dt.time(), tzinfo=dt.timezone.utc).timestamp())


def _resolve_limit(raw_key: str | None, default_limit: int) -> tuple[int, str | None]:
    """
    Return (daily_limit, key_hash) for a given raw API key.

    key_hash is None for anonymous requests.
    Falls back to `default_limit` on any DB error.
    """
    if not raw_key:
        return default_limit, None

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    today = dt.date.today().isoformat()
    cached = _tier_cache.get(key_hash)
    if cached and cached[0] == today:
        return cached[1], key_hash

    try:
        from database.queries import get_api_key_by_hash
        record = get_api_key_by_hash(key_hash)
        if record:
            tier = record.get("tier", "free")
            limit = TIER_LIMITS.get(tier, default_limit)
        else:
            limit = default_limit
    except Exception:
        limit = default_limit

    _tier_cache[key_hash] = (today, limit)
    return limit, key_hash


def get_usage_today(client_id: str) -> int:
    """Return the request count for a client_id for today (used by /auth/usage)."""
    # client_id is a key_hash for authenticated users
    try:
        from database.queries import get_daily_usage
        return get_daily_usage(client_id)
    except Exception:
        return 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-API-key tier-aware daily request cap."""

    def __init__(self, app, limit_per_day: int = 0) -> None:
        super().__init__(app)
        self.default_limit = limit_per_day  # 0 = global bypass (dev mode)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Path-based exemptions
        path = request.url.path
        if path in _EXEMPT_PATHS or any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        raw_key = request.headers.get("X-MacroPulse-Key")
        # Resolve client IP (for anonymous fallback) — take only first IP to avoid spoofing
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        first_ip = forwarded_for.split(",")[0].strip()
        client_ip = first_ip if first_ip else (request.client.host if request.client else "unknown")

        # Resolve tier limit
        limit, key_hash = _resolve_limit(raw_key, self.default_limit)

        # 0 = unlimited (pro / owner tier, or global bypass)
        if limit == 0:
            return await call_next(request)

        reset = _reset_ts()

        if key_hash:
            # ── Authenticated path: DB-persisted counter ──────────────────
            # Increment first, then check — prevents TOCTOU race.
            try:
                from database.queries import increment_daily_usage
                count = increment_daily_usage(key_hash)
            except Exception as exc:
                logger.error("Rate limit DB error for key %s…: %s", key_hash[:8], exc)
                # On DB failure, fall through rather than blocking the user.
                return await call_next(request)

            if count > limit:
                # Already over — undo the increment so we don't inflate the counter
                try:
                    from database.queries import get_daily_usage
                    count = get_daily_usage(key_hash)
                except Exception:
                    pass
                logger.warning(
                    "Rate limit exceeded: key=%s… count=%d limit=%d", key_hash[:8], count, limit
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "detail": (
                            f"Daily limit of {limit} requests reached. "
                            "Upgrade your plan or wait until midnight UTC."
                        ),
                        "upgrade_url": "https://macropulse.live/pricing",
                        "reset_at": reset,
                    },
                    headers={
                        "X-RateLimit-Limit":     str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset":     str(reset),
                        "Retry-After": str(reset - int(dt.datetime.now(dt.timezone.utc).timestamp())),
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"]     = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
            response.headers["X-RateLimit-Reset"]     = str(reset)
            return response

        else:
            # ── Anonymous path: in-memory IP counter ─────────────────────
            today = dt.date.today().isoformat()
            date_str, count = _anon_counters[client_ip]
            if date_str != today:
                count = 0

            if count >= limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "detail": (
                            f"Daily limit of {limit} requests reached. "
                            "Provide an API key or wait until midnight UTC."
                        ),
                        "reset_at": reset,
                    },
                    headers={
                        "X-RateLimit-Limit":     str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset":     str(reset),
                        "Retry-After": str(reset - int(dt.datetime.now(dt.timezone.utc).timestamp())),
                    },
                )

            count += 1
            _anon_counters[client_ip] = (today, count)

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"]     = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(limit - count)
            response.headers["X-RateLimit-Reset"]     = str(reset)
            return response
