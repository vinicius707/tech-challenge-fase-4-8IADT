"""TDD T10.1 — cliente Azure Speech real injetável + env (sem rede no CI)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.azure.circuit_breaker import AzureCircuitBreaker
from app.azure.provider import analyze_audio, clear_audio_analysis_cache
from app.azure.speech import (
    create_speech_analyze,
    speech_configured_from_environment,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIO_SPEECH = (
    REPO_ROOT / "data" / "fixtures" / "audio" / "audio_speech.wav"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_speech_env_and_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_audio_analysis_cache()
    monkeypatch.setenv("AZURE_ENABLED", "false")
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    yield
    clear_audio_analysis_cache()


def test_speech_configured_false_when_key_or_region_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_SPEECH_KEY", "fake-key")
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    assert speech_configured_from_environment() is False

    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.setenv("AZURE_SPEECH_REGION", "brazilsouth")
    assert speech_configured_from_environment() is False


def test_speech_configured_true_when_key_and_region_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_SPEECH_KEY", "fake-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "brazilsouth")
    assert speech_configured_from_environment() is True


def test_create_speech_analyze_without_credentials_raises() -> None:
    analyze = create_speech_analyze(speech_key="", speech_region="")
    with pytest.raises(ConnectionError, match="AZURE_SPEECH"):
        analyze(AUDIO_SPEECH)


def test_create_speech_analyze_uses_injected_recognize() -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_recognize(
        payload: bytes, key: str, region: str, locale: str
    ) -> str:
        assert payload == AUDIO_SPEECH
        calls.append((key, region, locale))
        return "paciente com falta de ar"

    analyze = create_speech_analyze(
        speech_key="k",
        speech_region="brazilsouth",
        locale="pt-BR",
        recognize=fake_recognize,
    )
    data = analyze(AUDIO_SPEECH)
    assert data["transcript"] == "paciente com falta de ar"
    assert 0.0 < float(data["score"]) <= 1.0
    assert calls == [("k", "brazilsouth", "pt-BR")]


def test_analyze_audio_azure_enabled_without_speech_key_falls_back_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_ENABLED", "true")
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

    result = analyze_audio(
        AUDIO_SPEECH,
        azure_enabled=True,
        circuit_breaker=AzureCircuitBreaker(failure_threshold=3, open_seconds=60),
    )
    assert result.provider == "local"
    assert result.transcript.startswith("local-transcript-")


def test_analyze_audio_with_speech_analyze_returns_azure_provider() -> None:
    analyze = create_speech_analyze(
        speech_key="k",
        speech_region="brazilsouth",
        recognize=lambda *_args: "transcricao real pt-BR",
    )
    result = analyze_audio(
        AUDIO_SPEECH,
        azure_enabled=True,
        azure_analyze=analyze,
        circuit_breaker=AzureCircuitBreaker(failure_threshold=3, open_seconds=60),
    )
    assert result.provider == "azure"
    assert result.transcript == "transcricao real pt-BR"


def test_default_azure_analyze_reads_env_and_injected_recognize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_SPEECH_KEY", "env-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setattr(
        "app.azure.speech.recognize_with_azure_speech_sdk",
        lambda payload, key, region, locale: f"sdk:{key}:{region}:{locale}",
    )

    from app.azure.provider import default_azure_analyze

    data = default_azure_analyze(AUDIO_SPEECH)
    assert data["transcript"] == "sdk:env-key:eastus:pt-BR"
    assert float(data["score"]) > 0.0
