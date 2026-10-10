"""Analytics computed from stored records only (see ``progress`` for the
definitions). Suggestions are deterministic rules over the same data."""
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ActivityCompletion, Course, CourseActivity, CourseModule, Enrollment, Goal, GoalCheckin, GoalMilestone, Interest,
    InterestRelationship, Message, Opportunity,
)
from app.services.progress import course_progress

ACTIVITY_DAYS = 84
STALE_COURSE_DAYS = 14


async def overview(session: AsyncSession, user_id: UUID) -> dict:
    interests = await session.scalar(select(func.count()).select_from(Interest).where(Interest.user_id == user_id))
    enrollments = (await session.execute(
        select(Enrollment.course_id, Enrollment.status, Course.title)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Enrollment.user_id == user_id, Course.status != "archived")
    )).all()
    progress = await course_progress(session, user_id, [course_id for course_id, _, _ in enrollments])
    courses = [
        {"course_id": course_id, "title": title, "enrollment": status, "percent": progress[course_id].percent,
         "completed_required_modules": progress[course_id].completed_required_modules,
         "required_modules": progress[course_id].required_modules}
        for course_id, status, title in enrollments
    ]
    goals = (await session.execute(
        select(Goal.id, Goal.title, Goal.status, func.count(GoalMilestone.id), func.count(GoalMilestone.completed_at))
        .outerjoin(GoalMilestone, GoalMilestone.goal_id == Goal.id)
        .where(Goal.user_id == user_id).group_by(Goal.id)
    )).all()
    goal_rows = [
        {"goal_id": gid, "title": title, "status": status, "milestones": total, "completed_milestones": done,
         "percent": round(done / total * 100) if total else 0}
        for gid, title, status, total, done in goals
    ]
    completed_projects = await session.scalar(
        select(func.count()).select_from(ActivityCompletion)
        .join(CourseActivity, CourseActivity.id == ActivityCompletion.activity_id)
        .where(ActivityCompletion.user_id == user_id, CourseActivity.kind == "project")
    )
    minutes = await session.scalar(select(func.coalesce(func.sum(GoalCheckin.minutes), 0)).where(GoalCheckin.user_id == user_id))
    saved = await session.scalar(
        select(func.count()).select_from(Opportunity).where(Opportunity.user_id == user_id, Opportunity.status != "found")
    )
    return {
        "active_interests": interests,
        "active_courses": sum(1 for c in courses if c["enrollment"] == "active"),
        "completed_courses": sum(1 for c in courses if c["enrollment"] == "completed"),
        "completed_modules": sum(p.completed_required_modules + p.completed_optional_modules for p in progress.values()),
        "completed_activities": sum(p.completed_activities for p in progress.values()),
        "completed_projects": completed_projects,
        "active_goals": sum(1 for g in goal_rows if g["status"] == "active"),
        "completed_goals": sum(1 for g in goal_rows if g["status"] == "completed"),
        "minutes_logged": minutes,
        "tracked_opportunities": saved,
        "courses": courses,
        "goals": goal_rows,
        "suggestions": await suggestions(session, user_id, courses),
        "definitions": {
            "course_percent": "Completed required modules / required modules. A module is complete when all its activities are done.",
            "goal_percent": "Completed milestones / milestones.",
            "minutes_logged": "Minutes you entered in goal check-ins. Course time is not tracked automatically.",
        },
    }


async def suggestions(session: AsyncSession, user_id: UUID, courses: list[dict]) -> list[dict]:
    result: list[dict] = []
    now = datetime.now(UTC)
    last_activity = dict((await session.execute(
        select(CourseModule.course_id, func.max(ActivityCompletion.completed_at))
        .join(CourseActivity, CourseActivity.module_id == CourseModule.id)
        .join(ActivityCompletion, ActivityCompletion.activity_id == CourseActivity.id)
        .where(ActivityCompletion.user_id == user_id)
        .group_by(CourseModule.course_id)
    )).all())
    for course in courses:
        if course["enrollment"] != "active":
            continue
        last = last_activity.get(course["course_id"])
        if last is None or now - last > timedelta(days=STALE_COURSE_DAYS):
            result.append({
                "kind": "resume_course", "course_id": str(course["course_id"]),
                "message": f'You haven\'t logged progress in "{course["title"]}" for a while. Try one small activity, or pause it to free up time.',
            })
    practiced = (await session.execute(
        select(Goal.id, Goal.title, Goal.interest_id, func.count(GoalCheckin.id))
        .join(GoalCheckin, GoalCheckin.goal_id == Goal.id)
        .where(Goal.user_id == user_id, Goal.status == "active", GoalCheckin.created_at > now - timedelta(days=30))
        .group_by(Goal.id).having(func.count(GoalCheckin.id) >= 3)
    )).all()
    for goal_id, title, interest_id, count in practiced:
        has_course = interest_id and await session.scalar(
            select(func.count()).select_from(Course).where(Course.user_id == user_id, Course.interest_id == interest_id, Course.status != "archived")
        )
        if interest_id and not has_course:
            result.append({
                "kind": "course_for_practice", "goal_id": str(goal_id), "interest_id": str(interest_id),
                "message": f'You checked in on "{title}" {count} times this month. A short learning pathway could give that practice structure.',
            })
    unplanned = (await session.execute(
        select(Goal.id, Goal.title).outerjoin(GoalMilestone, GoalMilestone.goal_id == Goal.id)
        .where(Goal.user_id == user_id, Goal.status == "active").group_by(Goal.id).having(func.count(GoalMilestone.id) == 0)
    )).all()
    for goal_id, title in unplanned[:3]:
        result.append({"kind": "plan_goal", "goal_id": str(goal_id), "message": f'"{title}" has no milestones yet. Generate or write a plan to start tracking it.'})
    return result[:8]


async def interests(session: AsyncSession, user_id: UUID) -> dict:
    rows = (await session.scalars(select(Interest).where(Interest.user_id == user_id).order_by(Interest.priority.desc()))).all()
    degree = dict((await session.execute(
        select(InterestRelationship.source_interest_id, func.count()).where(InterestRelationship.user_id == user_id)
        .group_by(InterestRelationship.source_interest_id)
    )).all())
    for target, count in (await session.execute(
        select(InterestRelationship.target_interest_id, func.count()).where(InterestRelationship.user_id == user_id)
        .group_by(InterestRelationship.target_interest_id)
    )).all():
        degree[target] = degree.get(target, 0) + count
    courses = (await session.execute(
        select(Course.id, Course.interest_id).join(Enrollment, (Enrollment.course_id == Course.id) & (Enrollment.user_id == user_id))
        .where(Course.user_id == user_id, Course.status != "archived", Course.interest_id.is_not(None))
    )).all()
    progress = await course_progress(session, user_id, [cid for cid, _ in courses])
    by_interest: dict[UUID, list[int]] = {}
    for cid, iid in courses:
        by_interest.setdefault(iid, []).append(progress[cid].percent)
    goals = dict((await session.execute(
        select(Goal.interest_id, func.count()).where(Goal.user_id == user_id, Goal.interest_id.is_not(None)).group_by(Goal.interest_id)
    )).all())
    return {
        "interests": [
            {"id": i.id, "name": i.name, "interest_type": i.interest_type, "node_kind": i.node_kind, "priority": i.priority,
             "connections": degree.get(i.id, 0), "enrolled_courses": len(by_interest.get(i.id, [])),
             "average_course_percent": round(sum(by_interest[i.id]) / len(by_interest[i.id])) if by_interest.get(i.id) else None,
             "goals": goals.get(i.id, 0)}
            for i in rows
        ],
        "by_type": [
            {"interest_type": t, "count": c} for t, c in (await session.execute(
                select(Interest.interest_type, func.count()).where(Interest.user_id == user_id).group_by(Interest.interest_type)
            )).all()
        ],
        "note": "Connections count links you or the AI added in your graph. They show how your interests relate, not career suitability.",
    }


async def activity(session: AsyncSession, user_id: UUID, days: int = ACTIVITY_DAYS) -> dict:
    since = datetime.now(UTC) - timedelta(days=days)

    async def per_day(column, *conditions):
        day = cast(func.timezone("UTC", column), Date)
        return dict((await session.execute(select(day, func.count()).where(*conditions, column >= since).group_by(day))).all())

    activities = await per_day(ActivityCompletion.completed_at, ActivityCompletion.user_id == user_id)
    milestones = await per_day(GoalMilestone.completed_at, GoalMilestone.user_id == user_id)
    checkins = await per_day(GoalCheckin.created_at, GoalCheckin.user_id == user_id)
    messages = await per_day(Message.created_at, Message.user_id == user_id, Message.role == "user")
    minutes_day = cast(func.timezone("UTC", GoalCheckin.created_at), Date)
    minutes = dict((await session.execute(
        select(minutes_day, func.coalesce(func.sum(GoalCheckin.minutes), 0))
        .where(GoalCheckin.user_id == user_id, GoalCheckin.created_at >= since).group_by(minutes_day)
    )).all())
    start = since.date()
    series = []
    for offset in range(days + 1):
        day: date = start + timedelta(days=offset)
        series.append({
            "date": day.isoformat(), "activities_completed": activities.get(day, 0), "milestones_completed": milestones.get(day, 0),
            "checkins": checkins.get(day, 0), "minutes_logged": int(minutes.get(day, 0)), "messages": messages.get(day, 0),
        })
    return {"days": days, "series": series}
