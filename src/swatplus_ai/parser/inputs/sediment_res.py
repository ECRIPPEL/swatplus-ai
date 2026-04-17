"""Parser for ``sediment.res`` — reservoir sediment parameters.

One row per named parameter set referenced from ``reservoir.res`` or
``wetland.wet``'s ``sed`` column. 7-column flat table: ``name`` + 6
floats describing sediment amount, median particle diameter, carbon
fraction, bulk density, and settling parameters.
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
    "sed_amt",
    "d50",
    "carbon",
    "bd",
    "sed_stl",
    "stl_vel",
)
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS)
_EXPECTED_TOKENS = len(_HEADER)


class SedimentResRow(BaseModel):
    """Reservoir sediment parameters for one named set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    sed_amt: float
    d50: float
    carbon: float
    bd: float
    sed_stl: float
    stl_vel: float


class SedimentRes(ParsedFile):
    """Contents of a ``sediment.res`` file."""

    rows: tuple[SedimentResRow, ...]

    def by_name(self, name: str) -> SedimentResRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_sediment_res(path: Path) -> SedimentRes:
    """Parse a ``sediment.res`` file into a :class:`SedimentRes` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[SedimentResRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return SedimentRes(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> SedimentResRow:
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
    return SedimentResRow(name=name, **float_values)
