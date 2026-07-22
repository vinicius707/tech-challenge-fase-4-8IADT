"""Classificação de erros e política de retry (ADR 0015)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

ErrorKind = Literal["transient", "permanent"]


class TransientProcessingError(Exception):
    """Erro recuperável — retry com backoff na fila RQ."""


class PermanentProcessingError(Exception):
    """Erro definitivo — modalidade `failed` + registro na DLQ (T5.7)."""


def classify_error(exc: BaseException) -> ErrorKind:
    if isinstance(exc, TransientProcessingError):
        return "transient"
    if isinstance(exc, PermanentProcessingError):
        return "permanent"
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return "transient"
    return "permanent"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0

    @classmethod
    def from_environment(cls) -> RetryPolicy:
        max_attempts = int(os.getenv("LIMEN_RETRY_MAX_ATTEMPTS", "3"))
        base = float(os.getenv("LIMEN_RETRY_BASE_DELAY_SECONDS", "1"))
        return cls(max_attempts=max_attempts, base_delay_seconds=base)

    def should_retry(self, exc: BaseException, *, attempt: int) -> bool:
        if classify_error(exc) != "transient":
            return False
        return attempt < self.max_attempts

    def backoff_seconds(self, attempt: int) -> float:
        return self.base_delay_seconds * (2 ** (attempt - 1))
