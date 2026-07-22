from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.auth.deps import AccessTokenClaims, get_current_access_claims
from app.cases.schemas import CaseResponse, ReprocessRequest
from app.cases.service import (
    CaseNotFoundError,
    CaseService,
    IdempotencyConflictError,
    NoFailedModalitiesError,
    PatientNotFoundError,
    VideoModalityExistsError,
    get_case_service,
)
from app.cases.storage import ArtifactStorageError

patients_cases_router = APIRouter(prefix="/patients", tags=["cases"])
cases_router = APIRouter(prefix="/cases", tags=["cases"])


@patients_cases_router.post(
    "/{patient_id}/cases",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria Caso com modalidade vitais (idempotente)",
    responses={
        200: {"description": "Replay idempotente do mesmo Caso"},
        400: {"description": "Idempotency-Key ausente"},
        401: {"description": "Não autenticado"},
        404: {"description": "Paciente não encontrado"},
        409: {"description": "Idempotency-Key reutilizada com conteúdo diferente"},
        503: {"description": "Object store (MinIO) indisponível"},
    },
)
async def create_case(
    patient_id: UUID,
    response: Response,
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[CaseService, Depends(get_case_service)],
    file: Annotated[UploadFile, File(description="CSV de vitais")],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CaseResponse:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header Idempotency-Key é obrigatório",
        )
    content = await file.read()
    content_type = file.content_type or "text/csv"
    filename = file.filename or "vitals.csv"
    try:
        case, created = service.create(
            patient_id=patient_id,
            idempotency_key=idempotency_key.strip(),
            content=content,
            content_type=content_type,
            filename=filename,
        )
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente não encontrado",
        ) from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key já usada com conteúdo diferente",
        ) from exc
    except ArtifactStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Armazenamento de Artefatos indisponível",
        ) from exc

    if not created:
        response.status_code = status.HTTP_200_OK
    return case


@cases_router.get(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Detalhe do Caso",
    responses={
        401: {"description": "Não autenticado"},
        404: {"description": "Caso não encontrado"},
    },
)
def get_case(
    case_id: UUID,
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[CaseService, Depends(get_case_service)],
) -> CaseResponse:
    try:
        return service.get(case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso não encontrado",
        ) from exc


@cases_router.post(
    "/{case_id}/modalities/video",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Anexa modalidade video ao Caso (idempotente)",
    responses={
        200: {"description": "Replay idempotente"},
        400: {"description": "Idempotency-Key ausente"},
        401: {"description": "Não autenticado"},
        404: {"description": "Caso não encontrado"},
        409: {"description": "Conflito de idempotência ou vídeo já anexado"},
        503: {"description": "Object store (MinIO) indisponível"},
    },
)
async def attach_video_modality(
    case_id: UUID,
    response: Response,
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[CaseService, Depends(get_case_service)],
    file: Annotated[UploadFile, File(description="Clip de vídeo")],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CaseResponse:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header Idempotency-Key é obrigatório",
        )
    content = await file.read()
    content_type = file.content_type or "video/x-msvideo"
    filename = file.filename or "video.avi"
    try:
        case, created = service.attach_video(
            case_id,
            idempotency_key=idempotency_key.strip(),
            content=content,
            content_type=content_type,
            filename=filename,
        )
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso não encontrado",
        ) from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key já usada com conteúdo diferente",
        ) from exc
    except VideoModalityExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Caso já possui modalidade video",
        ) from exc
    except ArtifactStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Armazenamento de Artefatos indisponível",
        ) from exc

    if not created:
        response.status_code = status.HTTP_200_OK
    return case


@cases_router.post(
    "/{case_id}/reprocess",
    response_model=CaseResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reprocessa modalidades failed (seletivo)",
    responses={
        401: {"description": "Não autenticado"},
        404: {"description": "Caso não encontrado"},
        409: {"description": "Nenhuma modalidade failed elegível"},
    },
)
def reprocess_case(
    case_id: UUID,
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[CaseService, Depends(get_case_service)],
    body: ReprocessRequest | None = None,
) -> CaseResponse:
    modalities = body.modalities if body is not None else None
    try:
        return service.reprocess(case_id, modalities=modalities)
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso não encontrado",
        ) from exc
    except NoFailedModalitiesError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nenhuma modalidade failed elegível para reprocessamento",
        ) from exc
