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
from time import perf_counter
from typing import Any, ClassVar

import httpx

import swatplus_ai.telemetry as telemetry
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
    - :meth:`_parse_sse_accounting` — SSE frame → optional dict with any
      of ``input_tokens`` / ``output_tokens`` / ``finish_reason``.
      Kept separate from ``_parse_sse_delta`` because the usage /
      stop-reason payloads ride on *different* events than the text
      deltas (Anthropic: ``message_start`` + ``message_delta``; OpenAI:
      the trailing ``choices=[]`` + ``usage`` frame).
    """

    DEFAULT_MODEL: ClassVar[str] = ""
    # Provider tag for telemetry. Subclasses override; kept on the
    # protocol class so both api-key and OAuth flavours of the same
    # provider report the same ``provider`` value without each subclass
    # re-declaring it (cf. the ``_AnthropicProtocol`` / OAuth split).
    PROVIDER: ClassVar[str] = ""

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

    def _parse_sse_accounting(self, frame: dict[str, Any]) -> dict[str, Any] | None:
        """Pull token counts / ``finish_reason`` out of one SSE frame.

        Return ``None`` for frames that carry neither (every text-delta
        frame in practice). Returned keys are merged into the running
        accounting dict in :meth:`stream`, so a later frame overrides an
        earlier value — Anthropic's ``message_delta`` supplies the
        *final* ``output_tokens`` by doing exactly that.
        """
        return None

    # ---- public API ----------------------------------------------------------
    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        resolved_model = model or self.DEFAULT_MODEL
        body = self._build_body(messages, resolved_model, max_tokens, temperature, stream=False)
        t0 = perf_counter()
        try:
            data = await request_json(
                self._client,
                "POST",
                self._endpoint(),
                headers=self._auth_headers(),
                json_body=body,
            )
            response = self._parse_response(data)
        except Exception as exc:
            # Emit before re-raising so the failure is on disk even if
            # the process dies inside the caller (JsonlFileSink flushes
            # per line). Same pattern as parse_error in slice 4.5.2.
            telemetry.emit(
                "llm_call",
                provider=self.PROVIDER,
                model=resolved_model,
                input_tokens=0,
                output_tokens=0,
                finish_reason="error",
                duration_ms=round((perf_counter() - t0) * 1000),
                streaming=False,
                exception=type(exc).__name__,
            )
            raise
        telemetry.emit(
            "llm_call",
            provider=self.PROVIDER,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            finish_reason=response.finish_reason,
            duration_ms=round((perf_counter() - t0) * 1000),
            streaming=False,
        )
        return response

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        resolved_model = model or self.DEFAULT_MODEL
        body = self._build_body(messages, resolved_model, max_tokens, temperature, stream=True)
        accounting: dict[str, Any] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "finish_reason": "stop",
        }
        t0 = perf_counter()
        try:
            async for frame in stream_sse(
                self._client,
                "POST",
                self._endpoint(),
                headers=self._auth_headers(),
                json_body=body,
            ):
                delta, _done = self._parse_sse_delta(frame)
                acct = self._parse_sse_accounting(frame)
                if acct:
                    accounting.update(acct)
                if delta:
                    yield delta
                # Note: we intentionally do NOT return on ``_done``. The
                # final text chunk carries ``finish_reason`` *before* the
                # trailing usage frame on OpenAI, and Anthropic's usage
                # lands on ``message_delta`` *after* ``message_stop`` in
                # some rollouts — letting ``stream_sse`` drive termination
                # via the server's close / ``[DONE]`` sentinel is the
                # only way to observe both without racing the provider.
        except Exception as exc:
            # GeneratorExit is a BaseException, not Exception — a
            # consumer's early break won't fire this branch, which is
            # the right semantics (no metric for a caller-side abort).
            telemetry.emit(
                "llm_call",
                provider=self.PROVIDER,
                model=resolved_model,
                input_tokens=accounting["input_tokens"],
                output_tokens=accounting["output_tokens"],
                finish_reason="error",
                duration_ms=round((perf_counter() - t0) * 1000),
                streaming=True,
                exception=type(exc).__name__,
            )
            raise
        telemetry.emit(
            "llm_call",
            provider=self.PROVIDER,
            model=resolved_model,
            input_tokens=accounting["input_tokens"],
            output_tokens=accounting["output_tokens"],
            finish_reason=accounting["finish_reason"],
            duration_ms=round((perf_counter() - t0) * 1000),
            streaming=True,
        )


# ----- Anthropic ----------------------------------------------------------------


class _AnthropicProtocol(_BaseBackend):
    """Anthropic Messages API wire protocol, auth-agnostic."""

    DEFAULT_MODEL: ClassVar[str] = "claude-haiku-4-5-20251001"
    PROVIDER: ClassVar[str] = "anthropic"
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

    def _parse_sse_accounting(self, frame: dict[str, Any]) -> dict[str, Any] | None:
        event = frame.get("event")
        data = frame.get("data", {}) or {}
        if event == "message_start":
            message = data.get("message", {}) or {}
            usage = message.get("usage", {}) or {}
            result: dict[str, Any] = {}
            if "input_tokens" in usage:
                result["input_tokens"] = int(usage["input_tokens"])
            if "output_tokens" in usage:
                result["output_tokens"] = int(usage["output_tokens"])
            return result or None
        if event == "message_delta":
            delta = data.get("delta", {}) or {}
            usage = data.get("usage", {}) or {}
            result = {}
            stop = delta.get("stop_reason")
            if stop:
                result["finish_reason"] = _normalize_anthropic_stop(str(stop))
            if "output_tokens" in usage:
                result["output_tokens"] = int(usage["output_tokens"])
            return result or None
        return None


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
    PROVIDER: ClassVar[str] = "openai"
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

    def _parse_sse_accounting(self, frame: dict[str, Any]) -> dict[str, Any] | None:
        data = frame.get("data", {}) or {}
        result: dict[str, Any] = {}
        usage = data.get("usage")
        if isinstance(usage, dict):
            if "prompt_tokens" in usage:
                result["input_tokens"] = int(usage["prompt_tokens"])
            if "completion_tokens" in usage:
                result["output_tokens"] = int(usage["completion_tokens"])
        choices = data.get("choices", []) or []
        if choices and isinstance(choices[0], dict):
            finish = choices[0].get("finish_reason")
            if finish:
                result["finish_reason"] = _normalize_openai_stop(str(finish))
        return result or None


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
