"""Experimental OAuth-passthrough backends.

Reuses the user's existing Claude.ai or ChatGPT subscription via the same
PKCE flow as the official Claude Code / OpenAI Codex CLIs. Not the
default — users opt in explicitly. See the architecture doc's
"Provider Access & Authentication > Backend 2" for the rationale and the
caveats users accept.

How it differs from the API-key backends:

- Auth header is ``Authorization: Bearer <access_token>``, where the
  access token comes from a :class:`TokenStore` (not a config value).
- On HTTP 401, the backend attempts a refresh-token exchange and
  retries the request once. If refresh still fails and a fallback
  backend is configured, the call is forwarded there with a visible
  warning.
- On first login per project, the user gets a rich-formatted consent
  prompt explaining the experimental status. Consent is persisted to
  ``.swatplus-ai/oauth_consent_<provider>.json`` so it doesn't repeat.

Client IDs for Claude.ai and ChatGPT are public values shipped in the
official CLIs — they are **not** secrets, but they must match what the
provider expects. Until pinned, login raises a clear
:class:`LLMError`. See the ``_CLIENT_ID = "TODO: ..."`` comments below.
"""

from __future__ import annotations

import contextlib
import json as _json
import webbrowser
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

import httpx
from rich.console import Console

from swatplus_ai.llm.backends.api_key import _AnthropicProtocol, _OpenAIProtocol
from swatplus_ai.llm.interface import AuthError, LLMBackend, LLMError, LLMResponse, Message
from swatplus_ai.llm.oauth_flow import (
    build_authorize_url,
    exchange_code_for_tokens,
    find_ephemeral_port,
    generate_code_challenge,
    generate_code_verifier,
    refresh_access_token,
    wait_for_redirect,
)
from swatplus_ai.llm.tokens import TokenStore

_CONSENT_TEXT = (
    "[bold yellow]⚠ EXPERIMENTAL OAuth backend[/]\n"
    "\n"
    "This reuses your Claude.ai / ChatGPT subscription via the same OAuth\n"
    "flow as the official Claude Code / Codex CLIs. Providers [italic]tolerate[/]\n"
    "but do [bold]not[/] formally endorse third-party use; the backend can break\n"
    "if client IDs rotate. You accept responsibility for compliance with\n"
    "provider Terms of Service.\n"
    "\n"
    "Press [bold]Enter[/] to continue, [bold]Ctrl-C[/] to abort."
)


def _default_consent_prompter(console: Console) -> None:
    console.print(_CONSENT_TEXT)
    try:
        input()
    except (KeyboardInterrupt, EOFError) as exc:
        raise LLMError("OAuth consent declined by user") from exc


def _log_fallback(console: Console, provider: str, exc: BaseException) -> None:
    console.print(
        f"[yellow]⚠ {provider} OAuth backend failed ({exc!s}); falling back to API-key backend.[/]"
    )


class _OAuthBackendBase:
    """Shared OAuth lifecycle (login, refresh, retry, fallback).

    Subclasses combine this with a provider protocol mixin
    (``_AnthropicProtocol`` / ``_OpenAIProtocol``) that supplies the
    wire contract, and set the class-level OAuth constants
    (``PROVIDER_KEY``, ``CLIENT_ID``, ``AUTH_URL``, ``TOKEN_URL``,
    ``SCOPE``, ``REDIRECT_PATH``).
    """

    PROVIDER_KEY: ClassVar[str] = ""
    CLIENT_ID: ClassVar[str] = ""
    AUTH_URL: ClassVar[str] = ""
    TOKEN_URL: ClassVar[str] = ""
    SCOPE: ClassVar[str] = ""
    REDIRECT_PATH: ClassVar[str] = "/callback"

    def __init__(
        self,
        store: TokenStore,
        *,
        client: httpx.AsyncClient | None = None,
        fallback: LLMBackend | None = None,
        project_dir: Path | None = None,
        consent_prompter: Callable[[Console], None] | None = None,
        console: Console | None = None,
    ) -> None:
        # _BaseBackend takes care of the httpx client lifecycle.
        super().__init__(client=client)  # type: ignore[call-arg]
        self._store = store
        self._fallback = fallback
        self._project_dir = project_dir or Path.cwd()
        self._console = console or Console(stderr=True)
        self._consent_prompter = consent_prompter or _default_consent_prompter

    # ---- storage keys --------------------------------------------------------
    def _k_access(self) -> str:
        return f"{self.PROVIDER_KEY}_oauth_access"

    def _k_refresh(self) -> str:
        return f"{self.PROVIDER_KEY}_oauth_refresh"

    def _k_expires(self) -> str:
        return f"{self.PROVIDER_KEY}_oauth_expires_at"

    # ---- consent -------------------------------------------------------------
    def _consent_flag_path(self) -> Path:
        return self._project_dir / ".swatplus-ai" / f"oauth_consent_{self.PROVIDER_KEY}.json"

    def _has_consent(self) -> bool:
        return self._consent_flag_path().exists()

    def _record_consent(self) -> None:
        flag = self._consent_flag_path()
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text(
            _json.dumps(
                {
                    "provider": self.PROVIDER_KEY,
                    "acknowledged_at": datetime.now(UTC).isoformat(),
                }
            ),
            encoding="utf-8",
        )

    def _ensure_consent(self) -> None:
        if self._has_consent():
            return
        self._consent_prompter(self._console)
        self._record_consent()

    # ---- login / refresh -----------------------------------------------------
    def _require_client_id(self) -> None:
        if not self.CLIENT_ID or self.CLIENT_ID.startswith("TODO"):
            raise LLMError(
                f"OAuth client_id for {self.PROVIDER_KEY} is not pinned yet. "
                "See comments in src/swatplus_ai/llm/backends/oauth.py for where "
                "the official CLIs publish it upstream. Use the API-key backend "
                "in the meantime."
            )

    async def login(self) -> None:
        """Run the PKCE flow and persist the issued tokens."""
        self._require_client_id()
        self._ensure_consent()

        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        port = find_ephemeral_port()
        redirect_uri = f"http://127.0.0.1:{port}{self.REDIRECT_PATH}"
        authorize_url = build_authorize_url(
            self.AUTH_URL, self.CLIENT_ID, challenge, redirect_uri, self.SCOPE
        )

        self._console.print(
            f"[cyan]Opening browser for {self.PROVIDER_KEY} OAuth login…[/]\n"
            f"If nothing opens, visit this URL manually:\n  {authorize_url}"
        )
        with contextlib.suppress(webbrowser.Error):
            webbrowser.open(authorize_url)

        params = wait_for_redirect(port)
        if "code" not in params:
            raise AuthError(
                f"OAuth redirect did not return an authorization code. Params: {params!r}"
            )

        bundle = await exchange_code_for_tokens(
            self._client,  # type: ignore[attr-defined]
            self.TOKEN_URL,
            self.CLIENT_ID,
            params["code"],
            verifier,
            redirect_uri,
        )
        self._store_bundle_fields(
            access=bundle.access_token,
            refresh=bundle.refresh_token,
            expires_at=bundle.expires_at,
        )
        self._console.print(f"[green]✓ {self.PROVIDER_KEY} OAuth login complete.[/]")

    async def _refresh(self) -> None:
        self._require_client_id()
        refresh = self._store.get(self._k_refresh())
        if not refresh:
            raise AuthError(f"No refresh token stored for {self.PROVIDER_KEY}; run login first.")
        bundle = await refresh_access_token(
            self._client,  # type: ignore[attr-defined]
            self.TOKEN_URL,
            self.CLIENT_ID,
            refresh,
        )
        self._store_bundle_fields(
            access=bundle.access_token,
            refresh=bundle.refresh_token,
            expires_at=bundle.expires_at,
        )

    def _store_bundle_fields(self, *, access: str, refresh: str | None, expires_at: float) -> None:
        self._store.set(self._k_access(), access)
        if refresh:
            self._store.set(self._k_refresh(), refresh)
        self._store.set(self._k_expires(), str(expires_at))

    # ---- auth header used by the provider protocol --------------------------
    def _auth_headers(self) -> dict[str, str]:
        access = self._store.get(self._k_access())
        if not access:
            raise AuthError(f"No OAuth access token for {self.PROVIDER_KEY}; run `login()` first.")
        return self._bearer_headers(access)

    def _bearer_headers(self, access: str) -> dict[str, str]:
        # Overridden per provider to add e.g. anthropic-version.
        raise NotImplementedError

    # ---- complete / stream with refresh-retry + optional fallback -----------
    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        try:
            return await super().complete(  # type: ignore[misc,no-any-return]
                messages, model=model, max_tokens=max_tokens, temperature=temperature
            )
        except AuthError:
            pass  # try refresh below

        try:
            await self._refresh()
            return await super().complete(  # type: ignore[misc,no-any-return]
                messages, model=model, max_tokens=max_tokens, temperature=temperature
            )
        except LLMError as exc:
            return await self._fallback_complete(
                messages, model=model, max_tokens=max_tokens, temperature=temperature, cause=exc
            )

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        emitted = False
        try:
            async for chunk in super().stream(  # type: ignore[misc]
                messages, model=model, max_tokens=max_tokens, temperature=temperature
            ):
                emitted = True
                yield chunk
            return
        except AuthError as exc:
            if emitted:
                # Can't safely restart after partial output — surface to caller.
                raise
            first_exc: LLMError = exc

        try:
            await self._refresh()
        except LLMError as exc:
            async for chunk in self._fallback_stream(
                messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                cause=exc,
                original=first_exc,
            ):
                yield chunk
            return

        try:
            async for chunk in super().stream(  # type: ignore[misc]
                messages, model=model, max_tokens=max_tokens, temperature=temperature
            ):
                yield chunk
        except LLMError as exc:
            async for chunk in self._fallback_stream(
                messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                cause=exc,
                original=first_exc,
            ):
                yield chunk

    async def _fallback_complete(
        self,
        messages: list[Message],
        *,
        model: str | None,
        max_tokens: int,
        temperature: float,
        cause: LLMError,
    ) -> LLMResponse:
        if self._fallback is None:
            raise cause
        _log_fallback(self._console, self.PROVIDER_KEY, cause)
        return await self._fallback.complete(
            messages, model=model, max_tokens=max_tokens, temperature=temperature
        )

    async def _fallback_stream(
        self,
        messages: list[Message],
        *,
        model: str | None,
        max_tokens: int,
        temperature: float,
        cause: LLMError,
        original: LLMError,
    ) -> AsyncIterator[str]:
        if self._fallback is None:
            raise cause
        _log_fallback(self._console, self.PROVIDER_KEY, original)
        async for chunk in self._fallback.stream(
            messages, model=model, max_tokens=max_tokens, temperature=temperature
        ):
            yield chunk


# ----- Anthropic OAuth ----------------------------------------------------------

# TODO: pin from upstream CLI. The public client_id lives in Anthropic's
# Claude Code source — see https://github.com/anthropics/claude-code (search
# for "oauth/authorize" or "client_id"). Leave as TODO until confidently
# identified; login() raises a clear LLMError while unpinned.
_ANTHROPIC_CLIENT_ID = "TODO: pin from upstream CLI (claude-code)"
_ANTHROPIC_AUTH_URL = "https://claude.ai/oauth/authorize"
_ANTHROPIC_TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
_ANTHROPIC_SCOPE = "org:create_api_key user:profile user:inference"


class AnthropicOAuthBackend(_OAuthBackendBase, _AnthropicProtocol):
    """OAuth passthrough to Anthropic's Messages API using a Claude.ai token."""

    PROVIDER_KEY: ClassVar[str] = "anthropic"
    CLIENT_ID: ClassVar[str] = _ANTHROPIC_CLIENT_ID
    AUTH_URL: ClassVar[str] = _ANTHROPIC_AUTH_URL
    TOKEN_URL: ClassVar[str] = _ANTHROPIC_TOKEN_URL
    SCOPE: ClassVar[str] = _ANTHROPIC_SCOPE

    def _bearer_headers(self, access: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access}",
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": "application/json",
        }


# ----- OpenAI OAuth -------------------------------------------------------------

# TODO: pin from upstream CLI. The public client_id for Codex CLI's OAuth
# flow lives in the openai/codex repo (https://github.com/openai/codex) —
# search the codex binary's source for "client_id" / "pkce". Leave as TODO
# until confidently identified; login() raises a clear LLMError.
_OPENAI_CLIENT_ID = "TODO: pin from upstream CLI (openai/codex)"
_OPENAI_AUTH_URL = "https://auth.openai.com/authorize"
_OPENAI_TOKEN_URL = "https://auth.openai.com/oauth/token"
_OPENAI_SCOPE = "openid email profile offline_access"


class OpenAIOAuthBackend(_OAuthBackendBase, _OpenAIProtocol):
    """OAuth passthrough to OpenAI's chat-completions API via a ChatGPT token."""

    PROVIDER_KEY: ClassVar[str] = "openai"
    CLIENT_ID: ClassVar[str] = _OPENAI_CLIENT_ID
    AUTH_URL: ClassVar[str] = _OPENAI_AUTH_URL
    TOKEN_URL: ClassVar[str] = _OPENAI_TOKEN_URL
    SCOPE: ClassVar[str] = _OPENAI_SCOPE

    def _bearer_headers(self, access: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access}",
            "content-type": "application/json",
        }


__all__ = [
    "AnthropicOAuthBackend",
    "OpenAIOAuthBackend",
]
