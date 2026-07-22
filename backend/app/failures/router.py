from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import AccessTokenClaims, require_admin
from app.failures.schemas import FailureListResponse, FailureResponse
from app.failures.service import (
    FailureNotFoundError,
    FailureNotOpenError,
    FailureService,
    get_failure_service,
)

router = APIRouter(prefix="/admin/failures", tags=["admin-failures"])


@router.get(
    "",
    response_model=FailureListResponse,
    summary="Lista Falhas de Processamento abertas (DLQ)",
    responses={403: {"description": "Papel sem permissão"}},
)
def list_failures(
    _claims: Annotated[AccessTokenClaims, Depends(require_admin)],
    service: Annotated[FailureService, Depends(get_failure_service)],
) -> FailureListResponse:
    return FailureListResponse(items=service.list_open())


@router.get(
    "/{failure_id}",
    response_model=FailureResponse,
    summary="Detalhe de Falha de Processamento",
    responses={
        403: {"description": "Papel sem permissão"},
        404: {"description": "Falha não encontrada"},
    },
)
def get_failure(
    failure_id: UUID,
    _claims: Annotated[AccessTokenClaims, Depends(require_admin)],
    service: Annotated[FailureService, Depends(get_failure_service)],
) -> FailureResponse:
    try:
        return service.get(failure_id)
    except FailureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Falha de Processamento não encontrada",
        ) from exc


@router.post(
    "/{failure_id}/redrive",
    response_model=FailureResponse,
    summary="Reenfileira job da falha (redrive)",
    responses={
        403: {"description": "Papel sem permissão"},
        404: {"description": "Falha não encontrada"},
        409: {"description": "Falha não está aberta"},
    },
)
def redrive_failure(
    failure_id: UUID,
    claims: Annotated[AccessTokenClaims, Depends(require_admin)],
    service: Annotated[FailureService, Depends(get_failure_service)],
) -> FailureResponse:
    try:
        return service.redrive(failure_id, operator_id=claims.sub)
    except FailureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Falha de Processamento não encontrada",
        ) from exc
    except FailureNotOpenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Falha de Processamento não está aberta",
        ) from exc


@router.post(
    "/{failure_id}/discard",
    response_model=FailureResponse,
    summary="Descarta falha sem reprocessar",
    responses={
        403: {"description": "Papel sem permissão"},
        404: {"description": "Falha não encontrada"},
        409: {"description": "Falha não está aberta"},
    },
)
def discard_failure(
    failure_id: UUID,
    claims: Annotated[AccessTokenClaims, Depends(require_admin)],
    service: Annotated[FailureService, Depends(get_failure_service)],
) -> FailureResponse:
    try:
        return service.discard(failure_id, operator_id=claims.sub)
    except FailureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Falha de Processamento não encontrada",
        ) from exc
    except FailureNotOpenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Falha de Processamento não está aberta",
        ) from exc
