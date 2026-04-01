"""
Parameterised database queries for MacroPulse.

All write operations use upsert semantics (INSERT … ON CONFLICT)
so the pipeline is safely idempotent.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Any

from database.connection import get_db_conn

logger = logging.getLogger(__name__)


# ── Writes ───────────────────────────────────────────────────────────


async def upsert_macro_features(row: dict[str, Any]) -> None:
    """Insert or update a single row in macro_features."""
    sql = """
        INSERT INTO macro_features (
            time, net_liquidity, d_liquidity, d_sp500, d_vix,
            d_dxy, d_hy_spread, d_yield_curve, d_10y, d_2y,
            d_gold, d_oil, d_btc, d_eth
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9, $10,
            $11, $12, $13, $14
        )
        ON CONFLICT (time) DO UPDATE SET
            net_liquidity  = EXCLUDED.net_liquidity,
            d_liquidity    = EXCLUDED.d_liquidity,
            d_sp500        = EXCLUDED.d_sp500,
            d_vix          = EXCLUDED.d_vix,
            d_dxy          = EXCLUDED.d_dxy,
            d_hy_spread    = EXCLUDED.d_hy_spread,
            d_yield_curve  = EXCLUDED.d_yield_curve,
            d_10y          = EXCLUDED.d_10y,
            d_2y           = EXCLUDED.d_2y,
            d_gold         = EXCLUDED.d_gold,
            d_oil          = EXCLUDED.d_oil,
            d_btc          = EXCLUDED.d_btc,
            d_eth          = EXCLUDED.d_eth;
    """
    # Ensure optional fields have defaults so old callers still work
    row.setdefault("d_gold", 0)
    row.setdefault("d_oil", 0)
    row.setdefault("d_btc", 0)
    row.setdefault("d_eth", 0)
    async with get_db_conn() as conn:
        await conn.execute(
            sql,
            row["time"], row["net_liquidity"], row["d_liquidity"],
            row["d_sp500"], row["d_vix"], row["d_dxy"],
            row["d_hy_spread"], row["d_yield_curve"], row["d_10y"],
            row["d_2y"], row["d_gold"], row["d_oil"],
            row["d_btc"], row["d_eth"],
        )


async def upsert_macro_factors(row: dict[str, Any]) -> None:
    """Insert or update a single row in macro_factors."""
    sql = """
        INSERT INTO macro_factors (
            time, factor_1, factor_2, factor_3, factor_4, model_version
        ) VALUES (
            $1, $2, $3, $4, $5, $6
        )
        ON CONFLICT (time) DO UPDATE SET
            factor_1      = EXCLUDED.factor_1,
            factor_2      = EXCLUDED.factor_2,
            factor_3      = EXCLUDED.factor_3,
            factor_4      = EXCLUDED.factor_4,
            model_version = EXCLUDED.model_version;
    """
    async with get_db_conn() as conn:
        await conn.execute(
            sql,
            row["time"], row["factor_1"], row["factor_2"],
            row["factor_3"], row["factor_4"], row["model_version"],
        )


async def upsert_macro_regime(row: dict[str, Any]) -> None:
    """Insert or update a single row in macro_regimes."""
    sql = """
        INSERT INTO macro_regimes (
            time, regime, prob_expansion, prob_tightening,
            prob_risk_off, prob_recovery, risk_score,
            volatility_state, model_version
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9
        )
        ON CONFLICT (time) DO UPDATE SET
            regime           = EXCLUDED.regime,
            prob_expansion   = EXCLUDED.prob_expansion,
            prob_tightening  = EXCLUDED.prob_tightening,
            prob_risk_off    = EXCLUDED.prob_risk_off,
            prob_recovery    = EXCLUDED.prob_recovery,
            risk_score       = EXCLUDED.risk_score,
            volatility_state = EXCLUDED.volatility_state,
            model_version    = EXCLUDED.model_version;
    """
    async with get_db_conn() as conn:
        await conn.execute(
            sql,
            row["time"], row["regime"], row["prob_expansion"],
            row["prob_tightening"], row["prob_risk_off"], row["prob_recovery"],
            row["risk_score"], row["volatility_state"], row["model_version"],
        )


async def upsert_drift_metrics(row: dict[str, Any]) -> None:
    """Insert or update a single row in model_drift_metrics."""
    sql = """
        INSERT INTO model_drift_metrics (
            time, pca_explained_variance, regime_persistence,
            feature_mean_shift, feature_std_shift, model_version
        ) VALUES (
            $1, $2, $3, $4, $5, $6
        )
        ON CONFLICT (time) DO UPDATE SET
            pca_explained_variance = EXCLUDED.pca_explained_variance,
            regime_persistence     = EXCLUDED.regime_persistence,
            feature_mean_shift     = EXCLUDED.feature_mean_shift,
            feature_std_shift      = EXCLUDED.feature_std_shift,
            model_version          = EXCLUDED.model_version;
    """
    async with get_db_conn() as conn:
        await conn.execute(
            sql,
            row["time"], row["pca_explained_variance"], row["regime_persistence"],
            row["feature_mean_shift"], row["feature_std_shift"], row["model_version"],
        )


async def fetch_latest_pipeline_run() -> dict[str, Any] | None:
    """Return the most recent pipeline_runs row, or None if no runs recorded."""
    sql = """
        SELECT run_ts, status, data_lag, duration_sec, error_message, model_version
        FROM pipeline_runs
        ORDER BY run_ts DESC
        LIMIT 1;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql)
        return dict(row) if row else None


async def insert_pipeline_run(row: dict[str, Any]) -> None:
    """Log a pipeline execution."""
    sql = """
        INSERT INTO pipeline_runs (
            run_ts, status, data_lag, duration_sec,
            error_message, model_version
        ) VALUES (
            $1, $2, $3, $4, $5, $6
        );
    """
    async with get_db_conn() as conn:
        await conn.execute(
            sql,
            row["run_ts"], row["status"], row["data_lag"],
            row["duration_sec"], row["error_message"], row["model_version"],
        )


# ── Reads ────────────────────────────────────────────────────────────


async def fetch_current_regime() -> dict[str, Any] | None:
    """Return the most recent regime row."""
    sql = """
        SELECT * FROM macro_regimes
        ORDER BY time DESC
        LIMIT 1;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql)
        return dict(row) if row else None


async def fetch_regime_history(
    start: dt.date | None = None,
    end: dt.date | None = None,
    limit: int = 90,
) -> list[dict[str, Any]]:
    """Return regime history within an optional date window."""
    conditions: list[str] = []
    args: list[Any] = []
    if start:
        args.append(start)
        conditions.append(f"time >= ${len(args)}")
    if end:
        args.append(end)
        conditions.append(f"time <= ${len(args)}")
    args.append(limit)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT * FROM macro_regimes
        {where}
        ORDER BY time DESC
        LIMIT ${len(args)};
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql, *args)
        return [dict(r) for r in rows]


async def fetch_public_chart_data(limit: int = 730) -> list[dict[str, Any]]:
    """
    Return regime history + SP500/Gold daily returns for the public chart.
    LEFT JOINs macro_features so regime rows without feature data still appear.
    """
    sql = """
        SELECT
            r.time,
            r.regime,
            r.risk_score,
            COALESCE(f.d_sp500, 0) AS d_sp500,
            COALESCE(f.d_gold,  0) AS d_gold
        FROM macro_regimes r
        LEFT JOIN macro_features f ON f.time::date = r.time::date
        ORDER BY r.time DESC
        LIMIT $1;
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql, limit)
        return [dict(r) for r in rows]


async def create_newsletter_subscriber(email: str) -> None:
    """Insert a newsletter subscriber, silently ignoring duplicates."""
    sql = """
        INSERT INTO newsletter_subscribers (email)
        VALUES ($1)
        ON CONFLICT (email) DO NOTHING;
    """
    async with get_db_conn() as conn:
        await conn.execute(sql, email)


async def fetch_latest_liquidity(limit: int = 30) -> list[dict[str, Any]]:
    """Return recent net liquidity values."""
    sql = """
        SELECT time, net_liquidity, d_liquidity
        FROM macro_features
        ORDER BY time DESC
        LIMIT $1;
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql, limit)
        return [dict(r) for r in rows]


async def fetch_latest_factors(limit: int = 30) -> list[dict[str, Any]]:
    """Return recent PCA factors."""
    sql = """
        SELECT * FROM macro_factors
        ORDER BY time DESC
        LIMIT $1;
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql, limit)
        return [dict(r) for r in rows]


async def fetch_latest_drift(limit: int = 30) -> list[dict[str, Any]]:
    """Return recent drift metrics."""
    sql = """
        SELECT * FROM model_drift_metrics
        ORDER BY time DESC
        LIMIT $1;
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql, limit)
        return [dict(r) for r in rows]


# ── User management ──────────────────────────────────────────────────


async def create_user(email: str, name: str | None = None) -> dict[str, Any]:
    """Insert a new user row. Raises if email already exists."""
    sql = """
        INSERT INTO users (email, name)
        VALUES ($1, $2)
        RETURNING id, email, name, created_at;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, email, name)
        return dict(row)


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    sql = "SELECT id, email, name, created_at, paddle_customer_id, paddle_subscription_id FROM users WHERE email = $1;"
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, email)
        return dict(row) if row else None


async def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    sql = "SELECT id, email, name, created_at, paddle_customer_id, paddle_subscription_id, paddle_subscription_status, ls_portal_url, ls_status FROM users WHERE id = $1;"
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, user_id)
        return dict(row) if row else None


async def update_paddle_customer(
    user_id: int,
    paddle_customer_id: str,
    paddle_subscription_id: str | None = None,
) -> None:
    sql = """
        UPDATE users
        SET paddle_customer_id     = $1,
            paddle_subscription_id = COALESCE($2, paddle_subscription_id)
        WHERE id = $3;
    """
    async with get_db_conn() as conn:
        await conn.execute(sql, paddle_customer_id, paddle_subscription_id, user_id)


async def get_user_by_paddle_customer(paddle_customer_id: str) -> dict[str, Any] | None:
    sql = """
        SELECT id, email, name, paddle_customer_id, paddle_subscription_id
        FROM users WHERE paddle_customer_id = $1;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, paddle_customer_id)
        return dict(row) if row else None


async def update_paddle_subscription_status(user_id: int, status: str) -> None:
    """Persist Paddle subscription status on the users row (BILL-02)."""
    async with get_db_conn() as conn:
        await conn.execute(
            "UPDATE users SET paddle_subscription_status = $1 WHERE id = $2",
            status,
            user_id,
        )


async def get_user_by_ls_customer(ls_customer_id: str) -> dict[str, Any] | None:
    sql = """
        SELECT id, email, name, ls_customer_id, ls_subscription_id, ls_status
        FROM users WHERE ls_customer_id = $1;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, ls_customer_id)
        return dict(row) if row else None


async def upsert_ls_subscription(
    user_id: int,
    ls_customer_id: str,
    ls_subscription_id: str,
    ls_variant_id: str,
    ls_status: str,
    ls_portal_url: str | None = None,
) -> None:
    """Persist Lemon Squeezy subscription data on the user row."""
    sql = """
        UPDATE users
        SET ls_customer_id     = $1,
            ls_subscription_id = $2,
            ls_variant_id      = $3,
            ls_status          = $4,
            ls_portal_url      = COALESCE($5, ls_portal_url)
        WHERE id = $6;
    """
    async with get_db_conn() as conn:
        await conn.execute(
            sql,
            ls_customer_id, ls_subscription_id, ls_variant_id,
            ls_status, ls_portal_url, user_id,
        )


async def upgrade_user_tier(user_id: int, tier: str) -> None:
    """Set the tier on all active API keys for a user."""
    sql = "UPDATE api_keys SET tier = $1 WHERE user_id = $2 AND is_active = TRUE;"
    async with get_db_conn() as conn:
        await conn.execute(sql, tier, user_id)


async def create_api_key(
    user_id: int,
    key_hash: str,
    key_prefix: str,
    tier: str = "free",
) -> dict[str, Any]:
    """Store a hashed API key. Returns the created row (no plaintext)."""
    sql = """
        INSERT INTO api_keys (user_id, key_hash, key_prefix, tier)
        VALUES ($1, $2, $3, $4)
        RETURNING id, user_id, key_prefix, tier, is_active, created_at;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, user_id, key_hash, key_prefix, tier)
        return dict(row)


async def get_api_key_by_hash(key_hash: str) -> dict[str, Any] | None:
    """
    Look up a key by its SHA-256 hash.

    Returns the key row joined with the user email, or None if not found
    or the key has been revoked.
    """
    sql = """
        SELECT k.id, k.user_id, k.key_prefix, k.tier, k.is_active,
               k.created_at, k.last_used_at, u.email, u.name
        FROM api_keys k
        JOIN users u ON u.id = k.user_id
        WHERE k.key_hash = $1
          AND k.is_active = TRUE;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, key_hash)
        return dict(row) if row else None


async def get_active_keys_for_user(user_id: int) -> list[dict[str, Any]]:
    """Return all active API key rows for a user (key_hash not exposed)."""
    sql = """
        SELECT id, user_id, key_prefix, tier, is_active, created_at
        FROM api_keys
        WHERE user_id = $1 AND is_active = TRUE
        ORDER BY created_at ASC;
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql, user_id)
        return [dict(r) for r in rows]


async def revoke_api_keys_for_user(user_id: int) -> None:
    """Deactivate all active keys for a user (used during rotation)."""
    sql = """
        UPDATE api_keys
        SET is_active = FALSE, revoked_at = now()
        WHERE user_id = $1 AND is_active = TRUE;
    """
    async with get_db_conn() as conn:
        await conn.execute(sql, user_id)


async def touch_api_key(key_hash: str) -> None:
    """Update last_used_at for a key (fire-and-forget, best effort)."""
    sql = "UPDATE api_keys SET last_used_at = now() WHERE key_hash = $1;"
    async with get_db_conn() as conn:
        await conn.execute(sql, key_hash)


_IP_LOCK_MINUTES = 15


async def check_and_set_ip_lock(key_hash: str, client_ip: str) -> bool:
    """
    Enforce single-location key usage.

    Returns True  → request allowed (same IP, or lock expired, or first use).
    Returns False → request blocked (different IP, lock still active).

    The lock refreshes on every allowed request, so a user actively polling
    keeps the key bound to their IP. After IP_LOCK_MINUTES of inactivity the
    key is released and can be claimed from any location.
    """
    sql = """
        WITH current AS (
            SELECT last_ip, ip_locked_at
            FROM api_keys
            WHERE key_hash = $1
        ),
        updated AS (
            UPDATE api_keys
            SET last_ip      = CASE
                                  WHEN (SELECT last_ip FROM current) IS NULL
                                    OR (SELECT last_ip FROM current) = $2
                                    OR (SELECT ip_locked_at FROM current) < NOW() - INTERVAL 'WINDOW_INTERVAL'
                                  THEN $2
                                  ELSE (SELECT last_ip FROM current)
                                END,
                ip_locked_at = CASE
                                  WHEN (SELECT last_ip FROM current) IS NULL
                                    OR (SELECT last_ip FROM current) = $2
                                    OR (SELECT ip_locked_at FROM current) < NOW() - INTERVAL 'WINDOW_INTERVAL'
                                  THEN NOW()
                                  ELSE (SELECT ip_locked_at FROM current)
                                END
            WHERE key_hash = $1
            RETURNING last_ip
        )
        SELECT (SELECT last_ip FROM current) AS old_ip,
               (SELECT last_ip FROM updated) AS new_ip;
    """
    # asyncpg cannot parameterise values inside INTERVAL literals; use str.replace()
    sql = sql.replace("WINDOW_INTERVAL", f"{_IP_LOCK_MINUTES} minutes")
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, key_hash, client_ip)
    if not row:
        return True  # key not found — let auth handle it
    old_ip = row["old_ip"]
    new_ip = row["new_ip"]
    # Blocked if a different IP held the lock and we didn't update it
    return new_ip == client_ip or old_ip is None


async def increment_daily_usage(key_hash: str) -> int:
    """
    Atomically increment the daily request counter for a key.

    Resets the counter when the date changes (UTC).
    Returns the new count after incrementing.
    Persists across container restarts — the counter lives in the DB.
    """
    sql = """
        UPDATE api_keys
        SET
            usage_date      = CURRENT_DATE,
            daily_requests  = CASE
                                WHEN usage_date = CURRENT_DATE THEN daily_requests + 1
                                ELSE 1
                              END,
            last_used_at    = now()
        WHERE key_hash = $1
        RETURNING daily_requests;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, key_hash)
        return int(row["daily_requests"]) if row else 1


async def get_daily_usage(key_hash: str) -> int:
    """Return today's request count for a key (0 if not found or date differs)."""
    sql = """
        SELECT daily_requests
        FROM api_keys
        WHERE key_hash = $1
          AND usage_date = CURRENT_DATE
          AND is_active = TRUE;
    """
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, key_hash)
        return int(row["daily_requests"]) if row else 0


async def get_alert_recipients() -> list[dict]:
    """Return all active users on starter/pro tier for regime change alerts (owner excluded)."""
    sql = """
        SELECT DISTINCT ON (u.id)
            u.id, u.email, k.tier, u.webhook_url, u.alerts_enabled
        FROM users u
        JOIN api_keys k ON k.user_id = u.id
        WHERE k.is_active = TRUE
          AND k.tier IN ('starter', 'pro')
          AND u.alerts_enabled = TRUE
        ORDER BY u.id, k.created_at DESC
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql)
        return [dict(r) for r in rows]


async def update_webhook_url(user_id: int, webhook_url: str | None) -> None:
    """Set or clear a user's webhook URL."""
    async with get_db_conn() as conn:
        await conn.execute(
            "UPDATE users SET webhook_url = $1 WHERE id = $2",
            webhook_url, user_id,
        )


async def fetch_subscriber_emails() -> list[str]:
    """Return emails of all Starter/Pro users with an active API key (paid digest only)."""
    sql = """
        SELECT DISTINCT u.email
        FROM users u
        JOIN api_keys k ON k.user_id = u.id
        WHERE k.is_active = TRUE AND k.tier IN ('starter', 'pro')
        ORDER BY u.email;
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql)
        return [row["email"] for row in rows]


# ── Email verification ─────────────────────────────────────────────────

async def create_email_verification(email: str, code: str) -> None:
    """Delete any existing pending code for this email and insert a fresh one."""
    async with get_db_conn() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM email_verifications WHERE email = $1;",
                email,
            )
            await conn.execute(
                """
                INSERT INTO email_verifications (email, code, expires_at)
                VALUES ($1, $2, NOW() + INTERVAL '15 minutes');
                """,
                email, code,
            )


_OTP_MAX_ATTEMPTS = 5


async def verify_email_code(email: str, code: str) -> bool:
    """
    Mark code used and return True if valid + unexpired, False otherwise.

    Wrong guesses increment an attempt counter; after 5 failures the row is
    exhausted (marked used) so further guesses are impossible.
    """
    async with get_db_conn() as conn:
        async with conn.transaction():
            # Attempt exact match — also guards on attempt ceiling
            row = await conn.fetchrow(
                """
                UPDATE email_verifications
                SET used = TRUE
                WHERE email = $1
                  AND code  = $2
                  AND expires_at > NOW()
                  AND used = FALSE
                  AND attempts < $3
                RETURNING id;
                """,
                email, code, _OTP_MAX_ATTEMPTS,
            )
            if row:
                return True

            # Wrong code — increment attempts; exhaust row if ceiling reached
            await conn.execute(
                """
                UPDATE email_verifications
                SET attempts = attempts + 1,
                    used = (attempts + 1 >= $1)
                WHERE email = $2
                  AND expires_at > NOW()
                  AND used = FALSE;
                """,
                _OTP_MAX_ATTEMPTS, email,
            )
            return False


async def fetch_latest_features(limit: int = 252) -> list[dict[str, Any]]:
    """Return recent macro feature rows (used by domain views and performance attribution)."""
    sql = """
        SELECT time, d_sp500, d_vix, d_dxy, d_hy_spread,
               d_yield_curve, d_10y, d_2y, net_liquidity, d_liquidity,
               COALESCE(d_gold, 0) AS d_gold,
               COALESCE(d_oil,  0) AS d_oil,
               COALESCE(d_btc,  0) AS d_btc,
               COALESCE(d_eth,  0) AS d_eth
        FROM macro_features
        ORDER BY time DESC
        LIMIT $1;
    """
    async with get_db_conn() as conn:
        rows = await conn.fetch(sql, limit)
        return [dict(r) for r in rows]


# ── Auth endpoint rate limiting ────────────────────────────────────────


async def check_and_record_attempt(
    identifier: str,
    endpoint: str,
    max_attempts: int,
    window_minutes: int,
) -> dict:
    """
    Atomically record an auth attempt and return current state.

    Uses INSERT ... ON CONFLICT ... DO UPDATE so a single round-trip both
    records the attempt and reads back the current window state.

    Returns: {"attempt_count": int, "locked_until": datetime|None, "allowed": bool}
    On DB error: raises — caller handles fail-open.

    NOTE: WINDOW_INTERVAL is substituted via str.replace() before execution
    because asyncpg cannot parameterise values inside INTERVAL literals.
    """
    sql = """
        INSERT INTO auth_rate_limits (identifier, endpoint, attempt_count, window_start, updated_at)
        VALUES ($1, $2, 1, now(), now())
        ON CONFLICT (identifier, endpoint) DO UPDATE
            SET attempt_count = CASE
                                    WHEN auth_rate_limits.window_start < now() - INTERVAL 'WINDOW_INTERVAL'
                                    THEN 1
                                    ELSE auth_rate_limits.attempt_count + 1
                                END,
                window_start  = CASE
                                    WHEN auth_rate_limits.window_start < now() - INTERVAL 'WINDOW_INTERVAL'
                                    THEN now()
                                    ELSE auth_rate_limits.window_start
                                END,
                locked_until  = CASE
                                    WHEN auth_rate_limits.window_start < now() - INTERVAL 'WINDOW_INTERVAL'
                                    THEN NULL
                                    WHEN auth_rate_limits.locked_until IS NOT NULL
                                         AND auth_rate_limits.locked_until > now()
                                    THEN auth_rate_limits.locked_until
                                    ELSE NULL
                                END,
                updated_at    = now()
        RETURNING attempt_count, locked_until;
    """
    # asyncpg cannot substitute values inside INTERVAL literals; use str.replace()
    sql = sql.replace("WINDOW_INTERVAL", f"{window_minutes} minutes")
    async with get_db_conn() as conn:
        row = await conn.fetchrow(sql, identifier, endpoint)

    if not row:
        # Defensive fallback — should not happen with RETURNING on an upsert
        return {"attempt_count": 1, "locked_until": None, "allowed": True}

    attempt_count = int(row["attempt_count"])
    locked_until = row["locked_until"]

    # Determine allowed: blocked if still under an active lock OR attempt ceiling exceeded
    now_utc = dt.datetime.now(dt.timezone.utc)
    if locked_until is not None and locked_until > now_utc:
        allowed = False
    elif attempt_count > max_attempts:
        allowed = False
    else:
        allowed = True

    return {"attempt_count": attempt_count, "locked_until": locked_until, "allowed": allowed}


# ── GDPR right-to-erasure ─────────────────────────────────────────────


async def anonymise_user(user_id: int) -> bool:
    """
    GDPR right-to-erasure (Article 17). Anonymise the user row, deactivate all
    API keys, nullify PII in audit tables, and remove the newsletter subscription.
    All five operations run in one atomic transaction.

    Authentication note: deletion is authorised by possession of a valid API key
    (the X-MacroPulse-Key header). No email OTP re-verification is required —
    API key auth is not susceptible to CSRF (no browser cookies involved).

    Re-registration note: after anonymisation get_user_by_email() returns None
    for the original address, so the same email may register a new account.
    This is correct GDPR behaviour — data is erased, not just hidden.

    Subscription note: if ls_status = 'active', we proceed with erasure and log
    a warning. The user is expected to cancel via the billing portal beforehand.
    Subscription management is out of scope for Phase 11.

    Returns True if a users row was found and anonymised, False if user_id not found.
    """
    anon_email = f"deleted_{uuid.uuid4()}@deleted.invalid"
    async with get_db_conn() as conn:
        async with conn.transaction():
            # Step 1: Capture real email BEFORE overwriting (needed for newsletter DELETE)
            row = await conn.fetchrow("SELECT email, ls_status FROM users WHERE id = $1", user_id)
            if row is None:
                return False
            real_email = row["email"]
            if row["ls_status"] == "active":
                logger.warning(
                    "GDPR deletion for user_id=%d with active LS subscription. "
                    "Subscription was not cancelled automatically.",
                    user_id,
                )

            # Step 2: Anonymise the users row
            result = await conn.execute(
                """
                UPDATE users
                SET
                    email                      = $1,
                    name                       = NULL,
                    paddle_customer_id         = NULL,
                    paddle_subscription_id     = NULL,
                    paddle_subscription_status = NULL,
                    webhook_url                = NULL,
                    alerts_enabled             = FALSE,
                    ls_customer_id             = NULL,
                    ls_subscription_id         = NULL,
                    ls_variant_id              = NULL,
                    ls_status                  = NULL,
                    ls_portal_url              = NULL,
                    deleted_at                 = now()
                WHERE id = $2
                """,
                anon_email,
                user_id,
            )
            if result == "UPDATE 0":
                return False

            # Step 3: Deactivate all API keys and wipe historical IP data
            await conn.execute(
                """
                UPDATE api_keys
                SET
                    is_active    = FALSE,
                    revoked_at   = now(),
                    last_ip      = NULL,
                    ip_locked_at = NULL
                WHERE user_id = $1
                """,
                user_id,
            )

            # Step 4: Nullify PII in webhook_deliveries
            # payload JSONB commonly contains raw Paddle/LS event bodies with customer email
            await conn.execute(
                """
                UPDATE webhook_deliveries
                SET user_id = NULL,
                    payload  = NULL
                WHERE user_id = $1
                """,
                user_id,
            )

            # Step 5: Nullify PII in api_key_audit_log
            # Neither webhook_deliveries nor api_key_audit_log has a FK on user_id
            # (confirmed migration 008) — explicit nullification required
            await conn.execute(
                """
                UPDATE api_key_audit_log
                SET user_id    = NULL,
                    ip_addr    = NULL,
                    user_agent = NULL
                WHERE user_id = $1
                """,
                user_id,
            )

            # Step 6: Remove newsletter subscription using real email (captured above)
            await conn.execute(
                "DELETE FROM newsletter_subscribers WHERE email = $1",
                real_email,
            )

    return True
