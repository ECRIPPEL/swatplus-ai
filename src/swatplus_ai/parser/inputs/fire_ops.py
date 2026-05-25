"""Parser for ``fire.ops`` — SWAT+ fire / burn-operation parameter DB.

One row per fire type (e.g. ``grass``, ``tree_intense``), referenced
from ``burn`` scheduled-ops.

Columns: ``name``, 2 floats (``chg_cn2``, ``frac_burn``), optional
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

_FLOAT_FIELDS: tuple[str, ...] = ("chg_cn2", "frac_burn")
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_FILE = "fire.ops"


class FireOpsRow(BaseModel):
    """Parameters for a single fire operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    chg_cn2: float
    frac_burn: float
    description: str | None


class FireOps(ParsedFile):
    """Contents of a ``fire.ops`` file."""

    rows: tuple[FireOpsRow, ...]

    def by_name(self, name: str) -> FireOpsRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_fire_ops(path: Path) -> FireOps:
    """Parse a ``fire.ops`` file into a :class:`FireOps` model."""
    reader = LineReader(path)
    title = reader.next().text
    header_line = reader.next()
    idx_map, unknowns = expect_header_permissive(header_line, _HEADER, path=path)

    rows: list[FireOpsRow] = []
    first_row: Line | None = None
    while not reader.eof():
        line = reader.next()
        if first_row is None:
            first_row = line
        rows.append(_parse_row(line, idx_map=idx_map, path=path))

    record_unknown_columns(unknowns, first_row, file=_FILE)
    return FireOps(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, idx_map: dict[str, int], path: Path) -> FireOpsRow:
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
    return FireOpsRow(name=name, description=description, **values)
