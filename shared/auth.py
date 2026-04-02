"""
Authentication and rate-limiting utilities.

Provides:

* **FixedWindowRateLimiter** -- in-process, thread-safe fixed-window rate
  limiter suitable for single-instance deployments.
* **require_auth** -- FastAPI dependency that validates a ``Bearer`` token and
  applies a per-token rate limit.
"""

from __future__ import annotations

import hmac
import logging
import threading
import time
from typing import TYPE_CHECKING

from fastapi import Request

from shared.errors import ProblemError

if TYPE_CHECKING:
    from shared.config import Settings

logger = logging.getLogger(__name__)


class FixedWindowRateLimiter:
    """Simple fixed-window rate limiter.

    Each *key* (typically a Bearer token) is allowed ``max_per_minute``
    requests per calendar minute.  The implementation is fully in-process and
    protected by a :class:`threading.Lock` so it is safe for use with
    threaded ASGI servers.
    """

    def __init__(self, max_per_minute: int = 120) -> None:
        self.max_per_minute = max_per_minute
        self._lock = threading.Lock()
        # key -> (window_start_minute, count)
        self._windows: dict[str, tuple[int, int]] = {}

    def check(self, key: str) -> bool:
        """Return ``True`` if the request is allowed, ``False`` if rate-limited."""
        now_minute = int(time.time()) // 60

        with self._lock:
            window_start, count = self._windows.get(key, (now_minute, 0))

            if window_start != now_minute:
                # New window -- reset counter
                self._windows[key] = (now_minute, 1)
                return True

            if count >= self.max_per_minute:
                return False

            self._windows[key] = (now_minute, count + 1)
            return True


# Module-level singleton so the limiter survives across requests.
_rate_limiter = FixedWindowRateLimiter(max_per_minute=120)


async def require_auth(request: Request) -> str:
    """FastAPI dependency: validates a Bearer token and applies rate limiting.

    The ``Settings`` instance is expected on ``request.app.state.settings``.

    Returns the validated token string on success.

    Raises
    ------
    ProblemError 401
        Missing or invalid ``Authorization`` header.
    ProblemError 429
        Rate limit exceeded for this token.
    """
    settings: Settings = request.app.state.settings

    auth_header: str | None = request.headers.get("Authorization")
    if not auth_header:
        raise ProblemError(
            status=401,
            title="Unauthorized",
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split(" ", maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ProblemError(
            status=401,
            title="Unauthorized",
            detail="Authorization header must use the Bearer scheme.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()

    # Constant-time comparison against every allowed token.
    valid = False
    for allowed in settings.api_bearer_tokens:
        if hmac.compare_digest(token.encode(), allowed.encode()):
            valid = True
            break

    if not valid:
        logger.warning("Rejected invalid Bearer token from %s", request.client.host if request.client else "unknown")
        raise ProblemError(
            status=401,
            title="Unauthorized",
            detail="Invalid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Rate limit per token
    if not _rate_limiter.check(token):
        logger.warning("Rate limit exceeded for token ending ...%s", token[-4:])
        raise ProblemError(
            status=429,
            title="Too Many Requests",
            detail="Rate limit exceeded. Try again in a few seconds.",
            headers={"Retry-After": "60"},
        )

    return token
