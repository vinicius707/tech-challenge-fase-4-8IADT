"""AnomalyEngine de Prescrição — regras determinísticas (Épico 6 / T6.16).

Catálogo sintético Limen (ADR 0010). Sem desvio longitudinal (T6.17) e sem
rede/farmácia real.
"""

from __future__ import annotations

import csv
import io
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


class PrescriptionsAnomalyEngine:
    """Regras locais: dose fora de faixa, intervalo irregular, medicamento inesperado."""

    def __init__(
        self,
        catalog: dict[str, MedicationBounds] | None = None,
    ) -> None:
        self._catalog = catalog or DEFAULT_PRESCRIPTION_CATALOG

    def analyze_csv(self, content: bytes) -> ModalityRisk:
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
        if not rows:
            return ModalityRisk(score=0.0, level="BAIXO", anomalies=())

        anomalies: list[VitalsAnomaly] = []
        has_unexpected = False
        has_dose = False
        has_interval = False

        for row in rows:
            medication = row["medication"].strip()
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

        if has_unexpected:
            score = 0.85
        elif has_dose or has_interval:
            score = 0.55
        else:
            score = 0.10

        return ModalityRisk(
            score=score,
            level=risk_level_from_score(score),
            anomalies=tuple(anomalies),
        )
