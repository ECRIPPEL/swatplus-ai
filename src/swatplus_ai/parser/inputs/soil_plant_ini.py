"""Parser for ``soil_plant.ini`` — HRU soil / plant initial-condition sets.

One row per named initial-condition set referenced from
``hru-data.hru``'s ``soil_plant_init`` column. The row carries a
starting soil-water fraction (``sw_frac``, 0-1) and four nullable FK
columns pointing into chemistry databases: ``nutrients`` into
``nutrients.sol``, ``pest`` into pesticide initial state, ``path``
into pathogen initial state, ``hmet`` into heavy-metal initial state,
and ``salt`` into salt initial state.
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
    parse_nullable_str,
)
from swatplus_ai.parser.models import ParsedFile

_FK_FIELDS: tuple[str, ...] = ("nutrients", "pest", "path", "hmet", "salt")
_HEADER: tuple[str, ...] = ("name", "sw_frac", *_FK_FIELDS)
_EXPECTED_TOKENS = len(_HEADER)


class SoilPlantIniRow(BaseModel):
    """One soil/plant initial-condition set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    sw_frac: float
    nutrients: str | None
    pest: str | None
    path: str | None
    hmet: str | None
    salt: str | None


class SoilPlantIni(ParsedFile):
    """Contents of a ``soil_plant.ini`` file."""

    rows: tuple[SoilPlantIniRow, ...]

    def by_name(self, name: str) -> SoilPlantIniRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_soil_plant_ini(path: Path) -> SoilPlantIni:
    """Parse a ``soil_plant.ini`` file into a :class:`SoilPlantIni` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[SoilPlantIniRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return SoilPlantIni(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> SoilPlantIniRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    ln = line.line_no
    name = line.tokens[0]
    sw_frac = parse_float(line.tokens[1], path=path, line_no=ln, field="sw_frac")
    fk_values = {
        field: parse_nullable_str(line.tokens[i + 2]) for i, field in enumerate(_FK_FIELDS)
    }
    return SoilPlantIniRow(name=name, sw_frac=sw_frac, **fk_values)
