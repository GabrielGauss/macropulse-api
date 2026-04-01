"""
Tests for GDPR right-to-erasure: anonymise_user() query function and
DELETE /v1/auth/me route handler.

Covers GDPR-01 through GDPR-04 (see PLAN.md).
No live database required — all DB calls are mocked.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from database.queries import anonymise_user


# ── Helper: build a standard mock asyncpg connection ─────────────────


def _make_mock_conn(fetchrow_return, execute_return="UPDATE 1"):
    """Return a mock asyncpg connection with transaction support."""
    mock_conn = MagicMock()
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    mock_conn.execute = AsyncMock(return_value=execute_return)

    mock_txn = MagicMock()
    mock_txn.__aenter__ = AsyncMock(return_value=None)
    mock_txn.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=mock_txn)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    return mock_conn, mock_cm


# ── Task 1: anonymise_user() unit tests ──────────────────────────────


async def test_anonymise_user_wipes_pii():
    """
    GDPR-02 / GDPR-03: anonymise_user() must call conn.execute exactly 5 times
    (users UPDATE, api_keys UPDATE, webhook_deliveries UPDATE,
    api_key_audit_log UPDATE, newsletter_subscribers DELETE) and return True.
    The first execute call must pass an anonymised email containing '@deleted.invalid'.
    The users UPDATE SQL must contain 'deleted_at'.
    """
    mock_conn, mock_cm = _make_mock_conn(
        fetchrow_return={"email": "user@example.com", "ls_status": "inactive"},
        execute_return="UPDATE 1",
    )

    with patch("database.queries.get_db_conn", return_value=mock_cm):
        result = await anonymise_user(42)

    assert result is True
    assert mock_conn.execute.call_count == 5

    # First execute: users UPDATE — second positional arg is the anon email
    first_call_args = mock_conn.execute.call_args_list[0][0]
    first_call_sql = first_call_args[0]
    first_call_email_arg = first_call_args[1]
    assert "@deleted.invalid" in first_call_email_arg
    assert "deleted_at" in first_call_sql


async def test_anonymise_user_nullifies_audit_pii():
    """
    GDPR-04: webhook_deliveries UPDATE must include 'payload = NULL' and
    api_key_audit_log UPDATE must include 'user_agent = NULL'.
    newsletter_subscribers DELETE must target 'newsletter_subscribers'.
    """
    mock_conn, mock_cm = _make_mock_conn(
        fetchrow_return={"email": "user@example.com", "ls_status": "inactive"},
        execute_return="UPDATE 1",
    )

    with patch("database.queries.get_db_conn", return_value=mock_cm):
        result = await anonymise_user(42)

    assert result is True
    assert mock_conn.execute.call_count == 5

    # execute call index 2 → webhook_deliveries UPDATE
    webhook_sql = mock_conn.execute.call_args_list[2][0][0]
    assert "payload" in webhook_sql and "NULL" in webhook_sql

    # execute call index 3 → api_key_audit_log UPDATE
    audit_sql = mock_conn.execute.call_args_list[3][0][0]
    assert "user_agent" in audit_sql and "NULL" in audit_sql

    # execute call index 4 → newsletter_subscribers DELETE
    newsletter_sql = mock_conn.execute.call_args_list[4][0][0]
    assert "newsletter_subscribers" in newsletter_sql


async def test_anonymise_user_not_found():
    """
    When fetchrow returns None (user_id not in DB), anonymise_user() must
    return False immediately without calling conn.execute at all.
    """
    mock_conn, mock_cm = _make_mock_conn(fetchrow_return=None)

    with patch("database.queries.get_db_conn", return_value=mock_cm):
        result = await anonymise_user(999)

    assert result is False
    assert mock_conn.execute.call_count == 0
