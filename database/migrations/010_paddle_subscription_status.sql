-- Migration 010: add paddle_subscription_status column and customer index
-- Phase 10 — BILL-02 requires persisting subscription status per user

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS paddle_subscription_status TEXT;

-- Index speeds up webhook lookups by customer_id (fired on every subscription event)
CREATE INDEX IF NOT EXISTS idx_users_paddle_customer
    ON users (paddle_customer_id) WHERE paddle_customer_id IS NOT NULL;
