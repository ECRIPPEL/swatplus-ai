"""Parser for ``hru-data.hru`` — the master HRU definition table.

One row per HRU, with an integer id, a name, and references by name to the
HRU's topography, hydrology, soil, land-use/management, soil-plant init,
surface-storage, snow, and field parameter sets defined in other files.

This is the "join table" that wires everything together: a diagnostic rule
checking, say, "does HRU 42's hydrology.hyd entry look reasonable" starts
here, reads ``hydro="hyd00042"`` from the HRU row, and then looks that name
up in :class:`HydrologyHyd`. Unused slots appear as the literal ``null``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_tokens,
    parse_int,
    parse_nullable_str,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = (
    "id",
    "name",
    "topo",
    "hydro",
    "soil",
    "lu_mgt",
    "soil_plant_init",
    "surf_stor",
    "snow",
    "field",
)


class HruDataRow(BaseModel):
    """One row of ``hru-data.hru`` — a single HRU's master record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    topo: str | None
    hydro: str | None
    soil: str | None
    lu_mgt: str | None
    soil_plant_init: str | None
    surf_stor: str | None
    snow: str | None
    field: str | None


class HruData(ParsedFile):
    """Contents of ``hru-data.hru``: one row per HRU."""

    rows: tuple[HruDataRow, ...]

    def by_id(self, hru_id: int) -> HruDataRow | None:
        """Linear lookup by HRU id. O(n); cache if called in a hot loop."""
        for r in self.rows:
            if r.id == hru_id:
                return r
        return None

    def by_name(self, name: str) -> HruDataRow | None:
        for r in self.rows:
            if r.name == name:
                return r
        return None


def parse_hru_data(path: Path) -> HruData:
    """Parse a ``hru-data.hru`` file into a :class:`HruData` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[HruDataRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))

    return HruData(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> HruDataRow:
    if len(line.tokens) != len(_HEADER):
        raise ParseError(
            path,
            line.line_no,
            f"expected {len(_HEADER)} tokens, got {len(line.tokens)}",
        )
    id_tok, name, topo, hydro, soil, lu_mgt, spi, surf_stor, snow, field = line.tokens
    return HruDataRow(
        id=parse_int(id_tok, path=path, line_no=line.line_no, field="id"),
        name=name,
        topo=parse_nullable_str(topo),
        hydro=parse_nullable_str(hydro),
        soil=parse_nullable_str(soil),
        lu_mgt=parse_nullable_str(lu_mgt),
        soil_plant_init=parse_nullable_str(spi),
        surf_stor=parse_nullable_str(surf_stor),
        snow=parse_nullable_str(snow),
        field=parse_nullable_str(field),
    )
