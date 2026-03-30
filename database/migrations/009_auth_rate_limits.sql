-- database/migrations/009_auth_rate_limits.sql
-- DB-persisted auth endpoint rate limiting. SEC-30, SEC-31, SEC-32, SEC-33.
-- Safe to re-run (all DDL uses IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS auth_rate_limits (
    id             BIGSERIAL    PRIMARY KEY,
    identifier     TEXT         NOT NULL,
    endpoint       TEXT         NOT NULL
                                CHECK (endpoint IN ('register', 'verify_otp', 'recover', 'recover_verify')),
    attempt_count  INT          NOT NULL DEFAULT 0,
    window_start   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    locked_until   TIMESTAMPTZ,
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (identifier, endpoint)
);

CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_identifier_endpoint
    ON auth_rate_limits (identifier, endpoint);
