import json

import httpx
import pytest
from pydantic import BaseModel

from app.ai.llm_client import AINotConfiguredError, AIProviderError, LLMClient, strict_schema
from app.ai.schemas import CourseOutline, OnboardingTurn
from app.core.rate_limit import RateLimiter
from app.core.exceptions import RateLimitedError
from app.integrations.jobs import JobListing, JobSearchClient, muse_categories_for, relevance
from app.integrations.web import UrlVerifier
from app.integrations.youtube import YouTubeClient, parse_duration
from tests.fakes import JobsMock, YouTubeMock


class Small(BaseModel):
    name: str
    count: int | None = None


def llm_with(handler) -> LLMClient:
    return LLMClient(api_key="test", base_url="https://llm.test/v1", model="m", transport=httpx.MockTransport(handler))


def completion(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


def test_strict_schema_inlines_refs_and_requires_everything():
    for model in (OnboardingTurn, CourseOutline):
        schema = strict_schema(model)
        dumped = json.dumps(schema)
        assert "$ref" not in dumped and "$defs" not in dumped

        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "object" and "properties" in node:
                    assert node["additionalProperties"] is False
                    assert set(node["required"]) == set(node["properties"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(schema)


def test_strict_schema_keeps_fields_named_like_keywords():
    from app.ai.schemas import GoalPlan

    milestone = strict_schema(GoalPlan)["properties"]["milestones"]["items"]
    assert set(milestone["properties"]) == {"title", "description", "week_offset"}
    assert "title" in milestone["required"]
    course = strict_schema(CourseOutline)
    assert "title" in course["properties"] and "title" in course["required"]


async def test_structured_output_is_validated():
    seen = {}

    def handler(request):
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=completion('{"name": "x", "count": 2}'))

    result = await llm_with(handler).complete_structured(system="s", messages=[{"role": "user", "content": "u"}], schema=Small)
    assert result == Small(name="x", count=2)
    assert seen["headers"]["user-agent"].startswith("PlotPlanner")
    assert seen["body"]["response_format"]["json_schema"]["strict"] is True


@pytest.mark.parametrize("content", ["not json", '{"count": 1}', '{"name": 5}'])
async def test_malformed_output_raises(content):
    client = llm_with(lambda r: httpx.Response(200, json=completion(content)))
    with pytest.raises(AIProviderError):
        await client.complete_structured(system="s", messages=[], schema=Small)


async def test_provider_errors_are_controlled():
    with pytest.raises(AIProviderError, match="rate limiting"):
        await llm_with(lambda r: httpx.Response(429)).chat(messages=[{"role": "user", "content": "x"}])
    with pytest.raises(AIProviderError):
        await llm_with(lambda r: httpx.Response(500, text="secret internals")).chat(messages=[{"role": "user", "content": "x"}])

    def boom(request):
        raise httpx.ConnectTimeout("timeout")

    with pytest.raises(AIProviderError):
        await llm_with(boom).chat(messages=[{"role": "user", "content": "x"}])


async def test_unconfigured_llm():
    client = LLMClient(api_key=None, base_url="https://llm.test", model="m")
    assert client.configured is False
    with pytest.raises(AINotConfiguredError):
        await client.chat(messages=[{"role": "user", "content": "x"}])


async def test_oversized_input_is_refused_before_sending():
    calls = []
    client = llm_with(lambda r: calls.append(r) or httpx.Response(200, json=completion("{}")))
    with pytest.raises(AIProviderError, match="too large"):
        await client.chat(messages=[{"role": "user", "content": "x" * 70_000}])
    assert calls == []


async def test_tool_calls_are_parsed():
    message = {"role": "assistant", "content": None, "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "search_jobs", "arguments": '{"query": "python"}'}},
    ]}
    client = llm_with(lambda r: httpx.Response(200, json={"choices": [{"message": message}]}))
    result = await client.chat(messages=[{"role": "user", "content": "x"}], tools=[{"type": "function"}])
    assert result.tool_calls[0].name == "search_jobs" and result.tool_calls[0].arguments == {"query": "python"}


def test_parse_duration():
    assert parse_duration("PT1H2M3S") == 3723
    assert parse_duration("PT45S") == 45
    assert parse_duration("P1DT1S") == 86401
    assert parse_duration(None) is None and parse_duration("garbage") is None


async def test_youtube_only_returns_verified_public_videos():
    mock = YouTubeMock()
    client = YouTubeClient("key", transport=httpx.MockTransport(mock))
    videos = await client.search_videos("python", max_results=5)
    assert [v.video_id for v in videos] == ["vid_ok_1", "vid_ok_2"]
    assert videos[0].title == "Intro & Basics" and videos[0].duration_seconds == 750
    assert all("key" not in str(v) for v in videos)


async def test_youtube_quota_error_message():
    mock = YouTubeMock()
    mock.fail_with = 403
    with pytest.raises(Exception, match="quota"):
        await YouTubeClient("key", transport=httpx.MockTransport(mock)).search_videos("x")


def test_relevance_requires_every_keyword():
    listing = JobListing(source="s", external_id="1", title="Data Analyst", company=None, url="https://x", location=None,
                         employment_type=None, description="SQL and dashboards", tags=["Analytics"])
    assert relevance(listing, ["data", "analyst"]) > relevance(listing, ["sql"]) > 0
    assert relevance(listing, ["python"]) == 0


def test_muse_category_mapping():
    assert muse_categories_for("UX designer") == ["Design and UX"]
    assert "Software Engineering" in muse_categories_for("python developer")
    assert muse_categories_for("zebra keeper") == []


async def test_job_search_partial_failure_reports_provider():
    mock = JobsMock()

    def handler(request):
        if request.url.host == "www.themuse.com":
            return httpx.Response(500)
        return mock(request)

    outcome = await JobSearchClient(transport=httpx.MockTransport(handler)).search("python")
    assert [l.source for l in outcome.listings] == ["jobicy"]
    assert outcome.provider_errors == {"themuse": "unavailable"}


@pytest.mark.parametrize("url", ["http://docs.python.org/", "https://user:pw@example.com/", "https://example.com:8443/", "ftp://x"])
async def test_url_verifier_rejects_unsafe_urls(url):
    verifier = UrlVerifier(transport=httpx.MockTransport(lambda r: httpx.Response(200)), resolve_hosts=False)
    assert await verifier.verify(url) is None


async def test_url_verifier_rejects_private_hosts():
    verifier = UrlVerifier(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    assert await verifier.verify("https://localhost/") is None
    assert await verifier.verify("https://127.0.0.1/") is None


async def test_url_verifier_follows_safe_redirects_only():
    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "https://example.com/new"})
        if request.url.path == "/to-http":
            return httpx.Response(302, headers={"location": "http://example.com/"})
        return httpx.Response(200)

    verifier = UrlVerifier(transport=httpx.MockTransport(handler), resolve_hosts=False)
    assert (await verifier.verify("https://example.com/old")).url == "https://example.com/new"
    assert await verifier.verify("https://example.com/to-http") is None


def test_rate_limiter():
    limiter = RateLimiter()
    for _ in range(3):
        limiter.check("ai", "u1", limit=3, window_seconds=60)
    with pytest.raises(RateLimitedError) as exc:
        limiter.check("ai", "u1", limit=3, window_seconds=60)
    assert int(exc.value.headers["Retry-After"]) > 0
    limiter.check("ai", "u2", limit=3, window_seconds=60)


async def test_ai_endpoints_are_rate_limited(client, signed_in, settings, fake_llm):
    _, headers = signed_in()
    for _ in range(settings.ai_requests_per_minute):
        fake_llm.chat_replies.append("ok")
        assert (await client.post("/api/v1/chat", headers=headers, json={"message": "hi"})).status_code == 200
    limited = await client.post("/api/v1/chat", headers=headers, json={"message": "hi"})
    assert limited.status_code == 429 and limited.json()["error"]["code"] == "rate_limited"


async def test_rate_limit_is_retried_within_bound(monkeypatch):
    import app.ai.llm_client as module

    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(module.asyncio, "sleep", fake_sleep)
    responses = [
        httpx.Response(429, headers={"x-ratelimit-reset-tokens": "3.5s"}),
        httpx.Response(200, json=completion('{"name": "ok", "count": null}')),
    ]
    client = llm_with(lambda r: responses.pop(0))
    result = await client.complete_structured(system="s", messages=[], schema=Small)
    assert result.name == "ok" and sleeps == [4.0]


async def test_rate_limit_beyond_bound_fails_fast(monkeypatch):
    import app.ai.llm_client as module

    async def fail_sleep(_):
        raise AssertionError("should not wait")

    monkeypatch.setattr(module.asyncio, "sleep", fail_sleep)
    client = llm_with(lambda r: httpx.Response(429, headers={"x-ratelimit-reset-tokens": "1m2s"}))
    with pytest.raises(AIProviderError, match="63 seconds"):
        await client.chat(messages=[{"role": "user", "content": "x"}])


def test_retry_after_parsing():
    from app.ai.llm_client import retry_after_seconds

    assert retry_after_seconds(httpx.Headers({"retry-after": "7"})) == 7
    assert retry_after_seconds(httpx.Headers({"x-ratelimit-reset-tokens": "1m30.5s", "x-ratelimit-reset-requests": "2m"})) == 90.5
    assert retry_after_seconds(httpx.Headers({"x-ratelimit-reset-tokens": "250ms"})) == 0.25
    assert retry_after_seconds(httpx.Headers({})) is None
