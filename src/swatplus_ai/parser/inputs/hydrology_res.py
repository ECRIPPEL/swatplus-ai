"""Parser for ``hydrology.res`` — reservoir hydrology parameters.

One row per named parameter set referenced from ``reservoir.res``'s
``hyd`` column. 10-column flat table: ``name``, operation start year
(``yr_op``) and month (``mon_op``) as integers, followed by 7 floats
describing principal / emergency spillway areas and volumes, hydraulic
conductivity, evaporation coefficient, and two area-volume shape
coefficients.
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

_FLOAT_FIELDS: tuple[str, ...] = (
    "area_ps",
    "vol_ps",
    "area_es",
    "vol_es",
    "k",
    "evap_co",
    "shp_co1",
    "shp_co2",
)
_HEADER: tuple[str, ...] = ("name", "yr_op", "mon_op", *_FLOAT_FIELDS)
_EXPECTED_TOKENS = len(_HEADER)


class HydrologyResRow(BaseModel):
    """Reservoir hydrology parameters for one named set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    yr_op: int
    mon_op: int
    area_ps: float
    vol_ps: float
    area_es: float
    vol_es: float
    k: float
    evap_co: float
    shp_co1: float
    shp_co2: float


class HydrologyRes(ParsedFile):
    """Contents of a ``hydrology.res`` file."""

    rows: tuple[HydrologyResRow, ...]

    def by_name(self, name: str) -> HydrologyResRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_hydrology_res(path: Path) -> HydrologyRes:
    """Parse a ``hydrology.res`` file into a :class:`HydrologyRes` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[HydrologyResRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return HydrologyRes(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> HydrologyResRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    ln = line.line_no
    name = line.tokens[0]
    yr_op = parse_int(line.tokens[1], path=path, line_no=ln, field="yr_op")
    mon_op = parse_int(line.tokens[2], path=path, line_no=ln, field="mon_op")
    float_values = {
        field: parse_float(line.tokens[i + 3], path=path, line_no=ln, field=field)
        for i, field in enumerate(_FLOAT_FIELDS)
    }
    return HydrologyResRow(name=name, yr_op=yr_op, mon_op=mon_op, **float_values)
