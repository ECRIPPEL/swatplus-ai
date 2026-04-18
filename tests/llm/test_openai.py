"""Tests for OpenAIBackend: success, 401, 429, SSE parsing."""

from __future__ import annotations

import json

import httpx
import pytest

from swatplus_ai.llm.backends.api_key import OpenAIBackend
from swatplus_ai.llm.interface import AuthError, Message, RateLimitError

_MESSAGES = [
    Message(role="system", content="be terse"),
    Message(role="user", content="hi"),
]


def _openai_success(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode("utf-8"))
    assert body["model"] == "gpt-4o-mini"
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["system", "user"]
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hello"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 4, "completion_tokens": 1, "total_tokens": 5},
        },
    )


async def test_complete_happy_path() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_openai_success))
    try:
        backend = OpenAIBackend(api_key="sk-test", client=client)
        resp = await backend.complete(_MESSAGES)
        assert resp.text == "hello"
        assert resp.input_tokens == 4
        assert resp.output_tokens == 1
        assert resp.finish_reason == "stop"
        assert resp.model == "gpt-4o-mini"
    finally:
        await client.aclose()


async def test_auth_header_uses_bearer() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization", "")
        return _openai_success(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        backend = OpenAIBackend(api_key="sk-xyz", client=client)
        await backend.complete(_MESSAGES)
    finally:
        await client.aclose()
    assert captured["authorization"] == "Bearer sk-xyz"


async def test_401_raises_auth_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        backend = OpenAIBackend(api_key="bad", client=client)
        with pytest.raises(AuthError):
            await backend.complete(_MESSAGES)
    finally:
        await client.aclose()


async def test_429_raises_rate_limit_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "slow down"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        backend = OpenAIBackend(api_key="sk", client=client)
        with pytest.raises(RateLimitError):
            await backend.complete(_MESSAGES)
    finally:
        await client.aclose()


_SSE_BODY = (
    'data: {"id":"x","object":"chat.completion.chunk","choices":'
    '[{"index":0,"delta":{"role":"assistant","content":"Hel"},"finish_reason":null}]}\n'
    "\n"
    ": keepalive\n"
    "\n"
    'data: {"id":"x","object":"chat.completion.chunk","choices":'
    '[{"index":0,"delta":{"content":"lo"},"finish_reason":null}]}\n'
    "\n"
    'data: {"id":"x","object":"chat.completion.chunk","choices":'
    '[{"index":0,"delta":{},"finish_reason":"stop"}]}\n'
    "\n"
    "data: [DONE]\n"
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
        backend = OpenAIBackend(api_key="sk-test", client=client)
        chunks: list[str] = []
        async for chunk in backend.stream(_MESSAGES):
            chunks.append(chunk)
        assert "".join(chunks) == "Hello"
    finally:
        await client.aclose()
