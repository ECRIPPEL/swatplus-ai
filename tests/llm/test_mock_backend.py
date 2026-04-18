"""Tests for MockBackend deterministic replies + streaming."""

from __future__ import annotations

from swatplus_ai.llm.backends.mock import MockBackend
from swatplus_ai.llm.interface import Message


async def test_complete_returns_scripted_reply() -> None:
    backend = MockBackend(replies=["first", "second"])
    messages = [Message(role="user", content="q")]
    r1 = await backend.complete(messages)
    r2 = await backend.complete(messages)
    assert r1.text == "first"
    assert r2.text == "second"
    assert r1.model == "mock-model"
    assert r1.finish_reason == "stop"
    assert r1.output_tokens == len("first")


async def test_complete_falls_back_to_echo() -> None:
    backend = MockBackend()
    messages = [Message(role="user", content="ping")]
    resp = await backend.complete(messages)
    assert resp.text == "[mock] ping"


async def test_stream_yields_chunks_totaling_the_full_reply() -> None:
    backend = MockBackend(replies=["abcdefghijklmnop"], chunk_size=4)
    chunks: list[str] = []
    async for chunk in backend.stream([Message(role="user", content="q")]):
        chunks.append(chunk)
    assert "".join(chunks) == "abcdefghijklmnop"
    assert all(len(c) <= 4 for c in chunks)


async def test_model_override_honored_in_response() -> None:
    backend = MockBackend(replies=["hi"])
    resp = await backend.complete([Message(role="user", content="q")], model="custom-model")
    assert resp.model == "custom-model"
