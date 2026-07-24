"""TDD T12.2 — prints versionados + docs apontam evidência (spec epic-12)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGES = REPO_ROOT / "docs" / "notebooks" / "images"
NB_README = REPO_ROOT / "notebooks" / "README.md"
DOCS_README = REPO_ROOT / "docs" / "README.md"
RELATORIO = REPO_ROOT / "docs" / "relatorio-fase4.md"
SPEC = (
    REPO_ROOT
    / "specs"
    / "epic-12-notebooks-evidencia"
    / "01-execucao-prints-docs.md"
)
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"

CANONICAL_PNGS = (
    "01-eda-vitals-inicial.png",
    "02-eda-vitals-final.png",
    "03-evidencia-modalidades.png",
    "04-compare-vitals-ml.png",
    "05-autoencoder-loss.png",
)


def test_canonical_notebook_pngs_exist() -> None:
    assert IMAGES.is_dir()
    for name in CANONICAL_PNGS:
        path = IMAGES / name
        assert path.is_file(), f"PNG ausente: {path}"
        assert path.stat().st_size > 0


def test_notebooks_readme_has_visual_evidence_section() -> None:
    text = NB_README.read_text(encoding="utf-8")
    lower = text.lower()
    assert "evidência visual" in lower or "evidencia visual" in lower
    for name in CANONICAL_PNGS:
        assert name in text, f"README notebooks não referencia {name}"
    assert "docs/notebooks/images" in text or "../docs/notebooks/images" in text


def test_docs_index_marks_e12_and_links_images() -> None:
    text = DOCS_README.read_text(encoding="utf-8")
    assert "epic-12-notebooks-evidencia" in text
    assert "Concluída (E12)" in text or "Concluído (E12)" in text
    for line in text.splitlines():
        if "epic-12-notebooks-evidencia" in line and "|" in line:
            assert "pendente" not in line.lower()
            break
    else:
        raise AssertionError("linha da spec E12 ausente no índice")
    assert "notebooks/images" in text
    assert "04-compare-vitals-ml.png" in text or "05-autoencoder-loss.png" in text


def test_relatorio_53_cites_compare_and_or_ae_figures() -> None:
    text = RELATORIO.read_text(encoding="utf-8")
    assert "### 5.3" in text
    section = text.split("### 5.3", 1)[1]
    # Próxima seção de mesmo nível ou fim do doc.
    for marker in ("\n## ", "\n### 5.4", "\n### 6"):
        if marker in section:
            section = section.split(marker, 1)[0]
            break
    assert "04-compare-vitals-ml.png" in section or "05-autoencoder-loss.png" in section
    assert "notebooks/images" in section


def test_ci_does_not_run_jupyter_or_install_torch() -> None:
    ci = CI_YML.read_text(encoding="utf-8").lower()
    assert "jupyter" not in ci
    assert "torch" not in ci
    assert "pytorch" not in ci
    assert "requirements-ml" not in ci
    assert "nbconvert" not in ci
    assert "eda_vitals_inicial" not in ci
    assert "train_vitals_autoencoder" not in ci


def test_spec_e12_dod_complete() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "Concluída" in text
    dod = text.split("## Critérios de pronto")[-1]
    assert "- [x]" in dod
    assert "- [ ]" not in dod
