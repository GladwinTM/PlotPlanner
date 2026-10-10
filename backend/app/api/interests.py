from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import LLM, CurrentUser, Session, rate_limited
from app.schemas.interests import (
    GraphRead, InterestCreate, InterestRead, InterestUpdate, LayoutUpdate, RelationshipCreate, RelationshipRead,
    SuggestionsRead,
)
from app.services import interest_service

router = APIRouter(prefix="/interests", tags=["interests"])


@router.get("", response_model=list[InterestRead])
async def list_interests(user: CurrentUser, session: Session):
    return await interest_service.list_interests(session, user.id)


@router.post("", response_model=InterestRead, status_code=status.HTTP_201_CREATED)
async def create_interest(payload: InterestCreate, user: CurrentUser, session: Session):
    return await interest_service.create_interest(session, user.id, payload)


@router.get("/graph", response_model=GraphRead)
async def read_graph(user: CurrentUser, session: Session):
    return await interest_service.graph(session, user.id)


@router.put("/layout")
async def save_layout(payload: LayoutUpdate, user: CurrentUser, session: Session):
    return {"updated": await interest_service.save_layout(session, user.id, payload)}


@router.post("/suggestions", response_model=SuggestionsRead, dependencies=[rate_limited("ai")])
async def suggestions(user: CurrentUser, session: Session, llm: LLM):
    return await interest_service.suggest(session, llm, user.id)


@router.get("/relationships", response_model=list[RelationshipRead])
async def list_relationships(user: CurrentUser, session: Session):
    return await interest_service.list_relationships(session, user.id)


@router.post("/relationships", response_model=RelationshipRead, status_code=status.HTTP_201_CREATED)
async def create_relationship(payload: RelationshipCreate, user: CurrentUser, session: Session):
    return await interest_service.create_relationship(session, user.id, payload)


@router.delete("/relationships/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relationship(relationship_id: UUID, user: CurrentUser, session: Session):
    await interest_service.delete_relationship(session, user.id, relationship_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{interest_id}", response_model=InterestRead)
async def read_interest(interest_id: UUID, user: CurrentUser, session: Session):
    return await interest_service.get_interest(session, user.id, interest_id)


@router.patch("/{interest_id}", response_model=InterestRead)
async def update_interest(interest_id: UUID, payload: InterestUpdate, user: CurrentUser, session: Session):
    return await interest_service.update_interest(session, user.id, interest_id, payload)


@router.delete("/{interest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interest(interest_id: UUID, user: CurrentUser, session: Session):
    await interest_service.delete_interest(session, user.id, interest_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
