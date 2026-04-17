"""Parser for ``landuse.lum`` — SWAT+ land-use / land-management definitions.

One row per land-use class (e.g. ``corn_lum``, ``frse_lum``). Each row is a
bundle of named references into supporting tables:

* ``plnt_com``  → plant community in ``plant.ini``
* ``mgt``       → management schedule in ``management.sch``
* ``cn2``       → CN2 lookup in ``cntable.lum``
* ``cons_prac`` → conservation practice in ``cons_practice.lum``
* ``ov_mann``   → overland Manning's n in ``ovn_table.lum``
* ...plus optional urban / tile-drain / septic / VFS / grassed-waterway /
  BMP references.

Every row is keyed by ``name``; ``hru-data.hru`` points at a row here via
its ``lu_mgt`` column. Any unused reference is written as the literal
``null``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_tokens,
    parse_nullable_str,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = (
    "name",
    "cal_group",
    "plnt_com",
    "mgt",
    "cn2",
    "cons_prac",
    "urban",
    "urb_ro",
    "ov_mann",
    "tile",
    "sep",
    "vfs",
    "grww",
    "bmp",
)
_NULLABLE_FIELDS: tuple[str, ...] = _HEADER[1:]


class LanduseLumRow(BaseModel):
    """One row of ``landuse.lum`` — a single land-use definition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    cal_group: str | None
    plnt_com: str | None
    mgt: str | None
    cn2: str | None
    cons_prac: str | None
    urban: str | None
    urb_ro: str | None
    ov_mann: str | None
    tile: str | None
    sep: str | None
    vfs: str | None
    grww: str | None
    bmp: str | None


class LanduseLum(ParsedFile):
    """Contents of ``landuse.lum``: one row per land-use class."""

    rows: tuple[LanduseLumRow, ...]

    def by_name(self, name: str) -> LanduseLumRow | None:
        for r in self.rows:
            if r.name == name:
                return r
        return None


def parse_landuse_lum(path: Path) -> LanduseLum:
    """Parse a ``landuse.lum`` file into a :class:`LanduseLum` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[LanduseLumRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))

    return LanduseLum(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> LanduseLumRow:
    if len(line.tokens) != len(_HEADER):
        raise ParseError(
            path,
            line.line_no,
            f"expected {len(_HEADER)} tokens, got {len(line.tokens)}",
        )
    name = line.tokens[0]
    nullable_values = {
        field: parse_nullable_str(tok)
        for field, tok in zip(_NULLABLE_FIELDS, line.tokens[1:], strict=True)
    }
    return LanduseLumRow(name=name, **nullable_values)
