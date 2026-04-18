"""Tests for :func:`swatplus_ai.modules.setup_check.run_setup_check`.

Covers the orchestrator contract (shape of the result, offline path,
LLM path with a scripted :class:`MockBackend`) plus one typer-level
smoke test for the ``check`` CLI command — the on-disk session log is
the one side effect the CLI must get right, so we pin it explicitly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from swatplus_ai.cli import app as root_app
from swatplus_ai.llm.backends.mock import MockBackend
from swatplus_ai.modules import SetupCheckResult, run_setup_check
from swatplus_ai.prompts import ProjectSummary


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
