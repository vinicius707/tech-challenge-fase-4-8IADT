from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.auth.rate_limit import LoginRateLimiter, get_login_rate_limiter
from app.main import app


@pytest.fixture(autouse=True)
def isolated_login_rate_limiter() -> Iterator[None]:
    """Evita que o limiter global vaze estado entre testes."""
    app.dependency_overrides[get_login_rate_limiter] = lambda: LoginRateLimiter(
        limit=1000, window_seconds=60
    )
    yield
    app.dependency_overrides.pop(get_login_rate_limiter, None)
