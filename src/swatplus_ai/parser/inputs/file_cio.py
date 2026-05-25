"""Parser for ``file.cio`` — the master file index for a SWAT+ project.

``file.cio`` tells SWAT+ which input files to read, grouped by section
(simulation, basin, climate, connect, ...). Each line looks like::

    section_name   file1   file2   ...   fileN

Unused slots are written as the literal string ``null``. The first line
also carries the SWAT+ engine version and editor version — we extract both
here because later, version-aware parsers will dispatch off
``swatplus_version`` to pick the right variant of each per-file parser.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import LineReader, UnsupportedSwatPlusVersionError, parse_nullable_str
from swatplus_ai.parser.models import ParsedFile

# Example title written by SWAT+ editor:
#   "file.cio: written by SWAT+ editor v3.1.4 on 2026-03-18 10:50 for SWAT+ rev.61.0.2"
_SWATPLUS_REV_RE = re.compile(r"SWAT\+\s*rev\.?\s*(\S+)", re.IGNORECASE)
_EDITOR_RE = re.compile(r"SWAT\+\s*editor\s*v?(\S+)", re.IGNORECASE)
_VERSION_TRIPLE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")

# Supported floor — rev.60.x projects use enough different headers
# (``object.cnt`` ``mfl``, 24-column ``codes.bsn``, ``hydrology.hyd``
# ``harg_pet``) that trying to parse them would crash downstream anyway.
# The gate fails fast with a clear upgrade message.
MIN_SUPPORTED_SWATPLUS_REV: tuple[int, int, int] = (61, 0, 0)


class FileCioSection(BaseModel):
    """One row of ``file.cio``: a section name and its ordered file slots."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    files: tuple[str | None, ...]  # None wherever the literal 'null' appeared


class FileCio(ParsedFile):
    """Parsed ``file.cio`` — the master file index for a SWAT+ project."""

    swatplus_version: str | None
    editor_version: str | None
    sections: tuple[FileCioSection, ...]

    def section(self, name: str) -> FileCioSection | None:
        """Return the section with the given name, or None if absent."""
        for s in self.sections:
            if s.name == name:
                return s
        return None


def parse_swatplus_rev(version: str | None) -> tuple[int, int, int] | None:
    """Extract a ``(major, minor, patch)`` triple from a rev string.

    Returns ``None`` when the input is missing or doesn't start with
    three dot-separated integers — callers should then fail-open rather
    than reject the project, since an exotic or custom-build version
    shouldn't be silently blocked.
    """
    if not version:
        return None
    m = _VERSION_TRIPLE_RE.match(version.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def check_swatplus_version(file_cio: FileCio) -> None:
    """Reject projects written by a SWAT+ version older than the supported floor.

    Raises :class:`UnsupportedSwatPlusVersionError` for rev.60.x and older;
    silent for rev.61+ or when the version is unparseable (fail-open).
    """
    parsed = parse_swatplus_rev(file_cio.swatplus_version)
    if parsed is None:
        return
    if parsed < MIN_SUPPORTED_SWATPLUS_REV:
        raise UnsupportedSwatPlusVersionError(
            f"SWAT+ project version rev.{file_cio.swatplus_version} is not supported. "
            "swatplus-ai requires rev.61+ (SWAT+ Editor v3.0 or newer). "
            "Re-open the project in a newer editor and Save As to upgrade the format."
        )


def parse_file_cio(path: Path) -> FileCio:
    """Parse a ``file.cio`` file into a :class:`FileCio` model."""
    reader = LineReader(path)
    title = reader.next().text

    swat_m = _SWATPLUS_REV_RE.search(title)
    editor_m = _EDITOR_RE.search(title)

    sections: list[FileCioSection] = []
    while not reader.eof():
        line = reader.next()
        name, *files = line.tokens
        sections.append(
            FileCioSection(
                name=name,
                files=tuple(parse_nullable_str(t) for t in files),
            )
        )

    return FileCio(
        source_path=path,
        title=title,
        swatplus_version=swat_m.group(1) if swat_m else None,
        editor_version=editor_m.group(1) if editor_m else None,
        sections=tuple(sections),
    )
