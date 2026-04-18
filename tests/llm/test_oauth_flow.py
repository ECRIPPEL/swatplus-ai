"""Tests for PKCE + OAuth token exchange / refresh and the redirect listener."""

from __future__ import annotations

import base64
import hashlib
import threading
import time
import urllib.parse
from urllib.request import urlopen

import httpx
import pytest

from swatplus_ai.llm.interface import AuthError
from swatplus_ai.llm.oauth_flow import (
    build_authorize_url,
    exchange_code_for_tokens,
    find_ephemeral_port,
    generate_code_challenge,
    generate_code_verifier,
    refresh_access_token,
    wait_for_redirect,
)


def test_code_verifier_is_url_safe_and_long_enough() -> None:
    v1 = generate_code_verifier()
    v2 = generate_code_verifier()
    # RFC 7636 section 4.1: 43-128 chars, unreserved set only
    assert 43 <= len(v1) <= 128
    assert v1 != v2  # random
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
    assert set(v1) <= allowed


def test_code_challenge_is_sha256_base64url_nopad() -> None:
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"  # RFC 7636 example
    challenge = generate_code_challenge(verifier)
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    assert challenge == expected
    # RFC 7636 section 4.2 worked example
    assert challenge == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_build_authorize_url_includes_pkce_params() -> None:
    url = build_authorize_url(
        "https://auth.example.com/authorize",
        client_id="my-client",
        code_challenge="abc",
        redirect_uri="http://127.0.0.1:5000/cb",
        scope="profile email",
    )
    parsed = urllib.parse.urlparse(url)
    q = dict(urllib.parse.parse_qsl(parsed.query))
    assert q["response_type"] == "code"
    assert q["client_id"] == "my-client"
    assert q["redirect_uri"] == "http://127.0.0.1:5000/cb"
    assert q["code_challenge"] == "abc"
    assert q["code_challenge_method"] == "S256"
    assert q["scope"] == "profile email"


async def test_exchange_code_for_tokens_parses_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        form = dict(urllib.parse.parse_qsl(request.content.decode("utf-8")))
        assert form["grant_type"] == "authorization_code"
        assert form["code"] == "the-code"
        assert form["code_verifier"] == "the-verifier"
        assert form["client_id"] == "c1"
        assert form["redirect_uri"] == "http://127.0.0.1:1234/cb"
        return httpx.Response(
            200,
            json={
                "access_token": "ACC",
                "refresh_token": "REF",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        before = time.time()
        bundle = await exchange_code_for_tokens(
            client,
            "https://auth.example.com/token",
            "c1",
            "the-code",
            "the-verifier",
            "http://127.0.0.1:1234/cb",
        )
        assert bundle.access_token == "ACC"
        assert bundle.refresh_token == "REF"
        assert bundle.token_type == "Bearer"
        # expires_at roughly one hour in the future
        assert before + 3500 <= bundle.expires_at <= time.time() + 3700
    finally:
        await client.aclose()


async def test_exchange_code_raises_on_error_status() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(AuthError):
            await exchange_code_for_tokens(
                client,
                "https://auth.example.com/token",
                "c1",
                "bad",
                "v",
                "http://127.0.0.1:1/cb",
            )
    finally:
        await client.aclose()


async def test_refresh_access_token_preserves_refresh_when_omitted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        form = dict(urllib.parse.parse_qsl(request.content.decode("utf-8")))
        assert form["grant_type"] == "refresh_token"
        assert form["refresh_token"] == "OLD-REFRESH"
        # Provider omits refresh_token on refresh (common).
        return httpx.Response(
            200,
            json={"access_token": "NEW-ACC", "expires_in": 1800, "token_type": "Bearer"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        bundle = await refresh_access_token(
            client, "https://auth.example.com/token", "c1", "OLD-REFRESH"
        )
        assert bundle.access_token == "NEW-ACC"
        assert bundle.refresh_token == "OLD-REFRESH"
    finally:
        await client.aclose()


async def test_refresh_access_token_replaces_refresh_when_returned() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "access_token": "NEW-ACC",
                "refresh_token": "NEW-REFRESH",
                "expires_in": 1800,
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        bundle = await refresh_access_token(client, "https://auth.example.com/token", "c1", "OLD")
        assert bundle.refresh_token == "NEW-REFRESH"
    finally:
        await client.aclose()


def test_wait_for_redirect_captures_query_params() -> None:
    port = find_ephemeral_port()
    captured: dict[str, dict[str, str]] = {}

    def listener() -> None:
        captured["params"] = wait_for_redirect(port, timeout=10.0)

    t = threading.Thread(target=listener, daemon=True)
    t.start()

    # Let the listener bind.
    time.sleep(0.2)
    url = f"http://127.0.0.1:{port}/callback?code=THE_CODE&state=xyz"
    with urlopen(url, timeout=5.0) as resp:
        assert resp.status == 200

    t.join(timeout=5.0)
    assert not t.is_alive()
    assert captured["params"]["code"] == "THE_CODE"
    assert captured["params"]["state"] == "xyz"


def test_wait_for_redirect_times_out() -> None:
    port = find_ephemeral_port()
    with pytest.raises(AuthError):
        wait_for_redirect(port, timeout=1.0)
