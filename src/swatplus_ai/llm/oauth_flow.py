"""Browser-based OAuth 2.0 Authorization Code + PKCE flow.

Powers the experimental :mod:`swatplus_ai.llm.backends.oauth` backend. The
flow mirrors what Claude Code and OpenAI Codex CLI do to obtain tokens
bound to a user's Claude.ai / ChatGPT subscription:

1. Generate a PKCE ``code_verifier`` + SHA-256 ``code_challenge`` (RFC 7636).
2. Open the user's browser at the provider's authorize endpoint with the
   challenge and a ``redirect_uri`` pointing at ``http://127.0.0.1:<port>/``.
3. Spin up a one-shot localhost HTTP listener on that port; wait for the
   provider to redirect the browser back with ``?code=...``.
4. POST the code + verifier to the provider's token endpoint to receive
   an access token + refresh token.
5. On expiry, POST the refresh token to the same endpoint for a new
   access token.

The auth/listener pieces are stdlib-only (``secrets``, ``hashlib``,
``base64``, ``socket``, ``http.server``, ``webbrowser``, ``urllib``). The
token-exchange POSTs use :mod:`httpx` so tests can swap in
``httpx.MockTransport`` and the whole gateway shares one HTTP transport.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import secrets
import socket
import time
import urllib.parse
from dataclasses import dataclass
from typing import Final

import httpx

from swatplus_ai.llm.interface import AuthError

_VERIFIER_BYTES: Final[int] = 48  # -> ~64 URL-safe chars, within RFC 7636's [43, 128]
_DEFAULT_REDIRECT_TIMEOUT: Final[float] = 300.0  # 5 minutes


@dataclass(frozen=True)
class TokenBundle:
    """Tokens returned by an OAuth token endpoint.

    ``expires_at`` is an absolute Unix timestamp, not a relative
    ``expires_in`` — computed once at receive time so downstream code
    doesn't need the original request clock.
    """

    access_token: str
    refresh_token: str | None
    expires_at: float
    token_type: str = "Bearer"


def generate_code_verifier() -> str:
    """Return a cryptographically-random PKCE code verifier (RFC 7636 §4.1)."""
    return secrets.token_urlsafe(_VERIFIER_BYTES)


def generate_code_challenge(verifier: str) -> str:
    """Return the S256 PKCE code challenge for ``verifier`` (RFC 7636 §4.2)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def find_ephemeral_port() -> int:
    """Bind a socket to port 0 to let the OS pick a free port, then release it.

    There's a small TOCTOU window where another process could grab the
    port before the listener re-binds; acceptable for a local dev-only
    flow that the user is watching in real time.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_authorize_url(
    auth_url: str,
    client_id: str,
    code_challenge: str,
    redirect_uri: str,
    scope: str,
    *,
    state: str | None = None,
) -> str:
    """Build the provider's ``/authorize`` URL with PKCE parameters."""
    params: dict[str, str] = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": scope,
    }
    if state is not None:
        params["state"] = state
    return f"{auth_url}?{urllib.parse.urlencode(params)}"


def wait_for_redirect(port: int, *, timeout: float = _DEFAULT_REDIRECT_TIMEOUT) -> dict[str, str]:
    """Block until the browser hits ``http://127.0.0.1:<port>/...``.

    Returns the query-string parameters from the redirect (typically
    ``code`` and ``state``). Raises :class:`AuthError` if nothing
    arrives within ``timeout`` seconds.
    """
    captured: dict[str, str] = {}

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            for k, v in urllib.parse.parse_qsl(parsed.query):
                captured[k] = v
            body = (
                b"<html><body style='font-family:sans-serif'>"
                b"<h2>SWAT+ai OAuth</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
                b"</body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            # Silence default stderr access log.
            return

    server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    server.timeout = 0.5  # poll interval
    deadline = time.monotonic() + timeout
    try:
        while not captured:
            if time.monotonic() > deadline:
                raise AuthError(f"Timed out after {timeout:.0f}s waiting for OAuth redirect")
            server.handle_request()
    finally:
        server.server_close()
    return captured


async def exchange_code_for_tokens(
    client: httpx.AsyncClient,
    token_url: str,
    client_id: str,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> TokenBundle:
    """POST ``code`` + ``verifier`` to ``token_url`` and return the issued tokens."""
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
    }
    response = await client.post(token_url, data=payload)
    return _parse_token_response(response)


async def refresh_access_token(
    client: httpx.AsyncClient,
    token_url: str,
    client_id: str,
    refresh_token: str,
) -> TokenBundle:
    """Exchange a refresh token for a fresh access token at ``token_url``."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    response = await client.post(token_url, data=payload)
    bundle = _parse_token_response(response)
    # Some providers omit refresh_token on refresh — preserve the prior one.
    if bundle.refresh_token is None:
        return TokenBundle(
            access_token=bundle.access_token,
            refresh_token=refresh_token,
            expires_at=bundle.expires_at,
            token_type=bundle.token_type,
        )
    return bundle


def _parse_token_response(response: httpx.Response) -> TokenBundle:
    if response.status_code >= 400:
        snippet = response.text[:500] if response.text else ""
        raise AuthError(f"OAuth token endpoint returned HTTP {response.status_code}: {snippet}")
    try:
        body = response.json()
    except ValueError as exc:
        raise AuthError(
            f"OAuth token endpoint returned non-JSON body: {response.text[:200]}"
        ) from exc
    access = body.get("access_token")
    if not access:
        raise AuthError(f"OAuth token response missing 'access_token': {body!r}")
    expires_in = float(body.get("expires_in", 3600))
    return TokenBundle(
        access_token=str(access),
        refresh_token=body.get("refresh_token"),
        expires_at=time.time() + expires_in,
        token_type=str(body.get("token_type", "Bearer")),
    )
