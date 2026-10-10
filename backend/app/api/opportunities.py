from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import LLM, CurrentUser, Jobs, Session, rate_limited, require_ai
from app.db import models as m
from app.schemas.opportunities import (
    EarningPlanRead, OpportunityRead, PlanRequest, SalaryRequest, SalaryResponse, SearchRequest, SearchResponse, StatusUpdate,
)
from app.services import opportunity_service

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=list[OpportunityRead])
async def list_opportunities(user: CurrentUser, session: Session, status: Literal[*m.OPPORTUNITY_STATUSES] | None = None):
    """Tracked opportunities (everything except unsaved search results) unless a status is given."""
    return await opportunity_service.list_opportunities(session, user.id, status)


@router.post("/search", response_model=SearchResponse, dependencies=[rate_limited("jobs", per_minute=6)])
async def search(payload: SearchRequest, user: CurrentUser, session: Session, llm: LLM, jobs: Jobs):
    return await opportunity_service.search(session, llm, jobs, user.id, payload)


@router.post("/salary", response_model=SalaryResponse, dependencies=[rate_limited("jobs", per_minute=6)])
async def salary(payload: SalaryRequest, user: CurrentUser, jobs: Jobs):
    return await opportunity_service.salary(jobs, payload)


@router.post("/plan", response_model=EarningPlanRead, status_code=status.HTTP_201_CREATED, dependencies=[rate_limited("ai")])
async def create_plan(payload: PlanRequest, user: CurrentUser, session: Session, llm: LLM):
    require_ai(llm)
    return await opportunity_service.create_plan(session, llm, user.id, payload)


@router.get("/plans", response_model=list[EarningPlanRead])
async def list_plans(user: CurrentUser, session: Session):
    return await opportunity_service.list_plans(session, user.id)


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: UUID, user: CurrentUser, session: Session):
    await opportunity_service.delete_plan(session, user.id, plan_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{opportunity_id}/save", response_model=OpportunityRead)
async def save(opportunity_id: UUID, user: CurrentUser, session: Session):
    return await opportunity_service.set_status(session, user.id, opportunity_id, "saved")


@router.patch("/{opportunity_id}/status", response_model=OpportunityRead)
async def update_status(opportunity_id: UUID, payload: StatusUpdate, user: CurrentUser, session: Session):
    return await opportunity_service.set_status(
        session, user.id, opportunity_id, payload.status, payload.notes, notes_set="notes" in payload.model_fields_set
    )


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(opportunity_id: UUID, user: CurrentUser, session: Session):
    await opportunity_service.delete_opportunity(session, user.id, opportunity_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
