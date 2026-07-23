"""TDD T8.3 — job CI de smoke Compose + Caso vitais (AZURE_ENABLED=false)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def ci_text() -> str:
    assert CI_YML.is_file()
    return CI_YML.read_text(encoding="utf-8")


def test_ci_has_smoke_caso_vitais_job(ci_text: str) -> None:
    lower = ci_text.lower()
    assert "smoke-caso-vitais" in lower or "smoke caso vitais" in lower
    assert "smoke-caso-vitais.sh" in ci_text or "smoke_caso_vitais.py" in ci_text


def test_ci_smoke_sets_azure_enabled_false(ci_text: str) -> None:
    assert "AZURE_ENABLED" in ci_text
    # Valor false explícito no job (env ou step).
    assert "AZURE_ENABLED: \"false\"" in ci_text or "AZURE_ENABLED: false" in ci_text or "AZURE_ENABLED=false" in ci_text


def test_ci_smoke_uses_docker_compose_path(ci_text: str) -> None:
    """O job deve exercitar Compose (via script de smoke ou compose direto)."""
    assert "smoke-caso-vitais.sh" in ci_text or "docker compose" in ci_text.lower()


def test_ci_smoke_waits_for_backend_tests(ci_text: str) -> None:
    """Evita subir Compose se o pytest já falhou."""
    # Job smoke declara needs: backend (ou needs: [backend]).
    assert "needs:" in ci_text
    assert "backend" in ci_text
    # Trecho do job de smoke referencia needs + backend.
    smoke_idx = ci_text.lower().find("smoke")
    assert smoke_idx != -1
    window = ci_text[max(0, smoke_idx - 200) : smoke_idx + 400]
    assert "needs" in window.lower()
    assert "backend" in window.lower()
