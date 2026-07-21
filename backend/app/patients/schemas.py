from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreatePatientRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensitive_label: str | None = None


class UpdatePatientRequest(BaseModel):
    """PATCH parcial; `code` não é aceito (imutável)."""

    model_config = ConfigDict(extra="forbid")

    sensitive_label: Annotated[str | None, Field(default=None)] = None


class PatientResponse(BaseModel):
    id: UUID
    code: str
    has_sensitive_label: bool
    sensitive_label_masked: str | None
    created_at: datetime
    updated_at: datetime


class PatientListResponse(BaseModel):
    items: list[PatientResponse] = Field(default_factory=list)


class SensitiveLabelRevealResponse(BaseModel):
    id: UUID
    code: str
    sensitive_label: str
    revealed_at: datetime
