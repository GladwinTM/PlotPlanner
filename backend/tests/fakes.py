"""Deterministic test doubles. The LLM is scripted per output schema; the
YouTube, job-board and link-check clients are the real clients pointed at
httpx mock transports, so their parsing and filtering are exercised."""
import json
from collections import defaultdict

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.llm_client import AIProviderError, ChatResult, ToolCall


class FakeLLM:
    configured = True

    def __init__(self):
        self.structured: dict[str, list] = defaultdict(list)
        self.chat_replies: list = []
        self.calls: list[dict] = []

    def queue(self, schema_name: str, *responses) -> None:
        self.structured[schema_name].extend(responses)

    async def complete_structured(self, *, system, messages, schema, max_tokens=2000, **_):
        self.calls.append({"kind": "structured", "schema": schema.__name__, "system": system, "messages": messages})
        if not self.structured[schema.__name__]:
            raise AssertionError(f"FakeLLM has no scripted response for {schema.__name__}")
        response = self.structured[schema.__name__].pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, BaseModel):
            return response
        try:
            return schema.model_validate(response)
        except ValidationError as exc:
            raise AIProviderError("The AI returned an invalid response. Nothing was changed; please try again.") from exc

    async def chat(self, *, messages, tools=None, max_tokens=1500, **_):
        self.calls.append({"kind": "chat", "messages": messages, "tools": tools})
        if not self.chat_replies:
            raise AssertionError("FakeLLM has no scripted chat reply")
        reply = self.chat_replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, str):
            return ChatResult(content=reply, raw_message={"role": "assistant", "content": reply})
        calls = [ToolCall(id=f"call_{i}", name=name, arguments=args) for i, (name, args) in enumerate(reply)]
        raw = {"role": "assistant", "content": "", "tool_calls": [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.arguments)}} for c in calls
        ]}
        return ChatResult(content=None, tool_calls=calls, raw_message=raw)

    async def aclose(self):
        pass


class UnconfiguredLLM(FakeLLM):
    configured = False


# --- YouTube ----------------------------------------------------------------

def video_item(video_id: str, *, title: str = "Tutorial", duration: str = "PT12M30S", privacy: str = "public") -> dict:
    return {
        "id": video_id,
        "snippet": {"title": title, "channelTitle": "Real Channel", "publishedAt": "2025-01-02T03:04:05Z"},
        "contentDetails": {"duration": duration},
        "status": {"privacyStatus": privacy, "uploadStatus": "processed"},
    }


class YouTubeMock:
    """search returns ``search_ids``; videos.list returns only ``available`` items."""

    def __init__(self):
        self.search_ids = ["vid_ok_1", "vid_ok_2", "vid_private", "vid_short"]
        self.available = {
            "vid_ok_1": video_item("vid_ok_1", title="Intro &amp; Basics"),
            "vid_ok_2": video_item("vid_ok_2", title="Second lesson"),
            "vid_private": video_item("vid_private", privacy="private"),
            "vid_short": video_item("vid_short", duration="PT45S"),
        }
        self.fail_with: int | None = None
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail_with:
            return httpx.Response(self.fail_with, json={"error": {"errors": [{"reason": "quotaExceeded"}]}})
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"items": [{"id": {"videoId": v}} for v in self.search_ids]})
        if request.url.path.endswith("/videos"):
            ids = request.url.params["id"].split(",")
            return httpx.Response(200, json={"items": [self.available[i] for i in ids if i in self.available]})
        return httpx.Response(404)


# --- Job boards -------------------------------------------------------------

class JobsMock:
    def __init__(self):
        self.jobicy_jobs = [
            {
                "id": 101, "url": "https://jobicy.com/jobs/101-python-developer", "jobTitle": "Python Developer",
                "companyName": "Acme", "jobIndustry": ["Programming"], "jobType": ["Full-Time"], "jobGeo": "USA",
                "jobLevel": "Midweight", "jobExcerpt": "Build Python APIs", "jobDescription": "<p>Python and FastAPI</p>",
                "pubDate": "2026-10-01T10:00:00+00:00", "salaryMin": 90000, "salaryMax": 120000,
                "salaryCurrency": "USD", "salaryPeriod": "yearly",
            },
            {
                "id": 102, "url": "https://jobicy.com/jobs/102-sales", "jobTitle": "Sales Lead", "companyName": "Other",
                "jobIndustry": ["Sales"], "jobType": ["Full-Time"], "jobGeo": "Anywhere", "jobExcerpt": "Sell things",
                "jobDescription": "<p>Quota</p>", "pubDate": "2026-10-02T10:00:00+00:00",
            },
            {
                "id": 103, "url": "http://insecure.example/job", "jobTitle": "Python insecure", "companyName": "Bad",
                "jobDescription": "python", "pubDate": "2026-10-02T10:00:00+00:00",
            },
        ]
        self.muse_jobs = [
            {
                "id": 555, "name": "Senior Python Engineer", "contents": "<p>Python services</p>",
                "publication_date": "2026-09-30T00:00:00Z", "locations": [{"name": "Flexible / Remote"}],
                "categories": [{"name": "Software Engineering"}], "levels": [{"name": "Senior Level"}],
                "refs": {"landing_page": "https://www.themuse.com/jobs/acme/senior-python-engineer"},
                "company": {"name": "Muse Co"},
            }
        ]
        self.fail = False
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail:
            return httpx.Response(503)
        if request.url.host == "jobicy.com":
            return httpx.Response(200, json={"jobs": self.jobicy_jobs})
        if request.url.host == "www.themuse.com":
            return httpx.Response(200, json={"results": self.muse_jobs})
        return httpx.Response(404)


class WebMock:
    """Link checker: URLs in ``ok`` return 200, everything else 404."""

    def __init__(self):
        self.ok = {"https://docs.python.org/3/tutorial/"}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200 if str(request.url) in self.ok else 404, text="ok")


def course_outline(title: str = "Python Foundations", *, optional_module: bool = True) -> dict:
    modules = [
        {
            "title": "Basics", "description": "Syntax", "learning_objectives": "Write scripts", "completion_criteria": "Script runs",
            "required": True, "video_search_query": "python basics tutorial",
            "official_documentation": [
                {"title": "Python tutorial", "url": "https://docs.python.org/3/tutorial/"},
                {"title": "Made up", "url": "https://docs.invalid.example/nope"},
            ],
            "activities": [
                {"kind": "lesson", "title": "Variables", "instructions": "Read and try", "estimated_minutes": 30},
                {"kind": "exercise", "title": "Loops", "instructions": "Write loops", "estimated_minutes": 45},
            ],
        },
        {
            "title": "Project", "description": "Build", "learning_objectives": "Ship", "completion_criteria": "Repo",
            "required": True, "video_search_query": "python project tutorial", "official_documentation": [],
            "activities": [{"kind": "project", "title": "CLI app", "instructions": "Build a CLI", "estimated_minutes": 120}],
        },
    ]
    if optional_module:
        modules.append({
            "title": "Earning path", "description": "Optional", "learning_objectives": "Freelance", "completion_criteria": "Offer",
            "required": False, "video_search_query": "freelance python", "official_documentation": [],
            "activities": [{"kind": "reflection", "title": "Pricing", "instructions": "Research", "estimated_minutes": 30}],
        })
    return {
        "title": title, "description": "Learn Python", "objective": "Be productive", "difficulty": "beginner",
        "estimated_hours": 20, "prerequisites": "None", "modules": modules,
    }
