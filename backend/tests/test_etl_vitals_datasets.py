"""TDD T9.1 — ETL offline de datasets de vitais (spec epic-09 / 01)."""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ETL_SCRIPT = REPO_ROOT / "scripts" / "etl_vitals_datasets.py"
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"
RAW_README = REPO_ROOT / "data" / "raw" / "README.md"
PROCESSED_README = REPO_ROOT / "data" / "processed" / "vitals" / "README.md"
GITIGNORE = REPO_ROOT / ".gitignore"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"

LIMEN_COLUMNS = (
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

DOWNLOAD_PATTERNS = re.compile(
    r"(kaggle\s+download|huggingface-cli|physionet|hf\s+download|wget\s+.*kaggle)",
    re.IGNORECASE,
)


def _run_etl(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ETL_SCRIPT), *args],
        cwd=cwd or REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_raw_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_etl_script_and_readmes_exist() -> None:
    assert ETL_SCRIPT.is_file(), "Script ETL ausente"
    assert RAW_README.is_file(), "README de data/raw/ ausente"
    assert PROCESSED_README.is_file(), "README de data/processed/vitals/ ausente"

    raw_text = RAW_README.read_text(encoding="utf-8")
    assert "kaggle.com/datasets/engrarri21/human-vital-signs" in raw_text
    assert "hospital-deterioration" in raw_text.lower()
    assert "physionet" in raw_text.lower()
    assert "etl_vitals_datasets" in raw_text

    processed_text = PROCESSED_README.read_text(encoding="utf-8")
    assert "heart_rate" in processed_text
    assert "etl_vitals_datasets" in processed_text


def test_etl_without_raws_exits_clean_and_keeps_fixtures() -> None:
    before = {
        name: hashlib.sha256((FIXTURES_DIR / name).read_bytes()).hexdigest()
        for name in (
            "vitals_normal.csv",
            "vitals_medium.csv",
            "vitals_high.csv",
        )
    }

    result = _run_etl("--raw-dir", str(REPO_ROOT / "data" / "raw" / "__missing__"))
    assert result.returncode == 0, result.stderr or result.stdout
    assert "nenhum" in (result.stdout + result.stderr).lower()

    after = {
        name: hashlib.sha256((FIXTURES_DIR / name).read_bytes()).hexdigest()
        for name in before
    }
    assert before == after


def test_etl_with_raws_writes_limen_schema_deterministically(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "processed"

    hvs = raw_dir / "human_vital_signs" / "sample.csv"
    _write_raw_csv(
        hvs,
        ["Heart Rate", "SpO2", "SystolicBP", "DiastolicBP", "RespRate", "Label"],
        [
            {
                "Heart Rate": "72",
                "SpO2": "98",
                "SystolicBP": "118",
                "DiastolicBP": "76",
                "RespRate": "15",
                "Label": "0",
            },
            {
                "Heart Rate": "130",
                "SpO2": "85",
                "SystolicBP": "150",
                "DiastolicBP": "95",
                "RespRate": "28",
                "Label": "1",
            },
        ],
    )

    det = raw_dir / "hospital_deterioration" / "sample.csv"
    _write_raw_csv(
        det,
        ["hr", "spo2", "sbp", "dbp", "rr", "deterioration"],
        [
            {
                "hr": "80",
                "spo2": "96",
                "sbp": "120",
                "dbp": "78",
                "rr": "16",
                "deterioration": "0",
            },
            {
                "hr": "110",
                "spo2": "90",
                "sbp": "140",
                "dbp": "88",
                "rr": "22",
                "deterioration": "1",
            },
        ],
    )

    first = _run_etl(
        "--raw-dir",
        str(raw_dir),
        "--out-dir",
        str(out_dir),
        "--seed",
        "20260721",
    )
    assert first.returncode == 0, first.stderr or first.stdout

    rows_path = out_dir / "train_rows.csv"
    features_path = out_dir / "train_features.csv"
    assert rows_path.is_file()
    assert features_path.is_file()

    with rows_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        fieldnames = list(reader.fieldnames)
        for column in LIMEN_COLUMNS:
            assert column in fieldnames
        assert "source" in fieldnames
        rows = list(reader)

    assert len(rows) == 4
    for column in fieldnames:
        assert FORBIDDEN_COLUMN_PATTERNS.search(column) is None
    for row in rows:
        float(row["heart_rate"])
        float(row["spo2"])
        assert row["label"] in {"normal", "anomaly"}
        assert row["source"] in {"human_vital_signs", "hospital_deterioration"}

    labels = {row["label"] for row in rows}
    assert labels == {"normal", "anomaly"}

    digest_1 = hashlib.sha256(rows_path.read_bytes()).hexdigest()
    digest_f1 = hashlib.sha256(features_path.read_bytes()).hexdigest()

    second = _run_etl(
        "--raw-dir",
        str(raw_dir),
        "--out-dir",
        str(out_dir),
        "--seed",
        "20260721",
    )
    assert second.returncode == 0, second.stderr or second.stdout
    assert hashlib.sha256(rows_path.read_bytes()).hexdigest() == digest_1
    assert hashlib.sha256(features_path.read_bytes()).hexdigest() == digest_f1


def test_etl_from_fixtures_produces_processed_sample(tmp_path: Path) -> None:
    out_dir = tmp_path / "processed"
    result = _run_etl("--from-fixtures", "--out-dir", str(out_dir), "--seed", "20260721")
    assert result.returncode == 0, result.stderr or result.stdout
    assert (out_dir / "train_rows.csv").is_file()
    assert (out_dir / "train_features.csv").is_file()

    with (out_dir / "train_rows.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) >= 60
    assert all(row["source"] == "fixtures" for row in rows)


def test_gitignore_covers_raw_and_processed_with_readme_exceptions() -> None:
    text = GITIGNORE.read_text(encoding="utf-8")
    assert "data/raw" in text
    assert "data/processed/vitals" in text or "data/processed/" in text
    assert "!data/raw/README.md" in text
    assert "!data/processed/vitals/README.md" in text


def test_ci_workflow_has_no_dataset_download_steps() -> None:
    assert CI_WORKFLOW.is_file()
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert DOWNLOAD_PATTERNS.search(text) is None
    assert "kaggle" not in text.lower()
    assert "physionet" not in text.lower()
    assert "huggingface" not in text.lower()


def test_dockerfile_unchanged_mandatory_deps_for_etl() -> None:
    """T9.1 não adiciona deps obrigatórias ao Dockerfile (stdlib only no ETL)."""
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "scikit-learn" not in text
    assert "torch" not in text
    assert "kaggle" not in text.lower()
