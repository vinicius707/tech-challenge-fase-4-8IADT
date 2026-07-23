"""TDD T8.7 — relatório Fase 4 + roteiro de vídeo (capítulo datasets)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RELATORIO = REPO_ROOT / "docs" / "relatorio-fase4.md"
ROTEIRO = REPO_ROOT / "docs" / "demo" / "roteiro-video.md"


def test_relatorio_exists_with_disclaimer_and_datasets_chapter() -> None:
    assert RELATORIO.is_file()
    text = RELATORIO.read_text(encoding="utf-8").lower()
    assert "dispositivo médico" in text or "nao e um dispositivo" in text
    assert "capítulo" in text or "capitulo" in text or "## datasets" in text
    assert "kaggle" in text or "human vital" in text
    assert "deterioration" in text or "deterioração" in text
    assert "physionet" in text
    assert "audioset" in text
    assert "fixture" in text or "runtime" in text
    assert "referência" in text or "referencia" in text or "metodológ" in text


def test_relatorio_covers_remaining_catalog() -> None:
    text = RELATORIO.read_text(encoding="utf-8").lower()
    assert "3dyoga" in text or "yoga" in text
    assert "prescription" in text or "prescri" in text
    assert "medical speech" in text or "speech" in text


def test_roteiro_video_covers_demo_flow_and_omissions() -> None:
    assert ROTEIRO.is_file()
    text = ROTEIRO.read_text(encoding="utf-8").lower()
    assert "login" in text
    assert "paciente" in text or "caso" in text
    assert "risco" in text or "alerta" in text
    assert "secret" in text or "senha" in text or "phi" in text
    assert "min" in text or "minuto" in text or "duração" in text or "duracao" in text
