"""Runtime injetável para o worker processar Casos (testes e processo RQ)."""

from __future__ import annotations

from dataclasses import dataclass

from app.cases.service import CaseStore
from app.cases.storage import ArtifactBlobStore

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


def get_case_runtime() -> CaseRuntime | None:
    if _case_store is None or _blob_store is None:
        return None
    return CaseRuntime(case_store=_case_store, blob_store=_blob_store)
