"""
Billing webhook hardening tests — Phase 6 (SEC-20, SEC-21, SEC-22).

Stubs created in Wave 0. Implementations filled in by 06-02-PLAN.md.
"""
import os

import pytest
from unittest.mock import patch


def test_ls_webhook_missing_secret():
    """API raises RuntimeError at startup when ENV=production and LS_WEBHOOK_SECRET unset."""
    from config.settings import get_settings
    from api.main import _validate_webhook_secrets

    get_settings.cache_clear()
    with patch.dict(os.environ, {"ENV": "production"}, clear=False):
        # Ensure LS_WEBHOOK_SECRET is absent
        os.environ.pop("LS_WEBHOOK_SECRET", None)
        get_settings.cache_clear()
        with pytest.raises(RuntimeError, match="LS_WEBHOOK_SECRET must be set"):
            _validate_webhook_secrets()
    get_settings.cache_clear()


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


def test_paddle_replay_window():
    """Paddle verify_webhook() rejects events with timestamp outside 5-minute window."""
    import time
    from config.settings import get_settings
    from services.paddle import verify_webhook

    # Build a fake Paddle-Signature header with old timestamp
    old_ts = int(time.time()) - 400  # 400 seconds ago — outside 5-min window
    fake_sig_header = f"ts={old_ts};h1=fakehash"

    # Set a Paddle secret so verify_webhook proceeds past the "secret not set" early-return
    # and reaches the timestamp check. Timestamp check fires before HMAC verification.
    get_settings.cache_clear()
    with patch.dict(os.environ, {"PADDLE_WEBHOOK_SECRET": "test-paddle-secret"}, clear=False):
        get_settings.cache_clear()
        result = verify_webhook(b'{"event_type": "test"}', fake_sig_header)
    get_settings.cache_clear()
    assert result is False
