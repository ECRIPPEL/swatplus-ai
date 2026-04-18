"""Slice-5-closure tests: every ``complete()`` emits ``llm_call``.

The instrumentation lives in two files — ``api_key.py`` (Anthropic +
OpenAI, shared via ``_BaseBackend``) and ``mock.py``. Tests cover
the happy path, the error path (provider 401 / 429), the disabled
state, and the streaming-stays-silent contract. ``stream()`` not
emitting is a **documented limitation** of this slice, not an
accident: see the commit body for why.
"""

from __future__ import annotations

import json
from collections import deque
from typing import Any

import httpx
import pytest

import swatplus_ai.telemetry as telemetry
from swatplus_ai.llm.backends.api_key import AnthropicBackend, OpenAIBackend
from swatplus_ai.llm.backends.mock import MockBackend
from swatplus_ai.llm.interface import AuthError, Message, RateLimitError
from swatplus_ai.telemetry.sinks import InMemorySink

_MESSAGES = [
    Message(role="system", content="be terse"),
    Message(role="user", content="hi"),
]


@pytest.fixture(autouse=True)
def _reset_telemetry_state(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mirrors tests/telemetry/conftest.py's reset — this file lives in
    # tests/llm/ so we re-declare instead of reaching across suites.
    monkeypatch.setattr(telemetry, "_DEFAULT_SINK", None)
    monkeypatch.setattr(telemetry, "_SESSION_ID", None)
    monkeypatch.setattr(telemetry, "_BUFFER", deque(maxlen=telemetry._BUFFER_MAXLEN))
    monkeypatch.setattr(telemetry, "_SINK_FAILURE_WARNED", False)


@pytest.fixture
def enable_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force telemetry on regardless of env or on-disk config."""

    def _always_enabled(*_args: Any, **_kwargs: Any) -> bool:
        return True

    monkeypatch.setattr("swatplus_ai.telemetry.config.is_enabled", _always_enabled)


# Keep model names short in these mocks: the redactor's token heuristic
# collapses anything ≥24 chars with digits inside to ``<REDACTED>``, and
# the real Anthropic default (``claude-haiku-4-5-20251001``, 25 chars)
# trips it. Short names still round-trip through the ``model`` field and
# keep the assertions honest.
_SHORT_ANTHROPIC_MODEL = "claude-haiku-5"
_SHORT_OPENAI_MODEL = "gpt-4o-mini"


def _anthropic_ok(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "msg_01",
            "type": "message",
            "role": "assistant",
            "model": _SHORT_ANTHROPIC_MODEL,
            "content": [{"type": "text", "text": "hello"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 4, "output_tokens": 1},
        },
    )


def _openai_ok(_request: httpx.Request) -> httpx.Response:
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
            "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
        },
    )


def _only(events: list[Any], event_type: str) -> list[Any]:
    return [e for e in events if e.event_type == event_type]


async def test_anthropic_complete_emits_llm_call(enable_telemetry: None) -> None:
    sink = InMemorySink()
    telemetry.configure(sink)
    client = httpx.AsyncClient(transport=httpx.MockTransport(_anthropic_ok))
    try:
        backend = AnthropicBackend(api_key="sk-test", client=client)
        await backend.complete(_MESSAGES, model=_SHORT_ANTHROPIC_MODEL)
    finally:
        await client.aclose()

    events = _only(sink.events, "llm_call")
    assert len(events) == 1
    fields = events[0].fields
    assert fields["provider"] == "anthropic"
    assert fields["model"] == _SHORT_ANTHROPIC_MODEL
    assert fields["input_tokens"] == 4
    assert fields["output_tokens"] == 1
    assert fields["finish_reason"] == "stop"
    assert fields["streaming"] is False
    # perf_counter is monotonic but for a mock-transport round-trip
    # ``0 ms`` is a legitimate outcome; just require non-negative.
    assert isinstance(fields["duration_ms"], int)
    assert fields["duration_ms"] >= 0


async def test_openai_complete_emits_llm_call(enable_telemetry: None) -> None:
    sink = InMemorySink()
    telemetry.configure(sink)
    client = httpx.AsyncClient(transport=httpx.MockTransport(_openai_ok))
    try:
        backend = OpenAIBackend(api_key="sk-test", client=client)
        await backend.complete(_MESSAGES)
    finally:
        await client.aclose()

    events = _only(sink.events, "llm_call")
    assert len(events) == 1
    fields = events[0].fields
    assert fields["provider"] == "openai"
    assert fields["model"] == "gpt-4o-mini"
    assert fields["input_tokens"] == 7
    assert fields["output_tokens"] == 3
    assert fields["finish_reason"] == "stop"
    assert fields["streaming"] is False


async def test_mock_complete_emits_llm_call(enable_telemetry: None) -> None:
    sink = InMemorySink()
    telemetry.configure(sink)
    backend = MockBackend(replies=["hi there"])
    await backend.complete(_MESSAGES)

    events = _only(sink.events, "llm_call")
    assert len(events) == 1
    fields = events[0].fields
    assert fields["provider"] == "mock"
    assert fields["model"] == "mock-model"
    # Mock accounts by character length; both sides are positive.
    assert fields["input_tokens"] > 0
    assert fields["output_tokens"] == len("hi there")
    assert fields["finish_reason"] == "stop"
    assert fields["streaming"] is False


async def test_complete_with_telemetry_disabled_emits_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Env-var override short-circuits before any Event is built.
    monkeypatch.setenv("SWATPLUS_AI_NO_LOG", "1")
    sink = InMemorySink()
    telemetry.configure(sink)
    client = httpx.AsyncClient(transport=httpx.MockTransport(_anthropic_ok))
    try:
        backend = AnthropicBackend(api_key="sk-test", client=client)
        await backend.complete(_MESSAGES)
    finally:
        await client.aclose()
    assert sink.events == []


async def test_auth_error_emits_llm_call_with_finish_reason_error(
    enable_telemetry: None,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    sink = InMemorySink()
    telemetry.configure(sink)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        backend = AnthropicBackend(api_key="sk-bad", client=client)
        with pytest.raises(AuthError):
            await backend.complete(_MESSAGES, model=_SHORT_ANTHROPIC_MODEL)
    finally:
        await client.aclose()

    events = _only(sink.events, "llm_call")
    assert len(events) == 1
    fields = events[0].fields
    assert fields["finish_reason"] == "error"
    assert fields["exception"] == "AuthError"
    # Error path: ``model`` is the resolved target (the one we tried
    # to call), not a response model — the response never arrived.
    assert fields["model"] == _SHORT_ANTHROPIC_MODEL
    assert fields["input_tokens"] == 0
    assert fields["output_tokens"] == 0


async def test_rate_limit_error_emits_llm_call_with_finish_reason_error(
    enable_telemetry: None,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "slow down"}})

    sink = InMemorySink()
    telemetry.configure(sink)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        backend = OpenAIBackend(api_key="sk-test", client=client)
        with pytest.raises(RateLimitError):
            await backend.complete(_MESSAGES)
    finally:
        await client.aclose()

    events = _only(sink.events, "llm_call")
    assert len(events) == 1
    fields = events[0].fields
    assert fields["finish_reason"] == "error"
    assert fields["exception"] == "RateLimitError"
    assert fields["provider"] == "openai"


async def test_contract_identity_across_telemetry_toggle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Same call, once with telemetry disabled and once with it on and
    # an attached sink — the LLMResponse bytes must be identical.
    client_a = httpx.AsyncClient(transport=httpx.MockTransport(_openai_ok))
    client_b = httpx.AsyncClient(transport=httpx.MockTransport(_openai_ok))
    try:
        monkeypatch.setenv("SWATPLUS_AI_NO_LOG", "1")
        backend_off = OpenAIBackend(api_key="sk-test", client=client_a)
        baseline = await backend_off.complete(_MESSAGES)

        monkeypatch.delenv("SWATPLUS_AI_NO_LOG", raising=False)

        def _on(*_a: Any, **_k: Any) -> bool:
            return True

        monkeypatch.setattr("swatplus_ai.telemetry.config.is_enabled", _on)
        telemetry.configure(InMemorySink())
        backend_on = OpenAIBackend(api_key="sk-test", client=client_b)
        instrumented = await backend_on.complete(_MESSAGES)
    finally:
        await client_a.aclose()
        await client_b.aclose()

    # Pydantic LLMResponse is frozen → structural equality is the contract.
    assert baseline == instrumented


async def test_stream_does_not_emit(enable_telemetry: None) -> None:
    # stream() instrumentation is deferred (see commit message) —
    # this guard documents the decision so re-enabling it becomes a
    # conscious edit rather than a silent drift.
    def sse_handler(_request: httpx.Request) -> httpx.Response:
        body = (
            "data: "
            + json.dumps(
                {
                    "choices": [{"index": 0, "delta": {"content": "hi"}, "finish_reason": None}],
                }
            )
            + "\n\n"
            "data: "
            + json.dumps(
                {
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
            )
            + "\n\n"
            "data: [DONE]\n\n"
        )
        return httpx.Response(
            200,
            content=body.encode("utf-8"),
            headers={"content-type": "text/event-stream"},
        )

    sink = InMemorySink()
    telemetry.configure(sink)
    client = httpx.AsyncClient(transport=httpx.MockTransport(sse_handler))
    try:
        backend = OpenAIBackend(api_key="sk-test", client=client)
        # Drain the iterator fully so the stream is exercised end to end.
        chunks = [chunk async for chunk in backend.stream(_MESSAGES)]
    finally:
        await client.aclose()

    assert "".join(chunks) == "hi"
    # Contract: no llm_call until streaming accounting lands (deferred).
    assert _only(sink.events, "llm_call") == []


async def test_mock_complete_reports_model_override(enable_telemetry: None) -> None:
    # The ``model`` arg on ``complete()`` flows into both the response
    # and the emitted event — important because MockBackend is the
    # primary fixture for downstream module tests.
    sink = InMemorySink()
    telemetry.configure(sink)
    backend = MockBackend()
    await backend.complete(_MESSAGES, model="custom-mock-2")

    events = _only(sink.events, "llm_call")
    assert len(events) == 1
    assert events[0].fields["model"] == "custom-mock-2"
