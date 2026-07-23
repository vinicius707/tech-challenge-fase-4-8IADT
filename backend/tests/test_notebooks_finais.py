"""TDD T8.6 — notebooks finais de evidência (sem download no CI)."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS = REPO_ROOT / "notebooks"


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


def test_notebooks_readme_indexes_finais() -> None:
    readme = NOTEBOOKS / "README.md"
    assert readme.is_file()
    text = readme.read_text(encoding="utf-8")
    assert "eda_vitals_final" in text
    assert "evidencia_modalidades" in text
    assert "não" in text.lower() or "nao" in text.lower() or "not" in text.lower()


def test_eda_vitals_final_covers_catalog_and_fixtures() -> None:
    path = NOTEBOOKS / "eda_vitals_final.ipynb"
    assert path.is_file()
    text = _nb_text(path).lower()
    assert "physionet" in text
    assert "hospital deterioration" in text or "deterioration" in text
    assert "kaggle" in text or "human vital" in text
    assert "fixtures" in text or "vitals_" in text
    assert "dispositivo médico" in text or "não é um dispositivo" in text
    # Sem download obrigatório de brutos
    assert "urllib.request.urlretrieve" not in text
    assert "kagglehub" not in text
    assert "wget " not in text


def test_evidencia_modalidades_covers_audio_video_rx() -> None:
    path = NOTEBOOKS / "evidencia_modalidades.ipynb"
    assert path.is_file()
    text = _nb_text(path).lower()
    assert "audioset" in text
    assert "3dyoga90" in text or "yoga" in text
    assert "prescription" in text or "prescri" in text
    assert "audio" in text and "video" in text
    assert "fixtures" in text
    assert "urllib.request.urlretrieve" not in text
    assert "kagglehub" not in text


def test_initial_vitals_notebook_still_present() -> None:
    assert (NOTEBOOKS / "eda_vitals_inicial.ipynb").is_file()
