"""Resolução do Provedor de Áudio com circuit breaker (sem Azure real)."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.azure.circuit_breaker import AzureCircuitBreaker

AudioProvider = Literal["azure", "local", "cache"]
AnalyzeFn = Callable[[bytes], dict[str, Any]]


@dataclass(frozen=True)
class AudioAnalysisResult:
    provider: AudioProvider
    transcript: str
    score: float


def azure_enabled_from_environment() -> bool:
    raw = os.getenv("AZURE_ENABLED", "false")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def resolve_audio_provider(
    circuit_breaker: AzureCircuitBreaker,
    *,
    azure_enabled: bool = True,
) -> AudioProvider:
    """Escolhe o provedor efetivo. CB aberto → `local` (sem rede)."""
    if not azure_enabled:
        return "local"
    if not circuit_breaker.allow_request():
        return "local"
    return "azure"


def default_local_analyze(payload: bytes) -> dict[str, Any]:
    """Fallback local stub — sem I/O de rede (Épico 6 substituirá)."""
    _ = payload
    return {"transcript": "", "score": 0.0}


def default_azure_analyze(payload: bytes) -> dict[str, Any]:
    """Stub que NÃO chama rede. Épico 6 pluga o cliente F0 real aqui."""
    raise ConnectionError("Azure Speech não configurado neste protótipo (stub T5.8)")


def analyze_audio(
    payload: bytes,
    *,
    circuit_breaker: AzureCircuitBreaker | None = None,
    azure_enabled: bool | None = None,
    azure_analyze: AnalyzeFn | None = None,
    local_analyze: AnalyzeFn | None = None,
) -> AudioAnalysisResult:
    """Caminho “Azure” consultável: respeita CB e nunca abre socket neste stub."""
    cb = circuit_breaker or AzureCircuitBreaker.from_environment()
    enabled = (
        azure_enabled_from_environment() if azure_enabled is None else azure_enabled
    )
    azure_fn = azure_analyze or default_azure_analyze
    local_fn = local_analyze or default_local_analyze

    provider = resolve_audio_provider(cb, azure_enabled=enabled)
    if provider != "azure":
        data = local_fn(payload)
        return AudioAnalysisResult(
            provider="local",
            transcript=str(data.get("transcript", "")),
            score=float(data.get("score", 0.0)),
        )

    try:
        data = azure_fn(payload)
        cb.record_success()
        return AudioAnalysisResult(
            provider="azure",
            transcript=str(data.get("transcript", "")),
            score=float(data.get("score", 0.0)),
        )
    except Exception:
        cb.record_failure()
        data = local_fn(payload)
        return AudioAnalysisResult(
            provider="local",
            transcript=str(data.get("transcript", "")),
            score=float(data.get("score", 0.0)),
        )
