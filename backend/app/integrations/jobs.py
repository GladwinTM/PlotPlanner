"""Job listing providers.

Each provider returns ``JobListing`` objects built only from fields the
provider supplied. Compensation is carried exactly as listed by the provider
and tagged with its basis; nothing is estimated here. Results are filtered to
listings that actually mention the user's keywords, because the free public
APIs do loose matching.

Providers:
- Jobicy (remote jobs, no key; credit + link back required by its terms)
- The Muse (remote and on-site, no key; category based)
- Adzuna (optional; enabled when ADZUNA_APP_ID/ADZUNA_APP_KEY are set)

Remotive is deliberately not used: its terms forbid showing listings behind
an account signup, which every PlotPlanner page requires.
"""
import asyncio
import html
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

USER_AGENT = "PlotPlanner/1.0 (+career exploration app)"
CACHE_SECONDS = 1800
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_PERIODS = {"yearly": "year", "annual": "year", "monthly": "month", "weekly": "week", "daily": "day", "hourly": "hour"}

MUSE_CATEGORIES = (
    "Accounting and Finance", "Advertising and Marketing", "Arts", "Business Operations", "Computer and IT",
    "Customer Service", "Data and Analytics", "Design and UX", "Education", "Healthcare",
    "Human Resources and Recruitment", "Legal Services", "Management", "Product Management",
    "Project Management", "Sales", "Science and Engineering", "Software Engineering", "Writing and Editing",
)

_MUSE_KEYWORDS = {
    "Software Engineering": ("software", "developer", "engineer", "backend", "frontend", "python", "javascript", "web", "programming", "devops"),
    "Data and Analytics": ("data", "analytics", "machine learning", "ml", "ai", "statistics", "analyst", "sql"),
    "Design and UX": ("design", "ux", "ui", "figma", "graphic", "illustration", "visual"),
    "Writing and Editing": ("writing", "writer", "editor", "content", "copywriting", "journalism"),
    "Advertising and Marketing": ("marketing", "seo", "social media", "brand", "advertising", "growth"),
    "Education": ("teaching", "teacher", "tutor", "education", "instruction", "curriculum"),
    "Healthcare": ("health", "nurse", "medical", "clinical", "fitness", "wellness"),
    "Accounting and Finance": ("finance", "accounting", "accountant", "investment", "bookkeeping"),
    "Sales": ("sales", "business development", "account executive"),
    "Product Management": ("product manager", "product management"),
    "Project Management": ("project manager", "project management", "scrum"),
    "Customer Service": ("customer", "support", "success"),
    "Arts": ("art", "music", "photography", "video", "film", "animation"),
    "Science and Engineering": ("science", "research", "mechanical", "electrical", "chemistry", "biology"),
}


@dataclass
class JobListing:
    source: str
    external_id: str
    title: str
    company: str | None
    url: str
    location: str | None
    employment_type: str | None
    description: str | None
    tags: list[str] = field(default_factory=list)
    published_at: datetime | None = None
    compensation_min: float | None = None
    compensation_max: float | None = None
    currency: str | None = None
    compensation_text: str | None = None
    compensation_basis: str | None = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    match_text: str = ""


@dataclass
class SearchOutcome:
    listings: list[JobListing]
    providers_used: list[str]
    provider_errors: dict[str, str]


def clean_text(value: str | None, limit: int = 1500) -> str | None:
    if not value:
        return None
    text = _WS.sub(" ", html.unescape(_TAG.sub(" ", value))).strip()
    return text[:limit] or None


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def keywords_for(query: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9+#.]+", query.lower()) if len(word) > 1]


def relevance(listing: JobListing, words: list[str]) -> int:
    """0 means not relevant: every keyword must appear in the listing text.
    Keywords found in the title or tags rank higher."""
    if not words:
        return 1
    haystack = " ".join(filter(None, [listing.title, " ".join(listing.tags), listing.description, listing.match_text])).lower()
    if not all(re.search(rf"\b{re.escape(word)}", haystack) for word in words):
        return 0
    headline = (listing.title + " " + " ".join(listing.tags)).lower()
    return 1 + sum(2 for word in words if word in headline)


def muse_categories_for(query: str) -> list[str]:
    lowered = query.lower()
    hits = [category for category, words in _MUSE_KEYWORDS.items() if any(re.search(rf"\b{re.escape(w)}\b", lowered) for w in words)]
    return hits[:3]


def _format_money(value: float) -> str:
    return f"{value / 1000:.0f}k" if value >= 1000 else f"{value:.0f}"


class JobSearchClient:
    def __init__(
        self,
        *,
        adzuna_app_id: str | None = None,
        adzuna_app_key: str | None = None,
        adzuna_country: str = "us",
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._adzuna = (adzuna_app_id, adzuna_app_key) if adzuna_app_id and adzuna_app_key else None
        self._adzuna_country = adzuna_country
        self._client = httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT}, transport=transport, follow_redirects=True)
        self._cache: dict[tuple, tuple[float, list[JobListing]]] = {}

    @property
    def providers(self) -> list[str]:
        return ["jobicy", "themuse"] + (["adzuna"] if self._adzuna else [])

    @property
    def adzuna_configured(self) -> bool:
        return self._adzuna is not None

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get_json(self, url: str, params: dict | list) -> dict:
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def _cached(self, key: tuple, fetch) -> list[JobListing]:
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]
        listings = await fetch()
        self._cache[key] = (time.monotonic(), listings)
        return listings

    async def _jobicy(self, query: str, geo: str | None) -> list[JobListing]:
        params = {"count": 50}
        words = keywords_for(query)
        if words:
            params["tag"] = max(words, key=len)
        if geo:
            params["geo"] = geo.lower()
        data = await self._get_json("https://jobicy.com/api/v2/remote-jobs", params)
        listings = []
        for job in data.get("jobs", []):
            if not str(job.get("url", "")).startswith("https://"):
                continue
            minimum, maximum = job.get("salaryMin"), job.get("salaryMax")
            currency, period = job.get("salaryCurrency"), job.get("salaryPeriod")
            text = None
            if minimum or maximum:
                low = _format_money(float(minimum)) if minimum else None
                high = _format_money(float(maximum)) if maximum and maximum != minimum else None
                period_word = _PERIODS.get(str(period).lower(), period) if period else None
                text = " - ".join(filter(None, [low, high])) + (f" {currency}" if currency else "") + (f" per {period_word}" if period_word else "")
            job_types = job.get("jobType") or []
            listings.append(
                JobListing(
                    source="jobicy",
                    external_id=str(job["id"]),
                    title=html.unescape(job.get("jobTitle", ""))[:300],
                    company=html.unescape(job.get("companyName") or "")[:200] or None,
                    url=job["url"],
                    location=(job.get("jobGeo") or "Remote")[:300],
                    employment_type=", ".join(job_types)[:80] if isinstance(job_types, list) else str(job_types)[:80],
                    description=clean_text(job.get("jobExcerpt") or job.get("jobDescription")),
                    tags=[str(t) for t in (job.get("jobIndustry") or [])] + ([job["jobLevel"]] if job.get("jobLevel") else []),
                    published_at=_parse_time(job.get("pubDate")),
                    match_text=clean_text(job.get("jobDescription"), 20000) or "",
                    compensation_min=float(minimum) if minimum else None,
                    compensation_max=float(maximum) if maximum else None,
                    currency=currency,
                    compensation_text=text,
                    compensation_basis="employer_provided" if text else None,
                )
            )
        return listings

    async def _muse(self, query: str, location: str | None, remote_only: bool) -> list[JobListing]:
        categories = muse_categories_for(query)
        if not categories:
            return []
        params: list[tuple[str, str]] = [("page", "0")] + [("category", c) for c in categories]
        if remote_only:
            params.append(("location", "Flexible / Remote"))
        elif location:
            params.append(("location", location))
        data = await self._get_json("https://www.themuse.com/api/public/jobs", params)
        listings = []
        for job in data.get("results", []):
            url = (job.get("refs") or {}).get("landing_page", "")
            if not url.startswith("https://"):
                continue
            listings.append(
                JobListing(
                    source="themuse",
                    external_id=str(job["id"]),
                    title=html.unescape(job.get("name", ""))[:300],
                    company=((job.get("company") or {}).get("name") or "")[:200] or None,
                    url=url,
                    location=", ".join(loc["name"] for loc in job.get("locations", []))[:300] or None,
                    employment_type=", ".join(level["name"] for level in job.get("levels", []))[:80] or None,
                    description=clean_text(job.get("contents")),
                    match_text=clean_text(job.get("contents"), 20000) or "",
                    tags=[c["name"] for c in job.get("categories", [])],
                    published_at=_parse_time(job.get("publication_date")),
                )
            )
        return listings

    async def _adzuna_search(self, query: str, location: str | None) -> list[JobListing]:
        assert self._adzuna
        app_id, app_key = self._adzuna
        params = {"app_id": app_id, "app_key": app_key, "results_per_page": 30, "what": query[:100], "content-type": "application/json"}
        if location:
            params["where"] = location[:100]
        data = await self._get_json(f"https://api.adzuna.com/v1/api/jobs/{self._adzuna_country}/search/1", params)
        listings = []
        for job in data.get("results", []):
            url = job.get("redirect_url", "")
            if not url.startswith("https://"):
                continue
            minimum, maximum = job.get("salary_min"), job.get("salary_max")
            # Adzuna marks salaries it predicted itself; label them as such.
            predicted = str(job.get("salary_is_predicted", "0")) == "1"
            text = None
            if minimum or maximum:
                text = " - ".join(_format_money(float(v)) for v in (minimum, maximum) if v) + " per year"
            listings.append(
                JobListing(
                    source="adzuna",
                    external_id=str(job["id"]),
                    title=clean_text(job.get("title"), 300) or "",
                    company=((job.get("company") or {}).get("display_name") or "")[:200] or None,
                    url=url,
                    location=((job.get("location") or {}).get("display_name") or "")[:300] or None,
                    employment_type=job.get("contract_time"),
                    description=clean_text(job.get("description")),
                    tags=[(job.get("category") or {}).get("label", "")],
                    published_at=_parse_time(job.get("created")),
                    compensation_min=float(minimum) if minimum else None,
                    compensation_max=float(maximum) if maximum else None,
                    currency=None,
                    compensation_text=text,
                    compensation_basis=("provider_estimate" if predicted else "employer_provided") if text else None,
                )
            )
        return listings

    async def search(self, query: str, *, location: str | None = None, remote_only: bool = True, limit: int = 30) -> SearchOutcome:
        query = query.strip()[:120]
        words = keywords_for(query)
        tasks: dict[str, asyncio.Future] = {
            "jobicy": self._cached(("jobicy", query.lower(), None), lambda: self._jobicy(query, None)),
            "themuse": self._cached(("themuse", query.lower(), location, remote_only), lambda: self._muse(query, location, remote_only)),
        }
        if self._adzuna:
            tasks["adzuna"] = self._cached(("adzuna", query.lower(), location), lambda: self._adzuna_search(query, location))
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        listings: list[JobListing] = []
        errors: dict[str, str] = {}
        for name, result in zip(tasks, results, strict=True):
            if isinstance(result, BaseException):
                logger.warning("job provider %s failed: %s", name, type(result).__name__)
                errors[name] = "unavailable"
                continue
            listings.extend(result)
        if errors and len(errors) == len(tasks):
            raise ExternalServiceError("Job providers could not be reached. Please try again later.")
        scored = [(relevance(listing, words), listing) for listing in listings]
        scored = [item for item in scored if item[0] > 0]
        scored.sort(key=lambda item: (item[0], item[1].published_at or datetime.min.replace(tzinfo=UTC)), reverse=True)
        return SearchOutcome(listings=[listing for _, listing in scored[:limit]], providers_used=list(tasks), provider_errors=errors)
