"""Parser for ``rout_unit.rtu`` — SWAT+ routing-unit property wiring.

One row per routing unit giving the name of the ``rout_unit.def`` row
that defines its membership plus references to optional ``dlr``
(delivery-ratio), ``topo`` (topography) and ``field`` records. ``dlr``
is commonly ``null``. Each row is ``id name define dlr topo field``.
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
    parse_nullable_str,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = ("id", "name", "define", "dlr", "topo", "field")
_EXPECTED_TOKENS = len(_HEADER)


class RoutUnitRtuRow(BaseModel):
    """One routing-unit property-wiring entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    define: str
    dlr: str | None
    topo: str
    field: str


class RoutUnitRtu(ParsedFile):
    """Contents of a ``rout_unit.rtu`` file."""

    rows: tuple[RoutUnitRtuRow, ...]

    def by_name(self, name: str) -> RoutUnitRtuRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_rout_unit_rtu(path: Path) -> RoutUnitRtu:
    """Parse a ``rout_unit.rtu`` file into a :class:`RoutUnitRtu` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[RoutUnitRtuRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return RoutUnitRtu(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> RoutUnitRtuRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    t = line.tokens
    ln = line.line_no
    return RoutUnitRtuRow(
        id=parse_int(t[0], path=path, line_no=ln, field="id"),
        name=t[1],
        define=t[2],
        dlr=parse_nullable_str(t[3]),
        topo=t[4],
        field=t[5],
    )
