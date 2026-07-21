"""Placeholder do job RQ — AnomalyEngine/Fusion entram nas tarefas de Caso."""

from __future__ import annotations

import uuid


def process_modality(
    case_id: str,
    modality: str,
    outbox_job_id: str | None = None,
) -> None:
    """Entrypoint enfileirado na fila `default`.

    Nesta etapa (T3.4) só confirma consumo e marca o outbox como `processed`.
    """
    _ = (case_id, modality)
    if outbox_job_id:
        from app.outbox.completion import complete_job

        complete_job(uuid.UUID(outbox_job_id))
