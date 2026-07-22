"""TDD T6.16 — engine de regras determinísticas de Prescrição (sem histórico)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cases.prescriptions_engine import (
    DEFAULT_PRESCRIPTION_CATALOG,
    PrescriptionsAnomalyEngine,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RX_DIR = REPO_ROOT / "data" / "fixtures" / "prescriptions"


def _csv(name: str) -> bytes:
    return (RX_DIR / name).read_bytes()


def test_catalog_matches_fixture_manifest_keys() -> None:
    assert set(DEFAULT_PRESCRIPTION_CATALOG) == {
        "metformin",
        "amlodipine",
        "losartan",
    }
    metformin = DEFAULT_PRESCRIPTION_CATALOG["metformin"]
    assert metformin.dose_mg_min == 500.0
    assert metformin.dose_mg_max == 2000.0
    assert metformin.interval_hours == 12.0


def test_rules_normal_fixture_is_baixo() -> None:
    risk = PrescriptionsAnomalyEngine().analyze_csv(_csv("prescriptions_normal.csv"))
    assert risk.level == "BAIXO"
    assert risk.score < 0.40
    assert risk.anomalies == ()


def test_rules_medium_fixture_detects_dose_and_interval() -> None:
    risk = PrescriptionsAnomalyEngine().analyze_csv(_csv("prescriptions_medium.csv"))
    assert risk.level == "MEDIO"
    assert 0.40 <= risk.score < 0.70
    metrics = {a.metric for a in risk.anomalies}
    assert "dose_mg" in metrics
    assert "interval_hours" in metrics
    assert "medication" not in metrics  # medicamentos do catálogo


def test_rules_high_fixture_detects_unexpected_medication() -> None:
    risk = PrescriptionsAnomalyEngine().analyze_csv(_csv("prescriptions_high.csv"))
    assert risk.level == "ALTO"
    assert risk.score >= 0.70
    metrics = {a.metric for a in risk.anomalies}
    assert "medication" in metrics
    unexpected = [a for a in risk.anomalies if a.metric == "medication"]
    assert any("xyz_unknown_med" in a.detail for a in unexpected)


def test_rules_unexpected_medication_alone_is_alto() -> None:
    csv_bytes = (
        b"timestamp,medication,dose_mg,interval_hours,label\n"
        b"0000,unknown_drug,10.00,12.00,anomaly\n"
    )
    risk = PrescriptionsAnomalyEngine().analyze_csv(csv_bytes)
    assert risk.level == "ALTO"
    assert any(a.metric == "medication" for a in risk.anomalies)


def test_rules_dose_only_out_of_range_is_medio() -> None:
    csv_bytes = (
        b"timestamp,medication,dose_mg,interval_hours,label\n"
        b"0000,metformin,3000.00,12.00,anomaly\n"
    )
    risk = PrescriptionsAnomalyEngine().analyze_csv(csv_bytes)
    assert risk.level == "MEDIO"
    assert any(a.metric == "dose_mg" for a in risk.anomalies)
