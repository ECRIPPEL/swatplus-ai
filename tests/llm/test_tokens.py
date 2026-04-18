"""Tests for MemoryTokenStore + KeyringTokenStore fallback behavior."""

from __future__ import annotations

import sys
from typing import Any

import pytest

from swatplus_ai.llm.interface import LLMError
from swatplus_ai.llm.tokens import KeyringTokenStore, MemoryTokenStore


def test_memory_store_round_trip() -> None:
    store = MemoryTokenStore()
    assert store.get("a") is None
    store.set("a", "alpha")
    assert store.get("a") == "alpha"
    store.set("a", "alpha2")
    assert store.get("a") == "alpha2"
    store.delete("a")
    assert store.get("a") is None
    # delete on missing key is a no-op
    store.delete("a")


def test_memory_store_isolates_keys() -> None:
    store = MemoryTokenStore()
    store.set("anthropic_api_key", "sk-a")
    store.set("openai_api_key", "sk-o")
    assert store.get("anthropic_api_key") == "sk-a"
    assert store.get("openai_api_key") == "sk-o"


def test_keyring_store_raises_when_keyring_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate `keyring` not being importable.
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "keyring" or name.startswith("keyring."):
            raise ImportError("No module named 'keyring'")
        return real_import(name, *args, **kwargs)

    # Clear any cached keyring modules so the ImportError fires fresh.
    for mod_name in list(sys.modules):
        if mod_name == "keyring" or mod_name.startswith("keyring."):
            monkeypatch.delitem(sys.modules, mod_name, raising=False)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(LLMError) as excinfo:
        KeyringTokenStore()
    # Hint should name the install command so users aren't left guessing.
    assert "keyring" in str(excinfo.value).lower()
    assert "pip install" in str(excinfo.value).lower()
