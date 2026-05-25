"""Module 1 response formatter.

Parses inline ``[doc:<handle>]`` citation markers from a raw LLM
response and validates the handles against the set that was actually
visible to the model at prompt time (finding references + static
passage ids). The output is a frozen :class:`FormattedResponse` —
downstream consumers (the Step 7 CLI renderer, chat mode, tests)
read citations and flagged unknown handles without re-parsing.

Pure library code: no telemetry, no I/O, no Rich / CLI concerns, and
the raw text round-trips byte-for-byte through :attr:`FormattedResponse.text`
so any normalization stays a downstream concern.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Sequence

from pydantic import BaseModel, ConfigDict

from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.prompts.builder import StaticPassage

# Permissive character class — the documented convention is lowercase +
# digits + underscores (``swatplus_io_spec``, ``plunge_2024``), and we
# also tolerate hyphens, dots, and colons: hyphens / dots cover legacy
# bare handles (``swatplus-editor-check``, ``moriasi.2015``); colons
# cover the retrieval-layer handle shape where the source prefix and
# section slug are separated by colons (``io:time.sim:day-start``,
# ``io:parameters.bsn:day-lag-max``). The ``doc:`` prefix is marker
# syntax, not part of the handle, so ``[doc:io:time.sim:day-start]``
# captures ``io:time.sim:day-start`` and matches a ``StaticPassage``
# whose ``id`` was stripped of its ``doc:`` prefix by the grounding
# layer. Single-line by design: ``[doc:foo\nbar]`` across newlines
# never matches, nor do nested brackets.
_CITATION_PATTERN = re.compile(r"\[doc:([A-Za-z0-9_.\-:]+)\]")


class Citation(BaseModel):
    """One inline ``[doc:<handle>]`` marker found in an LLM response.

    The offsets are exact into the raw response text: for every
    ``Citation`` returned by :func:`format_module1_response`,
    ``raw_text[c.start:c.end] == c.marker`` by construction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    handle: str
    start: int
    end: int
    marker: str


class FormattedResponse(BaseModel):
    """Parsed Module 1 response with citation validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    citations: tuple[Citation, ...]
    unknown_citations: tuple[str, ...]

    @property
    def has_unknown_citations(self) -> bool:
        """True when at least one cited handle was outside the allowlist."""
        return len(self.unknown_citations) > 0


def collect_handles(
    findings: Sequence[Finding],
    static_passages: Sequence[StaticPassage] | None = None,
) -> frozenset[str]:
    """Union of every reference handle visible to the LLM at prompt time.

    Pulls from :attr:`Finding.references` across all findings, plus
    :attr:`StaticPassage.id` across all passages. ``static_passages=None``
    and ``static_passages=[]`` behave identically — neither contributes
    any handle.
    """
    handles: set[str] = set()
    for f in findings:
        handles.update(f.references)
    if static_passages:
        for p in static_passages:
            handles.add(p.id)
    return frozenset(handles)


def format_module1_response(
    raw_text: str,
    known_handles: Collection[str],
) -> FormattedResponse:
    """Parse ``[doc:<id>]`` citations; flag handles outside ``known_handles``.

    The returned ``citations`` tuple preserves document order and keeps
    every match (no dedup) — the CLI renderer needs positions to style
    each occurrence. The ``unknown_citations`` tuple is deduped in order
    of first appearance: the caller wants a short actionable list, not
    N copies of the same typo. Matching is case-sensitive against
    ``known_handles``; the future retrieval layer will key on the exact
    handle the LLM wrote.
    """
    known = frozenset(known_handles)
    citations: list[Citation] = []
    unknown_order: list[str] = []
    unknown_seen: set[str] = set()
    for m in _CITATION_PATTERN.finditer(raw_text):
        handle = m.group(1)
        citations.append(
            Citation(
                handle=handle,
                start=m.start(),
                end=m.end(),
                marker=m.group(0),
            )
        )
        if handle not in known and handle not in unknown_seen:
            unknown_seen.add(handle)
            unknown_order.append(handle)
    return FormattedResponse(
        text=raw_text,
        citations=tuple(citations),
        unknown_citations=tuple(unknown_order),
    )


__all__ = [
    "Citation",
    "FormattedResponse",
    "collect_handles",
    "format_module1_response",
]
