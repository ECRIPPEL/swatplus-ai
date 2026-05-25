"""``swatplus-ai config`` sub-app: manage per-provider API keys.

Four sibling commands:

* ``config set-key <provider> <key>`` — store a key.
* ``config show-key <provider>`` — report ``present`` / ``unset``
  without ever echoing the key or a prefix of it. That is a deliberate
  security floor, not an ergonomic regression: printing even the first
  few characters to a terminal ends up in screenshots and scrollback.
* ``config delete-key <provider>`` — idempotent remove.
* ``config status`` — two-line summary across both providers.

Backing store: :class:`~swatplus_ai.llm.tokens.KeyringTokenStore` in
production. ``_default_store()`` is overridable via monkeypatch so the
CI and local test suite never touch the user's real OS keychain. The
keyring package is optional — if it's missing, the default factory
raises :class:`LLMError` with an install hint and the CLI maps that to
exit 1 with a friendly message.

Key naming: ``<provider>_api_key`` inside the keyring service — matches
the ``<provider>_oauth_*`` convention already used by the OAuth
backend so a single keyring inspection shows the full credential set.
"""

from __future__ import annotations

import typer

from swatplus_ai.llm.interface import LLMError
from swatplus_ai.llm.tokens import KeyringTokenStore, TokenStore

app = typer.Typer(
    name="config",
    help="Manage per-provider API keys for SWAT+ai.",
    no_args_is_help=True,
)

_PROVIDERS: tuple[str, ...] = ("anthropic", "openai")


def _default_store() -> TokenStore:
    """Build the production token store.

    Isolated as a function (rather than an import-time singleton) so
    tests can monkeypatch it to a :class:`MemoryTokenStore` without
    importing the ``keyring`` package.
    """
    return KeyringTokenStore()


def _key_name(provider: str) -> str:
    return f"{provider}_api_key"


def _validate_provider(provider: str) -> str:
    """Accept only the known providers; exit 2 otherwise (typer convention)."""
    normalized = provider.strip().lower()
    if normalized not in _PROVIDERS:
        typer.echo(f"unknown provider {provider!r}; expected one of {', '.join(_PROVIDERS)}")
        raise typer.Exit(code=2)
    return normalized


def _store() -> TokenStore:
    """Resolve the active token store, mapping keyring-missing to exit 1."""
    try:
        return _default_store()
    except LLMError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc


@app.command("set-key")
def set_key(
    provider: str = typer.Argument(..., help="Provider id: anthropic | openai."),
    key: str = typer.Argument(..., help="API key string to store."),
) -> None:
    """Persist an API key for ``provider`` to the OS keychain."""
    normalized = _validate_provider(provider)
    trimmed = key.strip()
    if not trimmed:
        typer.echo("API key is empty after stripping whitespace; refusing to store.")
        raise typer.Exit(code=2)
    store = _store()
    store.set(_key_name(normalized), trimmed)
    typer.echo(f"{normalized}: key stored ({len(trimmed)} chars).")


@app.command("show-key")
def show_key(
    provider: str = typer.Argument(..., help="Provider id: anthropic | openai."),
) -> None:
    """Report whether a key is stored — never echoes the key itself."""
    normalized = _validate_provider(provider)
    store = _store()
    value = store.get(_key_name(normalized))
    typer.echo(f"{normalized}: {'present' if value else 'unset'}")


@app.command("delete-key")
def delete_key(
    provider: str = typer.Argument(..., help="Provider id: anthropic | openai."),
) -> None:
    """Remove the stored key for ``provider`` (idempotent)."""
    normalized = _validate_provider(provider)
    store = _store()
    store.delete(_key_name(normalized))
    typer.echo(f"{normalized}: key removed (if any).")


@app.command("status")
def status() -> None:
    """Print one line per known provider: ``<provider>: present|unset``."""
    store = _store()
    for provider in _PROVIDERS:
        value = store.get(_key_name(provider))
        typer.echo(f"{provider}: {'present' if value else 'unset'}")


__all__ = ["_default_store", "_key_name", "app"]
