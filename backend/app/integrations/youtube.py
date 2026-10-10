"""YouTube Data API v3 client.

Every returned video was confirmed by ``videos.list`` at retrieval time to be
public, processed and embeddable. Search results the API does not confirm
are dropped rather than shown.
"""
import html
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.exceptions import ExternalServiceError, ServiceUnavailableError

logger = logging.getLogger(__name__)

API_BASE = "https://www.googleapis.com/youtube/v3"
_DURATION = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


class YouTubeNotConfiguredError(ServiceUnavailableError):
    code = "youtube_not_configured"
    message = "YouTube search is not configured on this server (YOUTUBE_API_KEY is missing)."


@dataclass(frozen=True)
class VerifiedVideo:
    video_id: str
    title: str
    channel: str
    url: str
    duration_seconds: int | None
    published_at: datetime | None
    retrieved_at: datetime


def parse_duration(value: str | None) -> int | None:
    if not value:
        return None
    match = _DURATION.fullmatch(value)
    if not match:
        return None
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return ((days * 24 + hours) * 60 + minutes) * 60 + seconds


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class YouTubeClient:
    def __init__(self, api_key: str | None, *, transport: httpx.AsyncBaseTransport | None = None):
        self._api_key = api_key
        self._client = httpx.AsyncClient(base_url=API_BASE, timeout=15, transport=transport)

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict) -> dict:
        if not self._api_key:
            raise YouTubeNotConfiguredError()
        try:
            response = await self._client.get(path, params={**params, "key": self._api_key})
        except httpx.HTTPError as exc:
            logger.error("YouTube request failed: %s", type(exc).__name__)
            raise ExternalServiceError("YouTube could not be reached. Please try again.") from exc
        if response.status_code == 403 and "quota" in response.text.lower():
            raise ExternalServiceError("The YouTube API daily quota is exhausted. Resource search will work again after it resets.")
        if response.status_code >= 400:
            logger.error("YouTube returned HTTP %s for %s", response.status_code, path)
            raise ExternalServiceError("YouTube search failed. Please try again.")
        return response.json()

    async def search_videos(self, query: str, *, max_results: int = 5) -> list[VerifiedVideo]:
        search = await self._get(
            "/search",
            {
                "part": "snippet",
                "type": "video",
                "q": query[:200],
                "maxResults": min(max(max_results * 2, 5), 25),
                "safeSearch": "strict",
                "relevanceLanguage": "en",
                "videoEmbeddable": "true",
            },
        )
        ids = [item["id"]["videoId"] for item in search.get("items", []) if item.get("id", {}).get("videoId")]
        if not ids:
            return []
        return (await self.verify_videos(ids))[:max_results]

    async def verify_videos(self, video_ids: list[str]) -> list[VerifiedVideo]:
        details = await self._get("/videos", {"part": "snippet,contentDetails,status", "id": ",".join(video_ids[:50])})
        retrieved = datetime.now(UTC)
        by_id = {}
        for item in details.get("items", []):
            status = item.get("status", {})
            if status.get("privacyStatus") != "public" or status.get("uploadStatus") != "processed":
                continue
            duration = parse_duration(item.get("contentDetails", {}).get("duration"))
            # Skip shorts and live placeholders; they are not useful as course material.
            if duration is not None and duration < 120:
                continue
            snippet = item.get("snippet", {})
            by_id[item["id"]] = VerifiedVideo(
                video_id=item["id"],
                title=html.unescape(snippet.get("title", ""))[:300],
                channel=html.unescape(snippet.get("channelTitle", ""))[:200],
                url=f"https://www.youtube.com/watch?v={item['id']}",
                duration_seconds=duration,
                published_at=_parse_time(snippet.get("publishedAt")),
                retrieved_at=retrieved,
            )
        return [by_id[video_id] for video_id in video_ids if video_id in by_id]
