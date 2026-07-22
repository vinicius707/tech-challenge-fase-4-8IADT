"""TDD T5.8 — circuit breaker Azure stub (fallback local, sem rede)."""

from __future__ import annotations

import pytest

from app.azure.circuit_breaker import AzureCircuitBreaker, CircuitState
from app.azure.provider import (
    AudioAnalysisResult,
    analyze_audio,
    resolve_audio_provider,
)


def test_resolve_provider_uses_azure_when_circuit_closed() -> None:
    cb = AzureCircuitBreaker(failure_threshold=3, open_seconds=60)
    assert cb.state == "closed"
    assert resolve_audio_provider(cb, azure_enabled=True) == "azure"


def test_resolve_provider_forces_local_when_circuit_open() -> None:
    cb = AzureCircuitBreaker(failure_threshold=3, open_seconds=60, force_open=True)
    assert cb.state == "open"
    assert resolve_audio_provider(cb, azure_enabled=True) == "local"


def test_resolve_provider_local_when_azure_disabled() -> None:
    cb = AzureCircuitBreaker(failure_threshold=3, open_seconds=60)
    assert resolve_audio_provider(cb, azure_enabled=False) == "local"


def test_open_circuit_skips_azure_callable_and_uses_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cenário 5: CB aberto → fallback local sem chamar rede externa."""
    calls: list[str] = []

    def fake_azure(_payload: bytes) -> dict[str, object]:
        calls.append("azure")
        raise AssertionError("Azure não deveria ser chamado com CB aberto")

    def fake_local(_payload: bytes) -> dict[str, object]:
        calls.append("local")
        return {"transcript": "ok-local", "score": 0.1}

    monkeypatch.setenv("LIMEN_AZURE_CB_FORCE_OPEN", "true")
    cb = AzureCircuitBreaker.from_environment()
    assert cb.state == "open"

    result = analyze_audio(
        b"fake-audio",
        circuit_breaker=cb,
        azure_enabled=True,
        azure_analyze=fake_azure,
        local_analyze=fake_local,
    )

    assert result == AudioAnalysisResult(
        provider="local",
        transcript="ok-local",
        score=0.1,
    )
    assert calls == ["local"]


def test_consecutive_failures_open_circuit_then_force_local() -> None:
    cb = AzureCircuitBreaker(failure_threshold=2, open_seconds=300)
    azure_calls = 0

    def flaky_azure(_payload: bytes) -> dict[str, object]:
        nonlocal azure_calls
        azure_calls += 1
        raise ConnectionError("Azure F0 unavailable")

    def local_ok(_payload: bytes) -> dict[str, object]:
        return {"transcript": "fallback", "score": 0.0}

    # 1ª falha: ainda closed → tenta Azure, cai no fallback local.
    r1 = analyze_audio(
        b"a",
        circuit_breaker=cb,
        azure_enabled=True,
        azure_analyze=flaky_azure,
        local_analyze=local_ok,
    )
    assert r1.provider == "local"
    assert cb.state == "closed"
    assert azure_calls == 1

    # 2ª falha: atinge threshold → abre.
    r2 = analyze_audio(
        b"b",
        circuit_breaker=cb,
        azure_enabled=True,
        azure_analyze=flaky_azure,
        local_analyze=local_ok,
    )
    assert r2.provider == "local"
    assert cb.state == "open"
    assert azure_calls == 2

    # 3ª: CB aberto — não chama Azure de novo.
    r3 = analyze_audio(
        b"c",
        circuit_breaker=cb,
        azure_enabled=True,
        azure_analyze=flaky_azure,
        local_analyze=local_ok,
    )
    assert r3.provider == "local"
    assert azure_calls == 2


def test_success_resets_failure_count() -> None:
    cb = AzureCircuitBreaker(failure_threshold=2, open_seconds=60)
    cb.record_failure()
    assert cb.failure_count == 1
    cb.record_success()
    assert cb.failure_count == 0
    assert cb.state == "closed"


def test_from_environment_reads_threshold_and_force_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_AZURE_CB_FAILURE_THRESHOLD", "5")
    monkeypatch.setenv("LIMEN_AZURE_CB_OPEN_SECONDS", "120")
    monkeypatch.delenv("LIMEN_AZURE_CB_FORCE_OPEN", raising=False)
    cb = AzureCircuitBreaker.from_environment()
    assert cb.failure_threshold == 5
    assert cb.open_seconds == 120
    assert cb.state == "closed"

    monkeypatch.setenv("LIMEN_AZURE_CB_FORCE_OPEN", "1")
    forced = AzureCircuitBreaker.from_environment()
    assert forced.state == "open"


def test_state_literal_includes_open_closed() -> None:
    # Garante vocabulário estável para o Épico 6 / observabilidade.
    closed: CircuitState = "closed"
    opened: CircuitState = "open"
    assert closed != opened
