"""Sinks that write telemetry events somewhere durable (or nowhere).

Three concrete sinks cover the three realistic consumers:

* :class:`JsonlFileSink` is the production default — one
  :class:`~swatplus_ai.telemetry.events.Event` per line in an append-only
  ``.jsonl`` file under ``.swatplus-ai/logs/``. The parent dir is created
  on construction so callers don't need to pre-make it; the file handle
  is opened lazily on first write (so merely constructing the sink never
  touches disk) and kept open until :meth:`close` for throughput.
* :class:`InMemorySink` collects :class:`Event` objects in a list. Tests
  use it to assert on emission order and payloads without touching disk.
* :class:`NullSink` drops everything. The :mod:`swatplus_ai.telemetry`
  module installs one automatically after a sink failure, so a broken
  disk / permission error doesn't re-fire on every subsequent emission.

The :class:`Sink` protocol captures the minimum shape — ``write(event)``
plus ``close()``. Protocols (rather than ABCs) keep third-party sinks
(e.g. a future in-CI sink that uploads on green) duck-typed without
forcing a class hierarchy.
"""

from __future__ import annotations

from pathlib import Path
from typing import IO, Protocol, runtime_checkable

from swatplus_ai.telemetry.events import Event


@runtime_checkable
class Sink(Protocol):
    """Minimum interface every telemetry destination must implement."""

    def write(self, event: Event) -> None: ...
    def close(self) -> None: ...


class NullSink:
    """A sink that silently drops every event."""

    def write(self, event: Event) -> None:
        return None

    def close(self) -> None:
        return None


class InMemorySink:
    """A sink that collects events in a list; used by tests."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def write(self, event: Event) -> None:
        self.events.append(event)

    def close(self) -> None:
        return None


class JsonlFileSink:
    """Append-only JSON-Lines file sink."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file: IO[str] | None = None

    @property
    def path(self) -> Path:
        return self._path

    def write(self, event: Event) -> None:
        if self._file is None:
            self._file = self._path.open("a", encoding="utf-8")
        self._file.write(event.model_dump_json())
        self._file.write("\n")
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None


__all__ = ["InMemorySink", "JsonlFileSink", "NullSink", "Sink"]
