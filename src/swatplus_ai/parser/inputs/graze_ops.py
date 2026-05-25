"""Parser for ``graze.ops`` — SWAT+ grazing-operation parameter DB.

One row per grazing method (e.g. ``dairy_high``), referenced from
``graze`` scheduled-ops. The ``fert`` column is an FK into
``fertilizer.frt`` (the manure type deposited during grazing).

Columns: ``name``, ``fert`` (FK → fertilizer.frt), 4 floats
(``bm_eat``, ``bm_tramp``, ``man_amt``, ``grz_bm_min``), optional
trailing ``description``.
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

_FLOAT_FIELDS: tuple[str, ...] = ("bm_eat", "bm_tramp", "man_amt", "grz_bm_min")
_HEADER: tuple[str, ...] = ("name", "fert", *_FLOAT_FIELDS, "description")
_FILE = "graze.ops"


class GrazeOpsRow(BaseModel):
    """Parameters for a single grazing operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    fert: str
    bm_eat: float
    bm_tramp: float
    man_amt: float
    grz_bm_min: float
    description: str | None


class GrazeOps(ParsedFile):
    """Contents of a ``graze.ops`` file."""

    rows: tuple[GrazeOpsRow, ...]

    def by_name(self, name: str) -> GrazeOpsRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_graze_ops(path: Path) -> GrazeOps:
    """Parse a ``graze.ops`` file into a :class:`GrazeOps` model."""
    reader = LineReader(path)
    title = reader.next().text
    header_line = reader.next()
    idx_map, unknowns = expect_header_permissive(header_line, _HEADER, path=path)

    rows: list[GrazeOpsRow] = []
    first_row: Line | None = None
    while not reader.eof():
        line = reader.next()
        if first_row is None:
            first_row = line
        rows.append(_parse_row(line, idx_map=idx_map, path=path))

    record_unknown_columns(unknowns, first_row, file=_FILE)
    return GrazeOps(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, idx_map: dict[str, int], path: Path) -> GrazeOpsRow:
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
    fert = tokens[idx_map["fert"]]
    values = {
        field: parse_float(tokens[idx_map[field]], path=path, line_no=ln, field=field)
        for field in _FLOAT_FIELDS
    }
    desc_toks = tokens[desc_start:]
    description = " ".join(desc_toks) if desc_toks else None
    return GrazeOpsRow(name=name, fert=fert, description=description, **values)
