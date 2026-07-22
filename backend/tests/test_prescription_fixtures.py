"""TDD T6.14 — contrato das fixtures de prescrições (spec epic-06 E6.3)."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RX_DIR = REPO_ROOT / "data" / "fixtures" / "prescriptions"
PREPARE_SCRIPT = REPO_ROOT / "scripts" / "prepare_prescription_fixtures.py"

REQUIRED_FILES = (
    "prescriptions_normal.csv",
    "prescriptions_medium.csv",
    "prescriptions_high.csv",
    "manifest.json",
    "README.md",
)

REQUIRED_COLUMNS = (
    "timestamp",
    "medication",
    "dose_mg",
    "interval_hours",
    "label",
)

MANIFEST_REQUIRED_KEYS = ("version", "seed", "fixtures", "catalog")
FIXTURE_REQUIRED_KEYS = ("file", "scenario", "expected_risk_hint", "sha256")

FORBIDDEN_COLUMN_PATTERNS = re.compile(
    r"(cpf|nome|name|prontuario|patient_id|ssn|email|diagnostico|diagnosis)",
    re.IGNORECASE,
)


def _read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        return list(reader), list(reader.fieldnames)


@pytest.mark.parametrize("filename", REQUIRED_FILES)
def test_prescription_fixture_file_exists(filename: str) -> None:
    path = RX_DIR / filename
    assert path.is_file(), f"Fixture ausente: {path}"


@pytest.mark.parametrize(
    "filename",
    (
        "prescriptions_normal.csv",
        "prescriptions_medium.csv",
        "prescriptions_high.csv",
    ),
)
def test_prescription_csv_schema_and_no_phi(filename: str) -> None:
    path = RX_DIR / filename
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
        assert row["medication"].strip(), "medicamento vazio"
        float(row["dose_mg"])
        float(row["interval_hours"])
        assert row["label"] in {"normal", "anomaly"}


def test_manifest_declares_three_scenarios_and_catalog() -> None:
    manifest = json.loads((RX_DIR / "manifest.json").read_text(encoding="utf-8"))
    for key in MANIFEST_REQUIRED_KEYS:
        assert key in manifest, f"Chave ausente no manifest: {key}"

    by_file = {item["file"]: item for item in manifest["fixtures"]}
    for name in (
        "prescriptions_normal.csv",
        "prescriptions_medium.csv",
        "prescriptions_high.csv",
    ):
        assert name in by_file
        item = by_file[name]
        for key in FIXTURE_REQUIRED_KEYS:
            assert key in item, f"Chave ausente em fixture: {key}"
        assert (RX_DIR / item["file"]).is_file()
        digest = hashlib.sha256((RX_DIR / name).read_bytes()).hexdigest()
        assert item["sha256"] == digest

    scenarios = {item["scenario"] for item in manifest["fixtures"]}
    assert scenarios == {"normal", "medium", "high"}

    catalog = manifest["catalog"]
    assert isinstance(catalog, dict) and catalog
    for med, bounds in catalog.items():
        assert "dose_mg_min" in bounds
        assert "dose_mg_max" in bounds
        assert "interval_hours" in bounds
        assert float(bounds["dose_mg_min"]) < float(bounds["dose_mg_max"])

    readme = (RX_DIR / "README.md").read_text(encoding="utf-8")
    assert "prepare_prescription_fixtures" in readme
    assert "dose_mg" in readme
    assert "catálogo" in readme.lower() or "catalog" in readme.lower()


def test_prepare_prescription_fixtures_is_deterministic() -> None:
    assert PREPARE_SCRIPT.is_file()

    tracked = (
        "prescriptions_normal.csv",
        "prescriptions_medium.csv",
        "prescriptions_high.csv",
        "manifest.json",
    )
    before = {
        name: hashlib.sha256((RX_DIR / name).read_bytes()).hexdigest()
        for name in tracked
    }

    result = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    after = {
        name: hashlib.sha256((RX_DIR / name).read_bytes()).hexdigest()
        for name in tracked
    }
    assert before == after, (
        "Regeneração das fixtures de prescrições não foi bit-a-bit estável"
    )
