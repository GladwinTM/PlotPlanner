"""Compact user context for AI prompts.

Only what a workflow asks for is included, and long fields are truncated, so
the provider receives the minimum personal data needed.
"""
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Course, Enrollment, Goal, Interest, Profile, ProfileFact
from app.services.progress import course_progress


def _clip(value: str | None, limit: int = 400) -> str | None:
    if not value:
        return None
    return value if len(value) <= limit else value[: limit - 1] + "…"


async def build_user_context(
    session: AsyncSession,
    user_id: UUID,
    *,
    profile: bool = True,
    facts: bool = True,
    interests: bool = True,
    goals: bool = True,
    courses: bool = False,
) -> dict:
    context: dict = {}
    if profile:
        row = await session.scalar(select(Profile).where(Profile.user_id == user_id))
        if row:
            context["profile"] = {
                k: v for k, v in {
                    "name": row.display_name or None,
                    "location": row.location,
                    "occupation": row.current_occupation,
                    "education": _clip(row.education_summary),
                    "experience": _clip(row.experience_summary),
                    "hours_per_week": row.available_hours_per_week,
                    "learning_preferences": _clip(row.learning_preferences, 300),
                    "constraints": _clip(row.constraints_summary, 300),
                }.items() if v is not None
            }
    if facts:
        rows = (await session.scalars(
            select(ProfileFact).where(ProfileFact.user_id == user_id, ProfileFact.confirmed.is_(True)).limit(60)
        )).all()
        grouped: dict[str, list[str]] = {}
        for fact in rows:
            grouped.setdefault(fact.kind, []).append(_clip(fact.value, 160))
        if grouped:
            context["confirmed_facts"] = grouped
    if interests:
        rows = (await session.scalars(
            select(Interest).where(Interest.user_id == user_id).order_by(Interest.priority.desc(), Interest.name).limit(40)
        )).all()
        context["interests"] = [
            {k: v for k, v in {
                "name": i.name, "type": i.interest_type, "kind": i.node_kind, "priority": i.priority,
                "wants_income": i.seeks_income or None,
            }.items() if v is not None}
            for i in rows
        ]
    if goals:
        rows = (await session.scalars(
            select(Goal).where(Goal.user_id == user_id, Goal.status == "active").order_by(Goal.priority.desc()).limit(10)
        )).all()
        context["active_goals"] = [
            {k: v for k, v in {
                "title": g.title, "category": g.category, "target": _clip(g.target_outcome, 200),
                "target_date": g.target_date.isoformat() if g.target_date else None,
            }.items() if v is not None}
            for g in rows
        ]
    if courses:
        rows = (await session.execute(
            select(Course, Enrollment.status)
            .join(Enrollment, (Enrollment.course_id == Course.id) & (Enrollment.user_id == user_id))
            .where(Course.user_id == user_id, Course.status == "ready")
            .limit(10)
        )).all()
        progress = await course_progress(session, user_id, [course.id for course, _ in rows])
        context["courses"] = [
            {
                "title": course.title,
                "enrollment": status,
                "completion_percent": progress[course.id].percent,
                "next_activity": progress[course.id].next_activity.activity_title if progress[course.id].next_activity else None,
            }
            for course, status in rows
        ]
    return context


def context_json(context: dict) -> str:
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"))
