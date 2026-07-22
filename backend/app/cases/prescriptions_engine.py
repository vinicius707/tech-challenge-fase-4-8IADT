"""AnomalyEngine de Prescrição — regras + desvio longitudinal (Épico 6 / E6.3).

Catálogo sintético Limen (ADR 0010). Sem rede/farmácia real.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass

from app.cases.vitals_engine import ModalityRisk, VitalsAnomaly, risk_level_from_score


@dataclass(frozen=True)
class MedicationBounds:
    dose_mg_min: float
    dose_mg_max: float
    interval_hours: float


# Espelha `data/fixtures/prescriptions/manifest.json` → catalog.
DEFAULT_PRESCRIPTION_CATALOG: dict[str, MedicationBounds] = {
    "metformin": MedicationBounds(
        dose_mg_min=500.0, dose_mg_max=2000.0, interval_hours=12.0
    ),
    "amlodipine": MedicationBounds(
        dose_mg_min=5.0, dose_mg_max=10.0, interval_hours=24.0
    ),
    "losartan": MedicationBounds(
        dose_mg_min=25.0, dose_mg_max=100.0, interval_hours=24.0
    ),
}

_INTERVAL_TOLERANCE = 0.01
# Desvio relativo |nova - antiga| / antiga acima deste limiar → longitudinal.
_DOSE_DEVIATION_RATIO = 0.50


def parse_prescription_rows(content: bytes) -> list[dict[str, float | str]]:
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
    parsed: list[dict[str, float | str]] = []
    for row in rows:
        parsed.append(
            {
                "medication": row["medication"].strip(),
                "dose_mg": float(row["dose_mg"]),
                "interval_hours": float(row["interval_hours"]),
            }
        )
    return parsed


def _baseline_doses(history: Sequence[bytes]) -> dict[str, float]:
    """Última dose por medicamento nos CSVs históricos (ordem = mais antigo → recente)."""
    baseline: dict[str, float] = {}
    for blob in history:
        for row in parse_prescription_rows(blob):
            baseline[str(row["medication"])] = float(row["dose_mg"])
    return baseline


class PrescriptionsAnomalyEngine:
    """Regras locais + desvio longitudinal opcional vs. histórico do Paciente."""

    def __init__(
        self,
        catalog: dict[str, MedicationBounds] | None = None,
        *,
        dose_deviation_ratio: float = _DOSE_DEVIATION_RATIO,
    ) -> None:
        self._catalog = catalog or DEFAULT_PRESCRIPTION_CATALOG
        self._dose_deviation_ratio = dose_deviation_ratio

    def analyze_csv(
        self,
        content: bytes,
        *,
        history: Sequence[bytes] | None = None,
    ) -> ModalityRisk:
        rows = parse_prescription_rows(content)
        if not rows:
            return ModalityRisk(score=0.0, level="BAIXO", anomalies=())

        anomalies: list[VitalsAnomaly] = []
        has_unexpected = False
        has_dose = False
        has_interval = False
        has_longitudinal = False

        for row in rows:
            medication = str(row["medication"])
            dose_mg = float(row["dose_mg"])
            interval_hours = float(row["interval_hours"])
            bounds = self._catalog.get(medication)

            if bounds is None:
                has_unexpected = True
                anomalies.append(
                    VitalsAnomaly(
                        metric="medication",
                        value=0.0,
                        detail=f"Medicamento inesperado: {medication}",
                    )
                )
                continue

            if dose_mg < bounds.dose_mg_min or dose_mg > bounds.dose_mg_max:
                has_dose = True
                anomalies.append(
                    VitalsAnomaly(
                        metric="dose_mg",
                        value=dose_mg,
                        detail=(
                            f"Dose fora de faixa para {medication} "
                            f"({bounds.dose_mg_min}-{bounds.dose_mg_max} mg)"
                        ),
                    )
                )

            if abs(interval_hours - bounds.interval_hours) > _INTERVAL_TOLERANCE:
                has_interval = True
                anomalies.append(
                    VitalsAnomaly(
                        metric="interval_hours",
                        value=interval_hours,
                        detail=(
                            f"Intervalo irregular para {medication} "
                            f"(esperado {bounds.interval_hours} h)"
                        ),
                    )
                )

        prior = history or ()
        if prior:
            baseline = _baseline_doses(prior)
            if baseline:
                current_meds = {str(r["medication"]) for r in rows}
                for medication in sorted(current_meds - set(baseline)):
                    if medication in self._catalog:
                        has_longitudinal = True
                        anomalies.append(
                            VitalsAnomaly(
                                metric="longitudinal_medication",
                                value=0.0,
                                detail=(
                                    f"Medicamento novo vs. histórico do Paciente: "
                                    f"{medication}"
                                ),
                            )
                        )

                for row in rows:
                    medication = str(row["medication"])
                    dose_mg = float(row["dose_mg"])
                    if medication not in baseline:
                        continue
                    old = baseline[medication]
                    if old <= 0:
                        continue
                    ratio = abs(dose_mg - old) / old
                    if ratio > self._dose_deviation_ratio:
                        has_longitudinal = True
                        anomalies.append(
                            VitalsAnomaly(
                                metric="longitudinal_dose",
                                value=dose_mg,
                                detail=(
                                    f"Desvio longitudinal de dose para {medication}: "
                                    f"{old:g} → {dose_mg:g} mg "
                                    f"(>{self._dose_deviation_ratio:.0%})"
                                ),
                            )
                        )

        if has_unexpected:
            score = 0.85
        elif has_longitudinal and (has_dose or has_interval):
            score = 0.75
        elif has_longitudinal:
            score = 0.55
        elif has_dose or has_interval:
            score = 0.55
        else:
            score = 0.10

        return ModalityRisk(
            score=score,
            level=risk_level_from_score(score),
            anomalies=tuple(anomalies),
        )
