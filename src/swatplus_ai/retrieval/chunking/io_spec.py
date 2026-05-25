"""Chunk the SWAT+ I/O spec ``llms-full.txt`` dump into retrievable units.

The gitbook publishes every doc page flat-concatenated under a single
``#``-per-page rule: a *file* page (e.g. ``# time.sim``) and each of its
*field* pages (e.g. ``# day_start``, ``# yrc_start``) are siblings, not
parent/child, in the markdown hierarchy. That means we can't recover
the file-to-field association from header levels alone; instead we
track a running "last-seen file" context and attribute subsequent
non-file pages to it. The result is a deterministic mapping from each
``#`` section to a stable handle of the form
``doc:io:<swatplus-file>:<section-slug>`` (or
``doc:io:_general:<section-slug>`` for sections like
``# Introduction to SWAT+`` that precede any file page).

Large sections (>~1000 tokens ≈ 4000 characters) are sub-split on the
shallowest sub-header level they contain (``##`` preferred, falling
back to ``###``/``####``). Sub-chunks append a second slug to the
handle: ``doc:io:<file>:<section-slug>:<sub-slug>``. Sections with no
sub-headers are kept whole regardless of size — splitting on paragraph
boundaries would be non-deterministic and would break the reproducible
handle guarantee that Module 1's citation validator depends on.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from swatplus_ai.retrieval.sources.io_docs import IO_DOCS_URL
from swatplus_ai.retrieval.types import Chunk

MAX_CHUNK_CHARS: Final = 4000
"""Approximate per-chunk ceiling before sub-splitting kicks in.

4000 chars ≈ 1000 tokens with typical English prose, which is the
retrieval sweet spot: big enough to carry a self-contained field
description with its table/hints, small enough that the prompt can
afford to include three or four of them without starving the system
prompt or the findings block.
"""

_GENERAL_FILE_MARKER: Final = "_general"
"""Sentinel ``<file>`` segment for sections that precede any file page.

Keeps the handle shape uniform (``doc:io:<file>:<slug>``) without
requiring a wider grammar.
"""

# SWAT+ file extensions observed across the IO docs + the parsers/inputs
# tree. Kept as an explicit tuple instead of a regex character class so
# pyupgrade/readers can see the inventory at a glance and so adding a
# new extension is a one-line diff, not a regex edit.
_SWATPLUS_FILE_EXTENSIONS: Final = (
    "sim", "prt", "cio", "bsn", "hyd", "hru", "lum", "ini", "sol", "cli",
    "sch", "frt", "til", "pes", "ops", "con", "def", "ele", "rtu", "aqu",
    "cha", "res", "wet", "cal", "sft", "dtl", "cnt", "str", "plt", "urb",
    "sep", "sno", "exc", "rec", "del", "lin", "hrd", "wro", "mtl", "slt",
    "pth", "fld", "rtp",
)  # fmt: skip

_EXT_ALTERNATION = "|".join(_SWATPLUS_FILE_EXTENSIONS)
_SWATPLUS_FILE_RE: Final = re.compile(
    rf"\b([a-z][a-z0-9_-]*\.(?:{_EXT_ALTERNATION}))\b",
    re.IGNORECASE,
)

_HEADER_RE: Final = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def chunk_io_docs(path: Path, *, source_ref: str = IO_DOCS_URL) -> tuple[Chunk, ...]:
    """Parse the I/O docs dump at ``path`` into a tuple of :class:`Chunk`.

    The operation is pure and deterministic: same bytes in → same
    chunks out, same handles, same order. Callers (the BM25 index
    builder, tests) rely on that property — changing the chunker is a
    contract change, not a refactor.
    """
    text = path.read_text(encoding="utf-8")
    top_sections = _split_on_level(text, level=1)

    current_file: str = _GENERAL_FILE_MARKER
    chunks: list[Chunk] = []
    for title, body in top_sections:
        detected = _detect_swatplus_file(title)
        if detected is not None:
            current_file = detected
        section_slug = _slugify(title)

        if len(body) <= MAX_CHUNK_CHARS:
            chunks.append(
                _build_chunk(
                    file_segment=current_file,
                    section_slug=section_slug,
                    title=title,
                    body=body,
                    source_ref=source_ref,
                )
            )
            continue

        sub_level = _shallowest_sub_level(body)
        if sub_level is None:
            chunks.append(
                _build_chunk(
                    file_segment=current_file,
                    section_slug=section_slug,
                    title=title,
                    body=body,
                    source_ref=source_ref,
                )
            )
            continue

        for sub_title, sub_body in _split_on_level(body, level=sub_level):
            sub_slug = _slugify(sub_title)
            chunks.append(
                _build_sub_chunk(
                    file_segment=current_file,
                    section_slug=section_slug,
                    sub_slug=sub_slug,
                    parent_title=title,
                    sub_title=sub_title,
                    body=sub_body,
                    source_ref=source_ref,
                )
            )

    return tuple(chunks)


def _build_chunk(
    *,
    file_segment: str,
    section_slug: str,
    title: str,
    body: str,
    source_ref: str,
) -> Chunk:
    return Chunk(
        handle=f"doc:io:{file_segment}:{section_slug}",
        text=f"# {title}\n\n{body}".strip(),
        metadata={
            "file": file_segment,
            "section": title,
            "source_ref": source_ref,
        },
    )


def _build_sub_chunk(
    *,
    file_segment: str,
    section_slug: str,
    sub_slug: str,
    parent_title: str,
    sub_title: str,
    body: str,
    source_ref: str,
) -> Chunk:
    return Chunk(
        handle=f"doc:io:{file_segment}:{section_slug}:{sub_slug}",
        text=f"# {parent_title}\n\n## {sub_title}\n\n{body}".strip(),
        metadata={
            "file": file_segment,
            "section": parent_title,
            "subsection": sub_title,
            "source_ref": source_ref,
        },
    )


def _detect_swatplus_file(title: str) -> str | None:
    """Return the SWAT+ filename embedded in ``title``, or ``None``.

    Handles both the bare-filename form (``# time.sim``) and the
    parenthesised form that ``Master File (file.cio)`` uses. The first
    match in reading order wins, which matches how a human reads the
    header.
    """
    cleaned = _strip_markdown_escapes(title)
    match = _SWATPLUS_FILE_RE.search(cleaned)
    return match.group(1).lower() if match else None


def _slugify(text: str) -> str:
    """Lowercase, strip markdown escapes, keep ``[a-z0-9]+``, join with dashes.

    Deliberately deterministic and Unicode-agnostic: every character
    outside ``[a-z0-9]`` becomes a separator, including the dots in
    filenames. That collapses ``Master File (file.cio)`` to
    ``master-file-file-cio``, which is what we want for the *slug*
    portion of a handle. The ``<file>`` portion of the handle preserves
    the raw filename (with dot) via :func:`_detect_swatplus_file`.
    """
    cleaned = _strip_markdown_escapes(text).lower()
    parts = re.findall(r"[a-z0-9]+", cleaned)
    return "-".join(parts) if parts else "untitled"


def _strip_markdown_escapes(text: str) -> str:
    # Gitbook escapes underscores in headers as ``day\_start``; strip the
    # backslash so the filename detector and slugifier see the plain
    # identifier. Also collapse the HTML entity ``&#x20;`` that gitbook
    # sprinkles at line ends — keeps it out of titles.
    return text.replace("\\_", "_").replace("&#x20;", " ")


def _split_on_level(text: str, *, level: int) -> list[tuple[str, str]]:
    """Split ``text`` on markdown headers of exactly ``level``.

    Returns ``(title, body)`` pairs where ``body`` spans from the end of
    the header line to the next same-level header (or end of text). Any
    prefix before the first matching header is dropped — the retrieval
    contract is "chunk = section", so an orphan preface has nowhere to
    live.
    """
    pattern = re.compile(rf"^({'#' * level})\s+(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    sections: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        title = match.group(2)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip("\n").strip()
        sections.append((title, body))
    return sections


def _shallowest_sub_level(body: str) -> int | None:
    levels = {len(m.group(1)) for m in _iter_headers(body) if len(m.group(1)) > 1}
    return min(levels) if levels else None


def _iter_headers(text: str) -> Iterator[re.Match[str]]:
    return _HEADER_RE.finditer(text)
