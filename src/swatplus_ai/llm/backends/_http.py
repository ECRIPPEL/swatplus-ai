"""HTTP + SSE machinery shared by every real-provider backend.

Two public helpers:

- :func:`request_json` — POST JSON, return decoded JSON. Maps non-2xx
  responses to the appropriate :class:`~swatplus_ai.llm.interface.LLMError`
  subclass.
- :func:`stream_sse` — open an SSE stream and yield ``{event, data}``
  dicts, terminating on the OpenAI-style ``[DONE]`` sentinel.

Both API-key and OAuth backends reuse these so retry-on-401 wrappers
only need to re-supply the auth header, not the request body.
"""

from __future__ import annotations

import json as _json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from swatplus_ai.llm.interface import AuthError, LLMError, RateLimitError


def _map_http_error(status: int, body: bytes | str) -> LLMError:
    if isinstance(body, bytes):
        try:
            detail = body.decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover — decode with replace shouldn't fail
            detail = repr(body)
    else:
        detail = body
    snippet = detail[:2000]
    if status == 401 or status == 403:
        return AuthError(f"HTTP {status} from provider: {snippet}")
    if status == 429:
        return RateLimitError(f"HTTP {status} rate-limited: {snippet}")
    return LLMError(f"HTTP {status} from provider: {snippet}")


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any],
) -> dict[str, Any]:
    """Send a single JSON request and return the decoded response body."""
    response = await client.request(method, url, headers=headers, json=json_body)
    if response.status_code >= 400:
        raise _map_http_error(response.status_code, response.content)
    data = response.json()
    if not isinstance(data, dict):
        raise LLMError(f"Provider returned non-object JSON: {type(data).__name__}")
    return data


async def stream_sse(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    """Yield parsed SSE frames from ``url`` until the stream ends.

    Each yielded dict has shape ``{"event": str | None, "data": dict}``.
    The generator returns (terminates) cleanly on an OpenAI-style
    ``data: [DONE]`` sentinel; Anthropic's ``message_stop`` event is
    surfaced to the caller, which decides when to stop iterating.
    """
    async with client.stream(method, url, headers=headers, json=json_body) as response:
        if response.status_code >= 400:
            body = await response.aread()
            raise _map_http_error(response.status_code, body)

        event_type: str | None = None
        data_lines: list[str] = []

        async for raw_line in response.aiter_lines():
            line = raw_line.rstrip("\r")
            if line == "":
                if data_lines:
                    data_str = "\n".join(data_lines)
                    if data_str.strip() == "[DONE]":
                        return
                    try:
                        payload = _json.loads(data_str)
                    except _json.JSONDecodeError:
                        # Skip unparseable frames rather than failing the whole stream;
                        # providers occasionally emit comment/keepalive frames.
                        pass
                    else:
                        if isinstance(payload, dict):
                            yield {"event": event_type, "data": payload}
                event_type = None
                data_lines = []
                continue
            if line.startswith(":"):
                continue  # SSE comment / keepalive
            if line.startswith("event:"):
                event_type = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].lstrip(" "))
