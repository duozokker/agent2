"""Tests for shared.auth module."""
from shared.auth import FixedWindowRateLimiter

def test_rate_limiter_allows_under_limit():
    limiter = FixedWindowRateLimiter(max_per_minute=5)
    for _ in range(5):
        assert limiter.check("test-key") is True

def test_rate_limiter_blocks_over_limit():
    limiter = FixedWindowRateLimiter(max_per_minute=3)
    for _ in range(3):
        limiter.check("test-key")
    assert limiter.check("test-key") is False

def test_rate_limiter_separate_keys():
    limiter = FixedWindowRateLimiter(max_per_minute=1)
    assert limiter.check("key-a") is True
    assert limiter.check("key-b") is True
    assert limiter.check("key-a") is False
