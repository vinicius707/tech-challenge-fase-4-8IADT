from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FailureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    patient_id: uuid.UUID
    modality: str
    error_summary: str
    attempts: int
    status: str
    created_at: datetime
    updated_at: datetime


class FailureListResponse(BaseModel):
    items: list[FailureResponse] = Field(default_factory=list)
