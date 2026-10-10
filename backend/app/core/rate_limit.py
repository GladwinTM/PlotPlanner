"""Per-user sliding-window rate limiting for expensive endpoints (AI calls,
uploads, external searches).

State is in-process, which is adequate for the single-process modular
monolith; a multi-instance deployment would move this to a shared store.
"""
import time
from collections import defaultdict, deque
from threading import Lock

from app.core.exceptions import RateLimitedError


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, bucket: str, key: str, *, limit: int, window_seconds: float) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[(bucket, key)]
            while hits and now - hits[0] >= window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = int(window_seconds - (now - hits[0])) + 1
                error = RateLimitedError()
                error.headers = {"Retry-After": str(retry_after)}
                raise error
            hits.append(now)
