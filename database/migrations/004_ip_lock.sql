-- ============================================================
-- Migration 004 — Per-key IP lock for key-sharing prevention
-- Apply after migration 003.
-- ============================================================

-- last_ip:       the IP currently holding the key
-- ip_locked_at:  when the lock was last refreshed (NULL = never used)
ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS last_ip        TEXT,
    ADD COLUMN IF NOT EXISTS ip_locked_at   TIMESTAMPTZ;
