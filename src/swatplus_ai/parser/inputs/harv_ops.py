"""Parser for ``harv.ops`` — SWAT+ harvest-operation parameter DB.

One row per harvest method (e.g. ``forest_cut``, ``grain``), referenced
from ``harvest`` / ``harv_kill`` scheduled-ops in ``management.sch``.

Columns: ``name``, ``harv_typ`` (string: ``tree``, ``grain``, ``biomass``,
…), 3 floats (``harv_idx``, ``harv_eff``, ``harv_bm_min``), optional
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

_FLOAT_FIELDS: tuple[str, ...] = ("harv_idx", "harv_eff", "harv_bm_min")
_HEADER: tuple[str, ...] = ("name", "harv_typ", *_FLOAT_FIELDS, "description")
_FILE = "harv.ops"


class HarvOpsRow(BaseModel):
    """Parameters for a single harvest operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    harv_typ: str
    harv_idx: float
    harv_eff: float
    harv_bm_min: float
    description: str | None


class HarvOps(ParsedFile):
    """Contents of a ``harv.ops`` file."""

    rows: tuple[HarvOpsRow, ...]

    def by_name(self, name: str) -> HarvOpsRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_harv_ops(path: Path) -> HarvOps:
    """Parse a ``harv.ops`` file into a :class:`HarvOps` model."""
    reader = LineReader(path)
    title = reader.next().text
    header_line = reader.next()
    idx_map, unknowns = expect_header_permissive(header_line, _HEADER, path=path)

    rows: list[HarvOpsRow] = []
    first_row: Line | None = None
    while not reader.eof():
        line = reader.next()
        if first_row is None:
            first_row = line
        rows.append(_parse_row(line, idx_map=idx_map, path=path))

    record_unknown_columns(unknowns, first_row, file=_FILE)
    return HarvOps(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, idx_map: dict[str, int], path: Path) -> HarvOpsRow:
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
    harv_typ = tokens[idx_map["harv_typ"]]
    values = {
        field: parse_float(tokens[idx_map[field]], path=path, line_no=ln, field=field)
        for field in _FLOAT_FIELDS
    }
    desc_toks = tokens[desc_start:]
    description = " ".join(desc_toks) if desc_toks else None
    return HarvOpsRow(name=name, harv_typ=harv_typ, description=description, **values)
