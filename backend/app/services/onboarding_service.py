"""Conversational onboarding.

The conversation and an extracted *draft* (profile fields, interests, goals,
skills) live in the user's single onboarding conversation. Nothing in the
draft touches the real profile until the user reviews it and calls
``complete``; malformed AI output is rejected by the schema and never
reaches the draft.
"""
import logging
import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.ai import prompts
from app.ai.llm_client import BACKGROUND_RATE_LIMIT_WAIT, LLMClient
from app.ai.schemas import OnboardingTurn
from app.core.exceptions import AppError, BadRequestError, ConflictError
from app.core.security import AuthenticatedUser
from app.db.models import Conversation, Course, Goal, Interest, Message, Profile, ProfileFact
from app.schemas.onboarding import CompleteResponse, InputAssessment, MessageRead, OnboardingDraft, OnboardingStatus
from app.services import goal_service, interest_service
from app.services.context import context_json
from app.services.profile_service import get_or_create_profile

logger = logging.getLogger(__name__)

HISTORY_MESSAGES = 30
INITIAL_COURSES = 2
INITIAL_GOAL_PLANS = 3

OPENER = (
    "Let's start with what you're doing right now. "
    "What do you spend most of your time on (work, study, something else), and what would you like to explore next?"
)
UNUSABLE_REPLY = "I didn't quite catch that. Could you tell me a little more in your own words? A sentence or two is plenty."

_UNSURE = re.compile(
    r"^\s*(i\s*(really\s*)?(don'?t|do not|dont)\s*know|idk|not sure|no idea|dunno|unsure|i'?m not sure|nothing really|"
    r"no clue|hmm+)\b",
    re.IGNORECASE,
)


def validate_inputs(text: str) -> InputAssessment:
    """Classify a user's onboarding answer without rejecting personal responses.

    - Empty input is a client error (nothing to save).
    - "I don't know"-style answers are valid; the AI is told to ask something simpler.
    - Input with no letters or digits at all (e.g. "???", "...") is unusable;
      it is saved but a clarifying question is asked without calling the AI.
    - Everything else is a normal answer and is preserved verbatim.
    """
    cleaned = text.strip()
    if not cleaned:
        raise BadRequestError("Please type a response before sending.", code="empty_response")
    if not re.search(r"[^\W_]", cleaned):
        return InputAssessment(kind="unusable", text=cleaned)
    if _UNSURE.match(cleaned) and len(cleaned) < 60:
        return InputAssessment(kind="unsure", text=cleaned)
    return InputAssessment(kind="answer", text=cleaned)


def merge_drafts(previous: OnboardingDraft, extracted: OnboardingTurn) -> OnboardingDraft:
    """Combine the AI's updated draft with the previous one. Items the AI
    dropped are kept (the user removes things during review, not the model)."""
    profile = previous.profile.model_copy(
        update={k: v for k, v in extracted.profile.model_dump().items() if v not in (None, "")}
    )
    interests = {i.name.strip().lower(): i for i in previous.interests}
    for interest in extracted.interests:
        interests[interest.name.strip().lower()] = interest
    goals = {g.title.strip().lower(): g for g in previous.goals}
    for goal in extracted.goals:
        goals[goal.title.strip().lower()] = goal
    skills = {s.strip().lower(): s.strip() for s in previous.skills if s.strip()}
    for skill in extracted.skills:
        if skill.strip():
            skills.setdefault(skill.strip().lower(), skill.strip()[:120])
    return OnboardingDraft(
        profile=profile, interests=list(interests.values())[:40], goals=list(goals.values())[:15], skills=list(skills.values())[:60]
    )


async def _conversation(session: AsyncSession, user_id: UUID) -> Conversation | None:
    return await session.scalar(
        select(Conversation).options(selectinload(Conversation.messages))
        .where(Conversation.user_id == user_id, Conversation.kind == "onboarding")
        .execution_options(populate_existing=True)
    )


def _draft(conversation: Conversation | None) -> OnboardingDraft:
    if conversation and conversation.state.get("draft"):
        return OnboardingDraft.model_validate(conversation.state["draft"])
    return OnboardingDraft()


async def status(session: AsyncSession, user: AuthenticatedUser, llm: LLMClient) -> OnboardingStatus:
    profile = await get_or_create_profile(session, user)
    conversation = await _conversation(session, user.id)
    messages = conversation.messages if conversation else []
    return OnboardingStatus(
        completed=profile.onboarding_completed,
        conversation_id=conversation.id if conversation else None,
        messages=[MessageRead.model_validate(m) for m in messages],
        draft=_draft(conversation),
        ready_to_finish=bool(conversation and conversation.state.get("ready_to_finish")),
        awaiting_reply=bool(messages and messages[-1].role == "user"),
        ai_configured=llm.configured,
    )


async def start(session: AsyncSession, user: AuthenticatedUser, llm: LLMClient) -> OnboardingStatus:
    await get_or_create_profile(session, user)
    conversation = await _conversation(session, user.id)
    if conversation is None:
        conversation = Conversation(user_id=user.id, kind="onboarding", title="Onboarding", state={})
        session.add(conversation)
        await session.flush()
        session.add(Message(conversation_id=conversation.id, user_id=user.id, role="assistant", content=OPENER, meta={"scripted": True}))
        await session.commit()
    return await status(session, user, llm)


async def _reply(session: AsyncSession, llm: LLMClient, user: AuthenticatedUser, conversation: Conversation, assessment: InputAssessment) -> None:
    if assessment.kind == "unusable":
        session.add(Message(conversation_id=conversation.id, user_id=user.id, role="assistant", content=UNUSABLE_REPLY, meta={"scripted": True}))
        await session.commit()
        return
    draft = _draft(conversation)
    profile = await session.scalar(select(Profile).where(Profile.user_id == user.id))
    data = {"current_draft": draft.model_dump(exclude_none=True), "known_name": profile.display_name if profile else None}
    if assessment.kind == "unsure":
        data["note"] = "The user is unsure about the last question. Ask a simpler, exploratory question instead."
    history = [{"role": m.role, "content": m.content} for m in conversation.messages[-HISTORY_MESSAGES:]]
    turn = await llm.complete_structured(
        system=prompts.ONBOARDING,
        messages=[{"role": "user", "content": prompts.tagged("user_data", context_json(data))}, *history],
        schema=OnboardingTurn,
        max_tokens=3000,
    )
    merged = merge_drafts(draft, turn)
    conversation.state = {**conversation.state, "draft": merged.model_dump(), "ready_to_finish": turn.ready_to_finish}
    conversation.updated_at = datetime.now(UTC)
    session.add(Message(conversation_id=conversation.id, user_id=user.id, role="assistant", content=turn.reply, meta={}))
    await session.commit()


async def turn(session: AsyncSession, llm: LLMClient, user: AuthenticatedUser, text: str) -> tuple[OnboardingStatus, InputAssessment]:
    assessment = validate_inputs(text)
    conversation = await _conversation(session, user.id)
    if conversation is None:
        await start(session, user, llm)
        conversation = await _conversation(session, user.id)
    if conversation.messages and conversation.messages[-1].role == "user":
        raise ConflictError("The previous message is still waiting for a reply. Retry it first.")
    # The user's words are saved before the AI call so a provider failure never loses them.
    session.add(Message(conversation_id=conversation.id, user_id=user.id, role="user", content=assessment.text, meta={"assessment": assessment.kind}))
    await session.commit()
    conversation = await _conversation(session, user.id)
    await _reply(session, llm, user, conversation, assessment)
    return await status(session, user, llm), assessment


async def retry(session: AsyncSession, llm: LLMClient, user: AuthenticatedUser) -> OnboardingStatus:
    conversation = await _conversation(session, user.id)
    if not conversation or not conversation.messages or conversation.messages[-1].role != "user":
        raise ConflictError("There is no message waiting for a reply")
    last = conversation.messages[-1]
    await _reply(session, llm, user, conversation, InputAssessment(kind=last.meta.get("assessment", "answer"), text=last.content))
    return await status(session, user, llm)


async def save_draft(session: AsyncSession, user: AuthenticatedUser, llm: LLMClient, draft: OnboardingDraft) -> OnboardingStatus:
    await start(session, user, llm)
    conversation = await _conversation(session, user.id)
    conversation.state = {**conversation.state, "draft": draft.model_dump()}
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    return await status(session, user, llm)


async def skip(session: AsyncSession, user: AuthenticatedUser) -> None:
    profile = await get_or_create_profile(session, user)
    profile.onboarding_completed = True
    profile.updated_at = datetime.now(UTC)
    await session.commit()


async def complete(session: AsyncSession, llm: LLMClient, user: AuthenticatedUser, draft: OnboardingDraft) -> tuple[CompleteResponse, list[UUID], list[UUID]]:
    """Persist the reviewed draft. Returns the response plus goal ids and
    course ids whose AI work should continue in the background."""
    if not draft.interests and not draft.goals:
        raise BadRequestError("Add at least one interest or goal before finishing")
    profile = await get_or_create_profile(session, user)

    for key, value in draft.profile.model_dump().items():
        if value not in (None, ""):
            setattr(profile, key, value)
    profile.updated_at = datetime.now(UTC)

    existing_facts = {
        v.lower() for v in (await session.scalars(
            select(ProfileFact.value).where(ProfileFact.user_id == user.id, ProfileFact.kind == "skill")
        )).all()
    }
    for skill in draft.skills:
        if skill.strip() and skill.strip().lower() not in existing_facts:
            existing_facts.add(skill.strip().lower())
            session.add(ProfileFact(user_id=user.id, kind="skill", value=skill.strip()[:500], source="onboarding", confirmed=True))

    by_name: dict[str, Interest] = {}
    interests_created = 0
    for item in draft.interests:
        key = item.name.strip().lower()
        interest = by_name.get(key) or await interest_service.find_by_name(session, user.id, item.name)
        if interest is None:
            interest = Interest(
                user_id=user.id, name=item.name.strip(), description=item.description, category=item.category,
                interest_type=item.interest_type, node_kind=item.node_kind, priority=item.priority,
                seeks_income=item.seeks_income, source="onboarding",
            )
            session.add(interest)
            await session.flush()
            interests_created += 1
        by_name[key] = interest
    relationships_created = 0
    for item in draft.interests:
        parent = by_name.get((item.parent or "").strip().lower())
        child = by_name[item.name.strip().lower()]
        if parent and parent.id != child.id:
            if await interest_service._add_relationship(session, user.id, child.id, parent.id, "part_of"):
                relationships_created += 1

    existing_goals = {t.lower() for t in (await session.scalars(select(Goal.title).where(Goal.user_id == user.id))).all()}
    new_goals: list[Goal] = []
    for item in draft.goals:
        if item.title.strip().lower() in existing_goals:
            continue
        existing_goals.add(item.title.strip().lower())
        goal = Goal(
            user_id=user.id, title=item.title.strip(), category=item.category, target_outcome=item.target_outcome,
            priority=item.priority, hours_per_week=item.hours_per_week,
        )
        session.add(goal)
        new_goals.append(goal)

    profile.onboarding_completed = True
    conversation = await _conversation(session, user.id)
    if conversation:
        conversation.state = {**conversation.state, "draft": draft.model_dump(), "completed_at": datetime.now(UTC).isoformat()}
    await session.flush()
    # Plain values captured before AI calls, whose failure rolls back and expires ORM objects.
    goal_ids = [goal.id for goal in sorted(new_goals, key=lambda g: -g.priority)[:INITIAL_GOAL_PLANS]]
    candidates = [
        (interest.id, interest.name)
        for interest in sorted([i for i in by_name.values() if i.node_kind != "skill"], key=lambda i: (-i.priority, i.node_kind != "main"))
    ][:INITIAL_COURSES]
    goals_created = len(new_goals)
    await session.commit()

    warnings: list[str] = []
    if not llm.configured:
        warnings.append("AI is not configured, so connections, plans and pathways were not generated.")
        response = CompleteResponse(
            interests_created=interests_created, goals_created=goals_created, relationships_created=relationships_created,
            courses_started=[], warnings=warnings,
        )
        return response, [], []
    try:
        relationships_created += await interest_service.connect_with_ai(session, llm, user.id)
    except AppError as exc:
        await session.rollback()
        warnings.append(f"Connections between interests could not be suggested: {exc.message}")

    course_ids: list[UUID] = []
    for interest_id, name in candidates:
        has_course = await session.scalar(
            select(func.count()).select_from(Course).where(Course.user_id == user.id, Course.interest_id == interest_id, Course.status != "archived")
        )
        if not has_course:
            course = Course(user_id=user.id, interest_id=interest_id, title=name, status="generating")
            session.add(course)
            await session.flush()
            course_ids.append(course.id)
    await session.commit()

    response = CompleteResponse(
        interests_created=interests_created, goals_created=goals_created, relationships_created=relationships_created,
        courses_started=course_ids, warnings=warnings,
    )
    return response, goal_ids, course_ids


async def run_initial_goal_plans(session_factory: async_sessionmaker, llm: LLMClient, user_id: UUID, goal_ids: list[UUID]) -> None:
    for goal_id in goal_ids:
        async with session_factory() as session:
            try:
                await goal_service.generate_plan(session, llm, user_id, goal_id, rate_limit_wait=BACKGROUND_RATE_LIMIT_WAIT)
            except AppError as exc:
                logger.warning("initial goal plan failed: %s", exc.code)
