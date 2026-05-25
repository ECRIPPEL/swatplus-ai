"""Parser for ``tillage.til`` — SWAT+ tillage-implement parameter DB.

One row per tillage implement (e.g. ``fallplow``, ``sprgplow``),
referenced from ``till`` scheduled-ops in ``management.sch``.

Columns: ``name``, 5 floats (``mix_eff``, ``mix_dp``, ``rough``,
``ridge_ht``, ``ridge_sp``), optional trailing ``description``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_header_permissive,
    parse_float,
    record_unknown_columns,
)
from swatplus_ai.parser.models import ParsedFile

_FLOAT_FIELDS: tuple[str, ...] = ("mix_eff", "mix_dp", "rough", "ridge_ht", "ridge_sp")
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_FILE = "tillage.til"


class TillageTilRow(BaseModel):
    """Parameters for a single tillage implement."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    mix_eff: float
    mix_dp: float
    rough: float
    ridge_ht: float
    ridge_sp: float
    description: str | None


class TillageTil(ParsedFile):
    """Contents of a ``tillage.til`` file."""

    rows: tuple[TillageTilRow, ...]

    def by_name(self, name: str) -> TillageTilRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_tillage_til(path: Path) -> TillageTil:
    """Parse a ``tillage.til`` file into a :class:`TillageTil` model."""
    reader = LineReader(path)
    title = reader.next().text
    header_line = reader.next()
    idx_map, unknowns = expect_header_permissive(header_line, _HEADER, path=path)

    rows: list[TillageTilRow] = []
    first_row: Line | None = None
    while not reader.eof():
        line = reader.next()
        if first_row is None:
            first_row = line
        rows.append(_parse_row(line, idx_map=idx_map, path=path))

    record_unknown_columns(unknowns, first_row, file=_FILE)
    return TillageTil(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, idx_map: dict[str, int], path: Path) -> TillageTilRow:
    desc_start = idx_map["description"]
    if len(line.tokens) < desc_start:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {desc_start} tokens before 'description', got {len(line.tokens)}",
        )
    tokens = line.tokens
    ln = line.line_no
    name = tokens[idx_map["name"]]
    values = {
        field: parse_float(tokens[idx_map[field]], path=path, line_no=ln, field=field)
        for field in _FLOAT_FIELDS
    }
    desc_toks = tokens[desc_start:]
    description = " ".join(desc_toks) if desc_toks else None
    return TillageTilRow(name=name, description=description, **values)
