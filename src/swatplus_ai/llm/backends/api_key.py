"""API-key backends for Anthropic and OpenAI.

These are the default, stable backends. Both speak raw HTTP via
:mod:`httpx` (no vendor SDKs) so the wire contract is explicit and the
same transport mocking works across the whole test suite. Shared
request/response machinery lives in :mod:`._http`; the per-provider
logic here is the wire shape (endpoint, body, headers, SSE event
schema) and nothing else.

Both classes expose a ``client`` injection point so tests can plug in
``httpx.MockTransport`` without reaching inside the backend.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, ClassVar

import httpx

from swatplus_ai.llm.backends._http import request_json, stream_sse
from swatplus_ai.llm.interface import LLMError, LLMResponse, Message, split_system

_DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class _BaseBackend:
    """Shared orchestration (HTTP client lifecycle + complete/stream flow).

    Subclasses supply provider-specific hooks:

    - :meth:`_endpoint` — URL to POST against.
    - :meth:`_build_body` — request body dict.
    - :meth:`_auth_headers` — HTTP headers carrying credentials.
    - :meth:`_parse_response` — non-streaming response → :class:`LLMResponse`.
    - :meth:`_parse_sse_delta` — SSE frame → ``(text_delta_or_None, done)``.
    """

    DEFAULT_MODEL: ClassVar[str] = ""

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        if client is None:
            self._client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    async def aclose(self) -> None:
        """Close the underlying HTTP client iff this backend created it."""
        if self._owns_client:
            await self._client.aclose()

    # ---- provider hooks (override in subclasses) -----------------------------
    def _endpoint(self) -> str:
        raise NotImplementedError

    def _auth_headers(self) -> dict[str, str]:
        raise NotImplementedError

    def _build_body(
        self,
        messages: list[Message],
        model: str,
        max_tokens: int,
        temperature: float,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        raise NotImplementedError

    def _parse_sse_delta(self, frame: dict[str, Any]) -> tuple[str | None, bool]:
        raise NotImplementedError

    # ---- public API ----------------------------------------------------------
    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        body = self._build_body(
            messages, model or self.DEFAULT_MODEL, max_tokens, temperature, stream=False
        )
        data = await request_json(
            self._client,
            "POST",
            self._endpoint(),
            headers=self._auth_headers(),
            json_body=body,
        )
        return self._parse_response(data)

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        body = self._build_body(
            messages, model or self.DEFAULT_MODEL, max_tokens, temperature, stream=True
        )
        async for frame in stream_sse(
            self._client,
            "POST",
            self._endpoint(),
            headers=self._auth_headers(),
            json_body=body,
        ):
            delta, done = self._parse_sse_delta(frame)
            if delta:
                yield delta
            if done:
                return


# ----- Anthropic ----------------------------------------------------------------


class _AnthropicProtocol(_BaseBackend):
    """Anthropic Messages API wire protocol, auth-agnostic."""

    DEFAULT_MODEL: ClassVar[str] = "claude-haiku-4-5-20251001"
    API_URL: ClassVar[str] = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION: ClassVar[str] = "2023-06-01"

    def _endpoint(self) -> str:
        return self.API_URL

    def _build_body(
        self,
        messages: list[Message],
        model: str,
        max_tokens: int,
        temperature: float,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        system, rest = split_system(messages)
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in rest],
        }
        if system is not None:
            body["system"] = system
        if stream:
            body["stream"] = True
        return body

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        blocks = data.get("content", []) or []
        text = "".join(
            str(block.get("text", ""))
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        )
        usage = data.get("usage", {}) or {}
        stop = data.get("stop_reason") or "stop"
        return LLMResponse(
            text=text,
            model=str(data.get("model", "")),
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            finish_reason=_normalize_anthropic_stop(str(stop)),
        )

    def _parse_sse_delta(self, frame: dict[str, Any]) -> tuple[str | None, bool]:
        event = frame.get("event")
        data = frame.get("data", {}) or {}
        if event == "content_block_delta":
            delta = data.get("delta", {}) or {}
            if delta.get("type") == "text_delta":
                text = delta.get("text")
                return (str(text) if text else None, False)
        if event == "message_stop":
            return (None, True)
        return (None, False)


def _normalize_anthropic_stop(reason: str) -> str:
    # Anthropic: "end_turn" / "max_tokens" / "stop_sequence" / "tool_use"
    return {
        "end_turn": "stop",
        "stop_sequence": "stop",
        "max_tokens": "length",
    }.get(reason, reason)


class AnthropicBackend(_AnthropicProtocol):
    """Anthropic Messages API backend using an ``x-api-key``-authenticated request."""

    def __init__(self, api_key: str, *, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client=client)
        if not api_key:
            raise LLMError("AnthropicBackend requires a non-empty api_key")
        self._api_key = api_key

    def _auth_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": "application/json",
        }


# ----- OpenAI -------------------------------------------------------------------


class _OpenAIProtocol(_BaseBackend):
    """OpenAI Chat Completions API wire protocol, auth-agnostic."""

    DEFAULT_MODEL: ClassVar[str] = "gpt-4o-mini"
    API_URL: ClassVar[str] = "https://api.openai.com/v1/chat/completions"

    def _endpoint(self) -> str:
        return self.API_URL

    def _build_body(
        self,
        messages: list[Message],
        model: str,
        max_tokens: int,
        temperature: float,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if stream:
            body["stream"] = True
            body["stream_options"] = {"include_usage": True}
        return body

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        choices = data.get("choices", []) or []
        first = choices[0] if choices else {}
        message = first.get("message", {}) if isinstance(first, dict) else {}
        text = str(message.get("content") or "")
        usage = data.get("usage", {}) or {}
        finish_reason = (
            str(first.get("finish_reason") or "stop") if isinstance(first, dict) else "stop"
        )
        return LLMResponse(
            text=text,
            model=str(data.get("model", "")),
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            finish_reason=_normalize_openai_stop(finish_reason),
        )

    def _parse_sse_delta(self, frame: dict[str, Any]) -> tuple[str | None, bool]:
        data = frame.get("data", {}) or {}
        choices = data.get("choices", []) or []
        if not choices:
            return (None, False)
        first = choices[0]
        if not isinstance(first, dict):
            return (None, False)
        delta = first.get("delta", {}) or {}
        text = delta.get("content")
        finish = first.get("finish_reason")
        done = finish is not None and finish != ""
        return (str(text) if text else None, done)


def _normalize_openai_stop(reason: str) -> str:
    # OpenAI: "stop" / "length" / "content_filter" / "tool_calls" / "function_call"
    return reason


class OpenAIBackend(_OpenAIProtocol):
    """OpenAI Chat Completions backend using ``Authorization: Bearer <key>``."""

    def __init__(self, api_key: str, *, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client=client)
        if not api_key:
            raise LLMError("OpenAIBackend requires a non-empty api_key")
        self._api_key = api_key

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
        }
