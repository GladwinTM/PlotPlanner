"""Account data deletion.

Deletes every application record and stored document owned by the caller.
The Supabase Auth account itself can only be deleted with the service-role
key, which this backend deliberately does not hold; the response says so.
"""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete

from app.api.deps import CurrentUser, Session
from app.db.models import (
    ActivityCompletion, Conversation, Course, Document, EarningPlan, Enrollment, Goal, GoalCheckin, GoalMilestone,
    Interest, InterestRelationship, Message, Opportunity, Profile, ProfileFact,
)

router = APIRouter(prefix="/account", tags=["account"])

# Children before parents, so the order works with or without FK cascades.
USER_TABLES = (
    ActivityCompletion, Enrollment, Message, Conversation, GoalCheckin, GoalMilestone, Course, Goal,
    InterestRelationship, EarningPlan, Interest, ProfileFact, Document, Opportunity, Profile,
)


class DeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: Literal["DELETE"]


class DeleteResult(BaseModel):
    deleted: bool
    auth_account_deleted: bool
    note: str


@router.post("/delete-data", response_model=DeleteResult)
async def delete_data(_: DeleteRequest, user: CurrentUser, session: Session):
    for model in USER_TABLES:
        await session.execute(delete(model).where(model.user_id == user.id))
    await session.commit()
    return DeleteResult(
        deleted=True,
        auth_account_deleted=False,
        note="All PlotPlanner data and documents were deleted. Your sign-in account remains; "
        "contact the administrator to remove it.",
    )
