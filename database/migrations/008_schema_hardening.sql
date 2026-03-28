-- Schema hardening: constraints, indexes, audit tables

-- Regime value validation (add constraint only if it doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'macro_regimes_regime_check'
          AND conrelid = 'macro_regimes'::regclass
    ) THEN
        ALTER TABLE macro_regimes
        ADD CONSTRAINT macro_regimes_regime_check
        CHECK (regime IN ('expansion', 'tightening', 'risk_off', 'recovery'));
    END IF;
EXCEPTION WHEN undefined_table THEN
    NULL; -- table doesn't exist yet, skip
END $$;

-- Time-range query performance
CREATE INDEX IF NOT EXISTS idx_macro_regimes_time_desc
    ON macro_regimes (time DESC);

-- API key lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id
    ON api_keys (user_id);

-- Webhook delivery audit trail
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    delivery_id    BIGSERIAL   PRIMARY KEY,
    user_id        BIGINT,
    event_type     TEXT        NOT NULL,
    payload        JSONB,
    status         TEXT        NOT NULL DEFAULT 'pending'
                               CHECK (status IN ('pending', 'delivered', 'failed')),
    attempts       INT         NOT NULL DEFAULT 0,
    last_attempted TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- API key audit log
CREATE TABLE IF NOT EXISTS api_key_audit_log (
    log_id     BIGSERIAL   PRIMARY KEY,
    user_id    BIGINT,
    action     TEXT        NOT NULL CHECK (action IN ('created', 'rotated', 'revoked', 'used')),
    ip_addr    TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
