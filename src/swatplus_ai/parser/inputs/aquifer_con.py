"""Parser for ``aquifer.con`` — SWAT+ aquifer spatial connectivity table.

One row per aquifer object with base geographic fields and trailing
``(obj_typ, obj_id, hyd_typ, frac)`` 4-tuples describing each downstream
receiver. Referenced from ``rout_unit.con`` and feeds the channel
network via those connections.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import LineReader, expect_tokens
from swatplus_ai.parser.inputs._con import con_header, parse_con_row
from swatplus_ai.parser.models import ConConnection, ParsedFile

_HEADER: tuple[str, ...] = con_header("aqu")


class AquiferConRow(BaseModel):
    """One spatial aquifer connection entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    gis_id: int
    area: float
    lat: float
    lon: float
    elev: float
    aqu: int
    wst: str
    cst: int
    ovfl: int
    rule: int
    out_tot: int
    connections: tuple[ConConnection, ...]


class AquiferCon(ParsedFile):
    """Contents of an ``aquifer.con`` file."""

    rows: tuple[AquiferConRow, ...]

    def by_name(self, name: str) -> AquiferConRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_aquifer_con(path: Path) -> AquiferCon:
    """Parse an ``aquifer.con`` file into an :class:`AquiferCon` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[AquiferConRow] = []
    while not reader.eof():
        base, connections = parse_con_row(reader.next(), path=path)
        aqu = base.pop("type_col")
        rows.append(AquiferConRow(aqu=aqu, connections=connections, **base))
    return AquiferCon(source_path=path, title=title, rows=tuple(rows))
