from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db import models as m


class ResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    provider: str
    channel: str | None
    canonical_url: str
    resource_type: str
    cost_status: str
    duration_seconds: int | None
    published_at: datetime | None
    retrieved_at: datetime
    verification_status: str


class ActivityRead(BaseModel):
    id: UUID
    position: int
    kind: str
    title: str
    instructions: str | None
    estimated_minutes: int | None
    completed: bool
    completed_at: datetime | None
    notes: str | None


class ModuleRead(BaseModel):
    id: UUID
    position: int
    title: str
    description: str | None
    learning_objectives: str | None
    completion_criteria: str | None
    required: bool
    completed: bool
    activities: list[ActivityRead]
    resources: list[ResourceRead]
    resource_query: str | None


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    started_at: datetime
    completed_at: datetime | None


class ProgressRead(BaseModel):
    percent: int = Field(description="Completed required modules / required modules * 100")
    required_modules: int
    completed_required_modules: int
    optional_modules: int
    completed_optional_modules: int
    activities: int
    completed_activities: int


class NextActivityRead(BaseModel):
    module_id: UUID
    module_title: str
    activity_id: UUID
    activity_title: str
    kind: str


class CourseSummary(BaseModel):
    id: UUID
    title: str
    description: str | None
    objective: str | None
    interest_id: UUID | None
    interest_name: str | None
    goal_id: UUID | None
    difficulty: str
    estimated_hours: int | None
    status: str
    error: str | None
    version: int
    previous_version_id: UUID | None
    created_at: datetime
    updated_at: datetime
    enrollment: EnrollmentRead | None
    progress: ProgressRead
    next_activity: NextActivityRead | None
    module_count: int


class CourseDetail(CourseSummary):
    prerequisites: str | None
    focus: str | None
    modules: list[ModuleRead]


class CourseGenerate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    interest_id: UUID | None = None
    goal_id: UUID | None = None
    topic: str | None = Field(default=None, min_length=2, max_length=200, description="Free topic when no interest or goal is selected")
    focus: str | None = Field(default=None, max_length=500)


class CourseRegenerate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    focus: str | None = Field(default=None, max_length=500)


class EnrollmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "paused", "abandoned"]


class ProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    activity_id: UUID
    completed: bool
    notes: str | None = Field(default=None, max_length=4000, description="Project submission or reflection text")


CourseStatus = Literal[*m.COURSE_STATUSES]
