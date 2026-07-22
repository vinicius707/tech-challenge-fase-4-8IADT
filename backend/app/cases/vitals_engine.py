"""AnomalyEngine + Fusion para modalidade vitais (Épico 3 / T3.8)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass


@dataclass(frozen=True)
class VitalsAnomaly:
    metric: str
    value: float
    detail: str


@dataclass(frozen=True)
class ModalityRisk:
    score: float
    level: str
    anomalies: tuple[VitalsAnomaly, ...]


def risk_level_from_score(score: float) -> str:
    if score < 0.40:
        return "BAIXO"
    if score < 0.70:
        return "MEDIO"
    return "ALTO"


def fuse_vitals_only(vitals: ModalityRisk) -> ModalityRisk:
    """Com uma única modalidade, a Fusion devolve o risco parcial (peso 1.0)."""
    return fuse_done_modalities([vitals])


def fuse_done_modalities(risks: list[ModalityRisk]) -> ModalityRisk:
    """Fusão com pesos iguais renormalizados só sobre modalidades `done`."""
    if not risks:
        return ModalityRisk(score=0.0, level="BAIXO", anomalies=())
    score = sum(r.score for r in risks) / len(risks)
    anomalies = tuple(a for r in risks for a in r.anomalies)
    return ModalityRisk(
        score=score,
        level=risk_level_from_score(score),
        anomalies=anomalies,
    )


class VitalsAnomalyEngine:
    """Detecta anomalias em séries sintéticas calibradas (fixtures versionadas)."""

    def analyze_csv(self, content: bytes) -> ModalityRisk:
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
        if not rows:
            return ModalityRisk(score=0.0, level="BAIXO", anomalies=())

        heart_rates = [float(r["heart_rate"]) for r in rows]
        spo2_values = [float(r["spo2"]) for r in rows]
        max_hr = max(heart_rates)
        min_spo2 = min(spo2_values)

        anomalies: list[VitalsAnomaly] = []
        if max_hr >= 100:
            anomalies.append(
                VitalsAnomaly(
                    metric="heart_rate",
                    value=max_hr,
                    detail="Frequência cardíaca elevada",
                )
            )
        if min_spo2 < 95:
            anomalies.append(
                VitalsAnomaly(
                    metric="spo2",
                    value=min_spo2,
                    detail="SpO2 reduzida",
                )
            )

        if max_hr >= 130:
            hr_score = 0.85
        elif max_hr >= 100:
            hr_score = 0.55
        else:
            hr_score = 0.10

        if min_spo2 < 88:
            spo2_score = 0.90
        elif min_spo2 < 95:
            spo2_score = 0.50
        else:
            spo2_score = 0.10

        score = max(hr_score, spo2_score)
        return ModalityRisk(
            score=score,
            level=risk_level_from_score(score),
            anomalies=tuple(anomalies),
        )
