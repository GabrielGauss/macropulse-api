-- Webhook idempotency table
-- Prevents duplicate processing when Paddle retries delivery on network errors.
CREATE TABLE IF NOT EXISTS webhook_idempotency (
    event_id     TEXT        PRIMARY KEY,
    provider     TEXT        NOT NULL DEFAULT 'paddle',
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
