"""Structured outputs the LLM must return. Anything that fails these models is
rejected before it can touch the database."""
from typing import Literal

from pydantic import BaseModel, Field

from app.db import models as m

InterestType = Literal[*m.INTEREST_TYPES]
NodeKind = Literal[*m.NODE_KINDS]
GoalCategory = Literal[*m.GOAL_CATEGORIES]
RelationshipType = Literal[*m.RELATIONSHIP_TYPES]
FactKind = Literal[*m.FACT_KINDS]
ActivityKind = Literal[*m.ACTIVITY_KINDS]
Difficulty = Literal[*m.DIFFICULTIES]
FitLevel = Literal[*m.FIT_LEVELS]
EarningKind = Literal[*m.EARNING_PLAN_KINDS]


# --- Onboarding -------------------------------------------------------------

class ProfileDraft(BaseModel):
    display_name: str | None = Field(None, max_length=120)
    location: str | None = Field(None, max_length=200)
    current_occupation: str | None = Field(None, max_length=200)
    education_summary: str | None = Field(None, max_length=1000)
    experience_summary: str | None = Field(None, max_length=2000)
    available_hours_per_week: int | None = Field(None, ge=0, le=168)
    learning_preferences: str | None = Field(None, max_length=1000)
    constraints_summary: str | None = Field(None, max_length=2000)


class InterestDraft(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(None, max_length=500)
    interest_type: InterestType
    node_kind: NodeKind
    category: str | None = Field(None, max_length=80)
    priority: int = Field(ge=1, le=5)
    seeks_income: bool
    parent: str | None = Field(None, max_length=120, description="Name of a broader interest this belongs to, if the user implied one")


class GoalDraft(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: GoalCategory
    target_outcome: str | None = Field(None, max_length=500)
    priority: int = Field(ge=1, le=5)
    hours_per_week: int | None = Field(None, ge=0, le=168)


class OnboardingTurn(BaseModel):
    reply: str = Field(min_length=1, max_length=1200, description="Next conversational message to the user")
    profile: ProfileDraft
    interests: list[InterestDraft] = Field(max_length=15)
    goals: list[GoalDraft] = Field(max_length=8)
    skills: list[str] = Field(max_length=20)
    ready_to_finish: bool


class GraphRelationship(BaseModel):
    source: str = Field(max_length=120)
    target: str = Field(max_length=120)
    relationship_type: RelationshipType
    reason: str = Field(max_length=300)


class GraphSuggestions(BaseModel):
    relationships: list[GraphRelationship] = Field(max_length=25)


class InterestSuggestion(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    interest_type: InterestType
    node_kind: NodeKind
    connects_to: list[str] = Field(max_length=4)
    relationship_type: RelationshipType
    reason: str = Field(max_length=300)


class InterestSuggestions(BaseModel):
    suggestions: list[InterestSuggestion] = Field(max_length=8)
    connections: list[GraphRelationship] = Field(max_length=10)


# --- Goals ------------------------------------------------------------------

class MilestoneDraft(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(None, max_length=800)
    week_offset: int | None = Field(None, ge=0, le=104, description="Suggested week to finish, counted from now")


class GoalPlan(BaseModel):
    plan_summary: str = Field(max_length=1500)
    milestones: list[MilestoneDraft] = Field(min_length=2, max_length=10)


# --- Courses ----------------------------------------------------------------

class ActivityDraft(BaseModel):
    kind: ActivityKind
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(max_length=1500)
    estimated_minutes: int = Field(ge=5, le=600)


class DocumentationLink(BaseModel):
    title: str = Field(max_length=200)
    url: str = Field(max_length=500)


class ModuleDraft(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=1000)
    learning_objectives: str = Field(max_length=1000)
    completion_criteria: str = Field(max_length=600)
    required: bool
    activities: list[ActivityDraft] = Field(min_length=1, max_length=5)
    video_search_query: str = Field(min_length=3, max_length=120)
    official_documentation: list[DocumentationLink] = Field(max_length=2)


class CourseOutline(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=1500)
    objective: str = Field(max_length=800)
    difficulty: Difficulty
    estimated_hours: int = Field(ge=1, le=500)
    prerequisites: str = Field(max_length=800)
    modules: list[ModuleDraft] = Field(min_length=2, max_length=7)


# --- Opportunities ----------------------------------------------------------

class FitAssessment(BaseModel):
    listing_number: int
    fit_level: FitLevel
    reason: str = Field(max_length=400)


class FitAssessments(BaseModel):
    assessments: list[FitAssessment] = Field(max_length=15)


class EarningPlanDraft(BaseModel):
    title: str = Field(max_length=200)
    kind: EarningKind
    readiness: str = Field(max_length=600, description="Honest assessment of whether the user can start now or needs preparation first")
    offer: str = Field(max_length=1000)
    who_pays: str = Field(max_length=1000)
    what_you_need: list[str] = Field(max_length=8)
    portfolio: str = Field(max_length=1000)
    find_customers: list[str] = Field(max_length=8)
    test_demand: str = Field(max_length=1000)
    costs_and_pricing: str = Field(max_length=1200)
    first_week: list[str] = Field(min_length=3, max_length=7)
    evaluate_results: str = Field(max_length=1000)
    improve_next: str = Field(max_length=1000)
    cautions: list[str] = Field(max_length=5)


# --- Documents --------------------------------------------------------------

class ExtractedFact(BaseModel):
    kind: FactKind
    value: str = Field(min_length=1, max_length=300)
    detail: str | None = Field(None, max_length=600)


class DocumentExtraction(BaseModel):
    is_resume: bool
    summary: str = Field(max_length=800)
    facts: list[ExtractedFact] = Field(max_length=40)
