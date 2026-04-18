"""Tests for AnthropicBackend: success, 401, 429, SSE parsing."""

from __future__ import annotations

import json

import httpx
import pytest

from swatplus_ai.llm.backends.api_key import AnthropicBackend
from swatplus_ai.llm.interface import AuthError, LLMError, Message, RateLimitError

_MESSAGES = [
    Message(role="system", content="be terse"),
    Message(role="user", content="hi"),
]


def _anthropic_success(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode("utf-8"))
    assert body["model"] == "claude-haiku-4-5-20251001"
    assert body["system"] == "be terse"
    assert body["messages"] == [{"role": "user", "content": "hi"}]
    return httpx.Response(
        200,
        json={
            "id": "msg_01",
            "type": "message",
            "role": "assistant",
            "model": "claude-haiku-4-5-20251001",
            "content": [{"type": "text", "text": "hello"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 4, "output_tokens": 1},
        },
    )


async def test_complete_happy_path() -> None:
    transport = httpx.MockTransport(_anthropic_success)
    client = httpx.AsyncClient(transport=transport)
    try:
        backend = AnthropicBackend(api_key="sk-test", client=client)
        resp = await backend.complete(_MESSAGES)
        assert resp.text == "hello"
        assert resp.input_tokens == 4
        assert resp.output_tokens == 1
        assert resp.finish_reason == "stop"
        assert resp.model == "claude-haiku-4-5-20251001"
    finally:
        await client.aclose()


async def test_auth_header_uses_api_key() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["x-api-key"] = request.headers.get("x-api-key", "")
        captured["anthropic-version"] = request.headers.get("anthropic-version", "")
        return _anthropic_success(request)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    try:
        backend = AnthropicBackend(api_key="sk-xyz", client=client)
        await backend.complete(_MESSAGES)
    finally:
        await client.aclose()
    assert captured["x-api-key"] == "sk-xyz"
    assert captured["anthropic-version"] == "2023-06-01"


async def test_401_raises_auth_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        backend = AnthropicBackend(api_key="bad", client=client)
        with pytest.raises(AuthError):
            await backend.complete(_MESSAGES)
    finally:
        await client.aclose()


async def test_429_raises_rate_limit_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "slow down"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        backend = AnthropicBackend(api_key="sk", client=client)
        with pytest.raises(RateLimitError):
            await backend.complete(_MESSAGES)
    finally:
        await client.aclose()


_SSE_BODY = (
    "event: message_start\n"
    'data: {"type": "message_start"}\n'
    "\n"
    "event: content_block_delta\n"
    'data: {"type": "content_block_delta", "index": 0, '
    '"delta": {"type": "text_delta", "text": "Hel"}}\n'
    "\n"
    ": keepalive\n"
    "\n"
    "event: content_block_delta\n"
    'data: {"type": "content_block_delta", "index": 0, '
    '"delta": {"type": "text_delta", "text": "lo"}}\n'
    "\n"
    "event: message_stop\n"
    'data: {"type": "message_stop"}\n'
    "\n"
)


async def test_stream_parses_sse_text_deltas() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body.get("stream") is True
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=_SSE_BODY,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        backend = AnthropicBackend(api_key="sk-test", client=client)
        chunks: list[str] = []
        async for chunk in backend.stream(_MESSAGES):
            chunks.append(chunk)
        assert "".join(chunks) == "Hello"
    finally:
        await client.aclose()


def test_rejects_empty_api_key() -> None:
    with pytest.raises(LLMError):
        AnthropicBackend(api_key="")
