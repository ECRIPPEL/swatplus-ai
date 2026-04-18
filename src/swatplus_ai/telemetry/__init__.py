"""Passive, local-only structured logging for SWAT+ai.

The telemetry module is the software's eyes on its own behavior. Parsers
and the diagnostic engine call :func:`emit` at boundary points (file
parsed, rule fired, LLM call made, CLI command invoked) and the current
:class:`~swatplus_ai.telemetry.sinks.Sink` persists the resulting
:class:`~swatplus_ai.telemetry.events.Event` — by default into a
``.swatplus-ai/logs/session-<uuid>.jsonl`` file next to the user's
project.

Four design rules govern this surface, all load-bearing:

1. **Local-only.** No network sink exists, not even a disabled one. The
   roadmap closes that door deliberately — future aggregate sharing is a
   separate, opt-in feature.
2. **No runtime feedback loop.** Nothing in the rest of the codebase
   reads past log files. The log informs humans between releases, not
   the running process.
3. **Redact at write time.** ``fields`` passes through
   :func:`~swatplus_ai.telemetry.redact.redact` before the
   :class:`Event` is built, so sharing a session log is safe by default.
4. **Non-blocking.** A sink failure must never propagate into parsing /
   diagnostics. :func:`emit` swallows the first exception, warns once on
   stderr, and silently no-ops the rest of the session.

This module holds process-wide state (the default sink, the session id,
the pre-``configure()`` ring buffer, and the one-shot failure flag). The
state lives at module scope because emission has to be a one-liner at
call sites; a class-based logger would put a wrapper in every instrument
site for no gain.
"""

from __future__ import annotations

import uuid
import warnings
from collections import deque
from datetime import UTC, datetime
from typing import Any

from swatplus_ai import __version__
from swatplus_ai.telemetry import config as _config
from swatplus_ai.telemetry.config import ENV_DISABLE, is_enabled, set_enabled
from swatplus_ai.telemetry.events import Event, EventType
from swatplus_ai.telemetry.redact import REDACTED_MARKER, redact
from swatplus_ai.telemetry.sinks import InMemorySink, JsonlFileSink, NullSink, Sink

_BUFFER_MAXLEN = 50

_DEFAULT_SINK: Sink | None = None
_SESSION_ID: str | None = None
_BUFFER: deque[Event] = deque(maxlen=_BUFFER_MAXLEN)
_SINK_FAILURE_WARNED: bool = False


def new_session_id() -> str:
    """Return a fresh uuid4 hex string suitable for an ``Event.session_id``."""
    return uuid.uuid4().hex


def _session_id() -> str:
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = new_session_id()
    return _SESSION_ID


def configure(sink: Sink) -> None:
    """Install ``sink`` as the process-wide telemetry destination.

    Events emitted before the first :func:`configure` call are held in a
    bounded in-memory ring buffer (at most :data:`_BUFFER_MAXLEN` events)
    and flushed to the new sink here. That covers the narrow window
    between "CLI boots" and "wiring is complete" without losing early
    ``session_start`` events.
    """
    global _DEFAULT_SINK
    _DEFAULT_SINK = sink
    while _BUFFER:
        _write_event(_BUFFER.popleft())


def _write_event(event: Event) -> None:
    """Forward ``event`` to the current sink, swallowing any failure."""
    global _DEFAULT_SINK, _SINK_FAILURE_WARNED
    sink = _DEFAULT_SINK
    if sink is None:
        return
    try:
        sink.write(event)
    except Exception as exc:
        # Intentionally broad: telemetry must never propagate into hot
        # paths regardless of the sink's failure mode (disk full,
        # permission denied, broken stream, serialization bug).
        if not _SINK_FAILURE_WARNED:
            _SINK_FAILURE_WARNED = True
            warnings.warn(
                f"Telemetry sink write failed; switching to no-op for this session: {exc}",
                stacklevel=2,
            )
        _DEFAULT_SINK = NullSink()


def emit(event_type: EventType, **fields: Any) -> None:
    """Record one telemetry event, if telemetry is enabled.

    When telemetry is disabled via config or env var, no :class:`Event`
    is constructed — the call is effectively free.
    """
    if not _config.is_enabled():
        return
    redacted_fields = redact(dict(fields))
    event = Event(
        event_type=event_type,
        session_id=_session_id(),
        timestamp=datetime.now(tz=UTC),
        swatplus_ai_version=__version__,
        fields=redacted_fields,
    )
    if _DEFAULT_SINK is None:
        _BUFFER.append(event)
        return
    _write_event(event)


__all__ = [
    "ENV_DISABLE",
    "REDACTED_MARKER",
    "Event",
    "EventType",
    "InMemorySink",
    "JsonlFileSink",
    "NullSink",
    "Sink",
    "configure",
    "emit",
    "is_enabled",
    "new_session_id",
    "redact",
    "set_enabled",
]
