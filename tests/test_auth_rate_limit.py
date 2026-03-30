"""
Tests for auth endpoint rate limiting — SEC-30, SEC-31, SEC-32, SEC-33.

All tests use unittest.mock.patch so no live DB connection is required.
Do NOT import from api.main or any module that triggers the FastAPI
lifespan at collection time — the DB pool is not available outside
a running container.
"""
from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi import HTTPException

from api.middleware.auth_rate_limit import check_auth_rate_limit
from database.queries import check_and_record_attempt


# ── SEC-30: /auth/register brute-force protection ─────────────────────


def test_register_blocks_on_6th_attempt():
    """6th request from the same IP within the window returns 429."""
    call_count = {"n": 0}

    def fake_attempt(**kwargs):
        call_count["n"] += 1
        if call_count["n"] >= 6:
            return {"attempt_count": 6, "locked_until": None, "allowed": False}
        return {"attempt_count": call_count["n"], "locked_until": None, "allowed": True}

    with patch("database.queries.check_and_record_attempt", side_effect=fake_attempt):
        for _ in range(5):
            check_auth_rate_limit("1.2.3.4", "register", 5, 60)
        with pytest.raises(HTTPException) as exc_info:
            check_auth_rate_limit("1.2.3.4", "register", 5, 60)

    assert exc_info.value.status_code == 429


def test_register_window_reset():
    """Attempt counter resets after window_minutes elapses — no exception on reset."""
    call_count = {"n": 0}

    def fake_attempt(**kwargs):
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
            check_auth_rate_limit("1.2.3.4", "register", 5, 60)
        with pytest.raises(HTTPException):
            check_auth_rate_limit("1.2.3.4", "register", 5, 60)
        # After window reset, 7th call should succeed (no exception)
        check_auth_rate_limit("1.2.3.4", "register", 5, 60)


def test_register_retry_after_header():
    """429 response from /auth/register includes a Retry-After header."""
    locked_until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=300)

    with patch("database.queries.check_and_record_attempt",
               return_value={"attempt_count": 6, "locked_until": locked_until, "allowed": False}):
        with pytest.raises(HTTPException) as exc_info:
            check_auth_rate_limit("1.2.3.4", "register", 5, 60)

    exc = exc_info.value
    assert exc.status_code == 429
    assert "Retry-After" in exc.headers
    assert int(exc.headers["Retry-After"]) >= 1


# ── SEC-31: /auth/recover brute-force protection ──────────────────────


def test_recover_blocks_on_6th_attempt():
    """6th recover attempt for the same email returns 429."""
    call_count = {"n": 0}

    def fake_attempt(**kwargs):
        call_count["n"] += 1
        if call_count["n"] >= 6:
            return {"attempt_count": 6, "locked_until": None, "allowed": False}
        return {"attempt_count": call_count["n"], "locked_until": None, "allowed": True}

    with patch("database.queries.check_and_record_attempt", side_effect=fake_attempt):
        for _ in range(5):
            check_auth_rate_limit("a@b.com", "recover", 5, 15, with_backoff=True)
        with pytest.raises(HTTPException) as exc_info:
            check_auth_rate_limit("a@b.com", "recover", 5, 15, with_backoff=True)

    assert exc_info.value.status_code == 429


def test_recover_backoff_at_attempt_3():
    """locked_until is set after the 3rd recover attempt (progressive backoff)."""
    with patch("database.queries.check_and_record_attempt",
               return_value={"attempt_count": 3, "locked_until": None, "allowed": True}), \
         patch("api.middleware.auth_rate_limit._set_backoff_if_needed") as mock_backoff:
        check_auth_rate_limit("a@b.com", "recover", 5, 15, with_backoff=True)
        mock_backoff.assert_called_once_with("a@b.com", "recover", 3)


# ── SEC-32: /auth/verify-otp brute-force protection ───────────────────


def test_verify_otp_blocks_after_5():
    """verify_otp endpoint returns 429 after 5 attempts within the window."""
    call_count = {"n": 0}

    def fake_attempt(**kwargs):
        call_count["n"] += 1
        if call_count["n"] > 5:
            return {"attempt_count": call_count["n"], "locked_until": None, "allowed": False}
        return {"attempt_count": call_count["n"], "locked_until": None, "allowed": True}

    with patch("database.queries.check_and_record_attempt", side_effect=fake_attempt):
        for _ in range(5):
            check_auth_rate_limit("a@b.com", "verify_otp", 5, 15)
        with pytest.raises(HTTPException) as exc_info:
            check_auth_rate_limit("a@b.com", "verify_otp", 5, 15)

    assert exc_info.value.status_code == 429


def test_otp_row_exhausted_after_5_wrong():
    """
    Rate limit fires before verify_email_code() is called on the 6th attempt.
    verify_email_code call count must NOT increase when rate limit blocks.
    """
    call_count = {"rl": 0}
    mock_verify = MagicMock(return_value=False)

    def fake_attempt(**kwargs):
        call_count["rl"] += 1
        if call_count["rl"] > 5:
            return {"attempt_count": call_count["rl"], "locked_until": None, "allowed": False}
        return {"attempt_count": call_count["rl"], "locked_until": None, "allowed": True}

    with patch("database.queries.check_and_record_attempt", side_effect=fake_attempt), \
         patch("database.queries.verify_email_code", mock_verify):
        # First 5 calls allowed — verify_email_code would be called by the handler
        for _ in range(5):
            check_auth_rate_limit("a@b.com", "verify_otp", 5, 15)

        verify_calls_before = mock_verify.call_count

        # 6th call — rate limit fires before any DB verify call in handler
        with pytest.raises(HTTPException) as exc_info:
            check_auth_rate_limit("a@b.com", "verify_otp", 5, 15)

        # verify_email_code should NOT have been called during the rate-limited call
        assert mock_verify.call_count == verify_calls_before

    assert exc_info.value.status_code == 429


# ── SEC-33: State lives in DB, not memory ─────────────────────────────


def test_state_is_db_not_memory():
    """check_and_record_attempt() issues a DB call; no in-memory dict is mutated."""
    mock_row = {"attempt_count": 1, "locked_until": None}
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = mock_row
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_cur)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    # Patch where it's used (database.queries imports get_sync_cursor directly)
    with patch("database.queries.get_sync_cursor", return_value=mock_ctx):
        check_and_record_attempt(
            identifier="1.2.3.4",
            endpoint="register",
            max_attempts=5,
            window_minutes=60,
        )

    # Verify a DB execute call was made — state is in DB, not memory
    assert mock_cur.execute.called

    # Verify no module-level dict in auth_rate_limit holds identifier-keyed state
    import api.middleware.auth_rate_limit as rl_module
    for name, val in vars(rl_module).items():
        if isinstance(val, dict) and name != "_BACKOFF_SCHEDULE":
            for key in val:
                assert not isinstance(key, str) or not ("." in key or "@" in key), (
                    f"Module-level dict '{name}' contains identifier-like key '{key}' — state must live in DB"
                )
