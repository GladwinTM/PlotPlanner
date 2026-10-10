import logging
from contextlib import AsyncExitStack, asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine

from app.ai.llm_client import LLMClient
from app.api import account, analytics, chat, courses, documents, goals, health, interests, onboarding, opportunities, profile
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.rate_limit import RateLimiter
from app.core.security import JwksKeyResolver, TokenVerifier
from app.db.database import create_engine, create_session_factory
from app.integrations.jobs import JobSearchClient
from app.integrations.web import UrlVerifier
from app.integrations.youtube import YouTubeClient

logger = logging.getLogger(__name__)

ROUTERS = (profile, onboarding, interests, goals, courses, chat, documents, opportunities, analytics, account)


def create_app(
    settings: Settings | None = None,
    *,
    token_verifier: TokenVerifier | None = None,
    engine: AsyncEngine | None = None,
    llm: LLMClient | None = None,
    youtube: YouTubeClient | None = None,
    jobs: JobSearchClient | None = None,
    url_verifier: UrlVerifier | None = None,
) -> FastAPI:
    """Build the application. Collaborators are injectable for tests."""
    settings = settings or get_settings()
    engine = engine or create_engine(settings)
    state = SimpleNamespace(
        settings=settings,
        session_factory=create_session_factory(engine),
        token_verifier=token_verifier or TokenVerifier(
            issuer=settings.supabase_issuer,
            audience=settings.supabase_jwt_audience,
            key_resolver=JwksKeyResolver(settings.supabase_jwks_url),
        ),
        llm=llm or LLMClient(api_key=settings.llm_api_key, base_url=settings.llm_base_url, model=settings.llm_model),
        youtube=youtube or YouTubeClient(settings.youtube_api_key),
        jobs=jobs or JobSearchClient(
            adzuna_app_id=settings.adzuna_app_id, adzuna_app_key=settings.adzuna_app_key, adzuna_country=settings.adzuna_country
        ),
        url_verifier=url_verifier or UrlVerifier(),
        rate_limiter=RateLimiter(),
    )

    mcp_app = None
    if settings.mcp_enabled:
        from app.mcp_server import build_mcp

        mcp_app = build_mcp(state).http_app(path="/")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        async with AsyncExitStack() as stack:
            if mcp_app is not None:
                await stack.enter_async_context(mcp_app.lifespan(mcp_app))
            yield
        for client in (state.llm, state.youtube, state.jobs, state.url_verifier):
            await client.aclose()
        await engine.dispose()

    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    for key, value in vars(state).items():
        setattr(app.state, key, value)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_exception_handlers(app)

    app.include_router(health.router)
    for module in ROUTERS:
        app.include_router(module.router, prefix=settings.api_prefix)
    if mcp_app is not None:
        app.mount("/mcp", mcp_app)

    logger.info(
        "%s started in %s mode (ai=%s, youtube=%s, adzuna=%s)", settings.app_name, settings.app_env,
        state.llm.configured, state.youtube.configured, state.jobs.adzuna_configured,
    )
    return app
