"""Tests for the ``swatplus-ai logs`` sub-app.

The pure helpers live in ``test_logs.py``; this file asserts the
typer surface — exit codes, stdout contents, and the overwrite guard
on ``logs export`` — using the typer :class:`CliRunner`.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from swatplus_ai.telemetry.events import Event
from swatplus_ai.telemetry.logs_cli import app


def _mk_event(minute: int, event_type: str = "user_action", **fields: object) -> Event:
    return Event(
        event_type=event_type,  # type: ignore[arg-type]
        session_id="sess",
        timestamp=datetime(2026, 4, 18, 12, minute, 0, tzinfo=UTC),
        swatplus_ai_version="0.0.1",
        fields={"i": minute, **fields},
    )


def _write_session(path: Path, events: list[Event]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(event.model_dump_json() + "\n")


@pytest.fixture
def project_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run each test inside a throwaway cwd so ``default_logs_dir()`` points there."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run(args: list[str]) -> object:
    return CliRunner().invoke(app, args)


def test_list_empty_directory_prints_hint(project_cwd: Path) -> None:
    # No logs dir at all: command must succeed and tell the user where
    # to look instead of erroring out.
    result = _run(["list"])
    assert result.exit_code == 0
    assert "No session logs" in result.stdout


def test_list_renders_multiple_sessions_newest_first(project_cwd: Path) -> None:
    logs_dir = project_cwd / ".swatplus-ai" / "logs"
    a = logs_dir / "session-aaaaaaaa1111.jsonl"
    b = logs_dir / "session-bbbbbbbb2222.jsonl"
    _write_session(a, [_mk_event(1)])
    _write_session(b, [_mk_event(2), _mk_event(3)])
    os.utime(a, (1_700_000_000, 1_700_000_000))
    os.utime(b, (1_700_000_100, 1_700_000_100))

    result = _run(["list"])
    assert result.exit_code == 0
    # Both 8-char prefixes must appear; the newer one must come first.
    assert "aaaaaaaa" in result.stdout
    assert "bbbbbbbb" in result.stdout
    assert result.stdout.index("bbbbbbbb") < result.stdout.index("aaaaaaaa")


def test_show_default_picks_newest(project_cwd: Path) -> None:
    logs_dir = project_cwd / ".swatplus-ai" / "logs"
    older = logs_dir / "session-oooooooo1111.jsonl"
    newer = logs_dir / "session-nnnnnnnn2222.jsonl"
    _write_session(older, [_mk_event(1, event_type="file_parsed", filename="old.sim")])
    _write_session(
        newer,
        [_mk_event(5, event_type="file_parsed", filename="new.sim", rows=3, duration_ms=7)],
    )
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_700_000_100, 1_700_000_100))

    result = _run(["show"])
    assert result.exit_code == 0
    assert "new.sim" in result.stdout
    # The older session's filename should not appear when we pick newest.
    assert "old.sim" not in result.stdout


def test_show_last_trims_tail(project_cwd: Path) -> None:
    logs_dir = project_cwd / ".swatplus-ai" / "logs"
    path = logs_dir / "session-aaaaaaaa1111.jsonl"
    _write_session(
        path,
        [
            _mk_event(1, event_type="file_parsed", filename="first.sim"),
            _mk_event(2, event_type="file_parsed", filename="middle.sim"),
            _mk_event(3, event_type="file_parsed", filename="last.sim"),
        ],
    )
    result = _run(["show", "--last", "1"])
    assert result.exit_code == 0
    assert "last.sim" in result.stdout
    # The earlier events must be absent when --last=1 trims them off.
    assert "first.sim" not in result.stdout
    assert "middle.sim" not in result.stdout


def test_show_session_prefix_selects_specific(project_cwd: Path) -> None:
    logs_dir = project_cwd / ".swatplus-ai" / "logs"
    a = logs_dir / "session-aaaaaaaa1111.jsonl"
    b = logs_dir / "session-bbbbbbbb2222.jsonl"
    _write_session(a, [_mk_event(1, event_type="file_parsed", filename="alpha.sim")])
    _write_session(b, [_mk_event(2, event_type="file_parsed", filename="beta.sim")])
    # Make `b` newest so the explicit prefix must override default ordering.
    os.utime(a, (1_700_000_000, 1_700_000_000))
    os.utime(b, (1_700_000_100, 1_700_000_100))

    result = _run(["show", "--session", "aaaaaaaa"])
    assert result.exit_code == 0
    assert "alpha.sim" in result.stdout
    assert "beta.sim" not in result.stdout


def test_show_errors_on_ambiguous_session(project_cwd: Path) -> None:
    logs_dir = project_cwd / ".swatplus-ai" / "logs"
    _write_session(logs_dir / "session-abcd1111.jsonl", [_mk_event(1)])
    _write_session(logs_dir / "session-abcd2222.jsonl", [_mk_event(2)])
    result = _run(["show", "--session", "abcd"])
    assert result.exit_code == 1
    assert "ambiguous" in result.stdout


def test_show_errors_on_missing_logs_dir(project_cwd: Path) -> None:
    result = _run(["show"])
    assert result.exit_code == 1
    assert "Session-log directory not found" in result.stdout or "No session logs" in result.stdout


def test_export_copies_bytes_and_reports_count(project_cwd: Path) -> None:
    logs_dir = project_cwd / ".swatplus-ai" / "logs"
    src = logs_dir / "session-aaaaaaaa1111.jsonl"
    events = [_mk_event(1), _mk_event(2)]
    _write_session(src, events)
    output = project_cwd / "exported.jsonl"

    result = _run(["export", "--output", str(output)])
    assert result.exit_code == 0
    assert output.exists()
    # Byte-for-byte copy is the contract; re-reading the output must yield
    # the exact same line bytes as the source.
    assert output.read_bytes() == src.read_bytes()
    assert "exported 2 events" in result.stdout


def test_export_refuses_to_overwrite(project_cwd: Path) -> None:
    logs_dir = project_cwd / ".swatplus-ai" / "logs"
    _write_session(logs_dir / "session-aaaaaaaa1111.jsonl", [_mk_event(1)])
    output = project_cwd / "existing.jsonl"
    output.write_text("pre-existing content", encoding="utf-8")

    result = _run(["export", "--output", str(output)])
    assert result.exit_code == 1
    assert "Refusing to overwrite" in result.stdout
    # Existing file must be left untouched.
    assert output.read_text(encoding="utf-8") == "pre-existing content"


def test_export_with_session_prefix(project_cwd: Path) -> None:
    logs_dir = project_cwd / ".swatplus-ai" / "logs"
    a = logs_dir / "session-aaaaaaaa1111.jsonl"
    b = logs_dir / "session-bbbbbbbb2222.jsonl"
    _write_session(a, [_mk_event(1)])
    _write_session(b, [_mk_event(2), _mk_event(3)])
    os.utime(a, (1_700_000_000, 1_700_000_000))
    os.utime(b, (1_700_000_100, 1_700_000_100))
    output = project_cwd / "out.jsonl"

    result = _run(["export", "--session", "aaaaaaaa", "--output", str(output)])
    assert result.exit_code == 0
    assert output.read_bytes() == a.read_bytes()


def test_no_args_shows_help(project_cwd: Path) -> None:
    result = _run([])
    assert result.exit_code in (0, 2)
    assert "list" in result.stdout
    assert "show" in result.stdout
    assert "export" in result.stdout
