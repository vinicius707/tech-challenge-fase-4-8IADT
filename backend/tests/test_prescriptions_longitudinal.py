"""TDD T6.17 — desvio longitudinal de Prescrição vs. histórico do Paciente."""

from __future__ import annotations

from pathlib import Path

from app.cases.prescriptions_engine import PrescriptionsAnomalyEngine

REPO_ROOT = Path(__file__).resolve().parents[2]
RX_DIR = REPO_ROOT / "data" / "fixtures" / "prescriptions"


def _csv(name: str) -> bytes:
    return (RX_DIR / name).read_bytes()


def test_without_history_matches_local_rules_only() -> None:
    engine = PrescriptionsAnomalyEngine()
    local = engine.analyze_csv(_csv("prescriptions_normal.csv"))
    with_empty = engine.analyze_csv(
        _csv("prescriptions_normal.csv"),
        history=(),
    )
    assert local.level == with_empty.level == "BAIXO"
    assert local.anomalies == with_empty.anomalies == ()


def test_longitudinal_dose_deviation_beyond_threshold() -> None:
    """Dose dentro do catálogo, mas >50% vs. histórico → anomalia longitudinal."""
    prior = (
        b"timestamp,medication,dose_mg,interval_hours,label\n"
        b"0000,metformin,500.00,12.00,normal\n"
    )
    # 1500 está na faixa 500–2000; desvio 200% vs 500.
    current = (
        b"timestamp,medication,dose_mg,interval_hours,label\n"
        b"0000,metformin,1500.00,12.00,normal\n"
    )
    risk = PrescriptionsAnomalyEngine().analyze_csv(current, history=(prior,))
    assert any(a.metric == "longitudinal_dose" for a in risk.anomalies)
    assert risk.score >= 0.40
    assert risk.level in {"MEDIO", "ALTO"}


def test_longitudinal_new_catalog_medication_vs_history() -> None:
    prior = (
        b"timestamp,medication,dose_mg,interval_hours,label\n"
        b"0000,metformin,500.00,12.00,normal\n"
    )
    current = (
        b"timestamp,medication,dose_mg,interval_hours,label\n"
        b"0000,metformin,500.00,12.00,normal\n"
        b"0024,amlodipine,5.00,24.00,normal\n"
    )
    risk = PrescriptionsAnomalyEngine().analyze_csv(current, history=(prior,))
    assert any(a.metric == "longitudinal_medication" for a in risk.anomalies)
    assert risk.level in {"MEDIO", "ALTO"}


def test_stable_dose_vs_history_keeps_baixo() -> None:
    prior = _csv("prescriptions_normal.csv")
    risk = PrescriptionsAnomalyEngine().analyze_csv(
        _csv("prescriptions_normal.csv"),
        history=(prior,),
    )
    assert risk.level == "BAIXO"
    assert not any(a.metric.startswith("longitudinal_") for a in risk.anomalies)


def test_local_rules_still_apply_with_history() -> None:
    """Histórico não mascara medicamento inesperado / dose fora de faixa."""
    prior = _csv("prescriptions_normal.csv")
    risk = PrescriptionsAnomalyEngine().analyze_csv(
        _csv("prescriptions_high.csv"),
        history=(prior,),
    )
    assert risk.level == "ALTO"
    assert any(a.metric == "medication" for a in risk.anomalies)
