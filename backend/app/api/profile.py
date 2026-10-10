from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, Session
from app.schemas.profile import FactCreate, FactRead, FactUpdate, ProfileRead, ProfileUpdate
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileRead)
async def read_profile(user: CurrentUser, session: Session):
    return await profile_service.get_or_create_profile(session, user)


@router.patch("", response_model=ProfileRead)
async def patch_profile(payload: ProfileUpdate, user: CurrentUser, session: Session):
    return await profile_service.update_profile(session, user, payload)


@router.get("/facts", response_model=list[FactRead])
async def list_facts(user: CurrentUser, session: Session, confirmed: bool | None = None):
    return await profile_service.list_facts(session, user.id, confirmed=confirmed)


@router.post("/facts", response_model=FactRead, status_code=status.HTTP_201_CREATED)
async def create_fact(payload: FactCreate, user: CurrentUser, session: Session):
    return await profile_service.create_fact(session, user.id, payload)


@router.patch("/facts/{fact_id}", response_model=FactRead)
async def update_fact(fact_id: UUID, payload: FactUpdate, user: CurrentUser, session: Session):
    return await profile_service.update_fact(session, user.id, fact_id, payload)


@router.delete("/facts/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fact(fact_id: UUID, user: CurrentUser, session: Session):
    await profile_service.delete_fact(session, user.id, fact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
