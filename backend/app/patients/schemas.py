from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreatePatientRequest(BaseModel):
    """Corpo opcional nesta fatia; rótulo Fernet entra em T2.7."""

    model_config = ConfigDict(extra="forbid")


class UpdatePatientRequest(BaseModel):
    """PATCH parcial; `code` não é aceito (imutável)."""

    model_config = ConfigDict(extra="forbid")


class PatientResponse(BaseModel):
    id: UUID
    code: str
    has_sensitive_label: bool
    sensitive_label_masked: str | None
    created_at: datetime
    updated_at: datetime


class PatientListResponse(BaseModel):
    items: list[PatientResponse] = Field(default_factory=list)
