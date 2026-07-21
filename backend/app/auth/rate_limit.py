from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field

_WINDOWS_IN_SECONDS = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
}


def parse_rate_limit(value: str) -> tuple[int, int]:
    """Converte "5/minute" em (5, 60)."""
    limit_part, _, window_part = value.partition("/")
    limit = int(limit_part)
    window_seconds = _WINDOWS_IN_SECONDS[window_part.strip().lower()]
    if limit < 1:
        raise ValueError(f"Rate limit inválido: {value!r}")
    return limit, window_seconds


@dataclass
class LoginRateLimiter:
    """Janela deslizante de tentativas de login por originador."""

    limit: int
    window_seconds: int
    clock: Callable[[], float] = time.monotonic
    _attempts: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    @classmethod
    def from_environment(cls) -> LoginRateLimiter:
        limit, window_seconds = parse_rate_limit(
            os.getenv("AUTH_LOGIN_RATE_LIMIT", "5/minute")
        )
        return cls(limit=limit, window_seconds=window_seconds)

    def try_acquire(self, originator: str) -> bool:
        now = self.clock()
        attempts = self._attempts[originator]
        cutoff = now - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        if len(attempts) >= self.limit:
            return False
        attempts.append(now)
        return True


_default_rate_limiter: LoginRateLimiter | None = None


def get_login_rate_limiter() -> LoginRateLimiter:
    global _default_rate_limiter
    if _default_rate_limiter is None:
        _default_rate_limiter = LoginRateLimiter.from_environment()
    return _default_rate_limiter
