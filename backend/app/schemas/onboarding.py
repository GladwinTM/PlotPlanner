from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.schemas import GoalDraft, InterestDraft, ProfileDraft


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    meta: dict
    created_at: datetime


class OnboardingDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    profile: ProfileDraft = Field(default_factory=ProfileDraft)
    interests: list[InterestDraft] = Field(default_factory=list, max_length=40)
    goals: list[GoalDraft] = Field(default_factory=list, max_length=15)
    skills: list[str] = Field(default_factory=list, max_length=60)


class OnboardingStatus(BaseModel):
    completed: bool
    conversation_id: UUID | None
    messages: list[MessageRead]
    draft: OnboardingDraft
    ready_to_finish: bool
    awaiting_reply: bool = Field(description="True when the last user message has no assistant reply (e.g. the AI call failed)")
    ai_configured: bool


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(max_length=4000)


class InputAssessment(BaseModel):
    kind: str = Field(description="answer | unsure | unusable")
    text: str


class TurnResponse(BaseModel):
    status: OnboardingStatus
    assessment: InputAssessment


class CompleteResponse(BaseModel):
    interests_created: int
    goals_created: int
    relationships_created: int
    courses_started: list[UUID]
    warnings: list[str]
