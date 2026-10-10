from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request, Response, status

from app.api.deps import CurrentUser, Session, YouTube, rate_limited, require_ai
from app.schemas.courses import CourseDetail, CourseGenerate, CourseRegenerate, CourseSummary, EnrollmentUpdate, ProgressUpdate
from app.services import course_service

router = APIRouter(prefix="/courses", tags=["courses"])


def schedule_generation(request: Request, background: BackgroundTasks, user_id: UUID, course_id: UUID) -> None:
    state = request.app.state
    background.add_task(
        course_service.run_generation, state.session_factory, state.llm, state.youtube, state.url_verifier, user_id, course_id
    )


@router.get("", response_model=list[CourseSummary])
async def list_courses(user: CurrentUser, session: Session, include_archived: bool = False, interest_id: UUID | None = None):
    return await course_service.list_courses(session, user.id, include_archived=include_archived, interest_id=interest_id)


@router.post("/generate", response_model=CourseDetail, status_code=status.HTTP_202_ACCEPTED, dependencies=[rate_limited("ai")])
async def generate_course(payload: CourseGenerate, request: Request, background: BackgroundTasks, user: CurrentUser, session: Session):
    require_ai(request.app.state.llm)
    course = await course_service.request_generation(session, user.id, payload)
    schedule_generation(request, background, user.id, course.id)
    return await course_service.get_course_detail(session, user.id, course.id)


@router.get("/{course_id}", response_model=CourseDetail)
async def read_course(course_id: UUID, user: CurrentUser, session: Session):
    return await course_service.get_course_detail(session, user.id, course_id)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_course(course_id: UUID, user: CurrentUser, session: Session):
    await course_service.archive(session, user.id, course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{course_id}/regenerate", response_model=CourseDetail, status_code=status.HTTP_202_ACCEPTED, dependencies=[rate_limited("ai")])
async def regenerate_course(course_id: UUID, request: Request, background: BackgroundTasks, user: CurrentUser, session: Session, payload: CourseRegenerate | None = None):
    require_ai(request.app.state.llm)
    course = await course_service.request_regeneration(session, user.id, course_id, payload.focus if payload else None)
    schedule_generation(request, background, user.id, course.id)
    return await course_service.get_course_detail(session, user.id, course.id)


@router.post("/{course_id}/enroll", response_model=CourseDetail)
async def enroll(course_id: UUID, user: CurrentUser, session: Session):
    return await course_service.enroll(session, user.id, course_id)


@router.patch("/{course_id}/enrollment", response_model=CourseDetail)
async def update_enrollment(course_id: UUID, payload: EnrollmentUpdate, user: CurrentUser, session: Session):
    return await course_service.update_enrollment(session, user.id, course_id, payload.status)


@router.delete("/{course_id}/enrollment", status_code=status.HTTP_204_NO_CONTENT)
async def leave_course(course_id: UUID, user: CurrentUser, session: Session):
    await course_service.leave(session, user.id, course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{course_id}/modules/{module_id}/progress", response_model=CourseDetail)
async def update_progress(course_id: UUID, module_id: UUID, payload: ProgressUpdate, user: CurrentUser, session: Session):
    return await course_service.update_progress(session, user.id, course_id, module_id, payload)


@router.post("/{course_id}/modules/{module_id}/resources/refresh", response_model=CourseDetail, dependencies=[rate_limited("youtube", per_minute=6)])
async def refresh_resources(course_id: UUID, module_id: UUID, user: CurrentUser, session: Session, youtube: YouTube):
    return await course_service.refresh_module_resources(session, youtube, user.id, course_id, module_id)
