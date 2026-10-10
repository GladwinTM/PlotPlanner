"""Things That Can Pay for You.

- Job search: listings come only from provider APIs and are stored with their
  source URL and retrieval time. Search results are kept as ``found`` rows so
  they can be saved and tracked; re-searching never overwrites a user's
  status or notes.
- Fit labels are AI assessments and are labelled as such.
- Salary guidance aggregates only salaries present in current listings and
  keeps employer-provided figures separate from provider estimates.
- Earning plans are AI guidance following a fixed 10-point structure.
"""
import logging
import statistics
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import prompts
from app.ai.llm_client import LLMClient
from app.ai.schemas import EarningPlanDraft, FitAssessments
from app.core.exceptions import AppError, NotFoundError
from app.db.models import EarningPlan, Interest, Opportunity
from app.integrations.jobs import JobListing, JobSearchClient
from app.schemas.opportunities import (
    OpportunityRead, PlanRequest, SalaryEvidence, SalaryGroup, SalaryResponse, SearchRequest, SearchResponse,
)
from app.services.context import build_user_context, context_json

logger = logging.getLogger(__name__)

ATTRIBUTION = {
    "jobicy": {"name": "Jobicy", "url": "https://jobicy.com"},
    "themuse": {"name": "The Muse", "url": "https://www.themuse.com"},
    "adzuna": {"name": "Adzuna", "url": "https://www.adzuna.com"},
}
FIT_BATCH = 12


def _opportunity_type(listing: JobListing) -> str:
    text = (listing.employment_type or "").lower()
    if "part" in text:
        return "part_time"
    if "contract" in text:
        return "contract"
    if "intern" in text:
        return "internship"
    if "freelance" in text or "freelance" in listing.title.lower():
        return "freelance"
    return "full_time"


def _period(text: str | None) -> str:
    lowered = (text or "").lower()
    for word in ("hour", "day", "week", "month", "year"):
        if f"per {word}" in lowered:
            return word
    return "year"


async def _store(session: AsyncSession, user_id: UUID, listings: list[JobListing]) -> list[Opportunity]:
    if not listings:
        return []
    for listing in listings:
        values = {
            "user_id": user_id, "opportunity_type": _opportunity_type(listing), "title": listing.title[:300] or "Untitled role",
            "company": listing.company, "description": listing.description, "source": listing.source,
            "canonical_url": listing.url[:1000], "location": listing.location, "employment_type": listing.employment_type,
            "compensation_min": listing.compensation_min, "compensation_max": listing.compensation_max,
            "currency": listing.currency, "compensation_text": listing.compensation_text,
            "compensation_basis": listing.compensation_basis,
            "requirements": ", ".join(t for t in listing.tags if t)[:2000] or None,
            "external_id": listing.external_id[:200], "published_at": listing.published_at,
            "retrieved_at": listing.retrieved_at,
        }
        refreshed = {k: values[k] for k in (
            "title", "company", "description", "canonical_url", "location", "employment_type", "compensation_min",
            "compensation_max", "currency", "compensation_text", "compensation_basis", "requirements",
            "published_at", "retrieved_at",
        )}
        await session.execute(
            pg_insert(Opportunity).values(**values).on_conflict_do_update(
                index_elements=["user_id", "source", "external_id"], set_={**refreshed, "updated_at": datetime.now(UTC)},
            )
        )
    await session.flush()
    keys = [(listing.source, listing.external_id[:200]) for listing in listings]
    rows = (await session.scalars(
        select(Opportunity).where(Opportunity.user_id == user_id, Opportunity.external_id.in_([k[1] for k in keys]))
        .execution_options(populate_existing=True)
    )).all()
    by_key = {(row.source, row.external_id): row for row in rows}
    return [by_key[key] for key in keys if key in by_key]


async def search(session: AsyncSession, llm: LLMClient, jobs: JobSearchClient, user_id: UUID, request: SearchRequest) -> SearchResponse:
    outcome = await jobs.search(request.query, location=request.location, remote_only=request.remote_only)
    stored = await _store(session, user_id, outcome.listings)
    stored_ids = [o.id for o in stored]
    await session.commit()

    fit_assessed, fit_note = False, None
    if stored and request.assess_fit:
        if not llm.configured:
            fit_note = "Fit labels need AI, which is not configured."
        else:
            try:
                await _assess_fit(session, llm, user_id, stored[:FIT_BATCH])
                fit_assessed = True
                if len(stored) > FIT_BATCH:
                    fit_note = f"AI fit labels were added to the top {FIT_BATCH} results."
            except AppError as exc:
                await session.rollback()
                fit_note = f"Fit labels unavailable: {exc.message}"
    rows = (await session.scalars(
        select(Opportunity).where(Opportunity.id.in_(stored_ids)).execution_options(populate_existing=True)
    )).all() if stored_ids else []
    by_id = {row.id: row for row in rows}
    return SearchResponse(
        results=[OpportunityRead.model_validate(by_id[i]) for i in stored_ids if i in by_id],
        providers=outcome.providers_used,
        provider_errors=outcome.provider_errors,
        fit_assessed=fit_assessed,
        fit_note=fit_note,
        attribution=[ATTRIBUTION[p] for p in outcome.providers_used if p in ATTRIBUTION],
    )


async def _assess_fit(session: AsyncSession, llm: LLMClient, user_id: UUID, opportunities: list[Opportunity]) -> None:
    context = await build_user_context(session, user_id, goals=False)
    listings = "\n".join(
        f"[{index}] {o.title} at {o.company or 'unknown company'} | {o.location or ''} | tags: {o.requirements or ''} | "
        f"{(o.description or '')[:500]}"
        for index, o in enumerate(opportunities)
    )
    result = await llm.complete_structured(
        system=prompts.FIT_ASSESSMENT,
        messages=[{"role": "user", "content": prompts.tagged("user_data", context_json(context)) + "\n" + prompts.tagged("tool_result", listings)}],
        schema=FitAssessments,
        max_tokens=3000,
    )
    for assessment in result.assessments:
        if 0 <= assessment.listing_number < len(opportunities):
            opportunity = opportunities[assessment.listing_number]
            opportunity.fit_level = assessment.fit_level
            opportunity.fit_reason = assessment.reason
    await session.commit()


async def list_opportunities(session: AsyncSession, user_id: UUID, status: str | None) -> list[Opportunity]:
    query = select(Opportunity).where(Opportunity.user_id == user_id)
    query = query.where(Opportunity.status == status) if status else query.where(Opportunity.status != "found")
    return list((await session.scalars(query.order_by(Opportunity.updated_at.desc()).limit(200))).all())


async def get_opportunity(session: AsyncSession, user_id: UUID, opportunity_id: UUID) -> Opportunity:
    opportunity = await session.scalar(select(Opportunity).where(Opportunity.id == opportunity_id, Opportunity.user_id == user_id))
    if opportunity is None:
        raise NotFoundError("Opportunity not found")
    return opportunity


async def set_status(session: AsyncSession, user_id: UUID, opportunity_id: UUID, status: str, notes: str | None = None, *, notes_set: bool = False) -> Opportunity:
    opportunity = await get_opportunity(session, user_id, opportunity_id)
    opportunity.status = status
    if notes_set:
        opportunity.notes = notes
    opportunity.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(opportunity)
    return opportunity


async def delete_opportunity(session: AsyncSession, user_id: UUID, opportunity_id: UUID) -> None:
    await session.delete(await get_opportunity(session, user_id, opportunity_id))
    await session.commit()


async def salary(jobs: JobSearchClient, request) -> SalaryResponse:
    outcome = await jobs.search(request.role, location=request.location, remote_only=request.remote_only, limit=60)
    with_pay = [l for l in outcome.listings if l.compensation_text and (l.compensation_min or l.compensation_max)]
    groups: dict[tuple[str, str, str], list[float]] = {}
    for listing in with_pay:
        values = [v for v in (listing.compensation_min, listing.compensation_max) if v]
        midpoint = sum(values) / len(values)
        key = (listing.currency or "unspecified", _period(listing.compensation_text), listing.compensation_basis or "employer_provided")
        groups.setdefault(key, []).append(midpoint)
    group_reads = [
        SalaryGroup(currency=currency, period=period, basis=basis, sample_size=len(values),
                    low=min(values), median=statistics.median(values), high=max(values))
        for (currency, period, basis), values in sorted(groups.items(), key=lambda item: -len(item[1]))
    ]
    note = (
        "Figures are the midpoints of salary ranges published in current listings. They describe these specific "
        "listings only and are not a guarantee or a full market survey; pay varies by location, company, seniority and industry."
        if with_pay else
        "None of the current listings for this role published a salary, so there is no verified salary evidence to show. "
        "Check official labour statistics for your country or salary data on the employer's careers page."
    )
    return SalaryResponse(
        role=request.role, listings_checked=len(outcome.listings), groups=group_reads,
        evidence=[
            SalaryEvidence(title=l.title, company=l.company, location=l.location, compensation_text=l.compensation_text,
                           basis=l.compensation_basis or "employer_provided", source=l.source, url=l.url, retrieved_at=l.retrieved_at)
            for l in with_pay[:20]
        ],
        note=note,
    )


async def create_plan(session: AsyncSession, llm: LLMClient, user_id: UUID, request: PlanRequest) -> EarningPlan:
    context = await build_user_context(session, user_id, goals=True, courses=True)
    interest = None
    if request.interest_id:
        interest = await session.scalar(select(Interest).where(Interest.id == request.interest_id, Interest.user_id == user_id))
        if interest is None:
            raise NotFoundError("Interest not found")
        context["focus_interest"] = {"name": interest.name, "description": interest.description}
    if request.kind:
        context["requested_kind"] = request.kind
    if request.focus:
        context["requested_focus"] = request.focus
    draft = await llm.complete_structured(
        system=prompts.EARNING_PLAN,
        messages=[{"role": "user", "content": prompts.tagged("user_data", context_json(context))}],
        schema=EarningPlanDraft,
        max_tokens=4000,
    )
    plan = EarningPlan(
        user_id=user_id, interest_id=interest.id if interest else None, title=draft.title, kind=draft.kind,
        plan={**draft.model_dump(exclude={"title", "kind"}), "generated_by": "ai", "prompt_version": prompts.PROMPT_VERSION},
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def list_plans(session: AsyncSession, user_id: UUID) -> list[EarningPlan]:
    return list((await session.scalars(
        select(EarningPlan).where(EarningPlan.user_id == user_id).order_by(EarningPlan.created_at.desc())
    )).all())


async def delete_plan(session: AsyncSession, user_id: UUID, plan_id: UUID) -> None:
    plan = await session.scalar(select(EarningPlan).where(EarningPlan.id == plan_id, EarningPlan.user_id == user_id))
    if plan is None:
        raise NotFoundError("Earning plan not found")
    await session.delete(plan)
    await session.commit()
