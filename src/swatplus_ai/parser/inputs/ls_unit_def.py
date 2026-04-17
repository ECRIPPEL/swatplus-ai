"""Parser for ``ls_unit.def`` — SWAT+ landscape-unit definitions.

Landscape units group spatial elements (HRUs) that share a landscape
position. Each row is ``id name area elem_tot <elem_tot integer tokens>``
where negative values encode range sentinels (``212 -234`` means
HRU IDs 212..234 inclusive). Unusually among SWAT+ files, line 2 is a
single integer with the total row count — we validate it matches.
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
    parse_int,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = ("id", "name", "area", "elem_tot", "elements")
_MIN_TOKENS = 4


class LsUnitDefRow(BaseModel):
    """One landscape-unit definition with its element membership tokens."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    area: float
    elem_tot: int
    elements: tuple[int, ...]


class LsUnitDef(ParsedFile):
    """Contents of an ``ls_unit.def`` file."""

    row_count: int
    rows: tuple[LsUnitDefRow, ...]

    def by_name(self, name: str) -> LsUnitDefRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_ls_unit_def(path: Path) -> LsUnitDef:
    """Parse an ``ls_unit.def`` file into a :class:`LsUnitDef` model."""
    reader = LineReader(path)
    title = reader.next().text

    count_line = reader.next()
    if len(count_line.tokens) != 1:
        raise ParseError(
            path,
            count_line.line_no,
            f"expected single-token row count, got {len(count_line.tokens)} tokens",
        )
    row_count = parse_int(
        count_line.tokens[0], path=path, line_no=count_line.line_no, field="row_count"
    )

    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[LsUnitDefRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))

    if len(rows) != row_count:
        raise ParseError(
            path,
            count_line.line_no,
            f"declared row count {row_count} does not match parsed rows {len(rows)}",
        )
    return LsUnitDef(source_path=path, title=title, row_count=row_count, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> LsUnitDefRow:
    tokens = line.tokens
    if len(tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens (id name area elem_tot), got {len(tokens)}",
        )
    ln = line.line_no
    row_id = parse_int(tokens[0], path=path, line_no=ln, field="id")
    name = tokens[1]
    area = parse_float(tokens[2], path=path, line_no=ln, field="area")
    elem_tot = parse_int(tokens[3], path=path, line_no=ln, field="elem_tot")
    element_toks = tokens[4:]
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
    return LsUnitDefRow(id=row_id, name=name, area=area, elem_tot=elem_tot, elements=elements)
