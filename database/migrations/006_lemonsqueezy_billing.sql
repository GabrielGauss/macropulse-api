-- Migration 006: Add Lemon Squeezy billing columns
-- Replaces Paddle with Lemon Squeezy as the payment processor.
-- Paddle columns are retained for historical records.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS ls_customer_id     TEXT,
    ADD COLUMN IF NOT EXISTS ls_subscription_id TEXT,
    ADD COLUMN IF NOT EXISTS ls_variant_id       TEXT,
    ADD COLUMN IF NOT EXISTS ls_status           TEXT;

CREATE INDEX IF NOT EXISTS idx_users_ls_customer ON users (ls_customer_id) WHERE ls_customer_id IS NOT NULL;
