#!/usr/bin/env python3
"""ETL offline: brutos opcionais em data/raw/ → schema/features Limen.

Não baixa datasets. Sem brutos, sai com código 0 e mensagem clara.
PhysioNet é só citação (sem parse). Ver data/raw/README.md e ADR 0029.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw"
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "processed" / "vitals"
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"
DEFAULT_SEED = 20260721

LIMEN_COLUMNS = (
    "timestamp",
    "heart_rate",
    "spo2",
    "systolic_bp",
    "diastolic_bp",
    "respiratory_rate",
    "label",
)

OUTPUT_ROW_COLUMNS = (*LIMEN_COLUMNS, "source")

FEATURE_COLUMNS = (
    "heart_rate",
    "spo2",
    "systolic_bp",
    "diastolic_bp",
    "respiratory_rate",
    "label",
    "source",
)

# aliases normalizados (lower, sem espaços/underscores) → campo Limen
COLUMN_ALIASES: dict[str, str] = {
    "timestamp": "timestamp",
    "time": "timestamp",
    "t": "timestamp",
    "heartrate": "heart_rate",
    "hr": "heart_rate",
    "pulse": "heart_rate",
    "spo2": "spo2",
    "spo₂": "spo2",
    "oxygensaturation": "spo2",
    "o2sat": "spo2",
    "sat": "spo2",
    "systolicbp": "systolic_bp",
    "systolic": "systolic_bp",
    "sbp": "systolic_bp",
    "diastolicbp": "diastolic_bp",
    "diastolic": "diastolic_bp",
    "dbp": "diastolic_bp",
    "respiratoryrate": "respiratory_rate",
    "resprate": "respiratory_rate",
    "rr": "respiratory_rate",
    "respiration": "respiratory_rate",
    "label": "label",
    "deterioration": "label",
    "event": "label",
    "anomaly": "label",
    "target": "label",
}

SOURCE_DIRS = (
    ("human_vital_signs", "human_vital_signs"),
    ("hospital_deterioration", "hospital_deterioration"),
)


def _norm_key(key: str) -> str:
    return (
        key.strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("%", "")
    )


def _map_header(fieldnames: list[str] | None) -> dict[str, str]:
    """Mapa campo_original → campo_Limen (só aliases conhecidos)."""
    mapping: dict[str, str] = {}
    if not fieldnames:
        return mapping
    for original in fieldnames:
        limen = COLUMN_ALIASES.get(_norm_key(original))
        if limen and limen not in mapping.values():
            mapping[original] = limen
    return mapping


def _normalize_label(value: str) -> str:
    text = (value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "anomaly", "abnormal", "deterioration", "event"}:
        return "anomaly"
    if text in {"0", "false", "no", "n", "normal", "ok", "stable"}:
        return "normal"
    if text in {"normal", "anomaly"}:
        return text
    # default: qualquer não-vazio desconhecido → anomaly se numérico >0
    try:
        return "anomaly" if float(text) > 0 else "normal"
    except ValueError:
        return "normal" if not text else "anomaly"


def _safe_float(value: str, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _row_to_limen(
    raw: dict[str, str],
    mapping: dict[str, str],
    *,
    source: str,
    index: int,
) -> dict[str, str] | None:
    mapped: dict[str, str] = {}
    for original, limen in mapping.items():
        mapped[limen] = raw.get(original, "")

    if "heart_rate" not in mapped and "spo2" not in mapped:
        return None

    heart_rate = _safe_float(mapped.get("heart_rate", ""), 72.0)
    spo2 = _safe_float(mapped.get("spo2", ""), 98.0)
    spo2 = min(100.0, max(50.0, spo2))
    systolic = _safe_float(mapped.get("systolic_bp", ""), 120.0)
    diastolic = _safe_float(mapped.get("diastolic_bp", ""), 80.0)
    respiratory = _safe_float(mapped.get("respiratory_rate", ""), 16.0)

    timestamp = mapped.get("timestamp", "").strip()
    if not timestamp:
        timestamp = f"{index:04d}"

    label_raw = mapped.get("label", "")
    label = _normalize_label(label_raw) if label_raw != "" else "normal"

    return {
        "timestamp": timestamp,
        "heart_rate": f"{heart_rate:.2f}",
        "spo2": f"{spo2:.2f}",
        "systolic_bp": f"{systolic:.2f}",
        "diastolic_bp": f"{diastolic:.2f}",
        "respiratory_rate": f"{respiratory:.2f}",
        "label": label,
        "source": source,
    }


def _read_csv_rows(path: Path) -> tuple[list[str] | None, list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames) if reader.fieldnames else None
        return fieldnames, list(reader)


def collect_from_raw_dir(raw_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not raw_dir.is_dir():
        return rows

    for folder_name, source in SOURCE_DIRS:
        folder = raw_dir / folder_name
        if not folder.is_dir():
            continue
        for csv_path in sorted(folder.glob("*.csv")):
            fieldnames, raw_rows = _read_csv_rows(csv_path)
            mapping = _map_header(fieldnames)
            for index, raw in enumerate(raw_rows):
                limen = _row_to_limen(raw, mapping, source=source, index=index)
                if limen is not None:
                    rows.append(limen)
    return rows


def collect_from_fixtures(fixtures_dir: Path = FIXTURES_DIR) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for csv_path in sorted(fixtures_dir.glob("vitals_*.csv")):
        fieldnames, raw_rows = _read_csv_rows(csv_path)
        mapping = _map_header(fieldnames)
        for index, raw in enumerate(raw_rows):
            limen = _row_to_limen(raw, mapping, source="fixtures", index=index)
            if limen is not None:
                rows.append(limen)
    return rows


def _stable_order(rows: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    """Ordena de forma determinística (reproduzível entre corridas)."""
    keyed = [
        (
            hashlib.sha256(
                f"{seed}:{i}:{row['source']}:{row['timestamp']}:{row['heart_rate']}".encode()
            ).hexdigest(),
            row,
        )
        for i, row in enumerate(rows)
    ]
    keyed.sort(key=lambda item: item[0])
    return [row for _, row in keyed]


def write_outputs(out_dir: Path, rows: list[dict[str, str]]) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "train_rows.csv"
    features_path = out_dir / "train_features.csv"

    with rows_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=OUTPUT_ROW_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    with features_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=FEATURE_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in FEATURE_COLUMNS})

    return rows_path, features_path


def run_etl(
    *,
    raw_dir: Path,
    out_dir: Path,
    seed: int = DEFAULT_SEED,
    from_fixtures: bool = False,
) -> int:
    if from_fixtures:
        rows = collect_from_fixtures()
    else:
        rows = collect_from_raw_dir(raw_dir)

    if not rows:
        print("Nenhum bruto encontrado; nada a processar.")
        print(
            f"Coloque CSVs em {raw_dir}/human_vital_signs/ ou "
            f"{raw_dir}/hospital_deterioration/, ou use --from-fixtures."
        )
        return 0

    ordered = _stable_order(rows, seed)
    rows_path, features_path = write_outputs(out_dir, ordered)
    print(f"Wrote {len(ordered)} rows → {rows_path}")
    print(f"Wrote features → {features_path} (seed={seed})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ETL offline de vitais (data/raw → data/processed/vitals)."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="Diretório de brutos (default: data/raw)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Saída processada (default: data/processed/vitals)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Seed de ordenação estável (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--from-fixtures",
        action="store_true",
        help="Usa data/fixtures/vitals/*.csv (sem download de datasets).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_etl(
        raw_dir=args.raw_dir,
        out_dir=args.out_dir,
        seed=args.seed,
        from_fixtures=args.from_fixtures,
    )


if __name__ == "__main__":
    raise SystemExit(main())
