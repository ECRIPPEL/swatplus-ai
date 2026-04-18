"""Tests for the OAuth-passthrough backends.

Focus: 401 → refresh → retry; refresh failure surfaces AuthError;
first-use consent prompt fires and is recorded; optional fallback to
an API-key backend on persistent AuthError.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from rich.console import Console

from swatplus_ai.llm.backends.mock import MockBackend
from swatplus_ai.llm.backends.oauth import AnthropicOAuthBackend
from swatplus_ai.llm.interface import LLMError, Message
from swatplus_ai.llm.tokens import MemoryTokenStore

_MESSAGES = [Message(role="user", content="hi")]


class _PinnedAnthropicOAuth(AnthropicOAuthBackend):
    """Test subclass with a pinned (fake) client_id so refresh is exercisable."""

    CLIENT_ID = "test-client-id"


def _store_with_tokens(access: str = "ACC", refresh: str = "REF") -> MemoryTokenStore:
    s = MemoryTokenStore()
    s.set("anthropic_oauth_access", access)
    s.set("anthropic_oauth_refresh", refresh)
    s.set("anthropic_oauth_expires_at", "9999999999")
    return s


def _mark_consent(project_dir: Path) -> None:
    flag = project_dir / ".swatplus-ai" / "oauth_consent_anthropic.json"
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text(json.dumps({"provider": "anthropic"}))


def _success_payload(text: str = "hello") -> dict:
    return {
        "id": "msg_01",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-4-5-20251001",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


async def test_uses_bearer_token_from_store(tmp_path: Path) -> None:
    _mark_consent(tmp_path)
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization", "")
        return httpx.Response(200, json=_success_payload())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        backend = _PinnedAnthropicOAuth(
            _store_with_tokens(access="ACC123"),
            client=client,
            project_dir=tmp_path,
        )
        resp = await backend.complete(_MESSAGES)
        assert resp.text == "hello"
        assert captured["authorization"] == "Bearer ACC123"
    finally:
        await client.aclose()


async def test_401_triggers_refresh_and_retry(tmp_path: Path) -> None:
    _mark_consent(tmp_path)
    # Sequence of responses keyed by URL path.
    messages_hits = iter([401, 200])
    token_hits = iter([200])
    seen_tokens: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1/messages":
            seen_tokens.append(request.headers.get("authorization", ""))
            status = next(messages_hits)
            if status == 401:
                return httpx.Response(401, json={"error": "expired"})
            return httpx.Response(200, json=_success_payload("after-refresh"))
        if path == "/v1/oauth/token":
            assert next(token_hits) == 200
            return httpx.Response(
                200,
                json={
                    "access_token": "NEW-ACC",
                    "refresh_token": "NEW-REF",
                    "expires_in": 3600,
                },
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        store = _store_with_tokens(access="OLD-ACC", refresh="OLD-REF")
        backend = _PinnedAnthropicOAuth(store, client=client, project_dir=tmp_path)
        resp = await backend.complete(_MESSAGES)
        assert resp.text == "after-refresh"
        # First call used old token, second used freshly-stored new token.
        assert seen_tokens == ["Bearer OLD-ACC", "Bearer NEW-ACC"]
        assert store.get("anthropic_oauth_access") == "NEW-ACC"
        assert store.get("anthropic_oauth_refresh") == "NEW-REF"
    finally:
        await client.aclose()


async def test_refresh_failure_surfaces_auth_error_without_fallback(tmp_path: Path) -> None:
    _mark_consent(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/messages":
            return httpx.Response(401, json={"error": "expired"})
        if request.url.path == "/v1/oauth/token":
            return httpx.Response(400, json={"error": "invalid_grant"})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        backend = _PinnedAnthropicOAuth(_store_with_tokens(), client=client, project_dir=tmp_path)
        with pytest.raises(LLMError):
            await backend.complete(_MESSAGES)
    finally:
        await client.aclose()


async def test_fallback_used_on_persistent_auth_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _mark_consent(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/messages":
            return httpx.Response(401, json={"error": "denied"})
        if request.url.path == "/v1/oauth/token":
            return httpx.Response(400, json={"error": "invalid_grant"})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fallback = MockBackend(replies=["from-fallback"])
    try:
        backend = _PinnedAnthropicOAuth(
            _store_with_tokens(),
            client=client,
            project_dir=tmp_path,
            fallback=fallback,
            console=Console(stderr=True, force_terminal=False, no_color=True),
        )
        resp = await backend.complete(_MESSAGES)
        assert resp.text == "from-fallback"
    finally:
        await client.aclose()
    err = capsys.readouterr().err
    assert "falling back" in err.lower()


async def test_login_blocks_when_client_id_unpinned(tmp_path: Path) -> None:
    _mark_consent(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    try:
        backend = AnthropicOAuthBackend(MemoryTokenStore(), client=client, project_dir=tmp_path)
        with pytest.raises(LLMError) as excinfo:
            await backend.login()
        assert "client_id" in str(excinfo.value).lower()
    finally:
        await client.aclose()


async def test_consent_prompter_fires_on_first_login(tmp_path: Path) -> None:
    # Even though login will abort (client_id unpinned), consent should fire first.
    prompted = {"count": 0}

    def fake_prompt(_: Console) -> None:
        prompted["count"] += 1

    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    try:
        # Use a subclass that fakes a pinned client_id so consent runs before
        # the network flow — then we check the consent flag was recorded.
        class _PinnedBackend(AnthropicOAuthBackend):
            CLIENT_ID = "pinned-test-id"

        backend = _PinnedBackend(
            MemoryTokenStore(),
            client=client,
            project_dir=tmp_path,
            consent_prompter=fake_prompt,
        )
        # wait_for_redirect would block forever; replace the flow with just
        # the consent step by invoking _ensure_consent directly.
        backend._ensure_consent()
        assert prompted["count"] == 1
        assert (tmp_path / ".swatplus-ai" / "oauth_consent_anthropic.json").exists()
        # Second call must NOT re-prompt.
        backend._ensure_consent()
        assert prompted["count"] == 1
    finally:
        await client.aclose()


async def test_missing_access_token_raises_auth_error(tmp_path: Path) -> None:
    _mark_consent(tmp_path)
    # Empty store → no access token available.
    store = MemoryTokenStore()
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    try:
        backend = AnthropicOAuthBackend(store, client=client, project_dir=tmp_path)
        with pytest.raises(LLMError):
            await backend.complete(_MESSAGES)
    finally:
        await client.aclose()
