"""Interests and the interest graph.

Integrity rules: deleting an interest removes its relationships (FK cascade)
but keeps related goals and courses, which simply lose the link. A
relationship can only join two interests owned by the same user; this is
enforced here and by composite foreign keys in the database.
"""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import prompts
from app.ai.llm_client import LLMClient
from app.ai.schemas import GraphRelationship, GraphSuggestions, InterestSuggestions
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.db.models import (
    ActivityCompletion, Course, CourseActivity, CourseModule, Enrollment, Goal, Interest, InterestRelationship,
)
from app.schemas.interests import (
    GraphEdge, GraphNode, GraphRead, InterestCreate, InterestUpdate, LayoutUpdate, RelationshipCreate,
    SuggestedConnection, SuggestedInterest, SuggestionsRead,
)
from app.services.context import build_user_context, context_json
from app.services.progress import course_progress

MAX_INTERESTS = 300


async def list_interests(session: AsyncSession, user_id: UUID) -> list[Interest]:
    return list((await session.scalars(
        select(Interest).where(Interest.user_id == user_id).order_by(Interest.priority.desc(), Interest.name)
    )).all())


async def get_interest(session: AsyncSession, user_id: UUID, interest_id: UUID) -> Interest:
    interest = await session.scalar(select(Interest).where(Interest.id == interest_id, Interest.user_id == user_id))
    if interest is None:
        raise NotFoundError("Interest not found")
    return interest


async def find_by_name(session: AsyncSession, user_id: UUID, name: str) -> Interest | None:
    return await session.scalar(
        select(Interest).where(Interest.user_id == user_id, func.lower(Interest.name) == name.strip().lower())
    )


async def _add_relationship(session: AsyncSession, user_id: UUID, source_id: UUID, target_id: UUID, kind: str) -> InterestRelationship | None:
    """Insert unless the same pair (in either direction) already has this type."""
    if source_id == target_id:
        return None
    existing = await session.scalar(
        select(InterestRelationship.id).where(
            InterestRelationship.user_id == user_id,
            InterestRelationship.relationship_type == kind,
            or_(
                (InterestRelationship.source_interest_id == source_id) & (InterestRelationship.target_interest_id == target_id),
                (InterestRelationship.source_interest_id == target_id) & (InterestRelationship.target_interest_id == source_id),
            ),
        )
    )
    if existing:
        return None
    relationship = InterestRelationship(
        user_id=user_id, source_interest_id=source_id, target_interest_id=target_id, relationship_type=kind
    )
    session.add(relationship)
    await session.flush()
    return relationship


async def create_interest(session: AsyncSession, user_id: UUID, payload: InterestCreate) -> Interest:
    if await find_by_name(session, user_id, payload.name):
        raise ConflictError(f'You already have an interest named "{payload.name}"')
    count = await session.scalar(select(func.count()).select_from(Interest).where(Interest.user_id == user_id))
    if count >= MAX_INTERESTS:
        raise BadRequestError(f"You can have at most {MAX_INTERESTS} interests")
    targets = []
    for target_id in payload.connect_to:
        targets.append(await get_interest(session, user_id, target_id))
    interest = Interest(
        user_id=user_id,
        **payload.model_dump(exclude={"connect_to", "relationship_type"}),
    )
    session.add(interest)
    await session.flush()
    for target in targets:
        await _add_relationship(session, user_id, interest.id, target.id, payload.relationship_type)
    await session.commit()
    await session.refresh(interest)
    return interest


async def update_interest(session: AsyncSession, user_id: UUID, interest_id: UUID, payload: InterestUpdate) -> Interest:
    interest = await get_interest(session, user_id, interest_id)
    changes = payload.model_dump(exclude_unset=True)
    for nullable_only in ("name", "interest_type", "node_kind", "priority", "seeks_income"):
        if nullable_only in changes and changes[nullable_only] is None:
            raise BadRequestError(f"{nullable_only} cannot be null", code="validation_error")
    if "name" in changes and changes["name"].lower() != interest.name.lower():
        if await find_by_name(session, user_id, changes["name"]):
            raise ConflictError(f'You already have an interest named "{changes["name"]}"')
    for key, value in changes.items():
        setattr(interest, key, value)
    interest.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(interest)
    return interest


async def delete_interest(session: AsyncSession, user_id: UUID, interest_id: UUID) -> None:
    interest = await get_interest(session, user_id, interest_id)
    await session.delete(interest)
    await session.commit()


async def create_relationship(session: AsyncSession, user_id: UUID, payload: RelationshipCreate) -> InterestRelationship:
    if payload.source_interest_id == payload.target_interest_id:
        raise BadRequestError("An interest cannot be connected to itself")
    await get_interest(session, user_id, payload.source_interest_id)
    await get_interest(session, user_id, payload.target_interest_id)
    try:
        relationship = await _add_relationship(
            session, user_id, payload.source_interest_id, payload.target_interest_id, payload.relationship_type
        )
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("These interests are already connected that way") from exc
    if relationship is None:
        raise ConflictError("These interests are already connected that way")
    await session.commit()
    await session.refresh(relationship)
    return relationship


async def delete_relationship(session: AsyncSession, user_id: UUID, relationship_id: UUID) -> None:
    relationship = await session.scalar(
        select(InterestRelationship).where(InterestRelationship.id == relationship_id, InterestRelationship.user_id == user_id)
    )
    if relationship is None:
        raise NotFoundError("Relationship not found")
    await session.delete(relationship)
    await session.commit()


async def list_relationships(session: AsyncSession, user_id: UUID) -> list[InterestRelationship]:
    return list((await session.scalars(
        select(InterestRelationship).where(InterestRelationship.user_id == user_id).order_by(InterestRelationship.created_at)
    )).all())


async def save_layout(session: AsyncSession, user_id: UUID, payload: LayoutUpdate) -> int:
    ids = [p.id for p in payload.positions]
    interests = {i.id: i for i in (await session.scalars(
        select(Interest).where(Interest.user_id == user_id, Interest.id.in_(ids))
    )).all()}
    for position in payload.positions:
        interest = interests.get(position.id)
        if interest:
            interest.position_x, interest.position_y = position.x, position.y
    await session.commit()
    return len(interests)


async def graph(session: AsyncSession, user_id: UUID) -> GraphRead:
    interests = await list_interests(session, user_id)
    relationships = await list_relationships(session, user_id)

    courses = (await session.execute(
        select(Course.id, Course.interest_id, Enrollment.id)
        .outerjoin(Enrollment, (Enrollment.course_id == Course.id) & (Enrollment.user_id == user_id))
        .where(Course.user_id == user_id, Course.status.in_(["ready", "generating"]), Course.interest_id.is_not(None))
    )).all()
    enrolled = [course_id for course_id, _, enrollment_id in courses if enrollment_id]
    progress = await course_progress(session, user_id, enrolled)
    course_counts: dict[UUID, int] = {}
    progress_values: dict[UUID, list[int]] = {}
    for course_id, interest_id, enrollment_id in courses:
        course_counts[interest_id] = course_counts.get(interest_id, 0) + 1
        if enrollment_id:
            progress_values.setdefault(interest_id, []).append(progress[course_id].percent)

    goal_counts = dict((await session.execute(
        select(Goal.interest_id, func.count()).where(Goal.user_id == user_id, Goal.interest_id.is_not(None)).group_by(Goal.interest_id)
    )).all())
    evidence = dict((await session.execute(
        select(Course.interest_id, func.count())
        .join(CourseModule, CourseModule.course_id == Course.id)
        .join(CourseActivity, CourseActivity.module_id == CourseModule.id)
        .join(ActivityCompletion, (ActivityCompletion.activity_id == CourseActivity.id) & (ActivityCompletion.user_id == user_id))
        .where(Course.user_id == user_id, CourseActivity.kind == "project", Course.interest_id.is_not(None))
        .group_by(Course.interest_id)
    )).all())

    nodes = [
        GraphNode(
            id=i.id, name=i.name, description=i.description, category=i.category, interest_type=i.interest_type,
            node_kind=i.node_kind, priority=i.priority, source=i.source, confidence=i.confidence,
            seeks_income=i.seeks_income,
            position={"x": i.position_x, "y": i.position_y} if i.position_x is not None and i.position_y is not None else None,
            course_count=course_counts.get(i.id, 0),
            course_progress_percent=round(sum(progress_values[i.id]) / len(progress_values[i.id])) if progress_values.get(i.id) else None,
            goal_count=goal_counts.get(i.id, 0),
            evidence_count=evidence.get(i.id, 0),
        )
        for i in interests
    ]
    edges = [
        GraphEdge(id=r.id, source=r.source_interest_id, target=r.target_interest_id, relationship_type=r.relationship_type)
        for r in relationships
    ]
    return GraphRead(nodes=nodes, edges=edges)


def _resolve_relationships(proposed: list[GraphRelationship], by_name: dict[str, Interest]) -> list[tuple[Interest, Interest, GraphRelationship]]:
    """Keep only relationships whose endpoints are existing interests."""
    resolved = []
    for rel in proposed:
        source, target = by_name.get(rel.source.strip().lower()), by_name.get(rel.target.strip().lower())
        if source and target and source.id != target.id:
            resolved.append((source, target, rel))
    return resolved


async def connect_with_ai(session: AsyncSession, llm: LLMClient, user_id: UUID) -> int:
    """Ask the AI for relationships between existing interests and persist the
    valid ones. Used at onboarding completion."""
    interests = await list_interests(session, user_id)
    if len(interests) < 2:
        return 0
    existing = await list_relationships(session, user_id)
    names = {i.id: i.name for i in interests}
    data = {
        "interests": [{"name": i.name, "type": i.interest_type, "kind": i.node_kind} for i in interests],
        "existing_relationships": [
            [names[r.source_interest_id], r.relationship_type, names[r.target_interest_id]] for r in existing
        ],
    }
    result = await llm.complete_structured(
        system=prompts.GRAPH_CONNECTIONS,
        messages=[{"role": "user", "content": prompts.tagged("user_data", context_json(data))}],
        schema=GraphSuggestions,
        max_tokens=2500,
    )
    by_name = {i.name.lower(): i for i in interests}
    created = 0
    for source, target, rel in _resolve_relationships(result.relationships, by_name):
        if await _add_relationship(session, user_id, source.id, target.id, rel.relationship_type):
            created += 1
    await session.commit()
    return created


async def suggest(session: AsyncSession, llm: LLMClient, user_id: UUID) -> SuggestionsRead:
    """AI-proposed interests and connections. Nothing is saved; the user accepts
    suggestions through the normal create endpoints."""
    interests = await list_interests(session, user_id)
    if not interests:
        raise BadRequestError("Add at least one interest before asking for suggestions")
    existing = await list_relationships(session, user_id)
    names = {i.id: i.name for i in interests}
    context = await build_user_context(session, user_id, goals=True)
    context["existing_relationships"] = [
        [names[r.source_interest_id], r.relationship_type, names[r.target_interest_id]] for r in existing
    ]
    result = await llm.complete_structured(
        system=prompts.INTEREST_SUGGESTIONS,
        messages=[{"role": "user", "content": prompts.tagged("user_data", context_json(context))}],
        schema=InterestSuggestions,
        max_tokens=2500,
    )
    by_name = {i.name.lower(): i for i in interests}
    existing_pairs = {frozenset((r.source_interest_id, r.target_interest_id)) for r in existing}
    suggestions = [
        SuggestedInterest(
            name=s.name.strip(), interest_type=s.interest_type, node_kind=s.node_kind,
            connects_to=[by_name[n.strip().lower()].id for n in s.connects_to if n.strip().lower() in by_name],
            relationship_type=s.relationship_type, reason=s.reason,
        )
        for s in result.suggestions
        if s.name.strip().lower() not in by_name
    ]
    connections = [
        SuggestedConnection(source_interest_id=src.id, target_interest_id=tgt.id, relationship_type=rel.relationship_type, reason=rel.reason)
        for src, tgt, rel in _resolve_relationships(result.connections, by_name)
        if frozenset((src.id, tgt.id)) not in existing_pairs
    ]
    return SuggestionsRead(interests=suggestions, connections=connections)
