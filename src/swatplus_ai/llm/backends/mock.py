"""In-process deterministic backend for tests and offline dev.

``MockBackend`` never hits the network — it returns a canned reply (or a
per-call scripted sequence of replies) and echoes the last user message
when no script is configured. Use it in unit tests that exercise
prompt-assembler / module code without binding to a real provider.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from time import perf_counter
from typing import ClassVar

import swatplus_ai.telemetry as telemetry
from swatplus_ai.llm.interface import LLMResponse, Message


class MockBackend:
    """Deterministic :class:`~swatplus_ai.llm.interface.LLMBackend` for tests.

    Parameters
    ----------
    replies:
        Optional sequence of canned reply strings, consumed in order on
        each ``complete``/``stream`` call. When exhausted (or not
        provided), the backend falls back to echoing the last user
        message, prefixed with ``"[mock] "``.
    model:
        Name reported in :attr:`LLMResponse.model`.
    chunk_size:
        Number of characters per streamed delta. Keeps streaming tests
        realistic without coupling to any real provider's chunking.
    """

    PROVIDER: ClassVar[str] = "mock"

    def __init__(
        self,
        replies: Sequence[str] | None = None,
        *,
        model: str = "mock-model",
        chunk_size: int = 8,
    ) -> None:
        self._replies: list[str] = list(replies) if replies else []
        self._call_index = 0
        self._model = model
        self._chunk_size = chunk_size

    def _next_reply(self, messages: list[Message]) -> str:
        if self._call_index < len(self._replies):
            reply = self._replies[self._call_index]
            self._call_index += 1
            return reply
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )
        return f"[mock] {last_user}"

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        resolved_model = model or self._model
        t0 = perf_counter()
        try:
            reply = self._next_reply(messages)
            response = LLMResponse(
                text=reply,
                model=resolved_model,
                input_tokens=sum(len(m.content) for m in messages),
                output_tokens=len(reply),
                finish_reason="stop",
            )
        except Exception as exc:
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
        reply = self._next_reply(messages)
        for i in range(0, len(reply), self._chunk_size):
            yield reply[i : i + self._chunk_size]
