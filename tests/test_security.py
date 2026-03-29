"""
Startup security guard tests — Phase 6 (SEC-42).

Stub created in Wave 0. Implementation filled in by 06-03-PLAN.md.
"""
import pytest


@pytest.mark.xfail(reason="SEC-42: CORS wildcard guard not yet implemented", strict=True)
def test_cors_wildcard_blocked_in_prod():
    """App raises RuntimeError at startup if ENV=production and CORS_ORIGINS contains '*'."""
    pytest.fail("not implemented")
