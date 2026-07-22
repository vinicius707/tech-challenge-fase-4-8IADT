#!/usr/bin/env python3
"""Gera fixtures sintéticas de prescrições (CSV) — reprodutível, sem PHI.

Cenários normal / medium / high para TDD/demo da modalidade `prescriptions`
(Épico 6 / E6.3). Catálogo local de medicamentos é demonstração acadêmica —
não é formulário hospitalar nem bula clínica.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "fixtures" / "prescriptions"

CALIBRATION_VERSION = "2026-07-21.1"
SEED = 20260721

# Catálogo sintético Limen (faixas demo — ADR 0010).
CATALOG: dict[str, dict[str, float]] = {
    "metformin": {
        "dose_mg_min": 500.0,
        "dose_mg_max": 2000.0,
        "interval_hours": 12.0,
    },
    "amlodipine": {
        "dose_mg_min": 5.0,
        "dose_mg_max": 10.0,
        "interval_hours": 24.0,
    },
    "losartan": {
        "dose_mg_min": 25.0,
        "dose_mg_max": 100.0,
        "interval_hours": 24.0,
    },
}

FIELDNAMES = (
    "timestamp",
    "medication",
    "dose_mg",
    "interval_hours",
    "label",
)

# Rows: (timestamp, medication, dose_mg, interval_hours, label)
SCENARIOS: dict[str, tuple[str, str, list[tuple[str, str, float, float, str]]]] = {
    "normal": (
        "prescriptions_normal.csv",
        "BAIXO",
        [
            ("0000", "metformin", 500.0, 12.0, "normal"),
            ("0012", "metformin", 500.0, 12.0, "normal"),
            ("0024", "amlodipine", 5.0, 24.0, "normal"),
            ("0048", "losartan", 50.0, 24.0, "normal"),
        ],
    ),
    "medium": (
        "prescriptions_medium.csv",
        "MEDIO",
        [
            ("0000", "metformin", 500.0, 12.0, "normal"),
            # Dose acima do máximo do catálogo (2000) → anomaly dose.
            ("0012", "metformin", 2500.0, 12.0, "anomaly"),
            # Intervalo irregular vs. 24h esperado para amlodipine.
            ("0024", "amlodipine", 5.0, 8.0, "anomaly"),
            ("0048", "losartan", 50.0, 24.0, "normal"),
        ],
    ),
    "high": (
        "prescriptions_high.csv",
        "ALTO",
        [
            ("0000", "metformin", 500.0, 12.0, "normal"),
            # Medicamento ausente do catálogo (inesperado).
            ("0012", "xyz_unknown_med", 999.0, 6.0, "anomaly"),
            # Dose muito acima + intervalo irregular.
            ("0024", "amlodipine", 40.0, 4.0, "anomaly"),
            ("0048", "losartan", 200.0, 6.0, "anomaly"),
        ],
    ),
}


def _write_csv(
    path: Path, rows: list[tuple[str, str, float, float, str]]
) -> str:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        for timestamp, medication, dose_mg, interval_hours, label in rows:
            writer.writerow(
                {
                    "timestamp": timestamp,
                    "medication": medication,
                    "dose_mg": f"{dose_mg:.2f}",
                    "interval_hours": f"{interval_hours:.2f}",
                    "label": label,
                }
            )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fixtures_meta: list[dict[str, object]] = []
    for scenario, (filename, risk_hint, rows) in SCENARIOS.items():
        path = OUTPUT_DIR / filename
        sha = _write_csv(path, rows)
        fixtures_meta.append(
            {
                "file": filename,
                "scenario": scenario,
                "expected_risk_hint": risk_hint,
                "row_count": len(rows),
                "sha256": sha,
                "notes": (
                    f"Cenário {scenario} sintético (seed={SEED}) — "
                    "sem PHI nem decisão terapêutica."
                ),
            }
        )
        print(f"Wrote {filename} sha256={sha}")

    manifest = {
        "version": CALIBRATION_VERSION,
        "seed": SEED,
        "fixtures": fixtures_meta,
        "catalog": CATALOG,
        "reference_sources": {
            "synthetic_catalog": (
                "Catálogo sintético Limen — faixas demo (ADR 0010); "
                "não é formulário hospitalar."
            ),
            "public_formularies": (
                "Formulários / bulas genéricas públicas — só calibração; "
                "brutos fora do Git"
            ),
        },
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote manifest.json (version={CALIBRATION_VERSION})")


if __name__ == "__main__":
    main()
