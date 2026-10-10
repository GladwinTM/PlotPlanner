from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db import models as m

_NULLABLE_TEXT_FIELDS = (
    "location", "current_occupation", "education_summary", "experience_summary",
    "learning_preferences", "constraints_summary",
)


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    display_name: str
    location: str | None
    current_occupation: str | None
    education_summary: str | None
    experience_summary: str | None
    available_hours_per_week: int | None
    learning_preferences: str | None
    constraints_summary: str | None
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    """Editable profile fields.

    Unknown fields are rejected (not ignored) so a client cannot believe it set
    ``user_id`` or ``onboarding_completed``, which are server-controlled.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=200)
    current_occupation: str | None = Field(default=None, max_length=200)
    education_summary: str | None = Field(default=None, max_length=4000)
    experience_summary: str | None = Field(default=None, max_length=4000)
    available_hours_per_week: int | None = Field(default=None, ge=0, le=168)
    learning_preferences: str | None = Field(default=None, max_length=1000)
    constraints_summary: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _normalize(self) -> "ProfileUpdate":
        if "display_name" in self.model_fields_set and self.display_name is None:
            raise ValueError("display_name cannot be null")
        # Blank optional text means "clear this field".
        for name in _NULLABLE_TEXT_FIELDS:
            if getattr(self, name) == "":
                setattr(self, name, None)
        return self


class FactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    value: str
    detail: str | None
    source: str
    document_id: UUID | None
    confirmed: bool
    created_at: datetime


class FactCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: Literal[*m.FACT_KINDS]
    value: str = Field(min_length=1, max_length=500)
    detail: str | None = Field(default=None, max_length=2000)


class FactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    value: str | None = Field(default=None, min_length=1, max_length=500)
    detail: str | None = Field(default=None, max_length=2000)
    confirmed: bool | None = None
