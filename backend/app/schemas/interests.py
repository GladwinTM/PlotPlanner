from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db import models as m

InterestType = Literal[*m.INTEREST_TYPES]
NodeKind = Literal[*m.NODE_KINDS]
RelationshipType = Literal[*m.RELATIONSHIP_TYPES]


class InterestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    category: str | None
    interest_type: str
    node_kind: str
    priority: int
    source: str
    confidence: float | None
    seeks_income: bool
    position_x: float | None
    position_y: float | None
    created_at: datetime
    updated_at: datetime


class InterestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=80)
    interest_type: InterestType = "personal"
    node_kind: NodeKind = "secondary"
    priority: int = Field(default=3, ge=1, le=5)
    seeks_income: bool = False
    position_x: float | None = None
    position_y: float | None = None
    connect_to: list[UUID] = Field(default_factory=list, max_length=10)
    relationship_type: RelationshipType = "related_to"
    source: Literal["manual", "suggestion", "chat"] = "manual"


class InterestUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=80)
    interest_type: InterestType | None = None
    node_kind: NodeKind | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    seeks_income: bool | None = None


class RelationshipCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_interest_id: UUID
    target_interest_id: UUID
    relationship_type: RelationshipType = "related_to"


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_interest_id: UUID
    target_interest_id: UUID
    relationship_type: str
    created_at: datetime


class NodePosition(BaseModel):
    id: UUID
    x: float = Field(ge=-100_000, le=100_000)
    y: float = Field(ge=-100_000, le=100_000)


class LayoutUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    positions: list[NodePosition] = Field(max_length=500)


class GraphNode(BaseModel):
    id: UUID
    name: str
    description: str | None
    category: str | None
    interest_type: str
    node_kind: str
    priority: int
    source: str
    confidence: float | None
    seeks_income: bool
    position: dict[str, float] | None
    course_count: int
    course_progress_percent: int | None = Field(description="Average completion of enrolled courses for this interest, from completion records")
    goal_count: int
    evidence_count: int = Field(description="Completed project activities in courses for this interest")


class GraphEdge(BaseModel):
    id: UUID
    source: UUID
    target: UUID
    relationship_type: str


class GraphRead(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class SuggestedInterest(BaseModel):
    name: str
    interest_type: str
    node_kind: str
    connects_to: list[UUID]
    relationship_type: str
    reason: str


class SuggestedConnection(BaseModel):
    source_interest_id: UUID
    target_interest_id: UUID
    relationship_type: str
    reason: str


class SuggestionsRead(BaseModel):
    interests: list[SuggestedInterest]
    connections: list[SuggestedConnection]
    generated_by: Literal["ai"] = "ai"
