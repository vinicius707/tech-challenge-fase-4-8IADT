"""Timeouts configuráveis por modalidade (ADR 0017)."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

DEFAULT_TIMEOUTS_SECONDS: dict[str, float] = {
    "vitals": 30.0,
    "audio": 90.0,
    "video": 180.0,
}


class ModalityTimeoutError(Exception):
    """Estouro do timeout da modalidade — marca `failed` (falha parcial)."""

    def __init__(self, modality: str, timeout_seconds: float) -> None:
        self.modality = modality
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Timeout de {timeout_seconds}s na modalidade {modality}"
        )


def modality_timeout_seconds(modality: str) -> float:
    env_key = f"LIMEN_TIMEOUT_{modality.upper()}_SECONDS"
    raw = os.getenv(env_key)
    if raw is not None and raw.strip():
        return float(raw)
    return DEFAULT_TIMEOUTS_SECONDS.get(modality, 60.0)


def run_with_modality_timeout(
    modality: str,
    fn: Callable[[], T],
    *,
    timeout_seconds: float | None = None,
) -> T:
    limit = (
        modality_timeout_seconds(modality)
        if timeout_seconds is None
        else timeout_seconds
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=limit)
        except FuturesTimeoutError as exc:
            raise ModalityTimeoutError(modality, limit) from exc
