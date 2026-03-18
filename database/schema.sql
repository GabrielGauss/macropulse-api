-- ============================================================
-- MacroPulse – TimescaleDB Schema
-- ============================================================
-- Run this file against a PostgreSQL database with the
-- TimescaleDB extension installed:
--
--   psql -U macropulse -d macropulse -f database/schema.sql
-- ============================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ── Pipeline metadata ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              BIGSERIAL PRIMARY KEY,
    run_ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    status          TEXT NOT NULL,          -- success | partial | failed
    data_lag        BOOLEAN NOT NULL DEFAULT FALSE,
    duration_sec    DOUBLE PRECISION,
    error_message   TEXT,
    model_version   TEXT
);

-- ── Model version registry ──────────────────────────────────

CREATE TABLE IF NOT EXISTS model_versions (
    version         TEXT PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    pca_variance    DOUBLE PRECISION,
    hmm_n_regimes   INTEGER,
    notes           TEXT
);

-- ── Macro features (stationary series) ──────────────────────

CREATE TABLE IF NOT EXISTS macro_features (
    time            TIMESTAMPTZ NOT NULL,
    net_liquidity   DOUBLE PRECISION,
    d_liquidity     DOUBLE PRECISION,
    d_sp500         DOUBLE PRECISION,
    d_vix           DOUBLE PRECISION,
    d_dxy           DOUBLE PRECISION,
    d_hy_spread     DOUBLE PRECISION,
    d_yield_curve   DOUBLE PRECISION,
    d_10y           DOUBLE PRECISION,
    d_2y            DOUBLE PRECISION,
    d_gold          DOUBLE PRECISION DEFAULT 0,
    d_oil           DOUBLE PRECISION DEFAULT 0,
    d_btc           DOUBLE PRECISION DEFAULT 0,
    d_eth           DOUBLE PRECISION DEFAULT 0,
    PRIMARY KEY (time)
);

SELECT create_hypertable('macro_features', 'time', if_not_exists => TRUE);

-- ── PCA latent factors ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS macro_factors (
    time            TIMESTAMPTZ NOT NULL,
    factor_1        DOUBLE PRECISION,
    factor_2        DOUBLE PRECISION,
    factor_3        DOUBLE PRECISION,
    factor_4        DOUBLE PRECISION,
    model_version   TEXT,
    PRIMARY KEY (time)
);

SELECT create_hypertable('macro_factors', 'time', if_not_exists => TRUE);

-- ── Regime probabilities ────────────────────────────────────

CREATE TABLE IF NOT EXISTS macro_regimes (
    time              TIMESTAMPTZ NOT NULL,
    regime            TEXT,
    prob_expansion    DOUBLE PRECISION,
    prob_tightening   DOUBLE PRECISION,
    prob_risk_off     DOUBLE PRECISION,
    prob_recovery     DOUBLE PRECISION,
    risk_score        DOUBLE PRECISION,
    volatility_state  TEXT,
    model_version     TEXT,
    PRIMARY KEY (time)
);

SELECT create_hypertable('macro_regimes', 'time', if_not_exists => TRUE);

-- ── Drift monitoring ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS model_drift_metrics (
    time                    TIMESTAMPTZ NOT NULL,
    pca_explained_variance  DOUBLE PRECISION,
    regime_persistence      DOUBLE PRECISION,
    feature_mean_shift      DOUBLE PRECISION,
    feature_std_shift       DOUBLE PRECISION,
    model_version           TEXT,
    PRIMARY KEY (time)
);

SELECT create_hypertable('model_drift_metrics', 'time', if_not_exists => TRUE);

-- ── User management ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id                   BIGSERIAL PRIMARY KEY,
    email                TEXT NOT NULL UNIQUE,
    name                 TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    paddle_customer_id   TEXT,
    paddle_subscription_id TEXT,
    webhook_url          TEXT DEFAULT NULL,
    alerts_enabled       BOOLEAN DEFAULT TRUE
);

-- Migration guard: add alert columns if upgrading from earlier schema
ALTER TABLE users ADD COLUMN IF NOT EXISTS webhook_url    TEXT DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS alerts_enabled BOOLEAN DEFAULT TRUE;

-- Tiers: free (50 req/day) | starter (500 req/day) | pro (unlimited)
CREATE TABLE IF NOT EXISTS api_keys (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash        TEXT NOT NULL UNIQUE,       -- SHA-256 of plaintext key
    key_prefix      TEXT NOT NULL,              -- first 12 chars for display
    tier            TEXT NOT NULL DEFAULT 'free',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at    TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    usage_date      DATE,                       -- date of current daily counter
    daily_requests  INTEGER NOT NULL DEFAULT 0  -- requests made on usage_date
);

-- Migration guard: add columns if upgrading from earlier schema
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS usage_date     DATE;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS daily_requests INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_api_keys_hash   ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user   ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active) WHERE is_active = TRUE;

-- ── TimescaleDB retention + compression ──────────────────────────
-- Keeps 3 years of data; compresses chunks older than 7 days.
-- These calls are idempotent — safe to re-run on schema reload.

ALTER TABLE macro_features     SET (timescaledb.compress, timescaledb.compress_orderby = 'time DESC');
ALTER TABLE macro_factors       SET (timescaledb.compress, timescaledb.compress_orderby = 'time DESC');
ALTER TABLE macro_regimes       SET (timescaledb.compress, timescaledb.compress_orderby = 'time DESC');
ALTER TABLE model_drift_metrics SET (timescaledb.compress, timescaledb.compress_orderby = 'time DESC');

SELECT add_compression_policy('macro_features',     INTERVAL '7 days',  if_not_exists => TRUE);
SELECT add_compression_policy('macro_factors',       INTERVAL '7 days',  if_not_exists => TRUE);
SELECT add_compression_policy('macro_regimes',       INTERVAL '7 days',  if_not_exists => TRUE);
SELECT add_compression_policy('model_drift_metrics', INTERVAL '7 days',  if_not_exists => TRUE);

SELECT add_retention_policy('macro_features',     INTERVAL '3 years', if_not_exists => TRUE);
SELECT add_retention_policy('macro_factors',       INTERVAL '3 years', if_not_exists => TRUE);
SELECT add_retention_policy('macro_regimes',       INTERVAL '3 years', if_not_exists => TRUE);
SELECT add_retention_policy('model_drift_metrics', INTERVAL '3 years', if_not_exists => TRUE);
