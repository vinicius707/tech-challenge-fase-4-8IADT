"""TDD T9.2 — Isolation Forest no VitalsAnomalyEngine (spec epic-09 / 02)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.cases.vitals_engine import (
    DEFAULT_IF_MODEL_PATH,
    ModalityRisk,
    VitalsAnomaly,
    VitalsAnomalyEngine,
    fuse_vitals_only,
    risk_level_from_score,
    vitals_backend_from_environment,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"
MODELS_DIR = REPO_ROOT / "models" / "vitals"
TRAIN_SCRIPT = REPO_ROOT / "scripts" / "train_vitals_if.py"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
README = REPO_ROOT / "README.md"
DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"
COMPOSE = REPO_ROOT / "docker-compose.yml"
PYPROJECT = REPO_ROOT / "backend" / "pyproject.toml"


def _csv(name: str) -> bytes:
    return (VITALS_DIR / name).read_bytes()


def test_default_backend_is_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIMEN_VITALS_BACKEND", raising=False)
    assert vitals_backend_from_environment() == "thresholds"


def test_thresholds_backend_preserves_fixture_risk_levels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_VITALS_BACKEND", "thresholds")
    expectations = {
        "vitals_normal.csv": "BAIXO",
        "vitals_medium.csv": "MEDIO",
        "vitals_high.csv": "ALTO",
    }
    engine = VitalsAnomalyEngine()
    for name, level in expectations.items():
        fused = fuse_vitals_only(engine.analyze_csv(_csv(name)))
        assert fused.level == level
        assert risk_level_from_score(fused.score) == level


def test_isolation_forest_artifact_exists_and_is_small() -> None:
    path = DEFAULT_IF_MODEL_PATH
    assert path.is_file(), f"Modelo IF ausente: {path}"
    assert path.stat().st_size < 500_000, "Artefato IF deve ser pequeno (<500KB)"
    assert (MODELS_DIR / "README.md").is_file()


def test_isolation_forest_flags_high_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_VITALS_BACKEND", "isolation_forest")
    result = VitalsAnomalyEngine().analyze_csv(_csv("vitals_high.csv"))
    fused = fuse_vitals_only(result)
    assert fused.level in {"MEDIO", "ALTO"}
    assert fused.score >= 0.40
    assert fused.anomalies
    assert any(a.metric.startswith("if_") or a.metric == "isolation_forest" for a in fused.anomalies) or fused.anomalies


def test_hybrid_or_union_of_threshold_and_if(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hybrid = limiares OU IF (máx. score + união de anomalias)."""
    monkeypatch.setenv("LIMEN_VITALS_BACKEND", "hybrid")

    @dataclass(frozen=True)
    class _FakeIF:
        risk: ModalityRisk

        def analyze_features(self, _rows: list[dict[str, str]]) -> ModalityRisk:
            return self.risk

    # Só IF dispara (série “quase normal” nos limiares, IF injeta MEDIO).
    only_if = ModalityRisk(
        score=0.55,
        level="MEDIO",
        anomalies=(
            VitalsAnomaly(
                metric="isolation_forest",
                value=0.55,
                detail="Anomalia Isolation Forest",
            ),
        ),
    )
    # Série abaixo dos limiares HR/SpO2.
    mild = (
        b"timestamp,heart_rate,spo2,systolic_bp,diastolic_bp,respiratory_rate,label\n"
        b"0000,72.0,98.0,118.0,76.0,15.0,normal\n"
        b"0060,73.0,97.5,119.0,77.0,15.0,normal\n"
    )
    engine = VitalsAnomalyEngine(if_scorer=_FakeIF(only_if))
    result = engine.analyze_csv(mild)
    assert result.level == "MEDIO"
    assert any(a.metric == "isolation_forest" for a in result.anomalies)

    # Só limiar dispara (HR alta), IF devolve BAIXO sem anomalias.
    only_thr_csv = (
        b"timestamp,heart_rate,spo2,systolic_bp,diastolic_bp,respiratory_rate,label\n"
        b"0000,110.0,98.0,118.0,76.0,15.0,anomaly\n"
    )
    quiet_if = ModalityRisk(score=0.10, level="BAIXO", anomalies=())
    engine2 = VitalsAnomalyEngine(if_scorer=_FakeIF(quiet_if))
    result2 = engine2.analyze_csv(only_thr_csv)
    assert result2.level == "MEDIO"
    assert any(a.metric == "heart_rate" for a in result2.anomalies)


def test_train_script_exists() -> None:
    assert TRAIN_SCRIPT.is_file()


def test_env_example_and_readme_document_vitals_backend() -> None:
    env_text = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "LIMEN_VITALS_BACKEND=thresholds" in env_text
    assert "isolation_forest" in env_text
    assert "hybrid" in env_text

    readme = README.read_text(encoding="utf-8")
    assert "LIMEN_VITALS_BACKEND" in readme

    compose = COMPOSE.read_text(encoding="utf-8")
    assert "LIMEN_VITALS_BACKEND" in compose


def test_no_torch_in_runtime_deps() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    assert "scikit-learn" in pyproject or "sklearn" in pyproject
    assert "joblib" in pyproject
    assert "torch" not in pyproject.lower()
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "torch" not in dockerfile.lower()
