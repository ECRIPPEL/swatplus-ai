"""Tests for the ``swatplus-ai config`` sub-app.

Keyring integration with the host OS keychain is deliberately **not**
exercised here — CI runners don't have one, and tests must never touch
the developer's real credential store. We monkeypatch
``_default_store`` to return a :class:`MemoryTokenStore`; the real
:class:`KeyringTokenStore` is tested separately in
``tests/llm/test_tokens.py``.
"""

from __future__ import annotations

from typing import Any

import pytest
from typer.testing import CliRunner

from swatplus_ai.config_cli import _key_name, app
from swatplus_ai.llm.interface import LLMError
from swatplus_ai.llm.tokens import MemoryTokenStore


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> MemoryTokenStore:
    """Inject a fresh in-memory store for each test."""
    instance = MemoryTokenStore()
    monkeypatch.setattr("swatplus_ai.config_cli._default_store", lambda: instance)
    return instance


def _run(args: list[str]) -> Any:
    return CliRunner().invoke(app, args)


def test_set_key_writes_to_store(store: MemoryTokenStore) -> None:
    result = _run(["set-key", "anthropic", "sk-xxx"])
    assert result.exit_code == 0, result.stdout
    assert store.get(_key_name("anthropic")) == "sk-xxx"
    assert "key stored" in result.stdout


def test_show_key_never_leaks_key_material(store: MemoryTokenStore) -> None:
    store.set(_key_name("anthropic"), "sk-secret-abcdef")
    result = _run(["show-key", "anthropic"])
    assert result.exit_code == 0
    assert "present" in result.stdout
    # The literal key — and any 4-char prefix of it — must never appear.
    assert "sk-secret" not in result.stdout
    assert "abcdef" not in result.stdout


def test_show_key_unset_reports_unset(store: MemoryTokenStore) -> None:
    del store
    result = _run(["show-key", "anthropic"])
    assert result.exit_code == 0
    assert "unset" in result.stdout


def test_delete_key_is_idempotent(store: MemoryTokenStore) -> None:
    # First delete on an unset key must still exit 0.
    first = _run(["delete-key", "openai"])
    assert first.exit_code == 0
    store.set(_key_name("openai"), "sk-x")
    second = _run(["delete-key", "openai"])
    assert second.exit_code == 0
    assert store.get(_key_name("openai")) is None
    third = _run(["delete-key", "openai"])
    assert third.exit_code == 0


def test_status_lists_both_providers(store: MemoryTokenStore) -> None:
    store.set(_key_name("anthropic"), "sk-x")
    result = _run(["status"])
    assert result.exit_code == 0
    assert "anthropic: present" in result.stdout
    assert "openai: unset" in result.stdout


def test_set_key_rejects_invalid_provider(store: MemoryTokenStore) -> None:
    del store
    result = _run(["set-key", "groq", "sk-x"])
    assert result.exit_code == 2
    assert "unknown provider" in result.stdout


def test_show_key_rejects_invalid_provider(store: MemoryTokenStore) -> None:
    del store
    result = _run(["show-key", "claude"])
    assert result.exit_code == 2


def test_set_key_rejects_empty_key_after_strip(store: MemoryTokenStore) -> None:
    result = _run(["set-key", "anthropic", "   "])
    assert result.exit_code == 2
    assert "empty" in result.stdout.lower()
    # Nothing was written to the store.
    assert store.get(_key_name("anthropic")) is None


def test_keyring_missing_exits_with_install_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate the optional dep missing: _default_store raises LLMError.
    def _raise() -> MemoryTokenStore:
        raise LLMError(
            "KeyringTokenStore requires the optional 'keyring' package. "
            "Install it with:  pip install 'swatplus-ai[secrets]'."
        )

    monkeypatch.setattr("swatplus_ai.config_cli._default_store", _raise)
    result = _run(["show-key", "anthropic"])
    assert result.exit_code == 1
    assert "swatplus-ai[secrets]" in result.stdout


def test_provider_normalized_case_insensitively(store: MemoryTokenStore) -> None:
    result = _run(["set-key", "ANTHROPIC", "sk-upper"])
    assert result.exit_code == 0
    assert store.get(_key_name("anthropic")) == "sk-upper"
