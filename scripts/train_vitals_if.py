#!/usr/bin/env python3
"""Treina Isolation Forest pequeno para vitais (Épico 9 / T9.2 / ADR 0029).

Fonte preferencial: data/processed/vitals/train_features.csv (ETL T9.1).
Fallback: fixtures sintéticas em data/fixtures/vitals/ (sem download).

Saída versionada: models/vitals/isolation_forest.joblib

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED = REPO_ROOT / "data" / "processed" / "vitals" / "train_features.csv"
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"
DEFAULT_OUT = REPO_ROOT / "models" / "vitals" / "isolation_forest.joblib"
SEED = 20260721

FEATURE_COLUMNS = (
    "heart_rate",
    "spo2",
    "systolic_bp",
    "diastolic_bp",
    "respiratory_rate",
)


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_training_rows(*, processed: Path, from_fixtures: bool) -> list[dict[str, str]]:
    if from_fixtures or not processed.is_file():
        rows: list[dict[str, str]] = []
        for csv_path in sorted(FIXTURES_DIR.glob("vitals_*.csv")):
            rows.extend(_load_csv_rows(csv_path))
        return rows
    return _load_csv_rows(processed)


def rows_to_matrix(rows: list[dict[str, str]]) -> list[list[float]]:
    return [[float(row[col]) for col in FEATURE_COLUMNS] for row in rows]


def train_and_save(
    *,
    processed: Path,
    out_path: Path,
    from_fixtures: bool,
    seed: int = SEED,
) -> Path:
    from sklearn.ensemble import IsolationForest
    import joblib
    import numpy as np

    rows = load_training_rows(processed=processed, from_fixtures=from_fixtures)
    if not rows:
        raise SystemExit("Nenhuma linha de treino encontrada.")

    # Prefere rótulos normal quando disponíveis; senão usa tudo (unsupervised).
    normals = [r for r in rows if r.get("label", "normal") == "normal"]
    train_rows = normals if len(normals) >= 20 else rows
    matrix = np.asarray(rows_to_matrix(train_rows), dtype=float)

    model = IsolationForest(
        n_estimators=64,
        max_samples="auto",
        contamination=0.08,
        random_state=seed,
        n_jobs=1,
    )
    model.fit(matrix)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model,
        "feature_columns": list(FEATURE_COLUMNS),
        "seed": seed,
        "n_train_rows": len(train_rows),
        "source": "fixtures" if from_fixtures or not processed.is_file() else str(processed),
    }
    joblib.dump(payload, out_path, compress=3)
    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes, n={len(train_rows)})")
    return out_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Treina Isolation Forest de vitais.")
    parser.add_argument(
        "--processed",
        type=Path,
        default=DEFAULT_PROCESSED,
        help="CSV de features do ETL (default: data/processed/vitals/train_features.csv)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Caminho do artefato .joblib",
    )
    parser.add_argument(
        "--from-fixtures",
        action="store_true",
        help="Treina só com data/fixtures/vitals (sem processados).",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    train_and_save(
        processed=args.processed,
        out_path=args.out,
        from_fixtures=args.from_fixtures,
        seed=args.seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
