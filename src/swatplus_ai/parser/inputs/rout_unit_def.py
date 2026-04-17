"""Parser for ``rout_unit.def`` — SWAT+ routing-unit definitions.

Each routing unit aggregates a set of HRUs. Rows are
``id name elem_tot <elem_tot integer tokens>`` where negative values
encode range sentinels (``212 -234`` means HRU IDs 212..234 inclusive).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_tokens,
    parse_int,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = ("id", "name", "elem_tot", "elements")
_MIN_TOKENS = 3


class RoutUnitDefRow(BaseModel):
    """One routing-unit definition with its element membership tokens."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    elem_tot: int
    elements: tuple[int, ...]


class RoutUnitDef(ParsedFile):
    """Contents of a ``rout_unit.def`` file."""

    rows: tuple[RoutUnitDefRow, ...]

    def by_name(self, name: str) -> RoutUnitDefRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_rout_unit_def(path: Path) -> RoutUnitDef:
    """Parse a ``rout_unit.def`` file into a :class:`RoutUnitDef` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[RoutUnitDefRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return RoutUnitDef(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> RoutUnitDefRow:
    tokens = line.tokens
    if len(tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens (id name elem_tot), got {len(tokens)}",
        )
    ln = line.line_no
    row_id = parse_int(tokens[0], path=path, line_no=ln, field="id")
    name = tokens[1]
    elem_tot = parse_int(tokens[2], path=path, line_no=ln, field="elem_tot")
    element_toks = tokens[3:]
    if len(element_toks) != elem_tot:
        raise ParseError(
            path,
            ln,
            f"expected {elem_tot} element tokens (elem_tot), got {len(element_toks)}",
        )
    elements = tuple(
        parse_int(tok, path=path, line_no=ln, field=f"element[{i}]")
        for i, tok in enumerate(element_toks)
    )
    return RoutUnitDefRow(id=row_id, name=name, elem_tot=elem_tot, elements=elements)
