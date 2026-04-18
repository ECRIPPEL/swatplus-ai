"""Tests for the pure helpers in :mod:`swatplus_ai.telemetry.logs`.

The helpers are exercised directly (no ``CliRunner``) so failure messages
point at ``resolve_session`` / ``find_sessions`` / ``load_session`` rather
than at typer plumbing.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from swatplus_ai.telemetry.events import Event
from swatplus_ai.telemetry.logs import (
    default_logs_dir,
    find_sessions,
    load_session,
    resolve_session,
    session_id_from_path,
)


def _mk_event(minute: int, event_type: str = "user_action") -> Event:
    return Event(
        event_type=event_type,  # type: ignore[arg-type]
        session_id="sess",
        timestamp=datetime(2026, 4, 18, 12, minute, 0, tzinfo=UTC),
        swatplus_ai_version="0.0.1",
        fields={"i": minute},
    )


def _write_session(path: Path, events: list[Event]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(event.model_dump_json() + "\n")


def test_default_logs_dir_is_project_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert default_logs_dir() == tmp_path / ".swatplus-ai" / "logs"


def test_session_id_from_path_strips_prefix_and_suffix(tmp_path: Path) -> None:
    assert session_id_from_path(tmp_path / "session-abc123.jsonl") == "abc123"
    # Fallback: a non-conforming filename falls through to .stem.
    assert session_id_from_path(tmp_path / "weird.log") == "weird"


def test_find_sessions_missing_dir_returns_empty(tmp_path: Path) -> None:
    # Missing directory must not raise — the read-side CLI has to be
    # safe to run on a fresh clone.
    assert find_sessions(tmp_path / "nope") == []


def test_find_sessions_empty_dir_returns_empty(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    assert find_sessions(logs_dir) == []


def test_find_sessions_sorts_by_mtime_desc(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    a = logs_dir / "session-aaaaaaaa.jsonl"
    b = logs_dir / "session-bbbbbbbb.jsonl"
    c = logs_dir / "session-cccccccc.jsonl"
    _write_session(a, [_mk_event(1)])
    _write_session(b, [_mk_event(2), _mk_event(3)])
    _write_session(c, [_mk_event(4)])
    # Stagger mtimes so ordering is deterministic on all filesystems.
    import os

    os.utime(a, (1_700_000_000, 1_700_000_000))
    os.utime(b, (1_700_000_100, 1_700_000_100))
    os.utime(c, (1_700_000_200, 1_700_000_200))

    summaries = find_sessions(logs_dir)
    assert [s.session_id for s in summaries] == ["cccccccc", "bbbbbbbb", "aaaaaaaa"]
    assert [s.event_count for s in summaries] == [1, 2, 1]
    # The summary's ``started`` is the first event's timestamp.
    assert summaries[1].started == datetime(2026, 4, 18, 12, 2, 0, tzinfo=UTC)


def test_find_sessions_surfaces_empty_file(tmp_path: Path) -> None:
    # A sink that crashed before its first write leaves an empty file
    # behind. Hiding it would mask the very failure telemetry exists
    # to record, so the summary must still appear (event_count=0).
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    path = logs_dir / "session-aaaaaaaa.jsonl"
    path.write_text("", encoding="utf-8")
    summaries = find_sessions(logs_dir)
    assert len(summaries) == 1
    assert summaries[0].event_count == 0
    assert summaries[0].started is None


def test_load_session_skips_malformed_lines(tmp_path: Path) -> None:
    # Mixed stream: blank lines, JSON-but-wrong-shape, and valid events.
    path = tmp_path / "session-aaaaaaaa.jsonl"
    good = _mk_event(1)
    path.write_text(
        "\n".join(
            [
                good.model_dump_json(),
                "",  # blank
                "not json at all",
                json.dumps({"event_type": "file_parsed"}),  # validation fails
                good.model_dump_json(),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    events = load_session(path)
    assert len(events) == 2
    assert events[0] == good


def test_load_session_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_session(tmp_path / "nope.jsonl") == []


def test_resolve_session_none_picks_newest(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    a = logs_dir / "session-aaaaaaaa.jsonl"
    b = logs_dir / "session-bbbbbbbb.jsonl"
    _write_session(a, [_mk_event(1)])
    _write_session(b, [_mk_event(2)])
    import os

    os.utime(a, (1_700_000_000, 1_700_000_000))
    os.utime(b, (1_700_000_100, 1_700_000_100))
    assert resolve_session(logs_dir, None) == b


def test_resolve_session_prefix_matches_unique(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    a = logs_dir / "session-abcdef01.jsonl"
    b = logs_dir / "session-12345678.jsonl"
    _write_session(a, [_mk_event(1)])
    _write_session(b, [_mk_event(2)])
    assert resolve_session(logs_dir, "abcd") == a
    assert resolve_session(logs_dir, "1234") == b


def test_resolve_session_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_session(tmp_path / "nope", None)


def test_resolve_session_empty_dir_raises(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        resolve_session(logs_dir, None)


def test_resolve_session_too_short_prefix_raises(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _write_session(logs_dir / "session-abcdef01.jsonl", [_mk_event(1)])
    with pytest.raises(ValueError, match="too short"):
        resolve_session(logs_dir, "abc")


def test_resolve_session_ambiguous_prefix_raises(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _write_session(logs_dir / "session-abcdef01.jsonl", [_mk_event(1)])
    _write_session(logs_dir / "session-abcd9999.jsonl", [_mk_event(2)])
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_session(logs_dir, "abcd")


def test_resolve_session_unmatched_prefix_raises(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _write_session(logs_dir / "session-abcdef01.jsonl", [_mk_event(1)])
    with pytest.raises(ValueError, match="No session matches"):
        resolve_session(logs_dir, "zzzz")
