"""Parser for ``chandeg.con`` — SWAT+ degrading-channel connectivity table.

One row per degrading channel (``cha###``) with base geographic fields
and trailing connection 4-tuples for each downstream receiver. Channels
are the primary routing objects in a SWAT+ network — each HRU → rout_unit
→ channel. The 8th column ``lcha`` is the 1-based index of the matching
row in ``channel-lte.cha`` / ``hyd-sed-lte.cha``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import LineReader, expect_tokens
from swatplus_ai.parser.inputs._con import con_header, parse_con_row
from swatplus_ai.parser.models import ConConnection, ParsedFile

_HEADER: tuple[str, ...] = con_header("lcha")


class ChandegConRow(BaseModel):
    """One spatial degrading-channel connection entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    gis_id: int
    area: float
    lat: float
    lon: float
    elev: float
    lcha: int
    wst: str
    cst: int
    ovfl: int
    rule: int
    out_tot: int
    connections: tuple[ConConnection, ...]


class ChandegCon(ParsedFile):
    """Contents of a ``chandeg.con`` file."""

    rows: tuple[ChandegConRow, ...]

    def by_name(self, name: str) -> ChandegConRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_chandeg_con(path: Path) -> ChandegCon:
    """Parse a ``chandeg.con`` file into a :class:`ChandegCon` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[ChandegConRow] = []
    while not reader.eof():
        base, connections = parse_con_row(reader.next(), path=path)
        lcha = base.pop("type_col")
        rows.append(ChandegConRow(lcha=lcha, connections=connections, **base))
    return ChandegCon(source_path=path, title=title, rows=tuple(rows))
