"""Provider-agnostic contracts for LLM backends.

Modules never talk to a specific provider — they consume :class:`LLMBackend`
and receive :class:`LLMResponse` objects. Swapping API-key for OAuth or local
models later means implementing one more class, nothing else.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    """One turn in an LLM conversation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: Role
    content: str


class LLMResponse(BaseModel):
    """Complete (non-streaming) LLM response plus accounting metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    finish_reason: str = Field(
        description=(
            "Provider-normalized stop reason: 'stop' (natural end), 'length' "
            "(max_tokens hit), 'content_filter', or 'error'."
        )
    )


class LLMError(Exception):
    """Base class for every LLM-backend error. Safe for modules to catch."""


class AuthError(LLMError):
    """Credentials missing, invalid, or revoked."""


class RateLimitError(LLMError):
    """Provider returned HTTP 429 or an equivalent throttling signal."""


@runtime_checkable
class LLMBackend(Protocol):
    """Minimum interface every provider backend implements.

    Implementations must be safe to call concurrently from multiple tasks
    (each call carries its own state; no mutable instance data beyond the
    HTTP client and credentials).
    """

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Return a fully-materialized response for ``messages``."""
        ...

    def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Yield incremental text deltas as the provider streams tokens.

        The iterator terminates when the provider signals end-of-message. On
        error (auth, rate-limit, transport) the iterator raises the matching
        :class:`LLMError` subclass at the point the error is observed.
        """
        ...


def split_system(messages: list[Message]) -> tuple[str | None, list[Message]]:
    """Split a leading system message out of ``messages``.

    Anthropic's Messages API takes the system prompt as a top-level field
    rather than as a role in the message list; OpenAI folds it into messages
    directly. Backends use this helper to normalize the difference.
    """
    if messages and messages[0].role == "system":
        return messages[0].content, messages[1:]
    return None, messages
