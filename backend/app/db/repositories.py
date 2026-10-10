"""Data access. Every user-owned query is scoped by ``user_id``."""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile


async def get_profile(session: AsyncSession, user_id: UUID) -> Profile | None:
    return await session.scalar(select(Profile).where(Profile.user_id == user_id))


async def insert_profile_if_absent(session: AsyncSession, user_id: UUID, display_name: str) -> None:
    """Race-safe: concurrent first requests for the same user create one row."""
    statement = (
        pg_insert(Profile)
        .values(user_id=user_id, display_name=display_name)
        .on_conflict_do_nothing(index_elements=[Profile.user_id])
    )
    await session.execute(statement)


async def update_profile(session: AsyncSession, profile: Profile, changes: dict) -> Profile:
    for field, value in changes.items():
        setattr(profile, field, value)
    profile.updated_at = datetime.now(UTC)
    await session.flush()
    return profile
