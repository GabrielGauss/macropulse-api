"""
Parameterised database queries for MacroPulse.

All write operations use upsert semantics (INSERT … ON CONFLICT)
so the pipeline is safely idempotent.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from database.connection import get_sync_cursor

logger = logging.getLogger(__name__)


# ── Writes ───────────────────────────────────────────────────────────


def upsert_macro_features(row: dict[str, Any]) -> None:
    """Insert or update a single row in macro_features."""
    sql = """
        INSERT INTO macro_features (
            time, net_liquidity, d_liquidity, d_sp500, d_vix,
            d_dxy, d_hy_spread, d_yield_curve, d_10y, d_2y,
            d_gold, d_oil, d_btc, d_eth
        ) VALUES (
            %(time)s, %(net_liquidity)s, %(d_liquidity)s, %(d_sp500)s, %(d_vix)s,
            %(d_dxy)s, %(d_hy_spread)s, %(d_yield_curve)s, %(d_10y)s, %(d_2y)s,
            %(d_gold)s, %(d_oil)s, %(d_btc)s, %(d_eth)s
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
    with get_sync_cursor() as cur:
        cur.execute(sql, row)


def upsert_macro_factors(row: dict[str, Any]) -> None:
    """Insert or update a single row in macro_factors."""
    sql = """
        INSERT INTO macro_factors (
            time, factor_1, factor_2, factor_3, factor_4, model_version
        ) VALUES (
            %(time)s, %(factor_1)s, %(factor_2)s, %(factor_3)s,
            %(factor_4)s, %(model_version)s
        )
        ON CONFLICT (time) DO UPDATE SET
            factor_1      = EXCLUDED.factor_1,
            factor_2      = EXCLUDED.factor_2,
            factor_3      = EXCLUDED.factor_3,
            factor_4      = EXCLUDED.factor_4,
            model_version = EXCLUDED.model_version;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, row)


def upsert_macro_regime(row: dict[str, Any]) -> None:
    """Insert or update a single row in macro_regimes."""
    sql = """
        INSERT INTO macro_regimes (
            time, regime, prob_expansion, prob_tightening,
            prob_risk_off, prob_recovery, risk_score,
            volatility_state, model_version
        ) VALUES (
            %(time)s, %(regime)s, %(prob_expansion)s, %(prob_tightening)s,
            %(prob_risk_off)s, %(prob_recovery)s, %(risk_score)s,
            %(volatility_state)s, %(model_version)s
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
    with get_sync_cursor() as cur:
        cur.execute(sql, row)


def upsert_drift_metrics(row: dict[str, Any]) -> None:
    """Insert or update a single row in model_drift_metrics."""
    sql = """
        INSERT INTO model_drift_metrics (
            time, pca_explained_variance, regime_persistence,
            feature_mean_shift, feature_std_shift, model_version
        ) VALUES (
            %(time)s, %(pca_explained_variance)s, %(regime_persistence)s,
            %(feature_mean_shift)s, %(feature_std_shift)s, %(model_version)s
        )
        ON CONFLICT (time) DO UPDATE SET
            pca_explained_variance = EXCLUDED.pca_explained_variance,
            regime_persistence     = EXCLUDED.regime_persistence,
            feature_mean_shift     = EXCLUDED.feature_mean_shift,
            feature_std_shift      = EXCLUDED.feature_std_shift,
            model_version          = EXCLUDED.model_version;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, row)


def fetch_latest_pipeline_run() -> dict[str, Any] | None:
    """Return the most recent pipeline_runs row, or None if no runs recorded."""
    sql = """
        SELECT run_ts, status, data_lag, duration_sec, error_message, model_version
        FROM pipeline_runs
        ORDER BY run_ts DESC
        LIMIT 1;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
        return dict(row) if row else None


def insert_pipeline_run(row: dict[str, Any]) -> None:
    """Log a pipeline execution."""
    sql = """
        INSERT INTO pipeline_runs (
            run_ts, status, data_lag, duration_sec,
            error_message, model_version
        ) VALUES (
            %(run_ts)s, %(status)s, %(data_lag)s, %(duration_sec)s,
            %(error_message)s, %(model_version)s
        );
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, row)


# ── Reads ────────────────────────────────────────────────────────────


def fetch_current_regime() -> dict[str, Any] | None:
    """Return the most recent regime row."""
    sql = """
        SELECT * FROM macro_regimes
        ORDER BY time DESC
        LIMIT 1;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()  # type: ignore[return-value]


def fetch_regime_history(
    start: dt.date | None = None,
    end: dt.date | None = None,
    limit: int = 90,
) -> list[dict[str, Any]]:
    """Return regime history within an optional date window."""
    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit}
    if start:
        conditions.append("time >= %(start)s")
        params["start"] = start
    if end:
        conditions.append("time <= %(end)s")
        params["end"] = end
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT * FROM macro_regimes
        {where}
        ORDER BY time DESC
        LIMIT %(limit)s;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()  # type: ignore[return-value]


def fetch_public_chart_data(limit: int = 730) -> list[dict[str, Any]]:
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
        LIMIT %(limit)s;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"limit": limit})
        return cur.fetchall()  # type: ignore[return-value]


def create_newsletter_subscriber(email: str) -> None:
    """Insert a newsletter subscriber, silently ignoring duplicates."""
    sql = """
        INSERT INTO newsletter_subscribers (email)
        VALUES (%(email)s)
        ON CONFLICT (email) DO NOTHING;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"email": email})


def fetch_latest_liquidity(limit: int = 30) -> list[dict[str, Any]]:
    """Return recent net liquidity values."""
    sql = """
        SELECT time, net_liquidity, d_liquidity
        FROM macro_features
        ORDER BY time DESC
        LIMIT %(limit)s;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"limit": limit})
        return cur.fetchall()  # type: ignore[return-value]


def fetch_latest_factors(limit: int = 30) -> list[dict[str, Any]]:
    """Return recent PCA factors."""
    sql = """
        SELECT * FROM macro_factors
        ORDER BY time DESC
        LIMIT %(limit)s;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"limit": limit})
        return cur.fetchall()  # type: ignore[return-value]


def fetch_latest_drift(limit: int = 30) -> list[dict[str, Any]]:
    """Return recent drift metrics."""
    sql = """
        SELECT * FROM model_drift_metrics
        ORDER BY time DESC
        LIMIT %(limit)s;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"limit": limit})
        return cur.fetchall()  # type: ignore[return-value]


# ── User management ──────────────────────────────────────────────────


def create_user(email: str, name: str | None = None) -> dict[str, Any]:
    """Insert a new user row. Raises if email already exists."""
    sql = """
        INSERT INTO users (email, name)
        VALUES (%(email)s, %(name)s)
        RETURNING id, email, name, created_at;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"email": email, "name": name})
        return cur.fetchone()  # type: ignore[return-value]


def get_user_by_email(email: str) -> dict[str, Any] | None:
    sql = "SELECT id, email, name, created_at, paddle_customer_id, paddle_subscription_id FROM users WHERE email = %(email)s;"
    with get_sync_cursor() as cur:
        cur.execute(sql, {"email": email})
        return cur.fetchone()  # type: ignore[return-value]


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    sql = "SELECT id, email, name, created_at, paddle_customer_id, paddle_subscription_id FROM users WHERE id = %(id)s;"
    with get_sync_cursor() as cur:
        cur.execute(sql, {"id": user_id})
        return cur.fetchone()  # type: ignore[return-value]


def update_paddle_customer(
    user_id: int,
    paddle_customer_id: str,
    paddle_subscription_id: str | None = None,
) -> None:
    sql = """
        UPDATE users
        SET paddle_customer_id     = %(cid)s,
            paddle_subscription_id = COALESCE(%(sid)s, paddle_subscription_id)
        WHERE id = %(uid)s;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"cid": paddle_customer_id, "sid": paddle_subscription_id, "uid": user_id})


def get_user_by_paddle_customer(paddle_customer_id: str) -> dict[str, Any] | None:
    sql = """
        SELECT id, email, name, paddle_customer_id, paddle_subscription_id
        FROM users WHERE paddle_customer_id = %(cid)s;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"cid": paddle_customer_id})
        return cur.fetchone()  # type: ignore[return-value]


def get_user_by_ls_customer(ls_customer_id: str) -> dict[str, Any] | None:
    sql = """
        SELECT id, email, name, ls_customer_id, ls_subscription_id, ls_status
        FROM users WHERE ls_customer_id = %(cid)s;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"cid": ls_customer_id})
        return cur.fetchone()  # type: ignore[return-value]


def upsert_ls_subscription(
    user_id: int,
    ls_customer_id: str,
    ls_subscription_id: str,
    ls_variant_id: str,
    ls_status: str,
) -> None:
    """Persist Lemon Squeezy subscription data on the user row."""
    sql = """
        UPDATE users
        SET ls_customer_id     = %(cid)s,
            ls_subscription_id = %(sid)s,
            ls_variant_id      = %(vid)s,
            ls_status          = %(status)s
        WHERE id = %(uid)s;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {
            "cid": ls_customer_id,
            "sid": ls_subscription_id,
            "vid": ls_variant_id,
            "status": ls_status,
            "uid": user_id,
        })


def upgrade_user_tier(user_id: int, tier: str) -> None:
    """Set the tier on all active API keys for a user."""
    sql = "UPDATE api_keys SET tier = %(tier)s WHERE user_id = %(uid)s AND is_active = TRUE;"
    with get_sync_cursor() as cur:
        cur.execute(sql, {"tier": tier, "uid": user_id})


def create_api_key(
    user_id: int,
    key_hash: str,
    key_prefix: str,
    tier: str = "free",
) -> dict[str, Any]:
    """Store a hashed API key. Returns the created row (no plaintext)."""
    sql = """
        INSERT INTO api_keys (user_id, key_hash, key_prefix, tier)
        VALUES (%(user_id)s, %(key_hash)s, %(key_prefix)s, %(tier)s)
        RETURNING id, user_id, key_prefix, tier, is_active, created_at;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {
            "user_id": user_id,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "tier": tier,
        })
        return cur.fetchone()  # type: ignore[return-value]


def get_api_key_by_hash(key_hash: str) -> dict[str, Any] | None:
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
        WHERE k.key_hash = %(hash)s
          AND k.is_active = TRUE;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"hash": key_hash})
        return cur.fetchone()  # type: ignore[return-value]


def revoke_api_keys_for_user(user_id: int) -> None:
    """Deactivate all active keys for a user (used during rotation)."""
    sql = """
        UPDATE api_keys
        SET is_active = FALSE, revoked_at = now()
        WHERE user_id = %(user_id)s AND is_active = TRUE;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"user_id": user_id})


def touch_api_key(key_hash: str) -> None:
    """Update last_used_at for a key (fire-and-forget, best effort)."""
    sql = "UPDATE api_keys SET last_used_at = now() WHERE key_hash = %(hash)s;"
    with get_sync_cursor() as cur:
        cur.execute(sql, {"hash": key_hash})


_IP_LOCK_MINUTES = 15


def check_and_set_ip_lock(key_hash: str, client_ip: str) -> bool:
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
            WHERE key_hash = %(hash)s
        ),
        updated AS (
            UPDATE api_keys
            SET last_ip      = CASE
                                  WHEN (SELECT last_ip FROM current) IS NULL
                                    OR (SELECT last_ip FROM current) = %(ip)s
                                    OR (SELECT ip_locked_at FROM current) < NOW() - INTERVAL '%(mins)s minutes'
                                  THEN %(ip)s
                                  ELSE (SELECT last_ip FROM current)
                                END,
                ip_locked_at = CASE
                                  WHEN (SELECT last_ip FROM current) IS NULL
                                    OR (SELECT last_ip FROM current) = %(ip)s
                                    OR (SELECT ip_locked_at FROM current) < NOW() - INTERVAL '%(mins)s minutes'
                                  THEN NOW()
                                  ELSE (SELECT ip_locked_at FROM current)
                                END
            WHERE key_hash = %(hash)s
            RETURNING last_ip
        )
        SELECT (SELECT last_ip FROM current) AS old_ip,
               (SELECT last_ip FROM updated) AS new_ip;
    """
    # psycopg2 doesn't support %(var)s inside INTERVAL literals; use format
    sql = sql.replace("%(mins)s", str(_IP_LOCK_MINUTES))
    with get_sync_cursor() as cur:
        cur.execute(sql, {"hash": key_hash, "ip": client_ip})
        row = cur.fetchone()
    if not row:
        return True  # key not found — let auth handle it
    old_ip = row["old_ip"]
    new_ip = row["new_ip"]
    # Blocked if a different IP held the lock and we didn't update it
    return new_ip == client_ip or old_ip is None


def increment_daily_usage(key_hash: str) -> int:
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
        WHERE key_hash = %(hash)s
        RETURNING daily_requests;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"hash": key_hash})
        row = cur.fetchone()
        return int(row["daily_requests"]) if row else 1


def get_daily_usage(key_hash: str) -> int:
    """Return today's request count for a key (0 if not found or date differs)."""
    sql = """
        SELECT daily_requests
        FROM api_keys
        WHERE key_hash = %(hash)s
          AND usage_date = CURRENT_DATE
          AND is_active = TRUE;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"hash": key_hash})
        row = cur.fetchone()
        return int(row["daily_requests"]) if row else 0


def get_alert_recipients() -> list[dict]:
    """Return all active users on starter/pro tier for regime change alerts (owner excluded)."""
    with get_sync_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (u.id)
                u.id, u.email, k.tier, u.webhook_url, u.alerts_enabled
            FROM users u
            JOIN api_keys k ON k.user_id = u.id
            WHERE k.is_active = TRUE
              AND k.tier IN ('starter', 'pro')
              AND u.alerts_enabled = TRUE
            ORDER BY u.id, k.created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def update_webhook_url(user_id: int, webhook_url: str | None) -> None:
    """Set or clear a user's webhook URL."""
    with get_sync_cursor() as cur:
        cur.execute(
            "UPDATE users SET webhook_url = %s WHERE id = %s",
            (webhook_url, user_id)
        )


def fetch_subscriber_emails() -> list[str]:
    """Return emails of all Starter/Pro users with an active API key (paid digest only)."""
    sql = """
        SELECT DISTINCT u.email
        FROM users u
        JOIN api_keys k ON k.user_id = u.id
        WHERE k.is_active = TRUE AND k.tier IN ('starter', 'pro')
        ORDER BY u.email;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        return [r["email"] for r in rows]


# ── Email verification ─────────────────────────────────────────────────

def create_email_verification(email: str, code: str) -> None:
    """Delete any existing pending code for this email and insert a fresh one."""
    with get_sync_cursor() as cur:
        cur.execute("DELETE FROM email_verifications WHERE email = %(email)s;", {"email": email})
        cur.execute(
            """
            INSERT INTO email_verifications (email, code, expires_at)
            VALUES (%(email)s, %(code)s, NOW() + INTERVAL '15 minutes');
            """,
            {"email": email, "code": code},
        )


_OTP_MAX_ATTEMPTS = 5


def verify_email_code(email: str, code: str) -> bool:
    """
    Mark code used and return True if valid + unexpired, False otherwise.

    Wrong guesses increment an attempt counter; after 5 failures the row is
    exhausted (marked used) so further guesses are impossible.
    """
    with get_sync_cursor() as cur:
        # Attempt exact match — also guards on attempt ceiling
        cur.execute(
            """
            UPDATE email_verifications
            SET used = TRUE
            WHERE email = %(email)s
              AND code  = %(code)s
              AND expires_at > NOW()
              AND used = FALSE
              AND attempts < %(max_attempts)s
            RETURNING id;
            """,
            {"email": email, "code": code, "max_attempts": _OTP_MAX_ATTEMPTS},
        )
        if cur.fetchone():
            return True

        # Wrong code — increment attempts; exhaust row if ceiling reached
        cur.execute(
            """
            UPDATE email_verifications
            SET attempts = attempts + 1,
                used = (attempts + 1 >= %(max_attempts)s)
            WHERE email = %(email)s
              AND expires_at > NOW()
              AND used = FALSE;
            """,
            {"email": email, "max_attempts": _OTP_MAX_ATTEMPTS},
        )
        return False


def fetch_latest_features(limit: int = 252) -> list[dict[str, Any]]:
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
        LIMIT %(limit)s;
    """
    with get_sync_cursor() as cur:
        cur.execute(sql, {"limit": limit})
        return cur.fetchall()  # type: ignore[return-value]
