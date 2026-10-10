"""Persistent AI chat with on-demand tools.

The model decides which tool (if any) a message needs. Tools are scoped to
the authenticated user and return only real data. The model cannot write to
the database: ``propose_change`` records a proposal that the user must accept,
after which the change goes through the normal validated service.
"""
import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai import prompts
from app.ai.llm_client import AIProviderError, LLMClient
from app.core.exceptions import AppError, BadRequestError, ConflictError, NotFoundError
from app.core.security import AuthenticatedUser
from app.db import models as m
from app.db.models import Conversation, Message
from app.integrations.jobs import JobSearchClient
from app.integrations.youtube import YouTubeClient
from app.schemas.goals import GoalCreate
from app.schemas.interests import InterestCreate
from app.schemas.profile import ProfileUpdate
from app.services import course_service, document_service, goal_service, interest_service, profile_service
from app.services.context import build_user_context, context_json

logger = logging.getLogger(__name__)

HISTORY_MESSAGES = 16
MAX_TOOL_ROUNDS = 3
TOOL_TIMEOUT_SECONDS = 25

TOOLS = [
    {"type": "function", "function": {
        "name": "get_learning_progress",
        "description": "Get the user's learning pathways with completion percentages and next activities.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "search_learning_videos",
        "description": "Search YouTube for tutorial videos. Returns only videos verified as public and available.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Search terms, 3-8 words"},
        }, "required": ["query"], "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "search_jobs",
        "description": "Search current job listings from public job boards (Jobicy, The Muse, Adzuna when configured).",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Role or skill keywords"},
            "remote_only": {"type": "boolean"},
            "location": {"type": "string", "description": "City or country, optional"},
        }, "required": ["query"], "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "search_my_documents",
        "description": "Full-text search across documents the user uploaded (e.g. their resume).",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
        }, "required": ["query"], "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "propose_change",
        "description": "Propose a change to the user's PlotPlanner data. The user must confirm it in the UI.",
        "parameters": {"type": "object", "properties": {
            "change_type": {"type": "string", "enum": ["add_interest", "create_goal", "update_weekly_hours"]},
            "name": {"type": "string", "description": "Interest name (add_interest) or goal title (create_goal)"},
            "category": {"type": "string", "enum": list(m.GOAL_CATEGORIES), "description": "Goal category (create_goal)"},
            "interest_type": {"type": "string", "enum": list(m.INTEREST_TYPES), "description": "Interest type (add_interest)"},
            "hours": {"type": "integer", "description": "Weekly hours (update_weekly_hours)"},
            "reason": {"type": "string", "description": "Why this change helps, shown to the user"},
        }, "required": ["change_type", "reason"], "additionalProperties": False},
    }},
]


class Proposal(BaseModel):
    change_type: Literal["add_interest", "create_goal", "update_weekly_hours"]
    name: str | None = Field(None, max_length=200)
    category: Literal[*m.GOAL_CATEGORIES] | None = None
    interest_type: Literal[*m.INTEREST_TYPES] | None = None
    hours: int | None = Field(None, ge=0, le=168)
    reason: str = Field(max_length=500)
    status: Literal["pending", "accepted", "dismissed"] = "pending"
    result: str | None = None


class ToolContext:
    def __init__(self, session: AsyncSession, user_id: UUID, youtube: YouTubeClient, jobs: JobSearchClient):
        self.session, self.user_id, self.youtube, self.jobs = session, user_id, youtube, jobs
        self.sources: list[dict] = []
        self.proposals: list[Proposal] = []
        self.tools_used: list[str] = []

    async def run(self, name: str, arguments: dict) -> dict:
        self.tools_used.append(name)
        try:
            return await asyncio.wait_for(self._dispatch(name, arguments), TOOL_TIMEOUT_SECONDS)
        except TimeoutError:
            return {"error": "The tool timed out."}
        except AppError as exc:
            return {"error": exc.message}

    async def _dispatch(self, name: str, args: dict) -> dict:
        if name == "get_learning_progress":
            courses = await course_service.list_courses(self.session, self.user_id)
            return {"courses": [
                {"title": c.title, "status": c.status, "enrollment": c.enrollment.status if c.enrollment else "not enrolled",
                 "completion_percent": c.progress.percent,
                 "completed_activities": f"{c.progress.completed_activities}/{c.progress.activities}",
                 "next_activity": f"{c.next_activity.module_title}: {c.next_activity.activity_title}" if c.next_activity else None}
                for c in courses
            ]}
        if name == "search_learning_videos":
            query = str(args.get("query", ""))[:120]
            if len(query) < 2:
                return {"error": "A search query is required."}
            videos = await self.youtube.search_videos(query, max_results=5)
            for v in videos:
                self.sources.append({"kind": "video", "title": v.title, "url": v.url, "provider": "YouTube", "channel": v.channel,
                                     "duration_seconds": v.duration_seconds, "retrieved_at": v.retrieved_at.isoformat()})
            return {"videos": [{"title": v.title, "channel": v.channel, "url": v.url, "minutes": round((v.duration_seconds or 0) / 60)} for v in videos]
                    or "No verified videos were found."}
        if name == "search_jobs":
            query = str(args.get("query", ""))[:120]
            if len(query) < 2:
                return {"error": "A search query is required."}
            outcome = await self.jobs.search(query, location=args.get("location") or None, remote_only=bool(args.get("remote_only", True)), limit=8)
            for listing in outcome.listings:
                self.sources.append({"kind": "job", "title": listing.title, "url": listing.url, "provider": listing.source,
                                     "company": listing.company, "salary": listing.compensation_text,
                                     "retrieved_at": listing.retrieved_at.isoformat()})
            return {"listings": [
                {"title": l.title, "company": l.company, "location": l.location, "source": l.source, "url": l.url,
                 "salary_listed_by_employer": l.compensation_text if l.compensation_basis == "employer_provided" else None,
                 "salary_estimate_by_provider": l.compensation_text if l.compensation_basis == "provider_estimate" else None}
                for l in outcome.listings
            ] or "No matching listings were found.", "unavailable_providers": list(outcome.provider_errors)}
        if name == "search_my_documents":
            query = str(args.get("query", ""))[:200]
            results = await document_service.search(self.session, self.user_id, query)
            return {"matches": results or "No matching text in the user's documents."}
        if name == "propose_change":
            try:
                proposal = Proposal.model_validate({k: v for k, v in args.items() if k in Proposal.model_fields})
            except ValidationError:
                return {"error": "Invalid proposal."}
            if proposal.change_type in ("add_interest", "create_goal") and not proposal.name:
                return {"error": "A name is required."}
            if proposal.change_type == "update_weekly_hours" and proposal.hours is None:
                return {"error": "hours is required."}
            self.proposals.append(proposal)
            return {"status": "Shown to the user for confirmation. It is NOT saved until they accept."}
        return {"error": f"Unknown tool {name}"}


async def list_conversations(session: AsyncSession, user_id: UUID) -> list[dict]:
    rows = (await session.execute(
        select(Conversation, func.count(Message.id))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user_id, Conversation.kind == "chat")
        .group_by(Conversation.id).order_by(Conversation.updated_at.desc())
    )).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at, "updated_at": c.updated_at, "message_count": count} for c, count in rows]


async def get_conversation(session: AsyncSession, user_id: UUID, conversation_id: UUID) -> Conversation:
    conversation = await session.scalar(
        select(Conversation).options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id, Conversation.user_id == user_id, Conversation.kind == "chat")
        .execution_options(populate_existing=True)
    )
    if conversation is None:
        raise NotFoundError("Conversation not found")
    return conversation


async def delete_conversation(session: AsyncSession, user_id: UUID, conversation_id: UUID) -> None:
    await session.delete(await get_conversation(session, user_id, conversation_id))
    await session.commit()


async def send(session: AsyncSession, llm: LLMClient, youtube: YouTubeClient, jobs: JobSearchClient, user: AuthenticatedUser,
               conversation_id: UUID | None, text: str) -> Conversation:
    text = text.strip()
    if not text:
        raise BadRequestError("Message cannot be empty", code="empty_message")
    await profile_service.get_or_create_profile(session, user)
    if conversation_id:
        conversation = await get_conversation(session, user.id, conversation_id)
        if conversation.messages and conversation.messages[-1].role == "user":
            raise ConflictError("The previous message is still waiting for a reply. Retry it first.")
    else:
        conversation = Conversation(user_id=user.id, kind="chat", title=text[:80], state={})
        session.add(conversation)
        await session.flush()
    session.add(Message(conversation_id=conversation.id, user_id=user.id, role="user", content=text, meta={}))
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    conversation = await get_conversation(session, user.id, conversation.id)
    await _respond(session, llm, youtube, jobs, user.id, conversation)
    return await get_conversation(session, user.id, conversation.id)


async def retry(session: AsyncSession, llm, youtube, jobs, user_id: UUID, conversation_id: UUID) -> Conversation:
    conversation = await get_conversation(session, user_id, conversation_id)
    if not conversation.messages or conversation.messages[-1].role != "user":
        raise ConflictError("There is no message waiting for a reply")
    await _respond(session, llm, youtube, jobs, user_id, conversation)
    return await get_conversation(session, user_id, conversation_id)


async def _respond(session: AsyncSession, llm: LLMClient, youtube, jobs, user_id: UUID, conversation: Conversation) -> None:
    context = await build_user_context(session, user_id, courses=True)
    messages: list[dict] = [
        {"role": "system", "content": prompts.CHAT},
        {"role": "system", "content": prompts.tagged("user_data", context_json(context))},
        *[{"role": msg.role, "content": msg.content} for msg in conversation.messages[-HISTORY_MESSAGES:]],
    ]
    tools = ToolContext(session, user_id, youtube, jobs)
    content = None
    for _ in range(MAX_TOOL_ROUNDS):
        result = await llm.chat(messages=messages, tools=TOOLS, max_tokens=2000)
        if not result.tool_calls:
            content = result.content
            break
        messages.append({"role": "assistant", "content": result.content or "", "tool_calls": result.raw_message.get("tool_calls")})
        for call in result.tool_calls:
            output = await tools.run(call.name, call.arguments)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": prompts.tagged("tool_result", json.dumps(output, default=str)[:12000])})
    if content is None:
        content = (await llm.chat(messages=messages, max_tokens=2000)).content
    if not content or not content.strip():
        raise AIProviderError("The AI returned an empty reply. Your message was saved; please retry.")
    session.add(Message(
        conversation_id=conversation.id, user_id=user_id, role="assistant", content=content.strip(),
        meta={"tools_used": tools.tools_used, "sources": tools.sources[:20], "proposals": [p.model_dump() for p in tools.proposals]},
    ))
    conversation.updated_at = datetime.now(UTC)
    await session.commit()


async def decide_proposal(session: AsyncSession, user: AuthenticatedUser, message_id: UUID, index: int, accept: bool) -> Message:
    message = await session.scalar(select(Message).where(Message.id == message_id, Message.user_id == user.id, Message.role == "assistant"))
    if message is None:
        raise NotFoundError("Message not found")
    proposals = list((message.meta or {}).get("proposals", []))
    if not 0 <= index < len(proposals):
        raise NotFoundError("Proposal not found")
    proposal = Proposal.model_validate(proposals[index])
    if proposal.status != "pending":
        raise ConflictError("This proposal was already handled")
    if accept:
        if proposal.change_type == "add_interest":
            interest = await interest_service.create_interest(session, user.id, InterestCreate(
                name=proposal.name or "", interest_type=proposal.interest_type or "personal", source="chat",
            ))
            proposal.result = f"Added interest {interest.name}"
        elif proposal.change_type == "create_goal":
            goal = await goal_service.create_goal(session, user.id, GoalCreate(title=proposal.name or "", category=proposal.category or "personal"))
            proposal.result = f"Created goal {goal.title}"
        else:
            await profile_service.update_profile(session, user, ProfileUpdate(available_hours_per_week=proposal.hours))
            proposal.result = f"Weekly hours set to {proposal.hours}"
        proposal.status = "accepted"
    else:
        proposal.status = "dismissed"
    message = await session.scalar(select(Message).where(Message.id == message_id).execution_options(populate_existing=True))
    proposals[index] = proposal.model_dump()
    message.meta = {**message.meta, "proposals": proposals}
    await session.commit()
    await session.refresh(message)
    return message
