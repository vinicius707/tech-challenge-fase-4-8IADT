"""Contrato das fixtures de vitais (spec epic-03 / T3.1)."""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"
CALIBRATE_SCRIPT = REPO_ROOT / "scripts" / "calibrate_vitals.py"

REQUIRED_FILES = (
    "vitals_normal.csv",
    "vitals_medium.csv",
    "vitals_high.csv",
)

REQUIRED_COLUMNS = (
    "timestamp",
    "heart_rate",
    "spo2",
    "systolic_bp",
    "diastolic_bp",
    "respiratory_rate",
    "label",
)

FORBIDDEN_COLUMN_PATTERNS = re.compile(
    r"(cpf|nome|name|prontuario|patient_id|ssn|email)",
    re.IGNORECASE,
)


def _read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        return list(reader), list(reader.fieldnames)


@pytest.mark.parametrize("filename", REQUIRED_FILES)
def test_vitals_fixture_exists_with_schema(filename: str) -> None:
    path = VITALS_DIR / filename
    assert path.is_file(), f"Fixture ausente: {path}"

    rows, fieldnames = _read_rows(path)
    assert rows, f"Fixture vazia: {filename}"
    for column in REQUIRED_COLUMNS:
        assert column in fieldnames, (
            f"Coluna obrigatória ausente em {filename}: {column}"
        )

    for column in fieldnames:
        assert FORBIDDEN_COLUMN_PATTERNS.search(column) is None, (
            f"Coluna suspeita de PHI em {filename}: {column}"
        )

    timestamps = [row["timestamp"] for row in rows]
    assert timestamps == sorted(timestamps), (
        f"Timestamps fora de ordem em {filename}"
    )

    for row in rows:
        float(row["heart_rate"])
        float(row["spo2"])
        float(row["systolic_bp"])
        float(row["diastolic_bp"])
        float(row["respiratory_rate"])
        assert row["label"] in {"normal", "anomaly"}


def test_vitals_fixtures_readme_and_notebook_exist() -> None:
    assert (VITALS_DIR / "README.md").is_file()
    notebooks = list((REPO_ROOT / "notebooks").glob("*.ipynb"))
    assert notebooks, "Notebook EDA ausente em notebooks/"


def test_calibrate_vitals_is_deterministic() -> None:
    assert CALIBRATE_SCRIPT.is_file()

    before = {
        name: hashlib.sha256((VITALS_DIR / name).read_bytes()).hexdigest()
        for name in REQUIRED_FILES
    }

    result = subprocess.run(
        [sys.executable, str(CALIBRATE_SCRIPT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    after = {
        name: hashlib.sha256((VITALS_DIR / name).read_bytes()).hexdigest()
        for name in REQUIRED_FILES
    }
    assert before == after, "Regeneração das fixtures não foi bit-a-bit estável"
