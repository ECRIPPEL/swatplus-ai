"""Aggregatable registry of SWAT+ writer / parser drifts.

A :class:`DriftRecord` is a structured note that some on-disk token
diverged from what one of three canonical authorities expected — the
Fortran core (which defines the true spec), the SWAT+ Editor Python
writer (which sometimes produces off-spec output), or the user (who
may hand-edit a file into an invalid state). Each record carries a
permalink to the upstream source we consulted so the classification
is auditable, not folklore.

Records are collected into a per-session :class:`DriftRegistry` via a
:class:`~contextvars.ContextVar` so parsers can call
:func:`record_drift` without threading a handle through every
signature; when no registry is active the call is a silent no-op, which
keeps unit tests that exercise parsers in isolation unaffected.

The diagnostic engine consumes the registry at rule-check time: a rule
like ``setup.bsn.day_lag_max_as_float`` inspects ``project.drifts`` and
emits a :class:`~swatplus_ai.diagnostics.finding.Finding` whose message
can cite both ``fixed_in_version`` (the Editor release that closed the
writer bug, so users know what version to upgrade to) and
``source_ref`` (the Fortran / changelog evidence backing the claim).
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from types import TracebackType
from typing import Literal

DriftCategory = Literal["spec_compliant", "tool_bug", "user_invalid", "unknown_column"]


@dataclass(frozen=True)
class DriftRecord:
    """One observation that a file token diverged from canonical authority.

    ``category`` is the judgement we reached after consulting upstream
    source: ``spec_compliant`` (writer matches Fortran, our parser was
    too strict), ``tool_bug`` (Editor emitted off-spec output that
    Fortran tolerates but the Editor team later fixed),
    ``user_invalid`` (hand-edit that neither Fortran nor any tool would
    produce), or ``unknown_column`` (extra column observed in header that
    our baseline doesn't know about — provisional marker pending
    source consultation that will promote it to one of the first three).
    Rules decide severity based on the category — ``spec_compliant``
    emits nothing, ``tool_bug`` emits a warning with upgrade guidance,
    ``user_invalid`` emits an error, and ``unknown_column`` is surfaced
    via the CLI drift footer rather than a finding (too noisy pre-triage).

    ``source_ref`` must be a stable URL (commit SHA preferred) so a
    reader can audit the classification months from now without the
    evidence rotting. The literal string ``"<pending>"`` is explicitly
    accepted for ``unknown_column`` records that haven't been triaged
    against upstream yet.
    """

    file: str
    column: str
    observed: str
    expected_by_fortran: str
    category: DriftCategory
    source_ref: str
    fixed_in_version: str | None = None
    writer_tool: str | None = None
    writer_version: str | None = None
    project_swatplus_rev: str | None = None
    upstream_issue: str | None = None


_current: ContextVar[DriftRegistry | None] = ContextVar("swatplus_ai_drift_registry", default=None)


class DriftRegistry:
    """Collects :class:`DriftRecord` entries produced during one parse pass.

    Used as a context manager: entering activates it as the current
    registry for :func:`record_drift` calls on this thread; exiting
    restores the previous registry (or ``None``). Nesting is supported
    but not expected — the top-level :meth:`TxtInOutProject.read` owns
    the single live registry for a project parse.
    """

    def __init__(self) -> None:
        self._records: list[DriftRecord] = []

    def record(self, drift: DriftRecord) -> None:
        self._records.append(drift)

    def all(self) -> tuple[DriftRecord, ...]:
        return tuple(self._records)

    def by_category(self, category: DriftCategory) -> tuple[DriftRecord, ...]:
        return tuple(r for r in self._records if r.category == category)

    def by_file(self, file: str) -> tuple[DriftRecord, ...]:
        return tuple(r for r in self._records if r.file == file)

    def __enter__(self) -> DriftRegistry:
        self._token = _current.set(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        _current.reset(self._token)


def record_drift(drift: DriftRecord) -> None:
    """Record ``drift`` into the current session registry.

    Silent no-op when no registry is active. Parsers call this freely
    without having to know whether they're running inside
    :meth:`TxtInOutProject.read` (registry active) or in an isolated
    unit test that parses one file (no registry) — the no-op branch
    keeps the two paths symmetric.
    """
    reg = _current.get()
    if reg is not None:
        reg.record(drift)


def current_registry() -> DriftRegistry | None:
    """Return the active registry, or ``None`` if no session is in scope."""
    return _current.get()


__all__ = [
    "DriftCategory",
    "DriftRecord",
    "DriftRegistry",
    "current_registry",
    "record_drift",
]
