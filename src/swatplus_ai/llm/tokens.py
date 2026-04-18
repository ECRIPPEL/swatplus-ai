"""Secret storage for LLM credentials.

Two implementations ship:

- :class:`MemoryTokenStore` — ephemeral dict, safe for tests and short-lived
  dev sessions where OS-keychain integration is not desired.
- :class:`KeyringTokenStore` — OS-keychain-backed (Windows Credential
  Manager, macOS Keychain, Linux Secret Service) via the ``keyring``
  package. Keyring is loaded lazily because it is an optional dependency:
  constructing the store without the package installed raises
  :class:`LLMError` with an install hint rather than failing at import.

Both stores share the same small protocol — ``get`` / ``set`` / ``delete``
keyed by string — so API keys and OAuth tokens coexist in one place. The
OAuth backend uses three keys per provider: ``<provider>_oauth_access``,
``<provider>_oauth_refresh``, ``<provider>_oauth_expires_at``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from swatplus_ai.llm.interface import LLMError

_SERVICE_NAME = "swatplus-ai"

_KEYRING_INSTALL_HINT = (
    "KeyringTokenStore requires the optional 'keyring' package. "
    "Install it with:  pip install 'swatplus-ai[secrets]'  "
    "(or directly:  pip install keyring)."
)


@runtime_checkable
class TokenStore(Protocol):
    """Minimum persistence surface for credentials."""

    def get(self, key: str) -> str | None:
        """Return the stored value for ``key`` or ``None`` if unset."""
        ...

    def set(self, key: str, value: str) -> None:
        """Overwrite the stored value for ``key``."""
        ...

    def delete(self, key: str) -> None:
        """Remove ``key`` if present. No-op when absent."""
        ...


class MemoryTokenStore:
    """In-process token store. Values live only for the lifetime of this object."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


class KeyringTokenStore:
    """OS-keychain-backed token store.

    ``keyring`` is imported lazily so the rest of the LLM package works
    without the optional dependency installed. If ``keyring`` is missing,
    constructing this store raises :class:`LLMError` with the install hint.
    """

    def __init__(self, service: str = _SERVICE_NAME) -> None:
        self._service = service
        try:
            import keyring  # noqa: F401  — import probe only
        except ImportError as exc:  # pragma: no cover - tested via monkeypatch
            raise LLMError(_KEYRING_INSTALL_HINT) from exc

    def get(self, key: str) -> str | None:
        import keyring

        value: str | None = keyring.get_password(self._service, key)
        return value

    def set(self, key: str, value: str) -> None:
        import keyring

        keyring.set_password(self._service, key, value)

    def delete(self, key: str) -> None:
        import contextlib

        import keyring
        from keyring.errors import PasswordDeleteError

        # Deleting an absent entry is a no-op by contract.
        with contextlib.suppress(PasswordDeleteError):
            keyring.delete_password(self._service, key)
