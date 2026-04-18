"""Tests for the provider-agnostic LLM interface surface."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from swatplus_ai.llm.interface import (
    AuthError,
    LLMError,
    LLMResponse,
    Message,
    RateLimitError,
    split_system,
)


def test_message_round_trip() -> None:
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"
    # frozen — mutation blocked
    with pytest.raises(ValidationError):
        msg.content = "mutated"  # type: ignore[misc]


def test_llm_response_round_trip() -> None:
    resp = LLMResponse(
        text="hi there",
        model="mock-model",
        input_tokens=3,
        output_tokens=2,
        finish_reason="stop",
    )
    data = resp.model_dump()
    clone = LLMResponse(**data)
    assert clone == resp


def test_llm_response_rejects_negative_tokens() -> None:
    with pytest.raises(ValidationError):
        LLMResponse(
            text="x",
            model="m",
            input_tokens=-1,
            output_tokens=0,
            finish_reason="stop",
        )


def test_split_system_extracts_leading_system_message() -> None:
    msgs = [
        Message(role="system", content="you are terse"),
        Message(role="user", content="hi"),
        Message(role="assistant", content="hi"),
    ]
    system, rest = split_system(msgs)
    assert system == "you are terse"
    assert [m.role for m in rest] == ["user", "assistant"]


def test_split_system_without_leading_system_returns_none() -> None:
    msgs = [Message(role="user", content="hi")]
    system, rest = split_system(msgs)
    assert system is None
    assert rest == msgs


def test_split_system_empty_messages() -> None:
    system, rest = split_system([])
    assert system is None
    assert rest == []


def test_error_hierarchy() -> None:
    assert issubclass(AuthError, LLMError)
    assert issubclass(RateLimitError, LLMError)
