"""Parser for ``ovn_table.lum`` — SWAT+ overland-flow Manning-n lookup.

One row per cover / residue state (e.g. ``fallow_nores``), referenced
from ``landuse.lum.ovn``. Three floats describe the mean, min and max
overland-flow Manning n values.

Columns: ``name``, 3 floats (``ovn_mean``, ``ovn_min``, ``ovn_max``),
optional trailing ``description``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_tokens,
    parse_float,
)
from swatplus_ai.parser.models import ParsedFile

_FLOAT_FIELDS: tuple[str, ...] = ("ovn_mean", "ovn_min", "ovn_max")
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_MIN_TOKENS = 1 + len(_FLOAT_FIELDS)


class OvnTableLumRow(BaseModel):
    """Parameters for a single overland-flow Manning-n entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    ovn_mean: float
    ovn_min: float
    ovn_max: float
    description: str | None


class OvnTableLum(ParsedFile):
    """Contents of an ``ovn_table.lum`` file."""

    rows: tuple[OvnTableLumRow, ...]

    def by_name(self, name: str) -> OvnTableLumRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_ovn_table_lum(path: Path) -> OvnTableLum:
    """Parse an ``ovn_table.lum`` file into an :class:`OvnTableLum` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[OvnTableLumRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return OvnTableLum(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> OvnTableLumRow:
    if len(line.tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens "
            f"(name + {len(_FLOAT_FIELDS)} floats), got {len(line.tokens)}",
        )
    name, *rest = line.tokens
    float_toks = rest[: len(_FLOAT_FIELDS)]
    desc_toks = rest[len(_FLOAT_FIELDS) :]
    values = {
        field: parse_float(tok, path=path, line_no=line.line_no, field=field)
        for field, tok in zip(_FLOAT_FIELDS, float_toks, strict=True)
    }
    description = " ".join(desc_toks) if desc_toks else None
    return OvnTableLumRow(name=name, description=description, **values)
