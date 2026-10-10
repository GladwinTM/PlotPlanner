from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db import models as m

GoalCategory = Literal[*m.GOAL_CATEGORIES]
GoalStatus = Literal[*m.GOAL_STATUSES]


class MilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    position: int
    due_date: date | None
    completed_at: datetime | None
    source: str


class CheckinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    note: str | None
    minutes: int | None
    created_at: datetime


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    category: str
    target_outcome: str | None
    priority: int
    status: str
    target_date: date | None
    hours_per_week: int | None
    interest_id: UUID | None
    plan_summary: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    milestones: list[MilestoneRead]
    checkins: list[CheckinRead]
    progress_percent: int = Field(0, description="Completed milestones / milestones * 100")
    minutes_logged: int = 0


class GoalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category: GoalCategory = "personal"
    target_outcome: str | None = Field(default=None, max_length=2000)
    priority: int = Field(default=3, ge=1, le=5)
    target_date: date | None = None
    hours_per_week: int | None = Field(default=None, ge=0, le=168)
    interest_id: UUID | None = None


class GoalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category: GoalCategory | None = None
    target_outcome: str | None = Field(default=None, max_length=2000)
    priority: int | None = Field(default=None, ge=1, le=5)
    status: GoalStatus | None = None
    target_date: date | None = None
    hours_per_week: int | None = Field(default=None, ge=0, le=168)
    interest_id: UUID | None = None


class MilestoneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None


class MilestoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    completed: bool | None = None
    position: int | None = Field(default=None, ge=0, le=1000)


class CheckinCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    note: str | None = Field(default=None, max_length=2000)
    minutes: int | None = Field(default=None, ge=0, le=1440)


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    adjustment: str | None = Field(default=None, max_length=1000, description="Optional note, e.g. 'I only have 2 hours a week now'")
