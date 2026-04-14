"""
Migration integrity tests — TEST-05.

Verifies that all migration files exist, are non-empty, and define the
expected tables and critical columns. No live database required — tests
read the SQL files from disk.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).parent.parent / "database" / "migrations"

EXPECTED_MIGRATIONS = [
    "001_user_management.sql",
    "002_paddle_billing.sql",
    "003_auth_and_usage.sql",
    "004_ip_lock.sql",
    "005_otp_attempts.sql",
    "006_lemonsqueezy_billing.sql",
    "007_webhook_idempotency.sql",
    "008_schema_hardening.sql",
    "009_auth_rate_limits.sql",
    "010_paddle_subscription_status.sql",
    "011_gdpr_deletion.sql",
    "012_stripe_billing.sql",
]

# Table → migration file that must CREATE it
EXPECTED_TABLES: dict[str, str] = {
    "users":                "001_user_management.sql",
    "api_keys":             "001_user_management.sql",
    "webhook_idempotency":  "007_webhook_idempotency.sql",
    "auth_rate_limits":     "009_auth_rate_limits.sql",
}

# (table, column) → migration file where the column must appear
EXPECTED_COLUMNS: list[tuple[str, str, str]] = [
    ("users",      "email",          "001_user_management.sql"),
    ("api_keys",   "key_hash",       "001_user_management.sql"),
    ("api_keys",   "tier",           "001_user_management.sql"),
    ("users",      "deleted_at",     "011_gdpr_deletion.sql"),
    ("auth_rate_limits", "attempt_count", "009_auth_rate_limits.sql"),
    ("auth_rate_limits", "locked_until",  "009_auth_rate_limits.sql"),
    ("webhook_idempotency", "event_id",   "007_webhook_idempotency.sql"),
    ("webhook_idempotency", "provider",   "007_webhook_idempotency.sql"),
]


# ── Helpers ────────────────────────────────────────────────────────────────


def _sql(filename: str) -> str:
    return (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")


def _normalise(text: str) -> str:
    """Collapse whitespace and lower-case for loose matching."""
    return re.sub(r"\s+", " ", text).lower()


# ── File existence ─────────────────────────────────────────────────────────


def test_migrations_directory_exists():
    """database/migrations/ directory is present."""
    assert MIGRATIONS_DIR.is_dir(), f"Migrations dir not found: {MIGRATIONS_DIR}"


@pytest.mark.parametrize("filename", EXPECTED_MIGRATIONS)
def test_migration_file_exists(filename: str):
    """Each expected migration file exists and is non-empty."""
    path = MIGRATIONS_DIR / filename
    assert path.exists(), f"Missing migration: {filename}"
    assert path.stat().st_size > 0, f"Empty migration: {filename}"


def test_all_migrations_sequential():
    """Migration files are sequentially numbered 001 through 011 with no gaps."""
    found = sorted(MIGRATIONS_DIR.glob("*.sql"))
    prefixes = [f.name[:3] for f in found]
    expected = [f"{i:03d}" for i in range(1, len(EXPECTED_MIGRATIONS) + 1)]
    assert prefixes == expected, (
        f"Migration numbering gap or mismatch. Found prefixes: {prefixes}"
    )


# ── SQL content — table definitions ───────────────────────────────────────


@pytest.mark.parametrize("table,migration", EXPECTED_TABLES.items())
def test_table_created_in_migration(table: str, migration: str):
    """CREATE TABLE for each expected table appears in the correct migration."""
    sql = _normalise(_sql(migration))
    # Match CREATE TABLE [IF NOT EXISTS] <table>
    pattern = rf"create table(?: if not exists)?\s+{re.escape(table)}"
    assert re.search(pattern, sql), (
        f"Expected 'CREATE TABLE {table}' in {migration}"
    )


@pytest.mark.parametrize("table,column,migration", EXPECTED_COLUMNS)
def test_column_defined_in_migration(table: str, column: str, migration: str):
    """Each expected column name appears in the appropriate migration file."""
    sql = _normalise(_sql(migration))
    assert column.lower() in sql, (
        f"Expected column '{column}' for table '{table}' in {migration}"
    )


# ── Schema integrity spot-checks ───────────────────────────────────────────


def test_users_table_has_primary_key():
    """users table defines a PRIMARY KEY (or BIGSERIAL which implies one)."""
    sql = _normalise(_sql("001_user_management.sql"))
    assert "primary key" in sql or "bigserial" in sql


def test_api_keys_references_users():
    """api_keys table has a foreign key reference to users."""
    sql = _normalise(_sql("001_user_management.sql"))
    assert "references users" in sql


def test_gdpr_migration_adds_deleted_at():
    """Migration 011 adds deleted_at column to users."""
    sql = _normalise(_sql("011_gdpr_deletion.sql"))
    assert "deleted_at" in sql
    # Should be an ALTER TABLE or CREATE TABLE with the column
    assert "alter table" in sql or "create table" in sql


def test_auth_rate_limits_has_unique_constraint():
    """auth_rate_limits table has a UNIQUE constraint on (identifier, endpoint)."""
    sql = _normalise(_sql("009_auth_rate_limits.sql"))
    assert "unique" in sql


def test_webhook_idempotency_has_conflict_guard():
    """webhook_idempotency event_id is UNIQUE (enables ON CONFLICT DO NOTHING)."""
    sql = _normalise(_sql("007_webhook_idempotency.sql"))
    assert "unique" in sql or "primary key" in sql
