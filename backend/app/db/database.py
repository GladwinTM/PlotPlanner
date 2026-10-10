"""Async SQLAlchemy engine and per-request session."""
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings


def create_engine(settings: Settings, *, null_pool: bool = False) -> AsyncEngine:
    # prepare_threshold=None disables server-side prepared statements, which are
    # incompatible with Supabase's transaction-mode pooler.
    options: dict = {"connect_args": {"prepare_threshold": None}}
    if null_pool:
        options["poolclass"] = NullPool
    else:
        options["pool_pre_ping"] = True
    return create_async_engine(settings.database_url, **options)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session
