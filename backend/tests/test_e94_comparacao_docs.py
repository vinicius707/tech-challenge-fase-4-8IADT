"""TDD T9.4 — comparação limiares/IF/AE + relatório + roteiro (spec epic-09 / 04)."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS = REPO_ROOT / "notebooks"
COMPARE_NB = NOTEBOOKS / "compare_vitals_ml.ipynb"
NB_README = NOTEBOOKS / "README.md"
RELATORIO = REPO_ROOT / "docs" / "relatorio-fase4.md"
ROTEIRO = REPO_ROOT / "docs" / "demo" / "roteiro-video.md"
DOCS_README = REPO_ROOT / "docs" / "README.md"
ROOT_README = REPO_ROOT / "README.md"
SPEC_04 = REPO_ROOT / "specs" / "epic-09-vitais-ml" / "04-comparacao-relatorio-roteiro.md"
BASELINE = REPO_ROOT / "specs" / "epic-09-vitais-ml" / "00-baseline-atual.md"


def _nb_text(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    parts: list[str] = []
    for cell in data.get("cells", []):
        src = cell.get("source", [])
        if isinstance(src, list):
            parts.extend(src)
        else:
            parts.append(str(src))
    return "\n".join(parts)


def test_compare_notebook_contrasts_three_approaches() -> None:
    assert COMPARE_NB.is_file()
    text = _nb_text(COMPARE_NB).lower()
    assert "threshold" in text or "limiar" in text
    assert "isolation" in text or "isolation_forest" in text
    assert "autoencoder" in text or "ae" in text
    assert "precision" in text or "recall" in text or "auroc" in text or "agreement" in text
    assert "api" in text or "runtime" in text or "worker" in text
    assert "evidência" in text or "evidencia" in text or "notebook" in text
    assert "dispositivo médico" in text or "não é um dispositivo" in text
    assert "kagglehub" not in text
    assert "urllib.request.urlretrieve" not in text


def test_relatorio_has_vitals_ml_section() -> None:
    text = RELATORIO.read_text(encoding="utf-8")
    lower = text.lower()
    assert "0029" in text or "adr 0029" in lower
    assert "limen_vitals_backend" in lower or "LIMEN_VITALS_BACKEND" in text
    assert "isolation forest" in lower or "isolation_forest" in lower
    assert "autoencoder" in lower or "pytorch" in lower
    assert "etl" in lower
    assert "não" in lower or "nao" in lower  # AE fora do runtime / disclaimer


def test_roteiro_prioritizes_app_and_short_notebook() -> None:
    text = ROTEIRO.read_text(encoding="utf-8")
    lower = text.lower()
    assert "hybrid" in lower or "limen_vitals_backend" in lower
    assert "notebook" in lower
    assert "compare_vitals_ml" in text or "train_vitals_autoencoder" in text or "autoencoder" in lower
    assert "kaggle download" not in lower
    assert "não baix" in lower or "sem download" in lower or "não" in lower and "download" in lower


def test_indexes_mark_epic9_complete() -> None:
    docs = DOCS_README.read_text(encoding="utf-8")
    assert "04-comparacao-relatorio-roteiro" in docs
    assert "Concluída (E9.4" in docs

    root = ROOT_README.read_text(encoding="utf-8")
    assert "LIMEN_VITALS_BACKEND" in root
    assert "Isolation Forest" in root or "isolation forest" in root.lower()
    assert "implementação ainda" not in root.lower()

    nb = NB_README.read_text(encoding="utf-8")
    assert "compare_vitals_ml" in nb


def test_spec_and_baseline_reflect_e94() -> None:
    spec = SPEC_04.read_text(encoding="utf-8")
    assert "**Concluída" in spec or "Concluída (T9.4)" in spec
    baseline = BASELINE.read_text(encoding="utf-8")
    assert "T9.4" in baseline
    assert "feita" in baseline.lower()
