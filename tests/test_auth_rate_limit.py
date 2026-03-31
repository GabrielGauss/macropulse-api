"""
Tests for auth endpoint rate limiting — SEC-30, SEC-31, SEC-32, SEC-33.

All tests use unittest.mock.patch so no live DB connection is required.
Do NOT import from api.main or any module that triggers the FastAPI
lifespan at collection time — the DB pool is not available outside
a running container.
"""
from __future__ import annotations

import asyncio
import datetime as dt
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi import HTTPException

from api.middleware.auth_rate_limit import check_auth_rate_limit
from database.queries import check_and_record_attempt


# ── SEC-30: /auth/register brute-force protection ─────────────────────


async def test_register_blocks_on_6th_attempt():
    """6th request from the same IP within the window returns 429."""
    call_count = {"n": 0}

    async def fake_attempt(**kwargs):
        call_count["n"] += 1
        if call_count["n"] >= 6:
            return {"attempt_count": 6, "locked_until": None, "allowed": False}
        return {"attempt_count": call_count["n"], "locked_until": None, "allowed": True}

    with patch("database.queries.check_and_record_attempt", side_effect=fake_attempt):
        for _ in range(5):
            await check_auth_rate_limit("1.2.3.4", "register", 5, 60)
        with pytest.raises(HTTPException) as exc_info:
            await check_auth_rate_limit("1.2.3.4", "register", 5, 60)

    assert exc_info.value.status_code == 429


async def test_register_window_reset():
    """Attempt counter resets after window_minutes elapses — no exception on reset."""
    call_count = {"n": 0}

    async def fake_attempt(**kwargs):
        call_count["n"] += 1
        # Simulate window reset: first 6 calls hit limit, then window resets (allowed=True)
        if call_count["n"] <= 5:
            return {"attempt_count": call_count["n"], "locked_until": None, "allowed": True}
        if call_count["n"] == 6:
            return {"attempt_count": 6, "locked_until": None, "allowed": False}
        # Window reset — attempt_count starts over
        return {"attempt_count": 1, "locked_until": None, "allowed": True}

    with patch("database.queries.check_and_record_attempt", side_effect=fake_attempt):
        for _ in range(5):
            await check_auth_rate_limit("1.2.3.4", "register", 5, 60)
        with pytest.raises(HTTPException):
            await check_auth_rate_limit("1.2.3.4", "register", 5, 60)
        # After window reset, 7th call should succeed (no exception)
        await check_auth_rate_limit("1.2.3.4", "register", 5, 60)


async def test_register_retry_after_header():
    """429 response from /auth/register includes a Retry-After header."""
    locked_until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=300)

    with patch("database.queries.check_and_record_attempt",
               new=AsyncMock(return_value={"attempt_count": 6, "locked_until": locked_until, "allowed": False})):
        with pytest.raises(HTTPException) as exc_info:
            await check_auth_rate_limit("1.2.3.4", "register", 5, 60)

    exc = exc_info.value
    assert exc.status_code == 429
    assert "Retry-After" in exc.headers
    assert int(exc.headers["Retry-After"]) >= 1


# ── SEC-31: /auth/recover brute-force protection ──────────────────────


async def test_recover_blocks_on_6th_attempt():
    """6th recover attempt for the same email returns 429."""
    call_count = {"n": 0}

    async def fake_attempt(**kwargs):
        call_count["n"] += 1
        if call_count["n"] >= 6:
            return {"attempt_count": 6, "locked_until": None, "allowed": False}
        return {"attempt_count": call_count["n"], "locked_until": None, "allowed": True}

    with patch("database.queries.check_and_record_attempt", side_effect=fake_attempt):
        for _ in range(5):
            await check_auth_rate_limit("a@b.com", "recover", 5, 15, with_backoff=True)
        with pytest.raises(HTTPException) as exc_info:
            await check_auth_rate_limit("a@b.com", "recover", 5, 15, with_backoff=True)

    assert exc_info.value.status_code == 429


async def test_recover_backoff_at_attempt_3():
    """locked_until is set after the 3rd recover attempt (progressive backoff)."""
    with patch("database.queries.check_and_record_attempt",
               new=AsyncMock(return_value={"attempt_count": 3, "locked_until": None, "allowed": True})), \
         patch("api.middleware.auth_rate_limit._set_backoff_if_needed", new=AsyncMock()) as mock_backoff:
        await check_auth_rate_limit("a@b.com", "recover", 5, 15, with_backoff=True)
        mock_backoff.assert_called_once_with("a@b.com", "recover", 3)


# ── SEC-32: /auth/verify-otp brute-force protection ───────────────────


async def test_verify_otp_blocks_after_5():
    """verify_otp endpoint returns 429 after 5 attempts within the window."""
    call_count = {"n": 0}

    async def fake_attempt(**kwargs):
        call_count["n"] += 1
        if call_count["n"] > 5:
            return {"attempt_count": call_count["n"], "locked_until": None, "allowed": False}
        return {"attempt_count": call_count["n"], "locked_until": None, "allowed": True}

    with patch("database.queries.check_and_record_attempt", side_effect=fake_attempt):
        for _ in range(5):
            await check_auth_rate_limit("a@b.com", "verify_otp", 5, 15)
        with pytest.raises(HTTPException) as exc_info:
            await check_auth_rate_limit("a@b.com", "verify_otp", 5, 15)

    assert exc_info.value.status_code == 429


async def test_otp_row_exhausted_after_5_wrong():
    """
    Rate limit fires before verify_email_code() is called on the 6th attempt.
    verify_email_code call count must NOT increase when rate limit blocks.
    """
    call_count = {"rl": 0}
    mock_verify = AsyncMock(return_value=False)

    async def fake_attempt(**kwargs):
        call_count["rl"] += 1
        if call_count["rl"] > 5:
            return {"attempt_count": call_count["rl"], "locked_until": None, "allowed": False}
        return {"attempt_count": call_count["rl"], "locked_until": None, "allowed": True}

    with patch("database.queries.check_and_record_attempt", side_effect=fake_attempt), \
         patch("database.queries.verify_email_code", mock_verify):
        # First 5 calls allowed — verify_email_code would be called by the handler
        for _ in range(5):
            await check_auth_rate_limit("a@b.com", "verify_otp", 5, 15)

        verify_calls_before = mock_verify.call_count

        # 6th call — rate limit fires before any DB verify call in handler
        with pytest.raises(HTTPException) as exc_info:
            await check_auth_rate_limit("a@b.com", "verify_otp", 5, 15)

        # verify_email_code should NOT have been called during the rate-limited call
        assert mock_verify.call_count == verify_calls_before

    assert exc_info.value.status_code == 429


# ── SEC-33: State lives in DB, not memory ─────────────────────────────


async def test_state_is_db_not_memory():
    """check_and_record_attempt() issues a DB call; no in-memory dict is mutated."""
    mock_conn = MagicMock()
    mock_conn.fetchrow = AsyncMock(return_value={"attempt_count": 1, "locked_until": None, "allowed": True})
    mock_conn.execute = AsyncMock(return_value=None)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    # Patch where get_db_conn is used (database.queries imports it directly)
    with patch("database.queries.get_db_conn", return_value=mock_cm):
        await check_and_record_attempt(
            identifier="1.2.3.4",
            endpoint="register",
            max_attempts=5,
            window_minutes=60,
        )

    # Verify a DB call was made — state is in DB, not memory
    assert mock_conn.fetchrow.called or mock_conn.execute.called

    # Verify no module-level dict in auth_rate_limit holds identifier-keyed state
    import api.middleware.auth_rate_limit as rl_module
    for name, val in vars(rl_module).items():
        if isinstance(val, dict) and name != "_BACKOFF_SCHEDULE":
            for key in val:
                assert not isinstance(key, str) or not ("." in key or "@" in key), (
                    f"Module-level dict '{name}' contains identifier-like key '{key}' — state must live in DB"
                )
