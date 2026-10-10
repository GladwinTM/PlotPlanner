"""Reachability checks for externally suggested URLs.

Only public https hosts are contacted (private, loopback, link-local and
reserved addresses are refused, including after redirects) so a suggested URL
cannot be used to probe internal infrastructure.
"""
import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

logger = logging.getLogger(__name__)

MAX_REDIRECTS = 3
TIMEOUT_SECONDS = 8


@dataclass(frozen=True)
class VerifiedUrl:
    url: str
    host: str


async def _is_public_host(host: str) -> bool:
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global or address.is_multicast:
            return False
    return bool(infos)


def _acceptable(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and bool(parts.hostname) and parts.port in (None, 443) and not parts.username


class UrlVerifier:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None, resolve_hosts: bool = True):
        self._client = httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS, follow_redirects=False, transport=transport,
            headers={"User-Agent": "PlotPlanner/1.0 (link checker)"},
        )
        self._resolve_hosts = resolve_hosts

    async def aclose(self) -> None:
        await self._client.aclose()

    async def verify(self, url: str) -> VerifiedUrl | None:
        current = url.strip()
        for _ in range(MAX_REDIRECTS + 1):
            if not _acceptable(current):
                return None
            host = urlsplit(current).hostname or ""
            if self._resolve_hosts and not await _is_public_host(host):
                return None
            try:
                async with self._client.stream("GET", current) as response:
                    status = response.status_code
                    location = response.headers.get("location")
            except httpx.HTTPError:
                return None
            if status in (301, 302, 303, 307, 308) and location:
                current = urljoin(current, location)
                continue
            if 200 <= status < 300:
                return VerifiedUrl(url=current, host=host.removeprefix("www."))
            return None
        return None
