from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db import models as m


class OpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_type: str
    title: str
    company: str | None
    description: str | None
    source: str
    canonical_url: str
    location: str | None
    employment_type: str | None
    compensation_min: float | None
    compensation_max: float | None
    currency: str | None
    compensation_text: str | None
    compensation_basis: str | None
    requirements: str | None
    published_at: datetime | None
    closing_at: datetime | None
    retrieved_at: datetime
    fit_level: str | None
    fit_reason: str | None
    status: str
    notes: str | None


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=2, max_length=120)
    location: str | None = Field(default=None, max_length=100)
    remote_only: bool = True
    assess_fit: bool = True


class SearchResponse(BaseModel):
    results: list[OpportunityRead]
    providers: list[str]
    provider_errors: dict[str, str]
    fit_assessed: bool
    fit_note: str | None
    attribution: list[dict[str, str]]


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal[*m.OPPORTUNITY_STATUSES]
    notes: str | None = Field(default=None, max_length=4000)


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    interest_id: UUID | None = None
    kind: Literal[*m.EARNING_PLAN_KINDS] | None = None
    focus: str | None = Field(default=None, max_length=500)


class EarningPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    interest_id: UUID | None
    title: str
    kind: str
    plan: dict
    created_at: datetime


class SalaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: str = Field(min_length=2, max_length=120)
    location: str | None = Field(default=None, max_length=100)
    remote_only: bool = False


class SalaryGroup(BaseModel):
    currency: str
    period: str
    basis: str
    sample_size: int
    low: float
    median: float
    high: float


class SalaryEvidence(BaseModel):
    title: str
    company: str | None
    location: str | None
    compensation_text: str
    basis: str
    source: str
    url: str
    retrieved_at: datetime


class SalaryResponse(BaseModel):
    role: str
    listings_checked: int
    groups: list[SalaryGroup]
    evidence: list[SalaryEvidence]
    note: str
