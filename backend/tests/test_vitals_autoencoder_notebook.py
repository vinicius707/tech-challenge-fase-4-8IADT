"""TDD T9.3 — Autoencoder PyTorch só evidência (spec epic-09 / 03)."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS = REPO_ROOT / "notebooks"
AE_NOTEBOOK = NOTEBOOKS / "train_vitals_autoencoder.ipynb"
REQ_ML = NOTEBOOKS / "requirements-ml.txt"
README = NOTEBOOKS / "README.md"
BACKEND_APP = REPO_ROOT / "backend" / "app"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"
GITIGNORE = REPO_ROOT / ".gitignore"
PYPROJECT = REPO_ROOT / "backend" / "pyproject.toml"


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


def test_ae_notebook_and_ml_requirements_exist() -> None:
    assert AE_NOTEBOOK.is_file()
    assert REQ_ML.is_file()
    req = REQ_ML.read_text(encoding="utf-8").lower()
    assert "torch" in req

    text = _nb_text(AE_NOTEBOOK).lower()
    assert "autoencoder" in text or "nn.module" in text or "torch.nn" in text
    assert "epoch" in text
    assert "loss" in text
    assert "early" in text and "stop" in text
    assert "ae_export" in text or ".pt" in text
    assert "processed" in text or "fixtures" in text
    assert "dispositivo médico" in text or "não é um dispositivo" in text
    assert "urllib.request.urlretrieve" not in text
    assert "kagglehub" not in text


def test_notebooks_readme_documents_ml_env_and_ci_exclusion() -> None:
    text = README.read_text(encoding="utf-8")
    assert "train_vitals_autoencoder" in text
    assert "requirements-ml" in text
    assert "torch" in text.lower() or "pytorch" in text.lower()
    lower = text.lower()
    assert "ci" in lower
    assert "não" in lower or "nao" in lower


def test_no_torch_in_backend_app() -> None:
    torch_import = re.compile(
        r"^\s*(import\s+torch|from\s+torch\b)",
        re.MULTILINE,
    )
    offenders: list[str] = []
    for path in BACKEND_APP.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        if torch_import.search(content):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []


def test_ci_and_dockerfile_without_torch() -> None:
    ci = CI_WORKFLOW.read_text(encoding="utf-8").lower()
    assert "torch" not in ci
    assert "pytorch" not in ci
    assert "train_vitals_autoencoder" not in ci
    assert "requirements-ml" not in ci

    dockerfile = DOCKERFILE.read_text(encoding="utf-8").lower()
    assert "torch" not in dockerfile

    pyproject = PYPROJECT.read_text(encoding="utf-8").lower()
    assert "torch" not in pyproject


def test_ae_weights_gitignored() -> None:
    text = GITIGNORE.read_text(encoding="utf-8")
    assert ".pt" in text or "ae_export" in text
