"""Parser for ``hydrology.wet`` — wetland hydrology parameters.

One row per named parameter set referenced from ``wetland.wet``'s
``hyd`` column. 10-column flat table: ``name`` + 9 floats covering
principal / emergency spillway fractions and depths, saturated
hydraulic conductivity, evaporation coefficient, volume-area shape
parameters, and the wetland's fractional coverage of its host HRU.
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
)
from swatplus_ai.parser.models import ParsedFile

_FLOAT_FIELDS: tuple[str, ...] = (
    "hru_ps",
    "dp_ps",
    "hru_es",
    "dp_es",
    "k",
    "evap",
    "vol_area_co",
    "vol_dp_a",
    "vol_dp_b",
    "hru_frac",
)
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS)
_EXPECTED_TOKENS = len(_HEADER)


class HydrologyWetRow(BaseModel):
    """Wetland hydrology parameters for one named set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    hru_ps: float
    dp_ps: float
    hru_es: float
    dp_es: float
    k: float
    evap: float
    vol_area_co: float
    vol_dp_a: float
    vol_dp_b: float
    hru_frac: float


class HydrologyWet(ParsedFile):
    """Contents of a ``hydrology.wet`` file."""

    rows: tuple[HydrologyWetRow, ...]

    def by_name(self, name: str) -> HydrologyWetRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_hydrology_wet(path: Path) -> HydrologyWet:
    """Parse a ``hydrology.wet`` file into a :class:`HydrologyWet` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[HydrologyWetRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return HydrologyWet(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> HydrologyWetRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    ln = line.line_no
    name = line.tokens[0]
    float_values = {
        field: parse_float(line.tokens[i + 1], path=path, line_no=ln, field=field)
        for i, field in enumerate(_FLOAT_FIELDS)
    }
    return HydrologyWetRow(name=name, **float_values)
