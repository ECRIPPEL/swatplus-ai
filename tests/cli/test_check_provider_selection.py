"""Tests for backend-selection behaviour of ``swatplus-ai check``.

The CLI's ``_select_backend`` is the one place where ``--provider``,
``--skip-llm``, and the configured key set meet; this file pins every
branch of that resolution tree. Backend classes are monkeypatched to
``FakeBackend`` so we don't have to script httpx responses just to
assert "the right constructor was called with the right key".
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, ClassVar

import pytest
from typer.testing import CliRunner

from swatplus_ai.cli import app as root_app
from swatplus_ai.config_cli import _key_name
from swatplus_ai.llm.interface import LLMResponse, Message
from swatplus_ai.llm.tokens import MemoryTokenStore


class FakeBackend:
    """Protocol-compatible backend that records how it was invoked."""

    instances: ClassVar[list[FakeBackend]] = []

    def __init__(self, api_key: str, *, client: Any = None) -> None:
        del client
        self.api_key = api_key
        self.complete_calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []
        FakeBackend.instances.append(self)

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        del messages, max_tokens, temperature
        self.complete_calls.append({"model": model})
        return LLMResponse(
            text="ok",
            model=model or "fake",
            input_tokens=1,
            output_tokens=1,
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        del messages, max_tokens, temperature
        self.stream_calls.append({"model": model})
        for chunk in ("ok",):
            yield chunk


@pytest.fixture
def fake_backends(monkeypatch: pytest.MonkeyPatch) -> type[FakeBackend]:
    """Patch both real backends in ``swatplus_ai.cli`` to ``FakeBackend``."""
    FakeBackend.instances = []
    monkeypatch.setattr("swatplus_ai.cli.AnthropicBackend", FakeBackend)
    monkeypatch.setattr("swatplus_ai.cli.OpenAIBackend", FakeBackend)
    return FakeBackend


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> MemoryTokenStore:
    """In-memory token store injected into both CLI and config sub-app."""
    instance = MemoryTokenStore()
    monkeypatch.setattr("swatplus_ai.cli._default_store", lambda: instance)
    monkeypatch.setattr("swatplus_ai.config_cli._default_store", lambda: instance)
    return instance


def _invoke_check(
    runner: CliRunner,
    minimal_project_path: Path,
    *extra_args: str,
) -> Any:
    return runner.invoke(
        root_app,
        ["check", str(minimal_project_path), *extra_args],
    )


def test_explicit_anthropic_without_key_exits_one(
    store: MemoryTokenStore,
    fake_backends: type[FakeBackend],
    minimal_project_path: Path,
    isolated_home: Path,
) -> None:
    del store, fake_backends, isolated_home
    result = _invoke_check(
        CliRunner(),
        minimal_project_path,
        "--provider",
        "anthropic",
        "--no-stream",
    )
    assert result.exit_code == 1, result.stdout
    # The remediation hint must be concrete — the user should be able to
    # copy-paste the command and move on.
    assert "config set-key anthropic" in result.stdout


def test_explicit_anthropic_with_key_uses_anthropic_backend(
    store: MemoryTokenStore,
    fake_backends: type[FakeBackend],
    minimal_project_path: Path,
    isolated_home: Path,
) -> None:
    del isolated_home
    store.set(_key_name("anthropic"), "sk-anthropic-key")
    result = _invoke_check(
        CliRunner(),
        minimal_project_path,
        "--provider",
        "anthropic",
        "--no-stream",
    )
    assert result.exit_code == 0, result.stdout
    assert len(fake_backends.instances) == 1
    assert fake_backends.instances[0].api_key == "sk-anthropic-key"
    # --no-stream must route through complete(), not stream().
    assert fake_backends.instances[0].complete_calls
    assert fake_backends.instances[0].stream_calls == []


def test_explicit_mock_provider_silences_warning(
    store: MemoryTokenStore,
    fake_backends: type[FakeBackend],
    minimal_project_path: Path,
    isolated_home: Path,
) -> None:
    del store, fake_backends, isolated_home
    result = _invoke_check(
        CliRunner(),
        minimal_project_path,
        "--provider",
        "mock",
        "--no-stream",
    )
    assert result.exit_code == 0, result.stdout
    # --provider mock is a deliberate choice, not a fallback — the
    # yellow "no credentials configured" banner must not appear.
    assert "falling back to MockBackend" not in result.stdout


def test_auto_detect_with_no_keys_warns_and_uses_mock(
    store: MemoryTokenStore,
    fake_backends: type[FakeBackend],
    minimal_project_path: Path,
    isolated_home: Path,
) -> None:
    del store, fake_backends, isolated_home
    result = _invoke_check(
        CliRunner(),
        minimal_project_path,
        "--no-stream",
    )
    assert result.exit_code == 0, result.stdout
    assert "falling back to MockBackend" in result.stdout


def test_auto_detect_prefers_anthropic_when_both_set(
    store: MemoryTokenStore,
    fake_backends: type[FakeBackend],
    minimal_project_path: Path,
    isolated_home: Path,
) -> None:
    del isolated_home
    store.set(_key_name("anthropic"), "sk-anthropic-key")
    store.set(_key_name("openai"), "sk-openai-key")
    result = _invoke_check(CliRunner(), minimal_project_path, "--no-stream")
    assert result.exit_code == 0, result.stdout
    # Default order: anthropic first (Haiku is the cheaper default).
    assert fake_backends.instances[0].api_key == "sk-anthropic-key"


def test_auto_detect_falls_back_to_openai_when_only_openai_set(
    store: MemoryTokenStore,
    fake_backends: type[FakeBackend],
    minimal_project_path: Path,
    isolated_home: Path,
) -> None:
    del isolated_home
    store.set(_key_name("openai"), "sk-openai-key")
    result = _invoke_check(CliRunner(), minimal_project_path, "--no-stream")
    assert result.exit_code == 0, result.stdout
    assert fake_backends.instances[0].api_key == "sk-openai-key"


def test_invalid_provider_exits_two(
    store: MemoryTokenStore,
    fake_backends: type[FakeBackend],
    minimal_project_path: Path,
    isolated_home: Path,
) -> None:
    del store, fake_backends, isolated_home
    result = _invoke_check(
        CliRunner(),
        minimal_project_path,
        "--provider",
        "groq",
        "--no-stream",
    )
    assert result.exit_code == 2


def test_model_flag_forwarded_to_backend(
    store: MemoryTokenStore,
    fake_backends: type[FakeBackend],
    minimal_project_path: Path,
    isolated_home: Path,
) -> None:
    del isolated_home
    store.set(_key_name("anthropic"), "sk-anthropic-key")
    result = _invoke_check(
        CliRunner(),
        minimal_project_path,
        "--provider",
        "anthropic",
        "--model",
        "claude-opus-4-7",
        "--no-stream",
    )
    assert result.exit_code == 0, result.stdout
    assert fake_backends.instances[0].complete_calls == [{"model": "claude-opus-4-7"}]


def test_stream_flag_routes_to_backend_stream(
    store: MemoryTokenStore,
    fake_backends: type[FakeBackend],
    minimal_project_path: Path,
    isolated_home: Path,
) -> None:
    del isolated_home
    store.set(_key_name("anthropic"), "sk-anthropic-key")
    result = _invoke_check(
        CliRunner(),
        minimal_project_path,
        "--provider",
        "anthropic",
        "--stream",
    )
    assert result.exit_code == 0, result.stdout
    # --stream must route through stream(), not complete().
    assert fake_backends.instances[0].stream_calls
    assert fake_backends.instances[0].complete_calls == []


def test_skip_llm_bypasses_backend_entirely(
    store: MemoryTokenStore,
    fake_backends: type[FakeBackend],
    minimal_project_path: Path,
    isolated_home: Path,
) -> None:
    del store, isolated_home
    # Even with --provider anthropic, --skip-llm wins — we go straight to
    # MockBackend and the real backend constructor is never called.
    result = _invoke_check(
        CliRunner(),
        minimal_project_path,
        "--provider",
        "anthropic",
        "--skip-llm",
    )
    assert result.exit_code == 0, result.stdout
    assert fake_backends.instances == []
