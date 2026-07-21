"""Placeholder do job RQ — implementação do worker no T3.4+."""

from __future__ import annotations


def process_modality(case_id: str, modality: str) -> None:
    """Entrypoint enfileirado na fila `default`.

    O corpo real (AnomalyEngine / Fusion) entra nas tarefas de Caso/vitais.
    """
    _ = (case_id, modality)
