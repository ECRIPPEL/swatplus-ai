"""Integration tests for :func:`swatplus_ai.telemetry.emit`."""

from __future__ import annotations

import warnings

import pytest

import swatplus_ai.telemetry as telemetry
from swatplus_ai.telemetry.events import Event
from swatplus_ai.telemetry.sinks import InMemorySink, NullSink


def test_emit_lands_in_configured_sink(enable_telemetry: None) -> None:
    sink = InMemorySink()
    telemetry.configure(sink)
    telemetry.emit("session_start", reason="cli-boot")
    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "session_start"
    assert event.fields == {"reason": "cli-boot"}
    assert event.session_id  # auto-generated


def test_emit_redacts_fields_before_writing(enable_telemetry: None) -> None:
    sink = InMemorySink()
    telemetry.configure(sink)
    telemetry.emit(
        "file_parsed",
        path="/home/alice/project/TxtInOut/time.sim",
        user_email="bob@example.com",
    )
    fields = sink.events[0].fields
    assert fields["path"] == "time.sim"
    assert fields["user_email"] == "<REDACTED>"


def test_emit_disabled_does_not_touch_sink(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("swatplus_ai.telemetry.config.is_enabled", lambda: False)
    sink = InMemorySink()
    telemetry.configure(sink)
    telemetry.emit("session_start")
    assert sink.events == []


def test_emit_buffers_before_configure_then_flushes(enable_telemetry: None) -> None:
    telemetry.emit("session_start", ordinal=0)
    telemetry.emit("user_action", ordinal=1)
    sink = InMemorySink()
    telemetry.configure(sink)
    # Both buffered events arrive, in order.
    assert [e.fields["ordinal"] for e in sink.events] == [0, 1]


def test_pre_configure_buffer_drops_oldest_when_full(enable_telemetry: None) -> None:
    limit = telemetry._BUFFER_MAXLEN
    for i in range(limit + 5):
        telemetry.emit("user_action", ordinal=i)
    sink = InMemorySink()
    telemetry.configure(sink)
    assert len(sink.events) == limit
    # The 5 oldest entries were dropped; the buffer kept the most recent.
    ordinals = [e.fields["ordinal"] for e in sink.events]
    assert ordinals[0] == 5
    assert ordinals[-1] == limit + 4


def test_sink_failure_is_non_blocking_and_warns_once(enable_telemetry: None) -> None:
    class BadSink:
        def write(self, event: Event) -> None:
            raise OSError("disk full")

        def close(self) -> None:
            return None

    telemetry.configure(BadSink())
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        telemetry.emit("session_start")
        telemetry.emit("user_action")
        telemetry.emit("session_end")

    # Exactly one warning, regardless of how many emits hit the bad sink.
    relevant = [w for w in caught if "Telemetry sink write failed" in str(w.message)]
    assert len(relevant) == 1
    # After the first failure, the default sink switches to NullSink so
    # subsequent emits no-op instead of raising again.
    assert isinstance(telemetry._DEFAULT_SINK, NullSink)


def test_new_session_id_is_unique() -> None:
    ids = {telemetry.new_session_id() for _ in range(10)}
    assert len(ids) == 10


def test_session_id_is_stable_within_a_session(enable_telemetry: None) -> None:
    sink = InMemorySink()
    telemetry.configure(sink)
    telemetry.emit("session_start")
    telemetry.emit("user_action")
    assert sink.events[0].session_id == sink.events[1].session_id
