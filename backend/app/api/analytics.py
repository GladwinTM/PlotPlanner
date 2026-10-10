from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, Session
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(user: CurrentUser, session: Session):
    return await analytics_service.overview(session, user.id)


@router.get("/interests")
async def interests(user: CurrentUser, session: Session):
    return await analytics_service.interests(session, user.id)


@router.get("/activity")
async def activity(user: CurrentUser, session: Session, days: int = Query(84, ge=7, le=365)):
    return await analytics_service.activity(session, user.id, days)
