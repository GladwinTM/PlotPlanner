from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai import prompts
from app.ai.llm_client import INTERACTIVE_RATE_LIMIT_WAIT, LLMClient
from app.ai.schemas import GoalPlan
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models import Goal, GoalCheckin, GoalMilestone, Interest
from app.schemas.goals import CheckinCreate, GoalCreate, GoalRead, GoalUpdate, MilestoneCreate, MilestoneUpdate
from app.services.context import build_user_context, context_json

MAX_GOALS = 100


def to_read(goal: Goal) -> GoalRead:
    read = GoalRead.model_validate(goal)
    total = len(goal.milestones)
    done = sum(1 for milestone in goal.milestones if milestone.completed_at)
    read.progress_percent = round(done / total * 100) if total else 0
    read.minutes_logged = sum(checkin.minutes or 0 for checkin in goal.checkins)
    return read


def _with_children():
    return (selectinload(Goal.milestones), selectinload(Goal.checkins))


async def list_goals(session: AsyncSession, user_id: UUID, status: str | None = None) -> list[Goal]:
    query = select(Goal).options(*_with_children()).where(Goal.user_id == user_id)
    if status:
        query = query.where(Goal.status == status)
    return list((await session.scalars(query.order_by(Goal.priority.desc(), Goal.created_at))).all())


async def get_goal(session: AsyncSession, user_id: UUID, goal_id: UUID) -> Goal:
    goal = await session.scalar(
        select(Goal).options(*_with_children()).where(Goal.id == goal_id, Goal.user_id == user_id)
        .execution_options(populate_existing=True)
    )
    if goal is None:
        raise NotFoundError("Goal not found")
    return goal


async def _check_interest(session: AsyncSession, user_id: UUID, interest_id: UUID | None) -> None:
    if interest_id and not await session.scalar(select(Interest.id).where(Interest.id == interest_id, Interest.user_id == user_id)):
        raise NotFoundError("Interest not found")


async def create_goal(session: AsyncSession, user_id: UUID, payload: GoalCreate) -> Goal:
    await _check_interest(session, user_id, payload.interest_id)
    count = len((await session.scalars(select(Goal.id).where(Goal.user_id == user_id))).all())
    if count >= MAX_GOALS:
        raise BadRequestError(f"You can have at most {MAX_GOALS} goals")
    goal = Goal(user_id=user_id, **payload.model_dump())
    session.add(goal)
    await session.commit()
    return await get_goal(session, user_id, goal.id)


async def update_goal(session: AsyncSession, user_id: UUID, goal_id: UUID, payload: GoalUpdate) -> Goal:
    goal = await get_goal(session, user_id, goal_id)
    changes = payload.model_dump(exclude_unset=True)
    for required in ("title", "category", "priority", "status"):
        if required in changes and changes[required] is None:
            raise BadRequestError(f"{required} cannot be null", code="validation_error")
    if "interest_id" in changes:
        await _check_interest(session, user_id, changes["interest_id"])
    if changes.get("status") == "completed" and goal.status != "completed":
        goal.completed_at = datetime.now(UTC)
    elif "status" in changes and changes["status"] != "completed":
        goal.completed_at = None
    for key, value in changes.items():
        setattr(goal, key, value)
    goal.updated_at = datetime.now(UTC)
    await session.commit()
    return await get_goal(session, user_id, goal_id)


async def delete_goal(session: AsyncSession, user_id: UUID, goal_id: UUID) -> None:
    goal = await get_goal(session, user_id, goal_id)
    await session.delete(goal)
    await session.commit()


async def add_milestone(session: AsyncSession, user_id: UUID, goal_id: UUID, payload: MilestoneCreate) -> Goal:
    goal = await get_goal(session, user_id, goal_id)
    position = max((m.position for m in goal.milestones), default=-1) + 1
    session.add(GoalMilestone(goal_id=goal.id, user_id=user_id, position=position, source="manual", **payload.model_dump()))
    goal.updated_at = datetime.now(UTC)
    await session.commit()
    return await get_goal(session, user_id, goal_id)


async def _get_milestone(session: AsyncSession, user_id: UUID, goal_id: UUID, milestone_id: UUID) -> GoalMilestone:
    milestone = await session.scalar(
        select(GoalMilestone).where(
            GoalMilestone.id == milestone_id, GoalMilestone.goal_id == goal_id, GoalMilestone.user_id == user_id
        )
    )
    if milestone is None:
        raise NotFoundError("Milestone not found")
    return milestone


async def update_milestone(session: AsyncSession, user_id: UUID, goal_id: UUID, milestone_id: UUID, payload: MilestoneUpdate) -> Goal:
    milestone = await _get_milestone(session, user_id, goal_id, milestone_id)
    changes = payload.model_dump(exclude_unset=True)
    if "completed" in changes:
        completed = changes.pop("completed")
        if completed and not milestone.completed_at:
            milestone.completed_at = datetime.now(UTC)
        elif completed is False:
            milestone.completed_at = None
    if "title" in changes and changes["title"] is None:
        raise BadRequestError("title cannot be null", code="validation_error")
    for key, value in changes.items():
        setattr(milestone, key, value)
    await session.commit()
    return await get_goal(session, user_id, goal_id)


async def delete_milestone(session: AsyncSession, user_id: UUID, goal_id: UUID, milestone_id: UUID) -> Goal:
    milestone = await _get_milestone(session, user_id, goal_id, milestone_id)
    await session.delete(milestone)
    await session.commit()
    return await get_goal(session, user_id, goal_id)


async def add_checkin(session: AsyncSession, user_id: UUID, goal_id: UUID, payload: CheckinCreate) -> Goal:
    goal = await get_goal(session, user_id, goal_id)
    if not payload.note and payload.minutes is None:
        raise BadRequestError("Add a note or the minutes you spent")
    session.add(GoalCheckin(goal_id=goal.id, user_id=user_id, **payload.model_dump()))
    await session.commit()
    return await get_goal(session, user_id, goal_id)


async def generate_plan(
    session: AsyncSession, llm: LLMClient, user_id: UUID, goal_id: UUID, adjustment: str | None = None,
    *, rate_limit_wait: float = INTERACTIVE_RATE_LIMIT_WAIT,
) -> Goal:
    """Replace the goal's open AI milestones with a fresh plan. Completed
    milestones and milestones the user wrote themselves are kept."""
    goal = await get_goal(session, user_id, goal_id)
    context = await build_user_context(session, user_id, goals=False, interests=False)
    context["goal"] = {
        "title": goal.title, "category": goal.category, "description": goal.description,
        "target_outcome": goal.target_outcome, "hours_per_week": goal.hours_per_week,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
        "already_completed_milestones": [m.title for m in goal.milestones if m.completed_at],
        "user_written_milestones": [m.title for m in goal.milestones if m.source == "manual" and not m.completed_at],
    }
    context["today"] = date.today().isoformat()
    if adjustment:
        context["requested_adjustment"] = adjustment
    plan = await llm.complete_structured(
        system=prompts.GOAL_PLAN,
        messages=[{"role": "user", "content": prompts.tagged("user_data", context_json(context))}],
        schema=GoalPlan,
        max_tokens=2500,
        rate_limit_wait=rate_limit_wait,
    )
    for milestone in list(goal.milestones):
        if milestone.source == "ai" and not milestone.completed_at:
            goal.milestones.remove(milestone)
    await session.flush()
    start = max((m.position for m in goal.milestones if m.completed_at or m.source == "manual"), default=-1) + 1
    today = date.today()
    for offset, draft in enumerate(plan.milestones):
        session.add(GoalMilestone(
            goal_id=goal.id, user_id=user_id, title=draft.title, description=draft.description,
            position=start + offset, source="ai",
            due_date=today + timedelta(weeks=draft.week_offset) if draft.week_offset else None,
        ))
    goal.plan_summary = plan.plan_summary
    goal.updated_at = datetime.now(UTC)
    await session.commit()
    return await get_goal(session, user_id, goal_id)
