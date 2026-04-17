"""Parser for ``rout_unit.ele`` — SWAT+ routing-unit element membership.

Expands routing-unit element tokens from ``rout_unit.def`` into one row
per member with its areal fraction and an optional delivery-ratio
reference. Each row is ``id name obj_typ obj_id frac dlr`` where ``dlr``
may be the literal ``null`` or an integer reference into ``del_ratio``
(SWAT+ writes ``0`` when no delivery-ratio applies).
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
    parse_nullable_str,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = ("id", "name", "obj_typ", "obj_id", "frac", "dlr")
_EXPECTED_TOKENS = len(_HEADER)


class RoutUnitEleRow(BaseModel):
    """One routing-unit element-membership entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    obj_typ: str
    obj_id: int
    frac: float
    dlr: int | None


class RoutUnitEle(ParsedFile):
    """Contents of a ``rout_unit.ele`` file."""

    rows: tuple[RoutUnitEleRow, ...]

    def by_name(self, name: str) -> RoutUnitEleRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_rout_unit_ele(path: Path) -> RoutUnitEle:
    """Parse a ``rout_unit.ele`` file into a :class:`RoutUnitEle` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[RoutUnitEleRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return RoutUnitEle(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> RoutUnitEleRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    t = line.tokens
    ln = line.line_no
    dlr_tok = parse_nullable_str(t[5])
    dlr = None if dlr_tok is None else parse_int(dlr_tok, path=path, line_no=ln, field="dlr")
    return RoutUnitEleRow(
        id=parse_int(t[0], path=path, line_no=ln, field="id"),
        name=t[1],
        obj_typ=t[2],
        obj_id=parse_int(t[3], path=path, line_no=ln, field="obj_id"),
        frac=parse_float(t[4], path=path, line_no=ln, field="frac"),
        dlr=dlr,
    )
