from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import LLM, CurrentUser, Session, rate_limited
from app.db import models as m
from app.schemas.goals import CheckinCreate, GoalCreate, GoalRead, GoalUpdate, MilestoneCreate, MilestoneUpdate, PlanRequest
from app.services import goal_service

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=list[GoalRead])
async def list_goals(user: CurrentUser, session: Session, status: Literal[*m.GOAL_STATUSES] | None = None):
    return [goal_service.to_read(goal) for goal in await goal_service.list_goals(session, user.id, status)]


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
async def create_goal(payload: GoalCreate, user: CurrentUser, session: Session):
    return goal_service.to_read(await goal_service.create_goal(session, user.id, payload))


@router.get("/{goal_id}", response_model=GoalRead)
async def read_goal(goal_id: UUID, user: CurrentUser, session: Session):
    return goal_service.to_read(await goal_service.get_goal(session, user.id, goal_id))


@router.patch("/{goal_id}", response_model=GoalRead)
async def update_goal(goal_id: UUID, payload: GoalUpdate, user: CurrentUser, session: Session):
    return goal_service.to_read(await goal_service.update_goal(session, user.id, goal_id, payload))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: UUID, user: CurrentUser, session: Session):
    await goal_service.delete_goal(session, user.id, goal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{goal_id}/plan", response_model=GoalRead, dependencies=[rate_limited("ai")])
async def generate_plan(goal_id: UUID, user: CurrentUser, session: Session, llm: LLM, payload: PlanRequest | None = None):
    goal = await goal_service.generate_plan(session, llm, user.id, goal_id, payload.adjustment if payload else None)
    return goal_service.to_read(goal)


@router.post("/{goal_id}/milestones", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
async def add_milestone(goal_id: UUID, payload: MilestoneCreate, user: CurrentUser, session: Session):
    return goal_service.to_read(await goal_service.add_milestone(session, user.id, goal_id, payload))


@router.patch("/{goal_id}/milestones/{milestone_id}", response_model=GoalRead)
async def update_milestone(goal_id: UUID, milestone_id: UUID, payload: MilestoneUpdate, user: CurrentUser, session: Session):
    return goal_service.to_read(await goal_service.update_milestone(session, user.id, goal_id, milestone_id, payload))


@router.delete("/{goal_id}/milestones/{milestone_id}", response_model=GoalRead)
async def delete_milestone(goal_id: UUID, milestone_id: UUID, user: CurrentUser, session: Session):
    return goal_service.to_read(await goal_service.delete_milestone(session, user.id, goal_id, milestone_id))


@router.post("/{goal_id}/checkins", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
async def add_checkin(goal_id: UUID, payload: CheckinCreate, user: CurrentUser, session: Session):
    return goal_service.to_read(await goal_service.add_checkin(session, user.id, goal_id, payload))
