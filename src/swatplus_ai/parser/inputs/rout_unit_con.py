"""Parser for ``rout_unit.con`` — SWAT+ routing-unit connectivity table.

Routing units aggregate HRUs before handing surface / lateral / total
flow to channels and aquifers. Each row lists the base geographic
attributes plus trailing connection 4-tuples; ``out_tot`` on any given
row is typically 2-4 (one per surface / lateral / total / recharge
stream). The 8th column ``rtu`` indexes the matching row in
``rout_unit.def``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import LineReader, expect_tokens
from swatplus_ai.parser.inputs._con import con_header, parse_con_row
from swatplus_ai.parser.models import ConConnection, ParsedFile

_HEADER: tuple[str, ...] = con_header("rtu")


class RoutUnitConRow(BaseModel):
    """One spatial routing-unit connection entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    gis_id: int
    area: float
    lat: float
    lon: float
    elev: float
    rtu: int
    wst: str
    cst: int
    ovfl: int
    rule: int
    out_tot: int
    connections: tuple[ConConnection, ...]


class RoutUnitCon(ParsedFile):
    """Contents of a ``rout_unit.con`` file."""

    rows: tuple[RoutUnitConRow, ...]

    def by_name(self, name: str) -> RoutUnitConRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_rout_unit_con(path: Path) -> RoutUnitCon:
    """Parse a ``rout_unit.con`` file into a :class:`RoutUnitCon` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[RoutUnitConRow] = []
    while not reader.eof():
        base, connections = parse_con_row(reader.next(), path=path)
        rtu = base.pop("type_col")
        rows.append(RoutUnitConRow(rtu=rtu, connections=connections, **base))
    return RoutUnitCon(source_path=path, title=title, rows=tuple(rows))
