-- Migration 012: Add Stripe billing columns
-- Replaces Paddle/LemonSqueezy with Stripe as the payment processor.
-- Previous columns are retained for historical records.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS stripe_customer_id     TEXT,
    ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
    ADD COLUMN IF NOT EXISTS stripe_price_id         TEXT,
    ADD COLUMN IF NOT EXISTS stripe_status           TEXT;

CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON users (stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
