from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModalityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    modality: str
    status: str
    artifact_id: uuid.UUID | None = None
    provider: str | None = None


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    modality: str
    bucket: str
    object_key: str
    content_sha256: str
    content_type: str


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    level: str
    version: int
    created_at: datetime


class JustificationModalityResponse(BaseModel):
    modality: str
    status: str
    weight: float | None = None
    partial_score: float | None = None
    partial_level: str | None = None
    top_anomalies: list[str] = Field(default_factory=list)


class JustificationResponse(BaseModel):
    narrative: str
    modalities: list[JustificationModalityResponse] = Field(default_factory=list)


class ReprocessRequest(BaseModel):
    """Body opcional: filtra modalidades failed a reprocessar."""

    modalities: list[str] | None = None


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    status: str
    risk_score: float | None = None
    risk_level: str | None = None
    modalities: list[ModalityResponse] = Field(default_factory=list)
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    alerts: list[AlertResponse] = Field(default_factory=list)
    justification: JustificationResponse | None = None
    created_at: datetime
    updated_at: datetime
