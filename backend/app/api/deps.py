"""Shared FastAPI dependencies. The user always comes from the verified token;
no endpoint accepts a user id from the client."""
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import AINotConfiguredError, LLMClient
from app.core.security import AuthenticatedUser, get_current_user
from app.db.database import get_session
from app.integrations.jobs import JobSearchClient
from app.integrations.youtube import YouTubeClient

CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
Session = Annotated[AsyncSession, Depends(get_session)]


def get_llm(request: Request) -> LLMClient:
    return request.app.state.llm


def get_youtube(request: Request) -> YouTubeClient:
    return request.app.state.youtube


def get_jobs(request: Request) -> JobSearchClient:
    return request.app.state.jobs


LLM = Annotated[LLMClient, Depends(get_llm)]
YouTube = Annotated[YouTubeClient, Depends(get_youtube)]
Jobs = Annotated[JobSearchClient, Depends(get_jobs)]


def rate_limited(bucket: str, *, per_minute: int | None = None):
    """Dependency that limits a user's calls to an expensive endpoint group."""

    def dependency(request: Request, user: CurrentUser) -> AuthenticatedUser:
        limit = per_minute or request.app.state.settings.ai_requests_per_minute
        request.app.state.rate_limiter.check(bucket, str(user.id), limit=limit, window_seconds=60)
        return user

    return Depends(dependency)


def require_ai(llm: LLMClient) -> None:
    """Fail before creating background work that could never succeed."""
    if not llm.configured:
        raise AINotConfiguredError()
