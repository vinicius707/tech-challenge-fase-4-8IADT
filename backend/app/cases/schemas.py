from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModalityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    modality: str
    status: str
    artifact_id: uuid.UUID | None = None


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
    created_at: datetime
    updated_at: datetime
