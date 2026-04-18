"""Read-side helpers for SWAT+ai's local session logs.

Slice 4.5.1 put events on disk; slice 4.5.3 gives the user a way to read
them back. These helpers are the pure, typer-free layer underneath
:mod:`swatplus_ai.telemetry.logs_cli` so the CLI stays thin and the
logic is exercised directly from tests without spinning up a
``CliRunner``.

Conventions:

* Logs live under ``<cwd>/.swatplus-ai/logs/session-<uuid>.jsonl`` —
  per-project, not per-user. The session file is the JSONL written by
  :class:`~swatplus_ai.telemetry.sinks.JsonlFileSink`.
* A file whose first event could not be decoded (or a completely empty
  file — a sink that crashed before writing anything) is still surfaced
  by :func:`find_sessions`. Invisible sessions would mask the very
  failure mode telemetry exists to record.
* :func:`load_session` is tolerant of mid-stream corruption: any line
  that fails JSON decoding *or* fails :class:`Event` validation is
  silently dropped, but the rest of the file loads. A disk-full error
  mid-session must not take down the log-reading path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from swatplus_ai.telemetry.events import Event

_LOGS_DIR_NAME = ".swatplus-ai"
_LOGS_SUBDIR = "logs"
_SESSION_GLOB = "session-*.jsonl"
_SESSION_PREFIX = "session-"
_SESSION_SUFFIX = ".jsonl"
_MIN_PREFIX_LEN = 4


@dataclass(frozen=True)
class SessionSummary:
    """Index-entry for one session log file.

    ``started`` is the ``timestamp`` field of the first event in the
    file; ``None`` when the file is empty or its first line is
    unreadable. ``event_count`` is the number of valid events —
    malformed lines don't inflate the count.
    """

    session_id: str
    path: Path
    started: datetime | None
    event_count: int


def default_logs_dir() -> Path:
    """Return the default session-log directory (``<cwd>/.swatplus-ai/logs``)."""
    return Path.cwd() / _LOGS_DIR_NAME / _LOGS_SUBDIR


def session_id_from_path(path: Path) -> str:
    """Extract the uuid portion of a ``session-<uuid>.jsonl`` filename."""
    stem = path.name
    if stem.startswith(_SESSION_PREFIX) and stem.endswith(_SESSION_SUFFIX):
        return stem[len(_SESSION_PREFIX) : -len(_SESSION_SUFFIX)]
    return path.stem


def _summarize(path: Path) -> SessionSummary:
    """Build a :class:`SessionSummary` for one session-log file."""
    events = load_session(path)
    started = events[0].timestamp if events else None
    return SessionSummary(
        session_id=session_id_from_path(path),
        path=path,
        started=started,
        event_count=len(events),
    )


def find_sessions(logs_dir: Path) -> list[SessionSummary]:
    """Return every session log in ``logs_dir``, most-recent first.

    A missing or non-directory ``logs_dir`` is treated as "no sessions" —
    the read-side CLI should be safe to run on a fresh clone.

    Sort key: the file's mtime. Empty files (``started=None``) keep
    their mtime slot rather than being shuffled to the end so a
    sink-crash session still surfaces near its actual time.
    """
    if not logs_dir.is_dir():
        return []
    files = sorted(
        logs_dir.glob(_SESSION_GLOB),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [_summarize(p) for p in files]


def load_session(path: Path) -> list[Event]:
    """Load every valid :class:`Event` line from ``path``.

    Lines that fail JSON decoding or :class:`Event` validation are
    dropped silently. This is the only place in the telemetry surface
    that tolerates malformed input — the write side validates at
    construction time, so any corruption here came from the disk or
    from a different process, and should not propagate.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    events: list[Event] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            events.append(Event.model_validate(raw))
        except ValidationError:
            continue
    return events


def resolve_session(logs_dir: Path, session_hint: str | None) -> Path:
    """Resolve a session hint to a concrete log path.

    ``session_hint=None`` → the most recently modified session file in
    ``logs_dir``. Any other value is treated as a uuid prefix; the match
    must be unique and at least :data:`_MIN_PREFIX_LEN` characters.

    Raises :class:`FileNotFoundError` when the directory or the most-
    recent file is missing, and :class:`ValueError` when a given prefix
    is too short, ambiguous, or unmatched.
    """
    if not logs_dir.is_dir():
        raise FileNotFoundError(
            f"Session-log directory not found: {logs_dir}. "
            "Run a telemetry-enabled command first, or check the directory path."
        )
    sessions = find_sessions(logs_dir)
    if not sessions:
        raise FileNotFoundError(f"No session logs in {logs_dir}.")
    if session_hint is None:
        return sessions[0].path
    if len(session_hint) < _MIN_PREFIX_LEN:
        raise ValueError(
            f"Session prefix {session_hint!r} is too short "
            f"(need at least {_MIN_PREFIX_LEN} characters)."
        )
    matches = [s for s in sessions if s.session_id.startswith(session_hint)]
    if not matches:
        raise ValueError(f"No session matches prefix {session_hint!r}.")
    if len(matches) > 1:
        ids = ", ".join(s.session_id for s in matches)
        raise ValueError(f"Session prefix {session_hint!r} is ambiguous; matches: {ids}.")
    return matches[0].path


__all__ = [
    "SessionSummary",
    "default_logs_dir",
    "find_sessions",
    "load_session",
    "resolve_session",
    "session_id_from_path",
]
