"""Tests for the ``Event`` pydantic model."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from swatplus_ai.telemetry.events import Event


def _base_kwargs() -> dict[str, object]:
    return {
        "event_type": "session_start",
        "session_id": "abc123",
        "timestamp": datetime(2026, 4, 18, 12, 0, 0, tzinfo=UTC),
        "swatplus_ai_version": "0.0.1",
        "fields": {"hello": "world"},
    }


def test_event_round_trips_through_json() -> None:
    event = Event(**_base_kwargs())  # type: ignore[arg-type]
    restored = Event.model_validate_json(event.model_dump_json())
    assert restored == event


def test_unknown_event_type_rejected() -> None:
    kwargs = _base_kwargs() | {"event_type": "definitely_not_a_real_event"}
    with pytest.raises(ValidationError):
        Event(**kwargs)  # type: ignore[arg-type]


def test_extra_top_level_fields_rejected() -> None:
    kwargs = _base_kwargs() | {"unexpected_key": 1}
    with pytest.raises(ValidationError):
        Event(**kwargs)  # type: ignore[arg-type]


def test_event_is_frozen() -> None:
    event = Event(**_base_kwargs())  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        event.session_id = "something_else"  # type: ignore[misc]


def test_fields_accepts_nested_payload() -> None:
    kwargs = _base_kwargs() | {
        "fields": {"nested": {"list": [1, 2, 3], "flag": True, "maybe": None}}
    }
    event = Event(**kwargs)  # type: ignore[arg-type]
    assert event.fields["nested"]["list"] == [1, 2, 3]
