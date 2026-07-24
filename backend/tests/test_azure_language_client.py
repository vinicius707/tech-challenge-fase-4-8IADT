"""TDD T10.2 — Azure Language (Sentimento + key phrases) e degradação independente."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.azure.circuit_breaker import AzureCircuitBreaker
from app.azure.language import (
    LanguageAnalysisResult,
    create_language_analyze,
    language_configured_from_environment,
)
from app.azure.provider import analyze_audio, clear_audio_analysis_cache
from app.azure.speech import create_speech_analyze

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIO_SPEECH = (
    REPO_ROOT / "data" / "fixtures" / "audio" / "audio_speech.wav"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_language_env_and_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_audio_analysis_cache()
    monkeypatch.setenv("AZURE_ENABLED", "false")
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    monkeypatch.delenv("AZURE_LANGUAGE_KEY", raising=False)
    monkeypatch.delenv("AZURE_LANGUAGE_ENDPOINT", raising=False)
    yield
    clear_audio_analysis_cache()


def test_language_configured_false_when_key_or_endpoint_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_LANGUAGE_KEY", "fake-key")
    monkeypatch.delenv("AZURE_LANGUAGE_ENDPOINT", raising=False)
    assert language_configured_from_environment() is False

    monkeypatch.delenv("AZURE_LANGUAGE_KEY", raising=False)
    monkeypatch.setenv(
        "AZURE_LANGUAGE_ENDPOINT",
        "https://example.cognitiveservices.azure.com/",
    )
    assert language_configured_from_environment() is False


def test_language_configured_true_when_key_and_endpoint_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_LANGUAGE_KEY", "fake-key")
    monkeypatch.setenv(
        "AZURE_LANGUAGE_ENDPOINT",
        "https://example.cognitiveservices.azure.com/",
    )
    assert language_configured_from_environment() is True


def test_create_language_analyze_without_credentials_returns_unavailable() -> None:
    analyze = create_language_analyze(language_key="", language_endpoint="")
    result = analyze("paciente com falta de ar")
    assert result == LanguageAnalysisResult(available=False)


def test_create_language_analyze_uses_injected_analyze() -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_analyze(text: str, key: str, endpoint: str) -> LanguageAnalysisResult:
        calls.append((text, key, endpoint))
        return LanguageAnalysisResult(
            available=True,
            sentiment="negative",
            sentiment_scores={
                "positive": 0.05,
                "neutral": 0.15,
                "negative": 0.80,
            },
            key_phrases=("falta de ar", "dor"),
        )

    analyze = create_language_analyze(
        language_key="lk",
        language_endpoint="https://example.cognitiveservices.azure.com/",
        analyze_text=fake_analyze,
    )
    result = analyze("paciente com falta de ar")
    assert result.available is True
    assert result.sentiment == "negative"
    assert result.key_phrases == ("falta de ar", "dor")
    assert calls == [
        (
            "paciente com falta de ar",
            "lk",
            "https://example.cognitiveservices.azure.com/",
        )
    ]


def test_analyze_audio_speech_ok_language_missing_keeps_azure_provider() -> None:
    speech = create_speech_analyze(
        speech_key="k",
        speech_region="brazilsouth",
        recognize=lambda *_a: "transcricao real pt-BR",
    )
    language = create_language_analyze(language_key="", language_endpoint="")
    cb = AzureCircuitBreaker(failure_threshold=3, open_seconds=60)

    result = analyze_audio(
        AUDIO_SPEECH,
        azure_enabled=True,
        azure_analyze=speech,
        language_analyze=language,
        circuit_breaker=cb,
    )
    assert result.provider == "azure"
    assert result.transcript == "transcricao real pt-BR"
    assert result.language_available is False
    assert result.sentiment is None
    assert cb.failure_count == 0
    assert cb.state == "closed"


def test_analyze_audio_language_failure_does_not_open_speech_cb() -> None:
    speech = create_speech_analyze(
        speech_key="k",
        speech_region="brazilsouth",
        recognize=lambda *_a: "transcricao real",
    )

    def boom(_text: str) -> LanguageAnalysisResult:
        raise ConnectionError("Language down")

    cb = AzureCircuitBreaker(failure_threshold=1, open_seconds=60)
    result = analyze_audio(
        AUDIO_SPEECH,
        azure_enabled=True,
        azure_analyze=speech,
        language_analyze=boom,
        circuit_breaker=cb,
    )
    assert result.provider == "azure"
    assert result.transcript == "transcricao real"
    assert result.language_available is False
    assert result.sentiment is None
    assert cb.failure_count == 0
    assert cb.state == "closed"


def test_analyze_audio_speech_and_language_success_exposes_sentiment() -> None:
    speech = create_speech_analyze(
        speech_key="k",
        speech_region="brazilsouth",
        recognize=lambda *_a: "estou muito mal",
    )
    language = create_language_analyze(
        language_key="lk",
        language_endpoint="https://example.cognitiveservices.azure.com/",
        analyze_text=lambda text, key, endpoint: LanguageAnalysisResult(
            available=True,
            sentiment="negative",
            sentiment_scores={"positive": 0.1, "neutral": 0.2, "negative": 0.7},
            key_phrases=("mal",),
        ),
    )
    result = analyze_audio(
        AUDIO_SPEECH,
        azure_enabled=True,
        azure_analyze=speech,
        language_analyze=language,
        circuit_breaker=AzureCircuitBreaker(failure_threshold=3, open_seconds=60),
    )
    assert result.provider == "azure"
    assert result.language_available is True
    assert result.sentiment == "negative"
    assert result.sentiment_scores == {
        "positive": 0.1,
        "neutral": 0.2,
        "negative": 0.7,
    }
    assert result.key_phrases == ("mal",)


def test_analyze_audio_local_skips_language() -> None:
    lang_calls: list[str] = []

    def language(_text: str) -> LanguageAnalysisResult:
        lang_calls.append("lang")
        return LanguageAnalysisResult(available=True, sentiment="positive")

    result = analyze_audio(
        AUDIO_SPEECH,
        azure_enabled=False,
        language_analyze=language,
    )
    assert result.provider == "local"
    assert result.language_available is False
    assert result.sentiment is None
    assert lang_calls == []


def test_analyze_audio_cache_skips_speech_and_language() -> None:
    speech_calls: list[str] = []
    lang_calls: list[str] = []

    speech = create_speech_analyze(
        speech_key="k",
        speech_region="brazilsouth",
        recognize=lambda *_a: speech_calls.append("speech") or "texto cache",
    )

    def language(_text: str) -> LanguageAnalysisResult:
        lang_calls.append("lang")
        return LanguageAnalysisResult(
            available=True,
            sentiment="neutral",
            sentiment_scores={"positive": 0.3, "neutral": 0.5, "negative": 0.2},
            key_phrases=("cache",),
        )

    cb = AzureCircuitBreaker(failure_threshold=3, open_seconds=60)
    first = analyze_audio(
        AUDIO_SPEECH,
        azure_enabled=True,
        azure_analyze=speech,
        language_analyze=language,
        circuit_breaker=cb,
    )
    second = analyze_audio(
        AUDIO_SPEECH,
        azure_enabled=True,
        azure_analyze=speech,
        language_analyze=language,
        circuit_breaker=cb,
    )
    assert first.provider == "azure"
    assert second.provider == "cache"
    assert second.sentiment == "neutral"
    assert second.key_phrases == ("cache",)
    assert speech_calls == ["speech"]
    assert lang_calls == ["lang"]
