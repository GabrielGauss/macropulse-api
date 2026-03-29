"""
Startup security guard tests — Phase 6 (SEC-42).
"""
import os
import pytest
from unittest.mock import patch


def test_cors_wildcard_blocked_in_prod():
    """App raises RuntimeError at startup if ENV=production and CORS_ORIGINS contains '*'."""
    from config.settings import get_settings
    from api.main import _validate_cors_origins

    # Production + wildcard → must raise
    get_settings.cache_clear()
    with patch.dict(os.environ, {"ENV": "production", "CORS_ORIGINS": '["*"]'}, clear=False):
        get_settings.cache_clear()
        with pytest.raises(RuntimeError, match="CORS wildcard"):
            _validate_cors_origins()

    # Development + wildcard → must NOT raise
    get_settings.cache_clear()
    with patch.dict(os.environ, {"ENV": "development", "CORS_ORIGINS": '["*"]'}, clear=False):
        get_settings.cache_clear()
        _validate_cors_origins()  # should not raise

    get_settings.cache_clear()
