"""Justificativa de Risco por template determinístico (Épico 7 / T7.1)."""

from __future__ import annotations

from typing import Any

from app.cases.service import ModalityRecord
from app.cases.vitals_engine import ModalityRisk

_TOP_ANOMALIES = 5


def build_justification(
    *,
    modalities: list[ModalityRecord],
    risks_by_modality: dict[str, ModalityRisk],
    fused_score: float,
    fused_level: str,
) -> dict[str, Any]:
    """Monta Justificativa com pesos iguais renormalizados só sobre `done`."""
    done = [m for m in modalities if m.status == "done" and m.modality in risks_by_modality]
    weight = (1.0 / len(done)) if done else None

    entries: list[dict[str, Any]] = []
    contrib_bits: list[str] = []
    unavailable_bits: list[str] = []

    for mod in sorted(modalities, key=lambda m: m.modality):
        if mod.status == "done" and mod.modality in risks_by_modality:
            risk = risks_by_modality[mod.modality]
            top = [a.metric for a in risk.anomalies[:_TOP_ANOMALIES]]
            entries.append(
                {
                    "modality": mod.modality,
                    "status": "done",
                    "weight": weight,
                    "partial_score": risk.score,
                    "partial_level": risk.level,
                    "top_anomalies": top,
                }
            )
            anomalies_suffix = f" [{', '.join(top)}]" if top else ""
            contrib_bits.append(
                f"{mod.modality}: {risk.level} ({risk.score:.2f}){anomalies_suffix}"
            )
        else:
            entries.append(
                {
                    "modality": mod.modality,
                    "status": mod.status,
                    "weight": None,
                    "partial_score": None,
                    "partial_level": None,
                    "top_anomalies": [],
                }
            )
            unavailable_bits.append(f"{mod.modality} ({mod.status})")

    narrative = (
        f"Risco {fused_level} (score {fused_score:.2f}). "
        f"Contribuições: {'; '.join(contrib_bits) if contrib_bits else 'nenhuma'}."
    )
    if unavailable_bits:
        narrative += f" Modalidades indisponíveis: {'; '.join(unavailable_bits)}."

    return {"narrative": narrative, "modalities": entries}
