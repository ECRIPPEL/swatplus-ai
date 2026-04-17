"""Parser for ``om_water.ini`` — organic-matter / water initial state sets.

One row per named initial state referenced from ``initial.aqu`` /
``initial.cha`` / ``initial.res`` via the ``org_min`` column, plus the
literal label ``no_init`` for "start empty". The 20-column row carries
name + 19 floats: flow, sediment, nitrogen and phosphorus species,
algae, NH3/NO2, CBOD, dissolved oxygen, sediment grain fractions
(sand/silt/clay/sag/lag/gravel), temperature, and an unspecified
constituent ``c``.
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
    "flo",
    "sed",
    "orgn",
    "sedp",
    "no3",
    "solp",
    "chl_a",
    "nh3",
    "no2",
    "cbn_bod",
    "dis_ox",
    "san",
    "sil",
    "cla",
    "sag",
    "lag",
    "grv",
    "tmp",
    "c",
)
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS)
_EXPECTED_TOKENS = len(_HEADER)


class OmWaterIniRow(BaseModel):
    """One organic-matter / water initial-state set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    flo: float
    sed: float
    orgn: float
    sedp: float
    no3: float
    solp: float
    chl_a: float
    nh3: float
    no2: float
    cbn_bod: float
    dis_ox: float
    san: float
    sil: float
    cla: float
    sag: float
    lag: float
    grv: float
    tmp: float
    c: float


class OmWaterIni(ParsedFile):
    """Contents of an ``om_water.ini`` file."""

    rows: tuple[OmWaterIniRow, ...]

    def by_name(self, name: str) -> OmWaterIniRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_om_water_ini(path: Path) -> OmWaterIni:
    """Parse an ``om_water.ini`` file into an :class:`OmWaterIni` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[OmWaterIniRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return OmWaterIni(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> OmWaterIniRow:
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
    return OmWaterIniRow(name=name, **float_values)
