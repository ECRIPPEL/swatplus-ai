"""Tests for :func:`swatplus_ai.modules.setup_check.run_setup_check`.

Covers the orchestrator contract (shape of the result, offline path,
LLM path with a scripted :class:`MockBackend`) plus one typer-level
smoke test for the ``check`` CLI command — the on-disk session log is
the one side effect the CLI must get right, so we pin it explicitly.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from swatplus_ai.cli import app as root_app
from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.llm.backends.mock import MockBackend
from swatplus_ai.llm.interface import LLMResponse, Message
from swatplus_ai.modules import SetupCheckResult, run_setup_check
from swatplus_ai.prompts import ProjectSummary, StaticPassage


class FakeStreamingBackend:
    """In-test stand-in for a streaming LLMBackend.

    Implements ``complete`` + ``stream`` to satisfy the Protocol without
    pulling in a real HTTP transport. Records the ``model`` argument on
    both methods so tests can assert that ``run_setup_check`` forwards
    the kwarg verbatim.
    """

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks
        self.complete_model: str | None = None
        self.stream_model: str | None = None
        self.complete_called = False
        self.stream_called = False

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        del messages, max_tokens, temperature
        self.complete_called = True
        self.complete_model = model
        return LLMResponse(
            text="".join(self._chunks),
            model=model or "fake-model",
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
        self.stream_called = True
        self.stream_model = model
        for chunk in self._chunks:
            yield chunk


async def test_run_setup_check_returns_frozen_result(minimal_project_path: Path) -> None:
    result = await run_setup_check(minimal_project_path, backend=MockBackend(), skip_llm=True)
    assert isinstance(result, SetupCheckResult)
    # Dataclass frozen=True → attribute assignment raises FrozenInstanceError
    # (a subclass of AttributeError).
    with pytest.raises(AttributeError):
        result.project_path = Path("/somewhere-else")  # type: ignore[misc]


async def test_run_setup_check_returns_path_and_summary(
    minimal_project_path: Path,
) -> None:
    result = await run_setup_check(minimal_project_path, backend=MockBackend(), skip_llm=True)
    assert result.project_path == Path(minimal_project_path)
    assert isinstance(result.summary, ProjectSummary)


async def test_run_setup_check_populates_findings(minimal_project_path: Path) -> None:
    result = await run_setup_check(minimal_project_path, backend=MockBackend(), skip_llm=True)
    # The committed fixture is known to produce at least one rule-engine
    # finding at the setup stage. Pin the invariant, not the exact count.
    assert len(result.findings) > 0
    assert all(f.severity in {"error", "warning", "info"} for f in result.findings)


async def test_run_setup_check_skip_llm_leaves_response_none(
    minimal_project_path: Path,
) -> None:
    result = await run_setup_check(minimal_project_path, backend=MockBackend(), skip_llm=True)
    assert result.response is None


async def test_run_setup_check_duration_is_nonnegative(
    minimal_project_path: Path,
) -> None:
    result = await run_setup_check(minimal_project_path, backend=MockBackend(), skip_llm=True)
    assert result.duration_ms >= 0


async def test_run_setup_check_calls_backend_when_not_skipped(
    minimal_project_path: Path,
) -> None:
    backend = MockBackend(replies=["[doc:swatplus_io_spec] confirms the finding."])
    result = await run_setup_check(minimal_project_path, backend=backend, skip_llm=False)
    assert result.response is not None
    assert result.response.text == "[doc:swatplus_io_spec] confirms the finding."


async def test_run_setup_check_parses_known_citations(
    minimal_project_path: Path,
) -> None:
    # Seed the fixture's rule set ships no references on the minimal
    # fixture, so every handle the mock cites is unknown — and that is
    # the contract we're verifying: unknown handles are collected, not
    # hidden.
    backend = MockBackend(replies=["See [doc:fabricated_handle] for detail."])
    result = await run_setup_check(minimal_project_path, backend=backend, skip_llm=False)
    assert result.response is not None
    assert "fabricated_handle" in result.response.unknown_citations


async def test_run_setup_check_bad_path_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(NotADirectoryError):
        await run_setup_check(missing, backend=MockBackend(), skip_llm=True)


async def test_run_setup_check_stream_captures_deltas_in_order(
    minimal_project_path: Path,
) -> None:
    backend = FakeStreamingBackend(chunks=["alpha ", "bravo ", "charlie"])
    captured: list[str] = []
    result = await run_setup_check(
        minimal_project_path,
        backend=backend,
        skip_llm=False,
        stream=True,
        on_delta=captured.append,
    )
    assert backend.stream_called and not backend.complete_called
    assert captured == ["alpha ", "bravo ", "charlie"]
    assert result.response is not None
    assert result.response.text == "alpha bravo charlie"


async def test_run_setup_check_stream_without_on_delta_still_concatenates(
    minimal_project_path: Path,
) -> None:
    backend = FakeStreamingBackend(chunks=["x", "y"])
    result = await run_setup_check(
        minimal_project_path, backend=backend, skip_llm=False, stream=True
    )
    assert result.response is not None
    assert result.response.text == "xy"


async def test_run_setup_check_stream_with_skip_llm_never_calls_on_delta(
    minimal_project_path: Path,
) -> None:
    backend = FakeStreamingBackend(chunks=["x", "y"])
    captured: list[str] = []
    result = await run_setup_check(
        minimal_project_path,
        backend=backend,
        skip_llm=True,
        stream=True,
        on_delta=captured.append,
    )
    # skip_llm trumps stream: no backend call, no callback, no response.
    assert not backend.stream_called
    assert not backend.complete_called
    assert captured == []
    assert result.response is None


async def test_run_setup_check_forwards_model_in_stream_mode(
    minimal_project_path: Path,
) -> None:
    backend = FakeStreamingBackend(chunks=["ok"])
    await run_setup_check(
        minimal_project_path,
        backend=backend,
        skip_llm=False,
        stream=True,
        model="gpt-foo",
    )
    assert backend.stream_model == "gpt-foo"


async def test_run_setup_check_forwards_model_in_complete_mode(
    minimal_project_path: Path,
) -> None:
    backend = FakeStreamingBackend(chunks=["ok"])
    await run_setup_check(
        minimal_project_path,
        backend=backend,
        skip_llm=False,
        stream=False,
        model="claude-foo",
    )
    assert backend.complete_model == "claude-foo"
    assert not backend.stream_called


async def test_run_setup_check_grounded_validates_retrieved_handles(
    minimal_project_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Grounded end-to-end: the retrieval step returns a canonical I/O-spec
    passage, the LLM cites that handle *plus* a fabricated one, and the
    formatter validates the real handle while flagging the fake. This is
    the core contract the slice closes — citations key against retrieval
    instead of an always-empty allowlist.
    """
    retrieved = (
        StaticPassage(
            id="io:time.sim:day-start",
            title="day-start",
            body="Day start field sets the start of the simulation window.",
            source="https://swatplus.gitbook.io/io-docs/llms-full.txt",
        ),
    )

    def _scripted(
        findings: Sequence[Finding],
        **_kwargs: Any,
    ) -> tuple[StaticPassage, ...]:
        del findings
        return retrieved

    monkeypatch.setattr("swatplus_ai.prompts.grounding.retrieve_passages_for_findings", _scripted)
    reply = (
        "See [doc:io:time.sim:day-start] for the simulation window. "
        "Also [doc:io:invented:handle] for unrelated context."
    )
    backend = MockBackend(replies=[reply])
    result = await run_setup_check(
        minimal_project_path, backend=backend, skip_llm=False, stream=False
    )
    assert result.response is not None
    assert result.response.text == reply
    assert "io:time.sim:day-start" not in result.response.unknown_citations
    assert "io:invented:handle" in result.response.unknown_citations


async def test_run_setup_check_falls_back_when_grounded_builder_raises(
    minimal_project_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Any exception from ``build_grounded_module1_prompt`` must not crash
    the ``check`` pipeline — the un-grounded builder takes over, a WARNING
    lands in the session log, and the caller still gets a formatted reply.
    """

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("grounding went sideways")

    monkeypatch.setattr("swatplus_ai.modules.setup_check.build_grounded_module1_prompt", _boom)
    backend = MockBackend(replies=["See [doc:fabricated_handle] for detail."])
    with caplog.at_level("WARNING", logger="swatplus_ai.modules.setup_check"):
        result = await run_setup_check(
            minimal_project_path, backend=backend, skip_llm=False, stream=False
        )
    assert result.response is not None
    assert "fabricated_handle" in result.response.unknown_citations
    assert any("grounded prompt build failed" in rec.message for rec in caplog.records), (
        "expected a WARNING log when grounding raises"
    )


async def test_run_setup_check_skip_llm_does_not_call_retriever(
    minimal_project_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``skip_llm=True`` must bypass grounding entirely. Retrieval is
    seconds of work on first call and the LLM isn't even running, so
    triggering the fetcher+index would be pure waste. Any call into
    retrieval here is the regression this test guards.
    """

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("retrieve_passages_for_findings was called despite skip_llm=True")

    monkeypatch.setattr("swatplus_ai.prompts.grounding.retrieve_passages_for_findings", _boom)
    result = await run_setup_check(minimal_project_path, backend=MockBackend(), skip_llm=True)
    assert result.response is None


def test_check_cli_exit_zero_and_writes_session_log(
    minimal_project_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enable_telemetry: None,
    isolated_home: Path,
) -> None:
    del enable_telemetry, isolated_home
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(root_app, ["check", str(minimal_project_path), "--skip-llm"])
    assert result.exit_code == 0, result.stdout
    logs_dir = tmp_path / ".swatplus-ai" / "logs"
    sessions = sorted(logs_dir.glob("session-*.jsonl"))
    assert len(sessions) == 1
    # The first event must be session_start and the last session_end —
    # log readers rely on those bookends to scope a session slice.
    lines = [
        json.loads(line)
        for line in sessions[0].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert lines, "session log is empty"
    assert lines[0]["event_type"] == "session_start"
    assert lines[-1]["event_type"] == "session_end"
    # session_end must carry the non-failure exit code so read-side tools
    # can distinguish a clean run from a crash.
    assert lines[-1]["fields"]["exit_code"] == 0


def test_check_cli_prints_session_id(
    minimal_project_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enable_telemetry: None,
    isolated_home: Path,
) -> None:
    del enable_telemetry, isolated_home
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(root_app, ["check", str(minimal_project_path), "--skip-llm"])
    assert result.exit_code == 0
    assert "session:" in result.stdout


def test_check_cli_no_log_when_telemetry_disabled(
    minimal_project_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    isolated_home: Path,
) -> None:
    del isolated_home
    # Env-var disable is the cheapest way to prove the NullSink branch
    # fires — the CLI boots without writing the session file at all.
    monkeypatch.setenv("SWATPLUS_AI_NO_LOG", "1")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(root_app, ["check", str(minimal_project_path), "--skip-llm"])
    assert result.exit_code == 0
    logs_dir = tmp_path / ".swatplus-ai" / "logs"
    assert not logs_dir.exists() or not list(logs_dir.glob("session-*.jsonl"))


def test_check_cli_missing_path_exits_nonzero(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    result = CliRunner().invoke(root_app, ["check", str(missing), "--skip-llm"])
    assert result.exit_code != 0
