"""Circuit breaker in-memory para o caminho Azure (ADR 0015)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Literal

CircuitState = Literal["closed", "open"]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class AzureCircuitBreaker:
    """Abre após N falhas consecutivas e força provedor local por T segundos.

    Stub pronto para o Épico 6 — sem chamada de rede. `force_open` (env) permite
    demonstrar o Cenário 5 da spec sem depender de falhas reais.
    """

    failure_threshold: int = 3
    open_seconds: float = 300.0
    force_open: bool = False
    failure_count: int = 0
    opened_at: float | None = field(default=None, repr=False)

    @classmethod
    def from_environment(cls) -> AzureCircuitBreaker:
        return cls(
            failure_threshold=int(os.getenv("LIMEN_AZURE_CB_FAILURE_THRESHOLD", "3")),
            open_seconds=float(os.getenv("LIMEN_AZURE_CB_OPEN_SECONDS", "300")),
            force_open=_env_bool("LIMEN_AZURE_CB_FORCE_OPEN", False),
        )

    @property
    def state(self) -> CircuitState:
        if self.force_open:
            return "open"
        if self.opened_at is None:
            return "closed"
        if (time.monotonic() - self.opened_at) >= self.open_seconds:
            # Janela expirou — fecha e zera contador (half-open simplificado).
            self.opened_at = None
            self.failure_count = 0
            return "closed"
        return "open"

    def allow_request(self) -> bool:
        return self.state == "closed"

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened_at = time.monotonic()
