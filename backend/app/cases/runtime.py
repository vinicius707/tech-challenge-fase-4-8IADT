"""Runtime injetável para o worker processar Casos (testes e processo RQ)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.cases.service import CaseStore
from app.cases.storage import ArtifactBlobStore, MinioArtifactBlobStore

_case_store: CaseStore | None = None
_blob_store: ArtifactBlobStore | None = None


@dataclass(frozen=True)
class CaseRuntime:
    case_store: CaseStore
    blob_store: ArtifactBlobStore


def configure_case_runtime(
    case_store: CaseStore | None,
    blob_store: ArtifactBlobStore | None,
) -> None:
    global _case_store, _blob_store
    _case_store = case_store
    _blob_store = blob_store


def uses_shared_postgres_store() -> bool:
    """Compose/runtime: MinIO configurado implica stack com Postgres compartilhado."""
    return bool(os.getenv("MINIO_ENDPOINT"))


def build_shared_case_runtime() -> CaseRuntime:
    """Monta CaseStore SQL + blob MinIO para API/worker no Compose."""
    from app.cases.db_store import SqlAlchemyCaseStore

    return CaseRuntime(
        case_store=SqlAlchemyCaseStore(),
        blob_store=MinioArtifactBlobStore(),
    )


def get_case_runtime() -> CaseRuntime | None:
    if _case_store is not None and _blob_store is not None:
        return CaseRuntime(case_store=_case_store, blob_store=_blob_store)
    if uses_shared_postgres_store():
        return build_shared_case_runtime()
    return None
