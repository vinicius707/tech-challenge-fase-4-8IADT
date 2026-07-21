#!/usr/bin/env python3
"""Gera fixtures sintéticas de sinais vitais (reprodutível, sem download).

Calibração metodológica alinhada a faixas típicas de datasets públicos de
referência (Kaggle Human Vital Signs / Hospital Deterioration). Os brutos
não são baixados em runtime nem no CI — ver data/fixtures/vitals/README.md.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"

# Seed e versão de calibração — alterar só com regeneração documentada.
CALIBRATION_VERSION = "2026-07-21.1"
SEED = 20260721
SAMPLES = 60  # 60 pontos @ 1/min ≈ 1 hora
INTERVAL_SECONDS = 60

FIELDNAMES = (
    "timestamp",
    "heart_rate",
    "spo2",
    "systolic_bp",
    "diastolic_bp",
    "respiratory_rate",
    "label",
)


@dataclass(frozen=True)
class ScenarioParams:
    name: str
    filename: str
    heart_rate: float
    spo2: float
    systolic_bp: float
    diastolic_bp: float
    respiratory_rate: float
    anomaly_start: int | None
    anomaly_deltas: dict[str, float]


SCENARIOS = (
    ScenarioParams(
        name="normal",
        filename="vitals_normal.csv",
        heart_rate=72.0,
        spo2=98.0,
        systolic_bp=118.0,
        diastolic_bp=76.0,
        respiratory_rate=15.0,
        anomaly_start=None,
        anomaly_deltas={},
    ),
    ScenarioParams(
        name="medium",
        filename="vitals_medium.csv",
        heart_rate=78.0,
        spo2=97.0,
        systolic_bp=122.0,
        diastolic_bp=78.0,
        respiratory_rate=16.0,
        anomaly_start=20,
        anomaly_deltas={
            "heart_rate": 28.0,
            "spo2": -5.0,
            "systolic_bp": 18.0,
            "diastolic_bp": 10.0,
            "respiratory_rate": 6.0,
        },
    ),
    ScenarioParams(
        name="high",
        filename="vitals_high.csv",
        heart_rate=80.0,
        spo2=96.0,
        systolic_bp=124.0,
        diastolic_bp=80.0,
        respiratory_rate=17.0,
        anomaly_start=15,
        anomaly_deltas={
            "heart_rate": 55.0,
            "spo2": -14.0,
            "systolic_bp": 35.0,
            "diastolic_bp": 18.0,
            "respiratory_rate": 12.0,
        },
    ),
)


def _noise(index: int, channel: int, amplitude: float) -> float:
    """Ruído determinístico (sem random) para séries estáveis bit-a-bit."""
    phase = (SEED % 997) + index * 0.37 + channel * 1.13
    return amplitude * math.sin(phase)


def generate_rows(scenario: ScenarioParams) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(SAMPLES):
        in_anomaly = (
            scenario.anomaly_start is not None and i >= scenario.anomaly_start
        )
        deltas = scenario.anomaly_deltas if in_anomaly else {}

        heart_rate = (
            scenario.heart_rate
            + deltas.get("heart_rate", 0.0)
            + _noise(i, 1, 1.5)
        )
        spo2 = scenario.spo2 + deltas.get("spo2", 0.0) + _noise(i, 2, 0.3)
        systolic = (
            scenario.systolic_bp
            + deltas.get("systolic_bp", 0.0)
            + _noise(i, 3, 2.0)
        )
        diastolic = (
            scenario.diastolic_bp
            + deltas.get("diastolic_bp", 0.0)
            + _noise(i, 4, 1.5)
        )
        respiratory = (
            scenario.respiratory_rate
            + deltas.get("respiratory_rate", 0.0)
            + _noise(i, 5, 0.4)
        )

        # SpO2 fisiológico saturado em [70, 100]
        spo2 = min(100.0, max(70.0, spo2))

        rows.append(
            {
                "timestamp": f"{i * INTERVAL_SECONDS:04d}",
                "heart_rate": f"{heart_rate:.2f}",
                "spo2": f"{spo2:.2f}",
                "systolic_bp": f"{systolic:.2f}",
                "diastolic_bp": f"{diastolic:.2f}",
                "respiratory_rate": f"{respiratory:.2f}",
                "label": "anomaly" if in_anomaly else "normal",
            }
        )
    return rows


def write_fixture(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for scenario in SCENARIOS:
        rows = generate_rows(scenario)
        write_fixture(OUTPUT_DIR / scenario.filename, rows)
        print(f"Wrote {scenario.filename} ({len(rows)} rows) [{CALIBRATION_VERSION}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
