"""Pydantic ``Event`` model for SWAT+ai's local telemetry log.

A single event is the smallest thing the telemetry sink writes — one
JSON-Lines row in ``.swatplus-ai/logs/session-<uuid>.jsonl``. The
:class:`Event` model exists to pin the shape at the *sink boundary*:
``fields`` is an open ``dict[str, Any]`` so call sites can hand over
event-specific payload without schema ceremony, but the wrapping frame
(``event_type``, ``session_id``, ``timestamp``, ``swatplus_ai_version``)
is strict and validated. That keeps sessions replayable and greppable
even after the set of event kinds grows over the roadmap.

``event_type`` is a ``Literal`` rather than a free string so construction
fails loud if a caller mistypes a name — the alternative (string field
with runtime validation) would let typos silently land on disk.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

EventType = Literal[
    "session_start",
    "session_end",
    "file_parsed",
    "parse_error",
    "rule_evaluated",
    "finding_emitted",
    "llm_call",
    "llm_tool_call_chosen",
    "user_action",
]


class Event(BaseModel):
    """One structured row in the interaction log."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: EventType
    session_id: str
    timestamp: datetime
    swatplus_ai_version: str
    fields: dict[str, Any]


__all__ = ["Event", "EventType"]
