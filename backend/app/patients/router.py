from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.deps import AccessTokenClaims, get_current_access_claims
from app.patients.schemas import (
    CreatePatientRequest,
    PatientListResponse,
    PatientResponse,
    UpdatePatientRequest,
)
from app.patients.service import PatientService, get_patient_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um Paciente com código pseudônimo",
    responses={401: {"description": "Não autenticado"}},
)
def create_patient(
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[PatientService, Depends(get_patient_service)],
    _payload: CreatePatientRequest | None = None,
) -> PatientResponse:
    return service.create()


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
    },
)
def update_patient(
    patient_id: UUID,
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[PatientService, Depends(get_patient_service)],
    _payload: UpdatePatientRequest | None = None,
) -> PatientResponse:
    patient = service.update(patient_id)
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
