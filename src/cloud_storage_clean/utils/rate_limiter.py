"""Token bucket rate limiter for API calls."""

import time
from threading import Lock
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter.

    Limits the rate of operations using a token bucket algorithm.
    Tokens are added at a constant rate, and operations consume tokens.
    """

    def __init__(self, rate: float, capacity: Optional[int] = None) -> None:
        """Initialize rate limiter.

        Args:
            rate: Maximum operations per second.
            capacity: Maximum burst capacity. Defaults to rate.
        """
        self.rate = rate
        self.capacity = capacity if capacity is not None else int(rate)
        self.tokens = float(self.capacity)
        self.last_update = time.time()
        self.lock = Lock()

    def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, blocking if necessary.

        Args:
            tokens: Number of tokens to acquire.
        """
        with self.lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(
                    self.capacity, self.tokens + elapsed * self.rate
                )
                self.last_update = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # Calculate wait time
                wait_time = (tokens - self.tokens) / self.rate
                time.sleep(wait_time)

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            True if tokens were acquired, False otherwise.
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
