"""Job RQ — processa modalidade e marca outbox como processed."""

from __future__ import annotations

import uuid


def process_modality(
    case_id: str,
    modality: str,
    outbox_job_id: str | None = None,
) -> None:
    """Entrypoint enfileirado na fila `default`."""
    if modality == "vitals":
        from app.cases.processing import process_vitals_for_case

        process_vitals_for_case(uuid.UUID(case_id))

    if outbox_job_id:
        from app.outbox.completion import complete_job

        complete_job(uuid.UUID(outbox_job_id))
