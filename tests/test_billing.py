"""
Billing webhook hardening tests — Phase 6 (SEC-20, SEC-21, SEC-22).

Stubs created in Wave 0. Implementations filled in by 06-02-PLAN.md.
"""
import os

import pytest
from unittest.mock import patch


@pytest.mark.xfail(reason="SEC-20: LS startup guard not yet implemented", strict=True)
def test_ls_webhook_missing_secret():
    """API raises RuntimeError at startup when ENV=production and LS_WEBHOOK_SECRET is unset."""
    pytest.fail("not implemented")


def test_ls_webhook_invalid_signature():
    """LS webhook returns 401 on HMAC mismatch; rejects without calling event handler."""
    from api.routes.billing import _ls_verify_signature

    # With correct secret set but wrong signature — must return False
    with patch.dict(os.environ, {"LS_WEBHOOK_SECRET": "test-secret"}, clear=False):
        result = _ls_verify_signature(b"test body", "wrong-signature")
    assert result is False

    # With no secret set — must also return False (fail closed, not True)
    os.environ.pop("LS_WEBHOOK_SECRET", None)
    result = _ls_verify_signature(b"test body", "any-signature")
    assert result is False


@pytest.mark.xfail(reason="SEC-22: Paddle replay protection verified and tested", strict=True)
def test_paddle_replay_window():
    """Paddle webhook rejects events with timestamp outside 5-minute window."""
    pytest.fail("not implemented")
