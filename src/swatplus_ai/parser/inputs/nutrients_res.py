"""Parser for ``nutrients.res`` — reservoir nutrient parameters.

One row per named parameter set referenced from ``reservoir.res`` or
``wetland.wet``'s ``nut`` column. 13-column flat table: ``name``,
settling-period start / end month (``mid_start`` / ``mid_end``) as
integers, then 10 floats describing nitrogen / phosphorus settling
rates, chlorophyll and secchi coefficients, temperature corrections,
and minimum settling thresholds.
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
    "mid_n_stl",
    "n_stl",
    "mid_p_stl",
    "p_stl",
    "chla_co",
    "secchi_co",
    "theta_n",
    "theta_p",
    "n_min_stl",
    "p_min_stl",
)
_HEADER: tuple[str, ...] = ("name", "mid_start", "mid_end", *_FLOAT_FIELDS)
_EXPECTED_TOKENS = len(_HEADER)


class NutrientsResRow(BaseModel):
    """Reservoir nutrient parameters for one named set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    mid_start: int
    mid_end: int
    mid_n_stl: float
    n_stl: float
    mid_p_stl: float
    p_stl: float
    chla_co: float
    secchi_co: float
    theta_n: float
    theta_p: float
    n_min_stl: float
    p_min_stl: float


class NutrientsRes(ParsedFile):
    """Contents of a ``nutrients.res`` file."""

    rows: tuple[NutrientsResRow, ...]

    def by_name(self, name: str) -> NutrientsResRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_nutrients_res(path: Path) -> NutrientsRes:
    """Parse a ``nutrients.res`` file into a :class:`NutrientsRes` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[NutrientsResRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return NutrientsRes(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> NutrientsResRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    ln = line.line_no
    name = line.tokens[0]
    mid_start = parse_int(line.tokens[1], path=path, line_no=ln, field="mid_start")
    mid_end = parse_int(line.tokens[2], path=path, line_no=ln, field="mid_end")
    float_values = {
        field: parse_float(line.tokens[i + 3], path=path, line_no=ln, field=field)
        for i, field in enumerate(_FLOAT_FIELDS)
    }
    return NutrientsResRow(name=name, mid_start=mid_start, mid_end=mid_end, **float_values)
