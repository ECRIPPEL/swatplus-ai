"""Tests for the three bundled sinks."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from swatplus_ai.telemetry.events import Event
from swatplus_ai.telemetry.sinks import InMemorySink, JsonlFileSink, NullSink


def _mk_event(i: int) -> Event:
    return Event(
        event_type="user_action",
        session_id="sess",
        timestamp=datetime(2026, 4, 18, 12, i, 0, tzinfo=UTC),
        swatplus_ai_version="0.0.1",
        fields={"i": i},
    )


def test_jsonl_file_sink_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "session.jsonl"
    sink = JsonlFileSink(path)
    events = [_mk_event(i) for i in range(3)]
    for event in events:
        sink.write(event)
    sink.close()

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    parsed = [Event.model_validate_json(line) for line in lines]
    assert parsed == events


def test_jsonl_file_sink_creates_parent_dir_on_init(tmp_path: Path) -> None:
    path = tmp_path / "fresh" / "logs" / "x.jsonl"
    JsonlFileSink(path)  # should not raise
    assert path.parent.is_dir()
    # No file written yet — construction must be lazy.
    assert not path.exists()


def test_jsonl_file_sink_reuses_handle_then_close_resets(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "s.jsonl"
    sink = JsonlFileSink(path)
    sink.write(_mk_event(0))
    sink.write(_mk_event(1))
    sink.close()
    # Can be safely closed twice.
    sink.close()
    # A fresh sink at the same path appends.
    sink2 = JsonlFileSink(path)
    sink2.write(_mk_event(2))
    sink2.close()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3


def test_in_memory_sink_collects() -> None:
    sink = InMemorySink()
    events = [_mk_event(i) for i in range(5)]
    for e in events:
        sink.write(e)
    assert sink.events == events
    sink.close()


def test_null_sink_drops_events() -> None:
    sink = NullSink()
    sink.write(_mk_event(0))
    sink.close()
