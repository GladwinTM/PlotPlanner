"""Progress is always computed from persisted completion records.

Definitions (shown to users in the UI):
- A module is complete when every activity in it has a completion record.
- Course completion % = completed required modules / required modules * 100.
  Optional modules never lower the percentage; they are reported separately.
- Goal progress % = completed milestones / milestones * 100.
"""
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ActivityCompletion, CourseActivity, CourseModule


@dataclass
class NextActivity:
    module_id: UUID
    module_title: str
    activity_id: UUID
    activity_title: str
    kind: str


@dataclass
class CourseProgress:
    required_modules: int = 0
    completed_required_modules: int = 0
    optional_modules: int = 0
    completed_optional_modules: int = 0
    activities: int = 0
    completed_activities: int = 0
    completed_activity_ids: set[UUID] = field(default_factory=set)
    completed_module_ids: set[UUID] = field(default_factory=set)
    next_activity: NextActivity | None = None

    @property
    def percent(self) -> int:
        if not self.required_modules:
            return 0
        return round(self.completed_required_modules / self.required_modules * 100)


async def course_progress(session: AsyncSession, user_id: UUID, course_ids: list[UUID]) -> dict[UUID, CourseProgress]:
    result: dict[UUID, CourseProgress] = {course_id: CourseProgress() for course_id in course_ids}
    if not course_ids:
        return result
    rows = await session.execute(
        select(
            CourseModule.course_id, CourseModule.id, CourseModule.title, CourseModule.required,
            CourseActivity.id, CourseActivity.title, CourseActivity.kind, ActivityCompletion.id,
        )
        .join(CourseActivity, CourseActivity.module_id == CourseModule.id)
        .outerjoin(
            ActivityCompletion,
            and_(ActivityCompletion.activity_id == CourseActivity.id, ActivityCompletion.user_id == user_id),
        )
        .where(CourseModule.course_id.in_(course_ids))
        .order_by(CourseModule.course_id, CourseModule.position, CourseActivity.position)
    )
    modules: dict[UUID, dict] = {}
    for course_id, module_id, module_title, required, activity_id, activity_title, kind, completion_id in rows:
        progress = result[course_id]
        progress.activities += 1
        info = modules.setdefault(module_id, {"course": course_id, "required": required, "done": True})
        if completion_id is not None:
            progress.completed_activities += 1
            progress.completed_activity_ids.add(activity_id)
        else:
            info["done"] = False
            if progress.next_activity is None:
                progress.next_activity = NextActivity(module_id, module_title, activity_id, activity_title, kind)
    for module_id, info in modules.items():
        progress = result[info["course"]]
        if info["required"]:
            progress.required_modules += 1
            progress.completed_required_modules += info["done"]
        else:
            progress.optional_modules += 1
            progress.completed_optional_modules += info["done"]
        if info["done"]:
            progress.completed_module_ids.add(module_id)
    return result
