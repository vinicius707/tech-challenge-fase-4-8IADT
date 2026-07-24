"""AnomalyEngine + Fusion para modalidade vitais (Épico 3 / T3.8 + Épico 9 / T9.2).

Backends via `LIMEN_VITALS_BACKEND`:
- `thresholds` (default CI) — limiares HR/SpO2 históricos
- `isolation_forest` — sklearn IsolationForest (joblib em models/vitals/)
- `hybrid` — limiares OU Isolation Forest (máx. score + união de anomalias)

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
"""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_IF_NAME = "isolation_forest.joblib"


def resolve_if_model_path() -> Path:
    override = os.getenv("LIMEN_VITALS_IF_MODEL_PATH", "").strip()
    if override:
        return Path(override)
    candidates = (
        REPO_ROOT / "models" / "vitals" / _DEFAULT_IF_NAME,
        _BACKEND_ROOT / "models" / "vitals" / _DEFAULT_IF_NAME,
        Path("/models/vitals") / _DEFAULT_IF_NAME,
    )
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


DEFAULT_IF_MODEL_PATH = resolve_if_model_path()

FEATURE_COLUMNS = (
    "heart_rate",
    "spo2",
    "systolic_bp",
    "diastolic_bp",
    "respiratory_rate",
)


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


class IsolationForestScorer(Protocol):
    def analyze_features(self, rows: list[dict[str, str]]) -> ModalityRisk: ...


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


def vitals_backend_from_environment() -> str:
    raw = os.getenv("LIMEN_VITALS_BACKEND", "thresholds").strip().lower()
    if raw in {"thresholds", "isolation_forest", "hybrid"}:
        return raw
    return "thresholds"


def _parse_rows(content: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def _analyze_thresholds(rows: list[dict[str, str]]) -> ModalityRisk:
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


def _rows_to_feature_matrix(rows: list[dict[str, str]]) -> list[list[float]]:
    matrix: list[list[float]] = []
    for row in rows:
        matrix.append([float(row[col]) for col in FEATURE_COLUMNS])
    return matrix


def _merge_hybrid(threshold: ModalityRisk, forest: ModalityRisk) -> ModalityRisk:
    """OR documentado: máx. score + união de anomalias."""
    score = max(threshold.score, forest.score)
    anomalies = tuple(dict.fromkeys([*threshold.anomalies, *forest.anomalies]))
    return ModalityRisk(
        score=score,
        level=risk_level_from_score(score),
        anomalies=anomalies,
    )


@dataclass
class JoblibIsolationForestScorer:
    """Carrega IsolationForest + metadata via joblib."""

    model_path: Path = DEFAULT_IF_MODEL_PATH

    def analyze_features(self, rows: list[dict[str, str]]) -> ModalityRisk:
        if not rows:
            return ModalityRisk(score=0.0, level="BAIXO", anomalies=())

        try:
            import joblib
            import numpy as np
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "LIMEN_VITALS_BACKEND isolation_forest/hybrid exige "
                "scikit-learn e joblib instalados"
            ) from exc

        if not self.model_path.is_file():
            raise RuntimeError(
                f"Artefato Isolation Forest ausente: {self.model_path}. "
                "Rode: python scripts/train_vitals_if.py"
            )

        payload = joblib.load(self.model_path)
        model = payload["model"] if isinstance(payload, dict) else payload
        matrix = np.asarray(_rows_to_feature_matrix(rows), dtype=float)
        preds = model.predict(matrix)
        decision = model.decision_function(matrix)
        n_anom = int((preds == -1).sum())
        if n_anom == 0:
            return ModalityRisk(score=0.10, level="BAIXO", anomalies=())

        # decision_function: quanto menor, mais anômalo
        min_decision = float(decision.min())
        frac = n_anom / len(rows)
        if min_decision < -0.15 or frac >= 0.35:
            score = 0.85
        elif min_decision < -0.05 or frac >= 0.15:
            score = 0.55
        else:
            score = 0.50

        return ModalityRisk(
            score=score,
            level=risk_level_from_score(score),
            anomalies=(
                VitalsAnomaly(
                    metric="isolation_forest",
                    value=round(min_decision, 4),
                    detail=(
                        f"Isolation Forest: {n_anom}/{len(rows)} pontos anômalos"
                    ),
                ),
            ),
        )


class VitalsAnomalyEngine:
    """Detecta anomalias em séries sintéticas (limiares e/ou Isolation Forest)."""

    def __init__(
        self,
        *,
        backend: str | None = None,
        model_path: Path | None = None,
        if_scorer: IsolationForestScorer | None = None,
    ) -> None:
        self.backend = (backend or vitals_backend_from_environment()).strip().lower()
        if self.backend not in {"thresholds", "isolation_forest", "hybrid"}:
            self.backend = "thresholds"
        self._if_scorer = if_scorer or JoblibIsolationForestScorer(
            model_path=model_path or resolve_if_model_path()
        )

    def analyze_csv(self, content: bytes) -> ModalityRisk:
        rows = _parse_rows(content)
        if self.backend == "thresholds":
            return _analyze_thresholds(rows)
        if self.backend == "isolation_forest":
            return self._if_scorer.analyze_features(rows)
        # hybrid
        threshold = _analyze_thresholds(rows)
        forest = self._if_scorer.analyze_features(rows)
        return _merge_hybrid(threshold, forest)
