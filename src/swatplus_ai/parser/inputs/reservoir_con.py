"""Parser for ``reservoir.con`` — SWAT+ reservoir connectivity table.

One row per reservoir object with base geographic fields and trailing
connection 4-tuples. The 8th column ``res`` is the 1-based index of the
matching row in ``reservoir.res``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import LineReader, expect_tokens
from swatplus_ai.parser.inputs._con import con_header, parse_con_row
from swatplus_ai.parser.models import ConConnection, ParsedFile

_HEADER: tuple[str, ...] = con_header("res")


class ReservoirConRow(BaseModel):
    """One spatial reservoir connection entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    gis_id: int
    area: float
    lat: float
    lon: float
    elev: float
    res: int
    wst: str
    cst: int
    ovfl: int
    rule: int
    out_tot: int
    connections: tuple[ConConnection, ...]


class ReservoirCon(ParsedFile):
    """Contents of a ``reservoir.con`` file."""

    rows: tuple[ReservoirConRow, ...]

    def by_name(self, name: str) -> ReservoirConRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_reservoir_con(path: Path) -> ReservoirCon:
    """Parse a ``reservoir.con`` file into a :class:`ReservoirCon` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[ReservoirConRow] = []
    while not reader.eof():
        base, connections = parse_con_row(reader.next(), path=path)
        res = base.pop("type_col")
        rows.append(ReservoirConRow(res=res, connections=connections, **base))
    return ReservoirCon(source_path=path, title=title, rows=tuple(rows))
