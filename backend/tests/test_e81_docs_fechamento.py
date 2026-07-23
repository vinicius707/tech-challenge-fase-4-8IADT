"""TDD T8.4 — fechamento docs E8.1 (spec, índice, README)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_E81 = REPO_ROOT / "specs" / "epic-08-cicd-entrega" / "01-ghcr-smoke-vitais.md"
DOCS_INDEX = REPO_ROOT / "docs" / "README.md"
ROOT_README = REPO_ROOT / "README.md"


def test_spec_e81_marked_concluded_with_dod() -> None:
    text = SPEC_E81.read_text(encoding="utf-8")
    assert "Concluída" in text
    assert "- [x] Spec SDD aprovada" in text or "- [x] Spec SDD" in text
    assert "- [x] Script `smoke-caso-vitais`" in text or "smoke-caso-vitais" in text
    assert text.count("- [x]") >= 5
    assert "- [ ]" not in text.split("## Critérios de pronto")[-1]


def test_docs_index_marks_e81_concluded() -> None:
    text = DOCS_INDEX.read_text(encoding="utf-8")
    assert "01-ghcr-smoke-vitais.md" in text
    assert "Concluída (E8.1)" in text
    assert "Spec (E8.2)" in text or "E8.2" in text


def test_readme_documents_ghcr_and_smoke_e81() -> None:
    text = ROOT_README.read_text(encoding="utf-8")
    assert "limen-backend" in text
    assert "limen-frontend" in text
    assert "smoke-caso-vitais.sh" in text
    assert "E8.1" in text or "Épico 8 / E8.1" in text
    assert "epic-08-cicd-entrega" in text
