from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.security import AuthenticatedUser
from app.db import repositories
from app.db.models import Profile, ProfileFact
from app.schemas.profile import FactCreate, FactUpdate, ProfileUpdate

DISPLAY_NAME_MAX = 120


def _default_display_name(user: AuthenticatedUser) -> str:
    candidate = user.display_name_hint or (user.email.split("@")[0] if user.email else "")
    return candidate.strip()[:DISPLAY_NAME_MAX]


async def get_or_create_profile(session: AsyncSession, user: AuthenticatedUser) -> Profile:
    """Return the caller's profile, creating it on first sign-in.

    A signed-in user always gets the same single profile row, however many times
    they sign in or however many requests race on first use.
    """
    profile = await repositories.get_profile(session, user.id)
    if profile is not None:
        return profile
    try:
        await repositories.insert_profile_if_absent(session, user.id, _default_display_name(user))
        await session.commit()
    except IntegrityError as exc:
        # The token is valid but auth.users has no such row: the account was
        # deleted and the access token has not expired yet.
        await session.rollback()
        raise AuthenticationError("This account no longer exists", code="account_not_found") from exc
    profile = await repositories.get_profile(session, user.id)
    assert profile is not None
    return profile


async def update_profile(session: AsyncSession, user: AuthenticatedUser, payload: ProfileUpdate) -> Profile:
    profile = await get_or_create_profile(session, user)
    changes = payload.model_dump(exclude_unset=True)
    if changes:
        await repositories.update_profile(session, profile, changes)
        await session.commit()
        await session.refresh(profile)
    return profile


async def list_facts(session: AsyncSession, user_id, *, confirmed: bool | None = None) -> list[ProfileFact]:
    query = select(ProfileFact).where(ProfileFact.user_id == user_id)
    if confirmed is not None:
        query = query.where(ProfileFact.confirmed.is_(confirmed))
    return list((await session.scalars(query.order_by(ProfileFact.kind, ProfileFact.created_at))).all())


async def _get_fact(session: AsyncSession, user_id, fact_id) -> ProfileFact:
    fact = await session.scalar(select(ProfileFact).where(ProfileFact.id == fact_id, ProfileFact.user_id == user_id))
    if fact is None:
        raise NotFoundError("Fact not found")
    return fact


async def create_fact(session: AsyncSession, user_id, payload: FactCreate) -> ProfileFact:
    fact = ProfileFact(user_id=user_id, source="manual", confirmed=True, **payload.model_dump())
    session.add(fact)
    await session.commit()
    await session.refresh(fact)
    return fact


async def update_fact(session: AsyncSession, user_id, fact_id, payload: FactUpdate) -> ProfileFact:
    fact = await _get_fact(session, user_id, fact_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None and key in ("value", "confirmed"):
            continue
        setattr(fact, key, value)
    await session.commit()
    await session.refresh(fact)
    return fact


async def delete_fact(session: AsyncSession, user_id, fact_id) -> None:
    await session.delete(await _get_fact(session, user_id, fact_id))
    await session.commit()
