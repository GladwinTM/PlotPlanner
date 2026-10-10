"""Groq (OpenAI-compatible) chat client.

Provider-specific request/response handling stays in this module. Callers get
validated Pydantic objects (``complete_structured``) or a normalized assistant
message (``chat``). Failures raise ``AIProviderError``; nothing here fabricates
a response.
"""
import asyncio
import json
import logging
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

REQUEST_TIMEOUT_SECONDS = 60
MAX_INPUT_CHARS = 60_000
# Interactive requests wait briefly for a provider rate-limit window; background
# jobs (pathway generation, plans) may wait for a full token window.
INTERACTIVE_RATE_LIMIT_WAIT = 12.0
BACKGROUND_RATE_LIMIT_WAIT = 65.0
MAX_RATE_LIMIT_RETRIES = 2
_DURATION_PART = re.compile(r"(\d+(?:\.\d+)?)(ms|h|m|s)")


def retry_after_seconds(headers: httpx.Headers) -> float | None:
    """Seconds until the provider accepts requests again (Retry-After or Groq's reset headers)."""
    if headers.get("retry-after"):
        try:
            return float(headers["retry-after"])
        except ValueError:
            pass
    waits = []
    for name in ("x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        value = headers.get(name)
        if value:
            seconds = 0.0
            for amount, unit in _DURATION_PART.findall(value):
                seconds += float(amount) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
            waits.append(seconds)
    return min(waits) if waits else None


class AIProviderError(AppError):
    status_code = 502
    code = "ai_provider_error"
    message = "The AI provider failed to respond. Please try again."


class AINotConfiguredError(AppError):
    status_code = 503
    code = "ai_not_configured"
    message = "AI features are not configured on this server (LLM_API_KEY is missing)."


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResult:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_message: dict[str, Any] = field(default_factory=dict)


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Convert a Pydantic schema to the strict subset providers accept:
    no $refs, every property required (optional ones made nullable), and no
    additional properties."""
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(deepcopy(definitions[node["$ref"].split("/")[-1]]))
            resolved = {}
            for key, value in node.items():
                if key == "properties":
                    # Keys here are field names (a field may be called "title"), not schema keywords.
                    resolved[key] = {name: resolve(child) for name, child in value.items()}
                elif key not in {"title", "default"}:
                    resolved[key] = resolve(value)
            node = resolved
            if node.get("type") == "object" and "properties" in node:
                node["required"] = list(node["properties"].keys())
                node["additionalProperties"] = False
            return node
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return resolve(schema)


class LLMClient:
    def __init__(self, *, api_key: str | None, base_url: str, model: str, transport: httpx.AsyncBaseTransport | None = None):
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=REQUEST_TIMEOUT_SECONDS, transport=transport)

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post(self, payload: dict[str, Any], rate_limit_wait: float) -> dict[str, Any]:
        if not self._api_key:
            raise AINotConfiguredError()
        size = sum(len(str(m.get("content") or "")) for m in payload["messages"])
        if size > MAX_INPUT_CHARS:
            raise AIProviderError("The request is too large for the AI provider.")
        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                response = await self._client.post(
                    "/chat/completions",
                    json={"model": self._model, "reasoning_effort": "low", **payload},
                    headers={"Authorization": f"Bearer {self._api_key}", "User-Agent": "PlotPlanner/1.0"},
                )
            except httpx.HTTPError as exc:
                logger.error("LLM request failed: %s", type(exc).__name__)
                raise AIProviderError() from exc
            if response.status_code != 429:
                break
            # 429 is the provider's documented transient failure: wait for the window, a bounded number of times.
            wait = retry_after_seconds(response.headers)
            if wait is None or wait > rate_limit_wait or attempt == MAX_RATE_LIMIT_RETRIES:
                hint = f" Try again in about {int(wait) + 1} seconds." if wait else " Please wait a moment and try again."
                raise AIProviderError("The AI provider is rate limiting requests." + hint)
            logger.info("LLM rate limited; retrying in %.1fs", wait)
            await asyncio.sleep(wait + 0.5)
        if response.status_code >= 400:
            logger.error("LLM provider returned HTTP %s", response.status_code)
            raise AIProviderError()
        body = response.json()
        usage = body.get("usage") or {}
        logger.info("llm usage prompt=%s completion=%s", usage.get("prompt_tokens"), usage.get("completion_tokens"))
        return body

    async def complete_structured(
        self, *, system: str, messages: list[dict[str, str]], schema: type[T], max_tokens: int = 2000,
        rate_limit_wait: float = INTERACTIVE_RATE_LIMIT_WAIT,
    ) -> T:
        body = await self._post(
            {
                "messages": [{"role": "system", "content": system}, *messages],
                "max_completion_tokens": max_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "strict": True, "schema": strict_schema(schema)},
                },
            },
            rate_limit_wait,
        )
        try:
            content = body["choices"][0]["message"]["content"]
            return schema.model_validate(json.loads(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            logger.error("LLM returned output that failed validation for %s: %s", schema.__name__, type(exc).__name__)
            raise AIProviderError("The AI returned an invalid response. Nothing was changed; please try again.") from exc

    async def chat(
        self, *, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, max_tokens: int = 1500,
        rate_limit_wait: float = INTERACTIVE_RATE_LIMIT_WAIT,
    ) -> ChatResult:
        payload: dict[str, Any] = {"messages": messages, "max_completion_tokens": max_tokens}
        if tools:
            payload["tools"] = tools
        body = await self._post(payload, rate_limit_wait)
        try:
            message = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError() from exc
        calls = []
        for call in message.get("tool_calls") or []:
            try:
                arguments = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}
            calls.append(ToolCall(id=call["id"], name=call["function"]["name"], arguments=arguments))
        return ChatResult(
            content=message.get("content"),
            tool_calls=calls,
            raw_message={k: v for k, v in message.items() if k in {"role", "content", "tool_calls"}},
        )
