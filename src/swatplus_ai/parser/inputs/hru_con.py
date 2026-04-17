"""Parser for ``hru.con`` — SWAT+ HRU spatial connectivity table.

One row per HRU recording its geographic position (lat/lon/elev), area,
weather-station reference and HRU-definition id. Unlike the other
``*.con`` files, HRUs never declare trailing outflow connections — they
are aggregated into routing units, which in turn connect to channels
and aquifers via ``rout_unit.con``. The header therefore stops at
``out_tot`` with no ``obj_typ`` columns following.
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

_HEADER: tuple[str, ...] = (
    "id",
    "name",
    "gis_id",
    "area",
    "lat",
    "lon",
    "elev",
    "hru",
    "wst",
    "cst",
    "ovfl",
    "rule",
    "out_tot",
)
_EXPECTED_TOKENS = len(_HEADER)


class HruConRow(BaseModel):
    """One spatial HRU connection entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    gis_id: int
    area: float
    lat: float
    lon: float
    elev: float
    hru: int
    wst: str
    cst: int
    ovfl: int
    rule: int
    out_tot: int


class HruCon(ParsedFile):
    """Contents of an ``hru.con`` file."""

    rows: tuple[HruConRow, ...]

    def by_name(self, name: str) -> HruConRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_hru_con(path: Path) -> HruCon:
    """Parse an ``hru.con`` file into a :class:`HruCon` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[HruConRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return HruCon(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> HruConRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    t = line.tokens
    return HruConRow(
        id=parse_int(t[0], path=path, line_no=line.line_no, field="id"),
        name=t[1],
        gis_id=parse_int(t[2], path=path, line_no=line.line_no, field="gis_id"),
        area=parse_float(t[3], path=path, line_no=line.line_no, field="area"),
        lat=parse_float(t[4], path=path, line_no=line.line_no, field="lat"),
        lon=parse_float(t[5], path=path, line_no=line.line_no, field="lon"),
        elev=parse_float(t[6], path=path, line_no=line.line_no, field="elev"),
        hru=parse_int(t[7], path=path, line_no=line.line_no, field="hru"),
        wst=t[8],
        cst=parse_int(t[9], path=path, line_no=line.line_no, field="cst"),
        ovfl=parse_int(t[10], path=path, line_no=line.line_no, field="ovfl"),
        rule=parse_int(t[11], path=path, line_no=line.line_no, field="rule"),
        out_tot=parse_int(t[12], path=path, line_no=line.line_no, field="out_tot"),
    )
