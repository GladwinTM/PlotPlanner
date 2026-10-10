"""PlotPlanner MCP server (mounted at ``/mcp``, streamable HTTP).

Exposes the same verified integrations the app uses so MCP clients (e.g. an
IDE assistant) can query them on the user's behalf:

- ``search_learning_resources``: YouTube videos verified via videos.list.
- ``search_jobs``: current listings from the configured job providers.
- ``get_course_details``: one of the caller's own learning pathways.

Every request needs a valid Supabase access token (``Authorization: Bearer``),
verified exactly like the REST API. Tools are read-only and scoped to the
token's user. Errors are returned as tool errors, never as fake results.
"""
import asyncio
from typing import Annotated
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.auth import TokenVerifier as McpTokenVerifier
from fastmcp.server.dependencies import get_access_token
from pydantic import Field

from app.core.exceptions import AppError
from app.core.security import TokenVerifier

TOOL_TIMEOUT_SECONDS = 25


class SupabaseTokenVerifier(McpTokenVerifier):
    def __init__(self, verifier: TokenVerifier):
        super().__init__()
        self._verifier = verifier

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            user = await asyncio.to_thread(self._verifier.verify, token)
        except AppError:
            return None
        return AccessToken(token=token, client_id=str(user.id), scopes=[], subject=str(user.id), claims={"sub": str(user.id)})


def _user_id() -> UUID:
    token = get_access_token()
    if token is None:
        raise ToolError("Authentication required")
    return UUID(token.claims["sub"])


async def _guard(coro):
    try:
        return await asyncio.wait_for(coro, TOOL_TIMEOUT_SECONDS)
    except TimeoutError as exc:
        raise ToolError("The upstream service timed out") from exc
    except AppError as exc:
        raise ToolError(exc.message) from exc


def build_mcp(state) -> FastMCP:
    mcp = FastMCP(
        name="PlotPlanner",
        instructions="Read-only tools for PlotPlanner learning resources, job listings and the caller's own courses.",
        auth=SupabaseTokenVerifier(state.token_verifier),
    )

    @mcp.tool
    async def search_learning_resources(
        query: Annotated[str, Field(min_length=2, max_length=120, description="Topic to learn, e.g. 'music production basics'")],
        max_results: Annotated[int, Field(ge=1, le=10)] = 5,
    ) -> list[dict]:
        """Search YouTube for tutorial videos. Every result was confirmed public and available at retrieval time."""
        _user_id()
        videos = await _guard(state.youtube.search_videos(query, max_results=max_results))
        return [
            {"title": v.title, "channel": v.channel, "url": v.url, "duration_seconds": v.duration_seconds,
             "published_at": v.published_at.isoformat() if v.published_at else None, "retrieved_at": v.retrieved_at.isoformat(),
             "provider": "YouTube", "cost": "free"}
            for v in videos
        ]

    @mcp.tool
    async def search_jobs(
        query: Annotated[str, Field(min_length=2, max_length=120, description="Role or skill keywords")],
        location: Annotated[str | None, Field(max_length=100)] = None,
        remote_only: bool = True,
        limit: Annotated[int, Field(ge=1, le=30)] = 10,
    ) -> dict:
        """Search current job listings. Salaries are included only when the provider published them, with their basis."""
        _user_id()
        outcome = await _guard(state.jobs.search(query, location=location, remote_only=remote_only, limit=limit))
        return {
            "listings": [
                {"title": l.title, "company": l.company, "location": l.location, "url": l.url, "source": l.source,
                 "employment_type": l.employment_type, "salary": l.compensation_text, "salary_basis": l.compensation_basis,
                 "published_at": l.published_at.isoformat() if l.published_at else None, "retrieved_at": l.retrieved_at.isoformat()}
                for l in outcome.listings
            ],
            "providers": outcome.providers_used,
            "unavailable_providers": list(outcome.provider_errors),
        }

    @mcp.tool
    async def get_course_details(course_id: UUID) -> dict:
        """Get one of your learning pathways with modules, activities, verified resources and progress."""
        from app.services import course_service

        user_id = _user_id()
        async with state.session_factory() as session:
            detail = await _guard(course_service.get_course_detail(session, user_id, course_id))
        return detail.model_dump(mode="json")

    return mcp
