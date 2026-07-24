"""TDD T10.6 — fechamento docs E10 (README, .env.example, índice)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = REPO_ROOT / "specs" / "epic-10-azure-audio-real" / "01-speech-language-evidencia.md"
DOCS = REPO_ROOT / "docs" / "README.md"
README = REPO_ROOT / "README.md"
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def test_spec_e10_marked_concluded_with_dod() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "Concluída" in text
    dod = text.split("## Critérios de pronto")[-1]
    assert "- [x]" in dod
    assert "- [ ]" not in dod
    assert text.count("- [x]") >= 6


def test_docs_index_marks_e10_concluded() -> None:
    text = DOCS.read_text(encoding="utf-8")
    assert "epic-10-azure-audio-real" in text
    assert "Concluída (E10)" in text or "Concluído (E10)" in text
    # Linha da tabela de specs do E10 não deve ficar como “pendente impl.”.
    for line in text.splitlines():
        if "epic-10-azure-audio-real" in line and "|" in line:
            assert "pendente" not in line.lower()
            break
    else:
        raise AssertionError("linha da spec E10 ausente no índice")


def test_readme_documents_azure_real_and_evidencia() -> None:
    text = README.read_text(encoding="utf-8")
    lower = text.lower()
    assert "epic-10-azure-audio-real" in text or "Épico 10" in text
    assert "AZURE_SPEECH_KEY" in text
    assert "AZURE_SPEECH_REGION" in text
    assert "AZURE_LANGUAGE_KEY" in text
    assert "AZURE_LANGUAGE_ENDPOINT" in text
    assert "gerar-evidencia-audio" in lower
    assert "data/evidencia/audio" in lower or "evidencia/audio" in lower
    assert "termo crítico" in lower or "termos críticos" in lower


def test_env_example_has_speech_and_language_placeholders() -> None:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "AZURE_ENABLED=false" in text
    assert "AZURE_SPEECH_KEY=" in text
    assert "AZURE_SPEECH_REGION=" in text
    assert "AZURE_LANGUAGE_KEY=" in text
    assert "AZURE_LANGUAGE_ENDPOINT=" in text
