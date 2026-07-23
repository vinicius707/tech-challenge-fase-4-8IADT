"""TDD T8.8 — fechamento docs E8.2 (README de entrega + índices)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = REPO_ROOT / "specs" / "epic-08-cicd-entrega" / "02-seed-notebooks-relatorio.md"
README = REPO_ROOT / "README.md"
DOCS = REPO_ROOT / "docs" / "README.md"
COMPOSE_GHCR = REPO_ROOT / "docker-compose.ghcr.yml"


def test_spec_e82_marked_concluded_with_dod() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "Concluída" in text
    assert text.count("- [x]") >= 6
    assert "- [ ]" not in text.split("## Critérios de pronto")[-1]


def test_docs_index_marks_e82_concluded() -> None:
    text = DOCS.read_text(encoding="utf-8")
    assert "Concluída (E8.2)" in text
    assert "Concluído (E8.1–E8.2)" in text or "E8.1–E8.2" in text or "E8.2 concluído" in text


def test_readme_entrega_covers_ghcr_smokes_seed_and_artifacts() -> None:
    text = README.read_text(encoding="utf-8")
    lower = text.lower()
    assert "limen-backend" in lower and "limen-frontend" in lower
    assert "ghcr.io" in lower
    assert "smoke-caso-vitais" in lower
    assert "seed-multimodal-demo" in lower
    assert "relatorio-fase4" in lower or "relatório-fase4" in lower
    assert "roteiro-video" in lower
    assert "notebooks/" in text
    # Não deve restar “Épico 8 pendente” / E8.2 como falta de entrega.
    assert "resta **e8.2**" not in lower
    assert "fechamento fino do readme de entrega\ne8.2" not in lower


def test_compose_ghcr_override_exists() -> None:
    assert COMPOSE_GHCR.is_file()
    text = COMPOSE_GHCR.read_text(encoding="utf-8")
    assert "limen-backend" in text
    assert "limen-frontend" in text
    assert "ghcr.io" in text
