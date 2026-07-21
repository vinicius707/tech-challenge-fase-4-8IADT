from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.deps import AccessTokenClaims, get_current_access_claims
from app.patients.crypto import PiiKeyUnavailableError
from app.patients.schemas import (
    CreatePatientRequest,
    PatientListResponse,
    PatientResponse,
    SensitiveLabelRevealResponse,
    UpdatePatientRequest,
)
from app.patients.service import (
    PatientNotFoundError,
    PatientService,
    SensitiveLabelUnavailableError,
    get_patient_service,
)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um Paciente com código pseudônimo",
    responses={
        401: {"description": "Não autenticado"},
        503: {"description": "Chave PII indisponível"},
    },
)
def create_patient(
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[PatientService, Depends(get_patient_service)],
    payload: CreatePatientRequest | None = None,
) -> PatientResponse:
    body = payload or CreatePatientRequest()
    try:
        return service.create(sensitive_label=body.sensitive_label)
    except PiiKeyUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Criptografia de Rótulo Sensível indisponível",
        ) from exc


@router.get(
    "",
    response_model=PatientListResponse,
    summary="Lista Pacientes com rótulo mascarado",
    responses={401: {"description": "Não autenticado"}},
)
def list_patients(
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientListResponse:
    return PatientListResponse(items=service.list_patients())


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Obtém um Paciente com rótulo mascarado",
    responses={
        401: {"description": "Não autenticado"},
        404: {"description": "Paciente não encontrado"},
    },
)
def get_patient(
    patient_id: UUID,
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientResponse:
    patient = service.get(patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente não encontrado",
        )
    return patient


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Atualiza campos mutáveis do Paciente",
    responses={
        401: {"description": "Não autenticado"},
        404: {"description": "Paciente não encontrado"},
        503: {"description": "Chave PII indisponível"},
    },
)
def update_patient(
    patient_id: UUID,
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[PatientService, Depends(get_patient_service)],
    payload: UpdatePatientRequest | None = None,
) -> PatientResponse:
    body = payload or UpdatePatientRequest()
    update_label = (
        payload is not None and "sensitive_label" in payload.model_fields_set
    )
    try:
        patient = service.update(
            patient_id,
            sensitive_label=body.sensitive_label,
            update_sensitive_label=update_label,
        )
    except PiiKeyUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Criptografia de Rótulo Sensível indisponível",
        ) from exc
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente não encontrado",
        )
    return patient


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um Paciente",
    responses={
        401: {"description": "Não autenticado"},
        404: {"description": "Paciente não encontrado"},
    },
)
def delete_patient(
    patient_id: UUID,
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> Response:
    deleted = service.delete(patient_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente não encontrado",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{patient_id}/sensitive-label/reveal",
    response_model=SensitiveLabelRevealResponse,
    summary="Revela o Rótulo Sensível e registra auditoria",
    responses={
        401: {"description": "Não autenticado"},
        404: {"description": "Paciente ou rótulo indisponível"},
        503: {"description": "Chave PII indisponível"},
    },
)
def reveal_sensitive_label(
    patient_id: UUID,
    claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> SensitiveLabelRevealResponse:
    try:
        return service.reveal(patient_id, operator_id=claims.sub)
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente não encontrado",
        ) from exc
    except SensitiveLabelUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rótulo Sensível não disponível",
        ) from exc
    except PiiKeyUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Criptografia de Rótulo Sensível indisponível",
        ) from exc
