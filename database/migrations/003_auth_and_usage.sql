-- ============================================================
-- Migration 003 — Auth, usage tracking, and alert columns
-- Apply after migration 002.
--
--   psql -U macropulse -d macropulse -f database/migrations/003_auth_and_usage.sql
-- ============================================================

-- OTP verification codes for self-serve registration
CREATE TABLE IF NOT EXISTS email_verifications (
    id          BIGSERIAL PRIMARY KEY,
    email       TEXT NOT NULL,
    code        TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_email_verifications_email ON email_verifications(email);

-- Daily usage tracking per API key (for per-tier rate limits)
ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS usage_date     DATE,
    ADD COLUMN IF NOT EXISTS daily_requests INT NOT NULL DEFAULT 0;

-- Alert preferences per user
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS webhook_url     TEXT,
    ADD COLUMN IF NOT EXISTS alerts_enabled  BOOLEAN NOT NULL DEFAULT FALSE;
