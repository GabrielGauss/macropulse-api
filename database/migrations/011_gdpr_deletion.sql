-- Migration 011: Add deleted_at to users for GDPR erasure tracking.
-- Safe to re-run (IF NOT EXISTS).
-- Note: auth_rate_limits rows keyed on email/IP expire naturally (<1h window)
-- and are intentionally NOT wiped during deletion to avoid race conditions.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_users_deleted_at
    ON users (deleted_at) WHERE deleted_at IS NOT NULL;
