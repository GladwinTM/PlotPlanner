from fastapi import APIRouter, BackgroundTasks, Request, Response, status

from app.api.courses import schedule_generation
from app.api.deps import LLM, CurrentUser, Session, rate_limited, require_ai
from app.schemas.onboarding import CompleteResponse, OnboardingDraft, OnboardingStatus, TurnRequest, TurnResponse
from app.services import onboarding_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status", response_model=OnboardingStatus)
async def read_status(user: CurrentUser, session: Session, llm: LLM):
    return await onboarding_service.status(session, user, llm)


@router.post("/start", response_model=OnboardingStatus)
async def start(user: CurrentUser, session: Session, llm: LLM):
    return await onboarding_service.start(session, user, llm)


@router.post("/turn", response_model=TurnResponse, dependencies=[rate_limited("ai")])
async def submit_turn(payload: TurnRequest, user: CurrentUser, session: Session, llm: LLM):
    require_ai(llm)
    result, assessment = await onboarding_service.turn(session, llm, user, payload.message)
    return TurnResponse(status=result, assessment=assessment)


@router.post("/retry", response_model=OnboardingStatus, dependencies=[rate_limited("ai")])
async def retry(user: CurrentUser, session: Session, llm: LLM):
    require_ai(llm)
    return await onboarding_service.retry(session, llm, user)


@router.put("/draft", response_model=OnboardingStatus)
async def save_draft(payload: OnboardingDraft, user: CurrentUser, session: Session, llm: LLM):
    return await onboarding_service.save_draft(session, user, llm, payload)


@router.post("/complete", response_model=CompleteResponse, dependencies=[rate_limited("ai")])
async def complete(payload: OnboardingDraft, request: Request, background: BackgroundTasks, user: CurrentUser, session: Session, llm: LLM):
    response, goal_ids, course_ids = await onboarding_service.complete(session, llm, user, payload)
    for course_id in course_ids:
        schedule_generation(request, background, user.id, course_id)
    if goal_ids:
        background.add_task(onboarding_service.run_initial_goal_plans, request.app.state.session_factory, llm, user.id, goal_ids)
    return response


@router.post("/skip", status_code=status.HTTP_204_NO_CONTENT)
async def skip(user: CurrentUser, session: Session):
    await onboarding_service.skip(session, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
