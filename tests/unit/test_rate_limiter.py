"""Unit tests for rate limiter."""

import time

import pytest

from cloud_storage_clean.utils.rate_limiter import RateLimiter


def test_rate_limiter_initialization() -> None:
    """Test rate limiter initialization."""
    limiter = RateLimiter(rate=10.0, capacity=20)
    assert limiter.rate == 10.0
    assert limiter.capacity == 20
    assert limiter.tokens == 20.0


def test_rate_limiter_default_capacity() -> None:
    """Test rate limiter with default capacity."""
    limiter = RateLimiter(rate=10.0)
    assert limiter.capacity == 10


def test_rate_limiter_acquire_immediate() -> None:
    """Test immediate token acquisition."""
    limiter = RateLimiter(rate=100.0)

    start = time.time()
    limiter.acquire(1)
    elapsed = time.time() - start

    # Should be nearly instant
    assert elapsed < 0.1


def test_rate_limiter_acquire_blocks() -> None:
    """Test that acquire blocks when tokens unavailable."""
    limiter = RateLimiter(rate=10.0, capacity=2)

    # Consume all tokens
    limiter.acquire(2)

    # Next acquire should block
    start = time.time()
    limiter.acquire(1)
    elapsed = time.time() - start

    # Should wait approximately 0.1 seconds (1 token at 10/sec)
    assert 0.05 < elapsed < 0.15


def test_rate_limiter_try_acquire_success() -> None:
    """Test successful non-blocking acquisition."""
    limiter = RateLimiter(rate=10.0, capacity=5)

    result = limiter.try_acquire(1)
    assert result is True


def test_rate_limiter_try_acquire_failure() -> None:
    """Test failed non-blocking acquisition."""
    limiter = RateLimiter(rate=10.0, capacity=2)

    # Consume all tokens
    limiter.acquire(2)

    # Should fail without blocking
    result = limiter.try_acquire(1)
    assert result is False


def test_rate_limiter_token_refill() -> None:
    """Test that tokens refill over time."""
    limiter = RateLimiter(rate=10.0, capacity=5)

    # Consume all tokens
    limiter.acquire(5)

    # Wait for refill
    time.sleep(0.5)

    # Should have approximately 5 tokens (10/sec * 0.5s)
    result = limiter.try_acquire(4)
    assert result is True


def test_rate_limiter_capacity_limit() -> None:
    """Test that tokens don't exceed capacity."""
    limiter = RateLimiter(rate=10.0, capacity=3)

    # Wait for potential overflow
    time.sleep(1.0)

    # Should only have capacity worth of tokens
    assert limiter.try_acquire(3) is True
    assert limiter.try_acquire(1) is False
