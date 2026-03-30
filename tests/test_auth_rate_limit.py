"""
Stub tests for auth endpoint rate limiting — SEC-30, SEC-31, SEC-32, SEC-33.

All tests are marked xfail(strict=True) until plan 07-01 provides real
implementations. strict=True means pytest will FAIL if any stub unexpectedly
passes without being filled in.

IMPORTANT: Do NOT import from api.main, api.app, or any module that triggers
the FastAPI lifespan at collection time — the DB pool is not available outside
a running container.
"""
from __future__ import annotations

import pytest


# ── SEC-30: /auth/register brute-force protection ─────────────────────


@pytest.mark.xfail(strict=True, reason="not implemented — Phase 7 plan 01")
def test_register_blocks_on_6th_attempt():
    """6th request from the same IP within the window returns 429."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=True, reason="not implemented — Phase 7 plan 01")
def test_register_window_reset():
    """Attempt counter resets after window_minutes elapses."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=True, reason="not implemented — Phase 7 plan 01")
def test_register_retry_after_header():
    """429 response from /auth/register includes a Retry-After header."""
    pytest.fail("not implemented")


# ── SEC-31: /auth/recover brute-force protection ──────────────────────


@pytest.mark.xfail(strict=True, reason="not implemented — Phase 7 plan 01")
def test_recover_blocks_on_6th_attempt():
    """6th recover attempt for the same email returns 429."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=True, reason="not implemented — Phase 7 plan 01")
def test_recover_backoff_at_attempt_3():
    """locked_until is set after the 3rd recover attempt (progressive backoff)."""
    pytest.fail("not implemented")


# ── SEC-32: /auth/verify-otp brute-force protection ───────────────────


@pytest.mark.xfail(strict=True, reason="not implemented — Phase 7 plan 01")
def test_verify_otp_blocks_after_5():
    """verify_otp endpoint returns 429 after 5 attempts within the window."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=True, reason="not implemented — Phase 7 plan 01")
def test_otp_row_exhausted_after_5_wrong():
    """
    verify_email_code() exhausts the OTP row on the 5th wrong guess.
    The caller now surfaces this as 429 (rate-limited) rather than 400.
    """
    pytest.fail("not implemented")


# ── SEC-33: State lives in DB, not memory ─────────────────────────────


@pytest.mark.xfail(strict=True, reason="not implemented — Phase 7 plan 01")
def test_state_is_db_not_memory():
    """check_and_record_attempt() issues a DB call; no in-memory dict is mutated."""
    pytest.fail("not implemented")
