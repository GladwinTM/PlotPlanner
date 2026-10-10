from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import LLM, CurrentUser, Jobs, Session, YouTube, rate_limited, require_ai
from app.schemas.onboarding import MessageRead
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=4000)


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead]


class ProposalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accept: bool


@router.post("", response_model=ConversationDetail, dependencies=[rate_limited("ai")])
async def send_message(payload: ChatRequest, user: CurrentUser, session: Session, llm: LLM, youtube: YouTube, jobs: Jobs):
    require_ai(llm)
    return await chat_service.send(session, llm, youtube, jobs, user, payload.conversation_id, payload.message)


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(user: CurrentUser, session: Session):
    return await chat_service.list_conversations(session, user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def read_conversation(conversation_id: UUID, user: CurrentUser, session: Session):
    return await chat_service.get_conversation(session, user.id, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: UUID, user: CurrentUser, session: Session):
    await chat_service.delete_conversation(session, user.id, conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/conversations/{conversation_id}/retry", response_model=ConversationDetail, dependencies=[rate_limited("ai")])
async def retry(conversation_id: UUID, user: CurrentUser, session: Session, llm: LLM, youtube: YouTube, jobs: Jobs):
    require_ai(llm)
    return await chat_service.retry(session, llm, youtube, jobs, user.id, conversation_id)


@router.post("/messages/{message_id}/proposals/{index}", response_model=MessageRead)
async def decide_proposal(message_id: UUID, index: int, payload: ProposalDecision, user: CurrentUser, session: Session):
    return await chat_service.decide_proposal(session, user, message_id, index, payload.accept)
