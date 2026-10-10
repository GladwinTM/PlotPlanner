"""Learning pathways.

Generation is an explicit job: the API creates a course in ``generating``
state and returns immediately; ``run_generation`` (a background task) asks the
LLM for the outline, attaches only resources verified at retrieval time, and
flips the status to ``ready`` or ``failed``.

Regeneration creates a new version and archives the old one only after the
new one succeeds, so completion history is never lost.
"""
import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.ai import prompts
from app.ai.llm_client import BACKGROUND_RATE_LIMIT_WAIT, LLMClient
from app.ai.schemas import CourseOutline
from app.core.exceptions import AppError, BadRequestError, ConflictError, NotFoundError
from app.db.models import (
    ActivityCompletion, Course, CourseActivity, CourseModule, Enrollment, Goal, Interest, LearningResource,
)
from app.integrations.web import UrlVerifier
from app.integrations.youtube import VerifiedVideo, YouTubeClient
from app.schemas.courses import (
    ActivityRead, CourseDetail, CourseGenerate, CourseSummary, EnrollmentRead, ModuleRead, NextActivityRead,
    ProgressRead, ProgressUpdate, ResourceRead,
)
from app.services.context import build_user_context, context_json
from app.services.progress import CourseProgress, course_progress

logger = logging.getLogger(__name__)

STALE_GENERATION = timedelta(minutes=10)
VIDEOS_PER_MODULE = 3
MAX_ACTIVE_COURSES = 60


# --- Reading ----------------------------------------------------------------

def _progress_read(progress: CourseProgress) -> ProgressRead:
    return ProgressRead(
        percent=progress.percent,
        required_modules=progress.required_modules,
        completed_required_modules=progress.completed_required_modules,
        optional_modules=progress.optional_modules,
        completed_optional_modules=progress.completed_optional_modules,
        activities=progress.activities,
        completed_activities=progress.completed_activities,
    )


def _next_read(progress: CourseProgress) -> NextActivityRead | None:
    n = progress.next_activity
    return NextActivityRead(module_id=n.module_id, module_title=n.module_title, activity_id=n.activity_id, activity_title=n.activity_title, kind=n.kind) if n else None


async def _mark_stale(session: AsyncSession, courses: list[Course]) -> None:
    """A generation interrupted by a restart would otherwise stay 'generating' forever."""
    now = datetime.now(UTC)
    changed = False
    for course in courses:
        if course.status == "generating" and now - course.updated_at > STALE_GENERATION:
            course.status = "failed"
            course.error = "Generation was interrupted. Please try again."
            course.updated_at = now
            changed = True
    if changed:
        await session.commit()


async def _summaries(session: AsyncSession, user_id: UUID, courses: list[Course]) -> list[CourseSummary]:
    await _mark_stale(session, courses)
    ids = [course.id for course in courses]
    progress = await course_progress(session, user_id, ids)
    enrollments = {e.course_id: e for e in (await session.scalars(
        select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id.in_(ids))
    )).all()} if ids else {}
    interest_ids = {c.interest_id for c in courses if c.interest_id}
    names = dict((await session.execute(
        select(Interest.id, Interest.name).where(Interest.user_id == user_id, Interest.id.in_(interest_ids))
    )).all()) if interest_ids else {}
    module_counts = dict((await session.execute(
        select(CourseModule.course_id, func.count()).where(CourseModule.course_id.in_(ids)).group_by(CourseModule.course_id)
    )).all()) if ids else {}
    return [
        CourseSummary(
            id=c.id, title=c.title, description=c.description, objective=c.objective, interest_id=c.interest_id,
            interest_name=names.get(c.interest_id), goal_id=c.goal_id, difficulty=c.difficulty,
            estimated_hours=c.estimated_hours, status=c.status, error=c.error, version=c.version,
            previous_version_id=c.previous_version_id, created_at=c.created_at, updated_at=c.updated_at,
            enrollment=EnrollmentRead.model_validate(enrollments[c.id]) if c.id in enrollments else None,
            progress=_progress_read(progress[c.id]), next_activity=_next_read(progress[c.id]),
            module_count=module_counts.get(c.id, 0),
        )
        for c in courses
    ]


async def list_courses(session: AsyncSession, user_id: UUID, *, include_archived: bool = False, interest_id: UUID | None = None) -> list[CourseSummary]:
    query = select(Course).where(Course.user_id == user_id)
    if not include_archived:
        query = query.where(Course.status != "archived")
    if interest_id:
        query = query.where(Course.interest_id == interest_id)
    courses = list((await session.scalars(query.order_by(Course.created_at.desc()))).all())
    return await _summaries(session, user_id, courses)


async def _get_course(session: AsyncSession, user_id: UUID, course_id: UUID, *, with_content: bool = False) -> Course:
    query = select(Course).where(Course.id == course_id, Course.user_id == user_id)
    if with_content:
        query = query.options(
            selectinload(Course.modules).selectinload(CourseModule.activities),
            selectinload(Course.modules).selectinload(CourseModule.resources),
        ).execution_options(populate_existing=True)
    course = await session.scalar(query)
    if course is None:
        raise NotFoundError("Course not found")
    return course


async def get_course_detail(session: AsyncSession, user_id: UUID, course_id: UUID) -> CourseDetail:
    course = await _get_course(session, user_id, course_id, with_content=True)
    summary = (await _summaries(session, user_id, [course]))[0]
    activity_ids = [a.id for module in course.modules for a in module.activities]
    completions = {c.activity_id: c for c in (await session.scalars(
        select(ActivityCompletion).where(ActivityCompletion.user_id == user_id, ActivityCompletion.activity_id.in_(activity_ids))
    )).all()} if activity_ids else {}
    modules = []
    for module in course.modules:
        activities = [
            ActivityRead(
                id=a.id, position=a.position, kind=a.kind, title=a.title, instructions=a.instructions,
                estimated_minutes=a.estimated_minutes, completed=a.id in completions,
                completed_at=completions[a.id].completed_at if a.id in completions else None,
                notes=completions[a.id].notes if a.id in completions else None,
            )
            for a in module.activities
        ]
        modules.append(ModuleRead(
            id=module.id, position=module.position, title=module.title, description=module.description,
            learning_objectives=module.learning_objectives, completion_criteria=module.completion_criteria,
            required=module.required, completed=bool(activities) and all(a.completed for a in activities),
            activities=activities, resources=[ResourceRead.model_validate(r) for r in module.resources],
            resource_query=(module.resource_queries or [None])[0],
        ))
    return CourseDetail(**summary.model_dump(), prerequisites=course.prerequisites, focus=course.focus, modules=modules)


# --- Generation -------------------------------------------------------------

async def request_generation(session: AsyncSession, user_id: UUID, payload: CourseGenerate) -> Course:
    if not (payload.interest_id or payload.goal_id or payload.topic):
        raise BadRequestError("Choose an interest, a goal or a topic for the learning pathway")
    title = payload.topic or ""
    if payload.interest_id:
        interest = await session.scalar(select(Interest).where(Interest.id == payload.interest_id, Interest.user_id == user_id))
        if not interest:
            raise NotFoundError("Interest not found")
        title = title or interest.name
    if payload.goal_id:
        goal = await session.scalar(select(Goal).where(Goal.id == payload.goal_id, Goal.user_id == user_id))
        if not goal:
            raise NotFoundError("Goal not found")
        title = title or goal.title
    active = await session.scalar(select(func.count()).select_from(Course).where(Course.user_id == user_id, Course.status != "archived"))
    if active >= MAX_ACTIVE_COURSES:
        raise BadRequestError("You have reached the course limit. Archive a course before generating another.")
    in_flight = await session.scalar(select(func.count()).select_from(Course).where(Course.user_id == user_id, Course.status == "generating"))
    if in_flight >= 3:
        raise ConflictError("Three pathways are already being generated. Please wait for them to finish.")
    course = Course(
        user_id=user_id, interest_id=payload.interest_id, goal_id=payload.goal_id,
        title=title[:200], focus=payload.focus, status="generating",
    )
    session.add(course)
    await session.commit()
    return course


async def request_regeneration(session: AsyncSession, user_id: UUID, course_id: UUID, focus: str | None) -> Course:
    old = await _get_course(session, user_id, course_id)
    if old.status in ("generating", "archived"):
        raise ConflictError("Only ready or failed pathways can be regenerated")
    if await session.scalar(select(Course.id).where(Course.previous_version_id == old.id, Course.status == "generating")):
        raise ConflictError("A new version is already being generated")
    course = Course(
        user_id=user_id, interest_id=old.interest_id, goal_id=old.goal_id, title=old.title,
        focus=focus or old.focus, status="generating", version=old.version + 1, previous_version_id=old.id,
    )
    session.add(course)
    await session.commit()
    return course


async def _find_videos(youtube: YouTubeClient, query: str) -> tuple[list[VerifiedVideo], str | None]:
    if not youtube.configured:
        return [], "YouTube search is not configured"
    try:
        return await youtube.search_videos(query, max_results=VIDEOS_PER_MODULE), None
    except AppError as exc:
        return [], exc.message


async def run_generation(
    session_factory: async_sessionmaker, llm: LLMClient, youtube: YouTubeClient, verifier: UrlVerifier,
    user_id: UUID, course_id: UUID,
) -> None:
    async with session_factory() as session:
        course = await session.scalar(select(Course).where(Course.id == course_id, Course.user_id == user_id))
        if course is None or course.status != "generating":
            return
        try:
            await _generate_into(session, llm, youtube, verifier, user_id, course)
        except Exception as exc:  # recorded on the course so the user sees a real failure
            await session.rollback()
            course = await session.scalar(select(Course).where(Course.id == course_id))
            if course is None:
                return
            course.status = "failed"
            course.error = exc.message if isinstance(exc, AppError) else "Pathway generation failed unexpectedly."
            course.updated_at = datetime.now(UTC)
            await session.commit()
            if not isinstance(exc, AppError):
                logger.exception("course generation failed", exc_info=exc)


async def _generate_into(session, llm, youtube, verifier, user_id: UUID, course: Course) -> None:
    context = await build_user_context(session, user_id, goals=True, interests=True)
    target: dict = {"topic": course.title}
    if course.interest_id:
        interest = await session.scalar(select(Interest).where(Interest.id == course.interest_id))
        if interest:
            target = {"interest": interest.name, "description": interest.description, "type": interest.interest_type,
                      "wants_to_earn_from_it": interest.seeks_income}
    if course.goal_id:
        goal = await session.scalar(select(Goal).where(Goal.id == course.goal_id))
        if goal:
            target["goal"] = {"title": goal.title, "target_outcome": goal.target_outcome, "hours_per_week": goal.hours_per_week}
    if course.focus:
        target["focus"] = course.focus
    if course.previous_version_id:
        previous = await session.scalar(select(Course).where(Course.id == course.previous_version_id))
        if previous:
            target["previous_version_title"] = previous.title
            target["regeneration"] = "Create an improved version that reflects the focus and the user's current context."
    context["pathway_target"] = target
    outline = await llm.complete_structured(
        system=prompts.COURSE_OUTLINE,
        messages=[{"role": "user", "content": prompts.tagged("user_data", context_json(context))}],
        schema=CourseOutline,
        max_tokens=7000,
        rate_limit_wait=BACKGROUND_RATE_LIMIT_WAIT,
    )

    video_results = await asyncio.gather(*[_find_videos(youtube, module.video_search_query) for module in outline.modules])
    doc_candidates = [(index, link) for index, module in enumerate(outline.modules) for link in module.official_documentation]
    doc_results = await asyncio.gather(*[verifier.verify(link.url) for _, link in doc_candidates])

    retrieved = datetime.now(UTC)
    for index, draft in enumerate(outline.modules):
        module = CourseModule(
            course_id=course.id, position=index, title=draft.title, description=draft.description,
            learning_objectives=draft.learning_objectives, completion_criteria=draft.completion_criteria,
            required=draft.required, resource_queries=[draft.video_search_query],
        )
        session.add(module)
        await session.flush()
        for position, activity in enumerate(draft.activities):
            session.add(CourseActivity(
                module_id=module.id, position=position, kind=activity.kind, title=activity.title,
                instructions=activity.instructions, estimated_minutes=activity.estimated_minutes,
            ))
        videos, _ = video_results[index]
        seen = set()
        for video in videos:
            seen.add(video.url)
            session.add(_video_resource(module.id, video))
        for (doc_index, link), verified in zip(doc_candidates, doc_results, strict=True):
            if doc_index == index and verified and verified.url not in seen:
                seen.add(verified.url)
                session.add(LearningResource(
                    module_id=module.id, title=link.title[:300], provider=verified.host[:80], channel=None,
                    canonical_url=verified.url[:500], resource_type="documentation", cost_status="unknown",
                    retrieved_at=retrieved, verification_status="verified",
                ))

    course.title = outline.title
    course.description = outline.description
    course.objective = outline.objective
    course.difficulty = outline.difficulty
    course.estimated_hours = outline.estimated_hours
    course.prerequisites = outline.prerequisites
    youtube_errors = {error for _, error in video_results if error}
    course.error = ("Some video resources could not be retrieved: " + "; ".join(sorted(youtube_errors))) if youtube_errors else None
    course.status = "ready"
    course.updated_at = datetime.now(UTC)

    if course.previous_version_id:
        previous = await session.scalar(select(Course).where(Course.id == course.previous_version_id))
        if previous and previous.status != "archived":
            previous.status = "archived"
            previous.updated_at = datetime.now(UTC)
            old_enrollment = await session.scalar(
                select(Enrollment).where(Enrollment.course_id == previous.id, Enrollment.user_id == user_id)
            )
            if old_enrollment and old_enrollment.status in ("active", "paused"):
                session.add(Enrollment(user_id=user_id, course_id=course.id, status=old_enrollment.status))
    await session.commit()


def _video_resource(module_id: UUID, video: VerifiedVideo) -> LearningResource:
    return LearningResource(
        module_id=module_id, title=video.title or "YouTube video", provider="YouTube", channel=video.channel or None,
        canonical_url=video.url, resource_type="video", cost_status="free", duration_seconds=video.duration_seconds,
        published_at=video.published_at, retrieved_at=video.retrieved_at, verification_status="verified",
        external_id=video.video_id,
    )


async def refresh_module_resources(session: AsyncSession, youtube: YouTubeClient, user_id: UUID, course_id: UUID, module_id: UUID) -> CourseDetail:
    """Re-check existing videos and look for new ones. Videos no longer
    available are kept but marked unavailable so the change is visible."""
    course = await _get_course(session, user_id, course_id, with_content=True)
    module = next((m for m in course.modules if m.id == module_id), None)
    if module is None:
        raise NotFoundError("Module not found")
    existing = {r.external_id: r for r in module.resources if r.provider == "YouTube" and r.external_id}
    if existing:
        still_available = {v.video_id: v for v in await youtube.verify_videos(list(existing))}
        for video_id, resource in existing.items():
            if video_id in still_available:
                resource.verification_status = "verified"
                resource.retrieved_at = still_available[video_id].retrieved_at
            else:
                resource.verification_status = "unavailable"
                resource.retrieved_at = datetime.now(UTC)
    query = (module.resource_queries or [f"{course.title} {module.title}"])[0]
    known_urls = {r.canonical_url for r in module.resources}
    for video in await youtube.search_videos(query, max_results=VIDEOS_PER_MODULE):
        if video.url not in known_urls:
            session.add(_video_resource(module.id, video))
    await session.commit()
    return await get_course_detail(session, user_id, course_id)


# --- Enrollment and progress ------------------------------------------------

async def _enrollment(session: AsyncSession, user_id: UUID, course_id: UUID) -> Enrollment | None:
    return await session.scalar(select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id))


async def enroll(session: AsyncSession, user_id: UUID, course_id: UUID) -> CourseDetail:
    course = await _get_course(session, user_id, course_id)
    if course.status != "ready":
        raise ConflictError("You can enroll once the pathway is ready")
    enrollment = await _enrollment(session, user_id, course_id)
    if enrollment is None:
        session.add(Enrollment(user_id=user_id, course_id=course_id, status="active"))
    elif enrollment.status in ("paused", "abandoned"):
        enrollment.status = "active"
    await session.commit()
    return await get_course_detail(session, user_id, course_id)


async def update_enrollment(session: AsyncSession, user_id: UUID, course_id: UUID, status: str) -> CourseDetail:
    await _get_course(session, user_id, course_id)
    enrollment = await _enrollment(session, user_id, course_id)
    if enrollment is None:
        raise ConflictError("You are not enrolled in this pathway")
    enrollment.status = status
    if status != "completed":
        enrollment.completed_at = None
    await session.commit()
    return await get_course_detail(session, user_id, course_id)


async def leave(session: AsyncSession, user_id: UUID, course_id: UUID) -> None:
    """Remove the enrollment. Activity completions are kept so re-enrolling resumes progress."""
    await _get_course(session, user_id, course_id)
    enrollment = await _enrollment(session, user_id, course_id)
    if enrollment is None:
        raise NotFoundError("You are not enrolled in this pathway")
    await session.delete(enrollment)
    await session.commit()


async def archive(session: AsyncSession, user_id: UUID, course_id: UUID) -> None:
    course = await _get_course(session, user_id, course_id)
    if course.status == "generating":
        raise ConflictError("Wait for generation to finish before archiving")
    course.status = "archived"
    course.updated_at = datetime.now(UTC)
    await session.commit()


async def update_progress(session: AsyncSession, user_id: UUID, course_id: UUID, module_id: UUID, payload: ProgressUpdate) -> CourseDetail:
    await _get_course(session, user_id, course_id)
    activity = await session.scalar(
        select(CourseActivity).join(CourseModule, CourseModule.id == CourseActivity.module_id)
        .where(CourseActivity.id == payload.activity_id, CourseModule.id == module_id, CourseModule.course_id == course_id)
    )
    if activity is None:
        raise NotFoundError("Activity not found in this module")
    enrollment = await _enrollment(session, user_id, course_id)
    if enrollment is None:
        raise ConflictError("Enroll in this pathway to record progress")
    if enrollment.status in ("paused", "abandoned"):
        raise ConflictError("This pathway is paused. Resume it to record progress.")
    completion = await session.scalar(
        select(ActivityCompletion).where(ActivityCompletion.user_id == user_id, ActivityCompletion.activity_id == activity.id)
    )
    if payload.completed:
        if completion is None:
            session.add(ActivityCompletion(user_id=user_id, activity_id=activity.id, notes=payload.notes))
        elif payload.notes is not None:
            completion.notes = payload.notes
    elif completion is not None:
        await session.delete(completion)
    await session.flush()

    progress = (await course_progress(session, user_id, [course_id]))[course_id]
    if progress.required_modules and progress.completed_required_modules == progress.required_modules:
        if enrollment.status != "completed":
            enrollment.status = "completed"
            enrollment.completed_at = datetime.now(UTC)
    elif enrollment.status == "completed":
        enrollment.status = "active"
        enrollment.completed_at = None
    await session.commit()
    return await get_course_detail(session, user_id, course_id)
