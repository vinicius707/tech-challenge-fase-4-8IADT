"""Resolução do Provedor de Áudio com circuit breaker, cache e fallback local."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.azure.circuit_breaker import AzureCircuitBreaker
from app.azure.language import (
    LanguageAnalyzeFn,
    LanguageAnalysisResult,
    default_language_analyze,
    empty_language_result,
)

AudioProvider = Literal["azure", "local", "cache"]
AnalyzeFn = Callable[[bytes], dict[str, Any]]


@dataclass(frozen=True)
class AudioAnalysisResult:
    provider: AudioProvider
    transcript: str
    score: float
    sentiment: str | None = None
    sentiment_scores: dict[str, float] | None = None
    key_phrases: tuple[str, ...] = ()
    language_available: bool = False


# Cache in-process keyed por SHA-256 do payload (spec E6.2 / ADR 0015).
_AUDIO_CACHE: dict[str, AudioAnalysisResult] = {}


def clear_audio_analysis_cache() -> None:
    """Limpa o cache (TDD / reprocess controlado)."""
    _AUDIO_CACHE.clear()


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
    """Analyzer local determinístico — sem I/O de rede."""
    digest = hashlib.sha256(payload).hexdigest()
    # Score calibrado pelo tamanho (fixtures curtas → BAIXO).
    score = max(0.05, min(0.35, 0.08 + len(payload) / 400_000))
    return {
        "transcript": f"local-transcript-{digest[:8]}",
        "score": round(score, 4),
    }


def default_azure_analyze(payload: bytes) -> dict[str, Any]:
    """Speech real via env (T10.1). Sem key/region → ConnectionError → fallback `local`.

    Testes injetam `azure_analyze=` ou patcham `recognize_with_azure_speech_sdk`
    para não tocar rede/SDK no CI.
    """
    from app.azure.speech import create_speech_analyze

    return create_speech_analyze()(payload)


def _apply_language(
    transcript: str,
    language_analyze: LanguageAnalyzeFn | None,
) -> LanguageAnalysisResult:
    """Enriquece Transcrição real com Language. Falha → indisponível; não propaga ao CB."""
    fn = language_analyze or default_language_analyze
    try:
        return fn(transcript)
    except Exception:
        return empty_language_result()


def _result_with_language(
    *,
    provider: AudioProvider,
    transcript: str,
    score: float,
    language: LanguageAnalysisResult,
) -> AudioAnalysisResult:
    return AudioAnalysisResult(
        provider=provider,
        transcript=transcript,
        score=score,
        sentiment=language.sentiment if language.available else None,
        sentiment_scores=language.sentiment_scores if language.available else None,
        key_phrases=language.key_phrases if language.available else (),
        language_available=language.available,
    )


def analyze_audio(
    payload: bytes,
    *,
    circuit_breaker: AzureCircuitBreaker | None = None,
    azure_enabled: bool | None = None,
    azure_analyze: AnalyzeFn | None = None,
    local_analyze: AnalyzeFn | None = None,
    language_analyze: LanguageAnalyzeFn | None = None,
) -> AudioAnalysisResult:
    """Analisa áudio: cache → Speech (CB) → Language (degradação independente)."""
    digest = hashlib.sha256(payload).hexdigest()
    cached = _AUDIO_CACHE.get(digest)
    if cached is not None:
        return AudioAnalysisResult(
            provider="cache",
            transcript=cached.transcript,
            score=cached.score,
            sentiment=cached.sentiment,
            sentiment_scores=cached.sentiment_scores,
            key_phrases=cached.key_phrases,
            language_available=cached.language_available,
        )

    cb = circuit_breaker or AzureCircuitBreaker.from_environment()
    enabled = (
        azure_enabled_from_environment() if azure_enabled is None else azure_enabled
    )
    azure_fn = azure_analyze or default_azure_analyze
    local_fn = local_analyze or default_local_analyze

    provider = resolve_audio_provider(cb, azure_enabled=enabled)
    if provider != "azure":
        data = local_fn(payload)
        result = _result_with_language(
            provider="local",
            transcript=str(data.get("transcript", "")),
            score=float(data.get("score", 0.0)),
            language=empty_language_result(),
        )
        _AUDIO_CACHE[digest] = result
        return result

    try:
        data = azure_fn(payload)
        cb.record_success()
        transcript = str(data.get("transcript", ""))
        score = float(data.get("score", 0.0))
        language = _apply_language(transcript, language_analyze)
        result = _result_with_language(
            provider="azure",
            transcript=transcript,
            score=score,
            language=language,
        )
        _AUDIO_CACHE[digest] = result
        return result
    except Exception:
        cb.record_failure()
        data = local_fn(payload)
        result = _result_with_language(
            provider="local",
            transcript=str(data.get("transcript", "")),
            score=float(data.get("score", 0.0)),
            language=empty_language_result(),
        )
        _AUDIO_CACHE[digest] = result
        return result
